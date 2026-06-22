import { ref, onMounted, onUnmounted } from "vue";

const connected = ref<boolean>(false);
const systemData = ref<SystemData | null>(null);
const containerData = ref<ContainerData[]>([]);

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let initialized = false;
let refCount = 0;

export interface SystemData {
    cpu_percent: number
    mem_percent: number
    disk_percent: number
};

export interface ContainerData {
    name: string
    status: string
    uptime_s: number
};

interface TelemetryMessage {
  system: SystemData;
  containers: ContainerData[];
};

export function useTelemetry(url: string) {
  const connect = () => {
    ws = new WebSocket(url);

    ws.onopen = () => (connected.value = true);

    ws.onclose = () => {
      connected.value = false;
      if (initialized) reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error("ws error:", error);
      connected.value = false;
    };

    ws.onmessage = (event) => {
      const msg: TelemetryMessage = JSON.parse(event.data);
      systemData.value = msg.system;
      containerData.value = msg.containers;
    };
  };

  onMounted(() => {
    if (!initialized) {
      initialized = true;
      connect();
    }
    refCount++;
  });

  onUnmounted(() => {
    refCount--;
    if (refCount === 0) {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      initialized = false;
    }
  });

  return { connected, systemData, containerData };
}
