import { ref, onMounted, onUnmounted } from "vue";

const heartbeat = ref<Heartbeat | null>(null);
const attitude = ref<Attitude | null>(null);
const position = ref<GlobalPosition | null>(null);
const sysStatus = ref<SysStatus | null>(null);
const vfrHud = ref<VfrHud | null>(null);
const pressure = ref<ScaledPressure2 | null>(null);
const battery = ref<BatteryStatus | null>(null);
const connected = ref<boolean>(false);

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let initialized = false;
let refCount = 0;

interface TelemetryMessage {
  topic: string;
  data: unknown;
}

export interface Heartbeat {
  system_id: number;
  component_id: number;
  mav_type: number;
  autopilot: number;
  base_mode: number;
  custom_mode: number;
  system_status: number;
  timestamp_ms: number;
}

export interface Attitude {
  roll: number;
  pitch: number;
  yaw: number;
  rollspeed: number;
  pitchspeed: number;
  yawspeed: number;
  timestamp_ms: number;
}

export interface GlobalPosition {
  lat: number;
  lon: number;
  alt: number;
  relative_alt: number;
  vx: number;
  vy: number;
  vz: number;
  hdg: number;
  timestamp_ms: number;
}

export interface SysStatus {
  sensors_present: number;
  sensors_enabled: number;
  sensors_health: number;
  load: number;
  voltage_battery: number;
  current_battery: number;
  battery_remaining: number;
  drop_rate_comm: number;
  errors_comm: number;
  timestamp_ms: number;
}

export interface VfrHud {
  airspeed: number;
  groundspeed: number;
  heading: number;
  throttle: number;
  alt: number;
  climb: number;
  timestamp_ms: number;
}

export interface ScaledPressure2 {
  press_abs: number;
  press_diff: number;
  temperature: number;
  timestamp_ms: number;
}

export interface BatteryStatus {
  id: number;
  battery_function: number;
  battery_type: number;
  temperature: number;
  voltages: number[];
  current_battery: number;
  current_consumed: number;
  energy_consumed: number;
  battery_remaining: number;
  charge_state: number;
  timestamp_ms: number;
}

export function useWebSocket(url: string) {
  const connect = () => {
    ws = new WebSocket(url);

    ws.onopen = () => (connected.value = true);
    ws.onclose = () => {
      connected.value = false;
      reconnectTimer = setTimeout(connect, 3000);
    };
    ws.onerror = (error) => {
      console.error("ws error:", error);
      connected.value = false;
    };

    ws.onmessage = (event) => {
      const msg: TelemetryMessage = JSON.parse(event.data);
      switch (msg.topic) {
        case "rov/heartbeat":
          heartbeat.value = msg.data as Heartbeat;
          break;
        case "rov/attitude":
          attitude.value = msg.data as Attitude;
          break;
        case "rov/global_position":
          position.value = msg.data as GlobalPosition;
          break;
        case "rov/sys_status":
          sysStatus.value = msg.data as SysStatus;
          break;
        case "rov/vfr_hud":
          vfrHud.value = msg.data as VfrHud;
          break;
        case "rov/scaled_pressure2":
          pressure.value = msg.data as ScaledPressure2;
          break;
        case "rov/battery_status":
          battery.value = msg.data as BatteryStatus;
          break;
      }
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

  return { heartbeat, attitude, position, sysStatus, vfrHud, pressure, battery, connected };
}
