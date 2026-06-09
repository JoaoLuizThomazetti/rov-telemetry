import { ref, onMounted } from "vue";

const source = ref<"simulation" | "serial">("simulation");
const selectedPort = ref<string | null>(null);
const ports = ref<string[]>([]);
const running = ref(false);

export function useSimulator() {
  const loading = ref(false);
  const error = ref(false);
  const errorMessage = ref("");

  function showError(msg: string) {
    errorMessage.value = msg;
    error.value = true;
  }

  const fetchStatus = async () => {
    try {
      const res = await fetch("/simulator/status");
      if (!res.ok) return;
      const data = await res.json();
      running.value = data.running;
      if (data.source) source.value = data.source;
      if (data.port) selectedPort.value = data.port;
    } catch {}
  };

  const fetchPorts = async () => {
    loading.value = true;
    try {
      const res = await fetch("/simulator/ports");
      if (!res.ok) throw new Error("Failed to fetch ports");
      ports.value = await res.json();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : "Failed to fetch ports");
    } finally {
      loading.value = false;
    }
  };

  const startSimulator = async () => {
    loading.value = true;
    try {
      const params = new URLSearchParams({ source: source.value });
      if (source.value === "serial" && selectedPort.value) {
        params.append("port", selectedPort.value);
      }
      const res = await fetch(`/simulator/start?${params}`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to start");
      const data = await res.json();
      running.value = data.running;
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : "Failed to start simulator");
    } finally {
      loading.value = false;
    }
  };

  const stopSimulator = async () => {
    loading.value = true;
    try {
      const res = await fetch(`/simulator/stop?source=${source.value}`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to stop");
      const data = await res.json();
      running.value = data.running;
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : "Failed to stop simulator");
    } finally {
      loading.value = false;
    }
  };

  onMounted(fetchStatus);

  return {
    source,
    selectedPort,
    ports,
    running,
    loading,
    error,
    errorMessage,
    fetchPorts,
    startSimulator,
    stopSimulator,
  };
}
