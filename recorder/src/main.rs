use std::fs::File;
use chrono::Local;
use std::sync::Arc;
use serde::{Serialize, Deserialize};
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use std::io::BufWriter;
use std::collections::HashMap;
use std::collections::BTreeMap;
use mcap::records::MessageHeader;
use utoipa::{OpenApi, ToSchema};
use utoipa_swagger_ui::SwaggerUi;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::signal::unix::{signal, SignalKind};
use tower_http::trace::TraceLayer;
use axum::{
    Router,
    Json,
    extract::State,
    http::StatusCode,
    routing::{get, post}
};


#[derive(OpenApi)]
#[openapi(
    paths(start_writer, stop_writer, get_status),
    components(schemas(RecorderStatus)),
    info(title = "ROV Recorder API", version = "1.0.0")
)]
struct ApiDoc;


#[derive(Serialize, Deserialize, Clone, ToSchema)]
struct RecorderStatus {
    active: bool,
    filename: Option<String>,
    started_at: Option<u64>,
}


enum WriterMsg {
    Start(String),
    Stop(tokio::sync::oneshot::Sender<()>),
    Sample { topic: String, payload: Vec<u8>, timestamp_ns: u64 },
}


#[derive(Clone)]
struct AppState {
    tx: mpsc::Sender<WriterMsg>,
    status: Arc<Mutex<RecorderStatus>>,
}


fn now_ns() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos() as u64
}


async fn zenoh_task(tx: mpsc::Sender<WriterMsg>, session: zenoh::Session) {
    tracing::info!("Starting zenoh listener"); 
    let subscriber = session.declare_subscriber("rov/**").await.unwrap();
    loop {
        match subscriber.recv_async().await {
            Ok(sample) => {
                let data = WriterMsg::Sample {
                    topic: sample.key_expr().to_string(),
                    payload: sample.payload().to_bytes().to_vec(),
                    timestamp_ns: now_ns(),
                };
                if tx.send(data).await.is_err() { break; }
            }
            Err(e) => {
                tracing::error!("Error in zenoh subscriber: {e}"); 
                break
            },
        }
    }
}


async fn writer_task(mut rx: mpsc::Receiver<WriterMsg>) {
    tracing::info!("Starting mcap writer"); 
    let mut writer: Option<mcap::Writer<BufWriter<File>>> = None;
    let mut channels: HashMap<String, u16> = HashMap::new();
    let mut sequence: u32 = 0;
    let metadata = BTreeMap::new();
    while let Some(value) = rx.recv().await {
        match value {
            WriterMsg::Start(s) => {
                tracing::info!("Opening MCAP file: {s}");
                match File::create(&s) {
                    Ok(file) => { writer = Some(mcap::Writer::new(BufWriter::new(file)).unwrap()); }
                    Err(e) => { tracing::error!("Failed to create MCAP file {s}: {e}"); }
                };
            },
            WriterMsg::Stop(done_tx) => {
                tracing::info!("Closing MCAP file");
                if let Some(mut w) = writer.take() {
                    w.finish().unwrap();
                }
                channels.clear();
                sequence = 0;
                let _ = done_tx.send(());
            },
            WriterMsg::Sample { topic, payload, timestamp_ns } => {
                if let Some(ref mut w) = writer {
                    let channel_id = if let Some(&id) = channels.get(&topic) {
                        id
                    } else {
                        let is_video = topic.starts_with("rov/video/");
                        let (schema_name, schema_encoding, schema_data, msg_encoding) = if is_video {
                            ("CompressedImage", "", b"".as_slice(), "jpeg")
                        } else {
                            ("Telemetry", "jsonschema", b"{}".as_slice(), "json")
                        };
                        let schema_id = w.add_schema(schema_name, schema_encoding, schema_data).unwrap();
                        let id = w.add_channel(schema_id, &topic, msg_encoding, &metadata).unwrap();
                        channels.insert(topic.clone(), id);
                        id
                    };
                    w.write_to_known_channel(&MessageHeader {
                        channel_id,
                        sequence,
                        log_time: timestamp_ns,
                        publish_time: now_ns()
                    }, &payload).unwrap();
                    sequence = sequence.wrapping_add(1)
                }
            }
        }
    }
}


#[utoipa::path(
    post,
    path = "/start",
    responses(
        (status = 200, description = "Recording started", body = RecorderStatus),
        (status = 500, description = "Internal server error"),
    ),
    tag = "RECORDER"
)]
async fn start_writer(State(state): State<AppState>) -> Result<(StatusCode, Json<RecorderStatus>), StatusCode> {
    tracing::info!("Starting recording");
    let mcap_dir = std::env::var("MCAP_DIR").unwrap_or_else(|_| ".".to_string());
    let date = Local::now().format("%Y-%m-%dT%H-%M-%S").to_string();
    let filename = format!("{}/recording_{}.mcap", mcap_dir, date);
    if state.tx.send(WriterMsg::Start(filename.clone())).await.is_err() {
        return Err(StatusCode::INTERNAL_SERVER_ERROR)
    }
    let mut status = state.status.lock().await;
    status.active = true;
    status.filename = Some(filename.clone());
    status.started_at = Some(now_ns());
    Ok((StatusCode::OK, Json(status.clone())))
}


