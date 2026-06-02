use std::fs::File;
use chrono::Local;
use std::sync::Arc;
use serde::Serialize;
use tokio::sync::mpsc;
use tokio::sync::Mutex;
use std::io::BufWriter;
use axum::extract::State;
use std::collections::HashMap;
use std::collections::BTreeMap;
use mcap::records::MessageHeader;
use utoipa::{OpenApi, ToSchema};
use utoipa_swagger_ui::SwaggerUi;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::signal::unix::{signal, SignalKind};
use axum::{
    Router,
    Json,
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


#[derive(Serialize, Clone, ToSchema)]
struct RecorderStatus {
    active: bool,
    filename: Option<String>,
    started_at: Option<u64>,
}


enum WriterMsg {
    Start(String),
    Stop,
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
            Err(_) => break,
        }
    }
}


async fn writer_task(mut rx: mpsc::Receiver<WriterMsg>, status: Arc<Mutex<RecorderStatus>>) {
    let mut writer: Option<mcap::Writer<BufWriter<File>>> = None;
    let mut channels: HashMap<String, u16> = HashMap::new();
    let mut sequence: u32 = 0;
    let metadata = BTreeMap::new();
    while let Some(value) = rx.recv().await {
        match value {
            WriterMsg::Start(s) => {
                let file = File::create(&s).unwrap();
                writer = Some(mcap::Writer::new(BufWriter::new(file)).unwrap());
            },
            WriterMsg::Stop => {
                if let Some(mut w) = writer.take() {
                    w.finish().unwrap();
                }
                channels.clear();
                sequence = 0;
                let mut s = status.lock().await;
                s.active = false;
                s.filename = None;
                s.started_at = None;
            },
            WriterMsg::Sample { topic, payload, timestamp_ns } => {
                if let Some(ref mut w) = writer {
                    let channel_id = if let Some(&id) = channels.get(&topic) {
                        id
                    } else {
                        let schema_name = topic.split('/').last().unwrap_or(&topic);
                        let schema_id = w.add_schema(schema_name, "jsonschema", b"{}").unwrap();
                        let id = w.add_channel(schema_id, &topic, "json", &metadata).unwrap();
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
    if state.tx.send(WriterMsg::Stop).await.is_err() {
        return Err(StatusCode::INTERNAL_SERVER_ERROR)
    }
    let status = state.status.lock().await;
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
    let writer_handle = tokio::spawn(writer_task(rx, status.clone()));
    let state = AppState { tx, status };
    let axum_handle = tokio::spawn(async move {
                let app = Router::new()
                    .merge(SwaggerUi::new("/swagger-ui")
                    .url("/recorder/api-docs/openapi.json", ApiDoc::openapi()))
                    .route("/start", post(start_writer))
                    .route("/stop", post(stop_writer))
                    .route("/status", get(get_status))
                    .with_state(state);
                let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
                axum::serve(listener, app).await.unwrap();
            });
    let mut sigterm = signal(SignalKind::terminate())?;
    tokio::select! {
        _ = zenoh_handle => {},
        _ = writer_handle => {},
        _ = axum_handle => {},
        _ = sigterm.recv() => {},
    }
    Ok(())
}
