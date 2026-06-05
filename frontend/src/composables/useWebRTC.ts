import { ref, onMounted, onUnmounted } from "vue";

interface VideoSources {
  videos: string[];
  cameras: number[];
}

const connected = ref<boolean>(false);
const stream = ref<MediaStream | null>(null);
const sources = ref<VideoSources>();
const sourceId = ref<string | number | null>(null);

let peer_conn: RTCPeerConnection | null = null;
let initialized = false;

export function useWebRTC() {
  const error = ref<boolean>(false);
  const errorMessage = ref<string>("");
  const confirmDelVideo = ref<boolean>(false);

  const connect = async (sourceType: "video" | "camera", sourceId: string | number | null) => {
    const iceServers: RTCIceServer[] = [{ urls: "stun:stun.l.google.com:19302" }];
    if (import.meta.env.VITE_TURN_URL) {
      iceServers.push({
        urls: import.meta.env.VITE_TURN_URL,
        username: import.meta.env.VITE_TURN_USER,
        credential: import.meta.env.VITE_TURN_PASS,
      });
    }
    peer_conn = new RTCPeerConnection({ iceServers });
    peer_conn.onconnectionstatechange = () => {
      if (peer_conn?.connectionState === "connected") {
        connected.value = true;
      }
      if (
        peer_conn?.connectionState === "failed" ||
        peer_conn?.connectionState === "disconnected"
      ) {
        connected.value = false;
        stream.value = null;
        peer_conn = null;
      }
    };
    peer_conn.addTransceiver("video", { direction: "recvonly" });
    peer_conn.ontrack = (e) => {
      stream.value = e.streams?.[0] ?? null;
      connected.value = true;
    };
    const offer = await peer_conn.createOffer();
    await peer_conn.setLocalDescription(offer);
    const payload = {
      sdp: offer.sdp,
      type: offer.type,
      source_type: sourceType,
      source_id: sourceId,
    };
    const response = await fetch("/vision/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      errorMessage.value = await response.json().then((r: any) => r.detail);
      error.value = true;
      peer_conn?.close();
      peer_conn = null;
      return;
    }
    const answer = await response.json();
    await peer_conn.setRemoteDescription(new RTCSessionDescription(answer));
  };

  const disconnect = async () => {
    peer_conn?.close();
    peer_conn = null;
    stream.value = null;
    connected.value = false;
  };

  const fetchSources = async () => {
    const response = await fetch("/vision/sources");
    if (!response.ok) {
      errorMessage.value = await response.json().then((r: any) => r.detail);
      error.value = true;
      return;
    }
    sources.value = await response.json();
  };

  const uploadVideo = async (event: Event) => {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch("/vision/videos", {
        method: "POST",
        body: form,
      });
      if (!response.ok) throw new Error(await response.json().then((r) => r.detail));
      await fetchSources();
    } catch (e) {
      error.value = true;
      errorMessage.value = e instanceof Error ? e.message : String(e);
    } finally {
      input.value = "";
    }
  };

  const deleteVideo = async () => {
    if (!sourceId.value) return;
    const response = await fetch(`/vision/videos/${sourceId.value}`, {
      method: "DELETE",
    });
    confirmDelVideo.value = false;
    if (!response.ok) {
      errorMessage.value = await response.json().then((r) => r.detail);
      error.value = true;
      return;
    }
    sourceId.value = null;
    await fetchSources();
  };

  onMounted(async () => {
    if (!initialized) {
      initialized = true;
      await fetchSources();
    }
  });

  onUnmounted(() => {
    peer_conn?.close();
    peer_conn = null;
    connected.value = false;
    stream.value = null;
    initialized = false;
  });

  return {
    stream,
    connected,
    sources,
    sourceId,
    error,
    errorMessage,
    confirmDelVideo,
    connect,
    disconnect,
    fetchSources,
    uploadVideo,
    deleteVideo,
  };
}