#[utoipa::path(
    post,
    path = "/stop",
    responses(
        (status = 200, description = "Recording stopped", body = RecorderStatus),
        (status = 500, description = "Internal server error"),
    ),
    tag = "RECORDER"
)]
async fn stop_writer(State(state): State<AppState>) -> Result<(StatusCode, Json<RecorderStatus>), StatusCode> {
    tracing::info!("Stopping recording");
    let (done_tx, done_rx) = tokio::sync::oneshot::channel();
    if state.tx.send(WriterMsg::Stop(done_tx)).await.is_err() {
        return Err(StatusCode::INTERNAL_SERVER_ERROR)
    }
    done_rx.await.ok();
    let mut status = state.status.lock().await;
    status.active = false;
    status.filename = None;
    status.started_at = None;
    Ok((StatusCode::OK, Json(status.clone())))
}


#[utoipa::path(
    get,
    path = "/status",
    responses(
        (status = 200, description = "Return recorder status", body = RecorderStatus),
    ),
    tag = "RECORDER"
)]
async fn get_status(State(state): State<AppState>) -> Json<RecorderStatus> {
    let status = state.status.lock().await;
    Json(status.clone())
}


#[tokio::main]
async fn main() -> anyhow::Result<()> {

    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
    tracing::info!("Starting Recorder");

    let connect = std::env::var("ZENOH_CONNECT")
        .unwrap_or_else(|_| "tcp/localhost:7447".to_string());
    let config = zenoh::Config::from_json5(&format!(
        r#"{{"mode":"client","connect":{{"endpoints":["{connect}"]}}}}"#
    )).map_err(|e| anyhow::anyhow!("{e}"))?;
    let session = zenoh::open(config).await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let (tx, rx) = mpsc::channel::<WriterMsg>(32);

    let status = Arc::new(Mutex::new(RecorderStatus {
            active: false,
            filename: None,
            started_at: None,
        }));

    let zenoh_handle = tokio::spawn(zenoh_task(tx.clone(), session));
    let writer_handle = tokio::spawn(writer_task(rx));
    let close_tx = tx.clone();

    let state = AppState { tx, status };
    let axum_handle = tokio::spawn(async move {
        tracing::info!("Starting API");
        let app = Router::new()
            .merge(SwaggerUi::new("/swagger-ui")
            .url("/recorder/api-docs/openapi.json", ApiDoc::openapi()))
            .route("/start", post(start_writer))
            .route("/stop", post(stop_writer))
            .route("/status", get(get_status))
            .layer(TraceLayer::new_for_http())
            .with_state(state);
        let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });

    tracing::info!("Starting Recorder main loop"); 
    let mut sigterm = signal(SignalKind::terminate())?;
    tokio::select! {
        _ = zenoh_handle => {},
        _ = writer_handle => {},
        _ = axum_handle => {},
        _ = tokio::signal::ctrl_c() => {},
        _ = sigterm.recv() => {},
    }

    tracing::info!("Flushing writer");
    let (done_tx, done_rx) = tokio::sync::oneshot::channel();
    let _ = close_tx.send(WriterMsg::Stop(done_tx)).await;
    let _ = done_rx.await;

    tracing::info!("Stopping Recorder");
    Ok(())
}


#[cfg(test)]
mod tests {
    use tower::ServiceExt;
    use super::*;
    use axum::{
        http,
        body::{Body, to_bytes},
        http::Request,
    };

    fn build_test_app() -> Router {
        let (tx, mut rx) = mpsc::channel::<WriterMsg>(10);
        tokio::spawn(async move { while rx.recv().await.is_some() {} });
        let status = Arc::new(Mutex::new(RecorderStatus {
            active: false,
            filename: None,
            started_at: None,
        }));
        Router::new()
            .route("/start", post(start_writer))
            .route("/stop", post(stop_writer))
            .route("/status", get(get_status))
            .with_state(AppState { tx, status })
    }

    async fn deserialize_body(response: http::Response<axum::body::Body>) -> Option<RecorderStatus> {
        let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
        serde_json::from_slice(&body).unwrap()
    }

    #[tokio::test]
    async fn test_get_status() {
        let app = build_test_app();
        let response = app
            .oneshot(Request::get("/status").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let status: RecorderStatus = deserialize_body(response).await.unwrap();
        assert!(!status.active);
    }

    #[tokio::test]
    async fn test_get_status_started() {
        let app = build_test_app();
        let _ = app.clone()
            .oneshot(Request::post("/start").body(Body::empty()).unwrap())
            .await
            .unwrap();
        let response = app
            .oneshot(Request::get("/status").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let status: RecorderStatus = deserialize_body(response).await.unwrap();
        assert!(status.active);
    }

    #[tokio::test]
    async fn test_post_start() {
        let app = build_test_app();
        let response = app
            .oneshot(Request::post("/start").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let status: RecorderStatus = deserialize_body(response).await.unwrap();
        assert!(status.active);
        assert!(status.filename.is_some());
    }

    #[tokio::test]
    async fn test_post_stop() {
        let app = build_test_app();
        let _ = app.clone()
            .oneshot(Request::post("/start").body(Body::empty()).unwrap())
            .await
            .unwrap();
        let response = app
            .oneshot(Request::post("/stop").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
        let status: RecorderStatus = deserialize_body(response).await.unwrap();
        assert!(!status.active);
    }
}