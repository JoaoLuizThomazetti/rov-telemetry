import { ref, onMounted, watch, computed } from "vue";

const active = ref<boolean>(false);
const filename = ref<string | null>();
const started_at = ref<number | null>();
const recording = ref<boolean>(false);
const elapsed = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

export function useRecorderControl() {
  const error = ref<boolean>(false);
  const errorMessage = ref<string>("");

  const fetchStatus = async () => {
    const response = await fetch("/recorder/status");
    if (!response.ok) {
      errorMessage.value = await response.json().then((r) => r.detail);
      error.value = true;
      return;
    }
    let status = await response.json();
    active.value = status.active;
    filename.value = status.filename.replace("./", "");
    started_at.value = status.started_at;
  };

  const startRecorder = async () => {
    const response = await fetch("/recorder/start", { method: "POST" });
    if (!response.ok) {
      errorMessage.value = await response.json().then((r) => r.detail);
      error.value = true;
      return;
    }
    recording.value = true;
    await fetchStatus();
  };

  const stopRecorder = async () => {
    const response = await fetch("/recorder/stop", { method: "POST" });
    if (!response.ok) {
      errorMessage.value = await response.json().then((r) => r.detail);
      error.value = true;
      return;
    }
    recording.value = false;
    await fetchStatus();
  };

  watch(active, (val) => {
    if (val && started_at.value) {
      timer = setInterval(() => {
        elapsed.value = Math.floor((Date.now() - started_at.value! / 1_000_000) / 1000);
      }, 1000);
    } else {
      if (timer) clearInterval(timer);
      elapsed.value = 0;
    }
  });

  const elapsedFormatted = computed(() => {
    const h = Math.floor(elapsed.value / 3600);
    const m = Math.floor((elapsed.value % 3600) / 60);
    const s = elapsed.value % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  });

  onMounted(async () => {
    await fetchStatus();
  });

  return {
    active,
    filename,
    recording,
    elapsedFormatted,
    started_at,
    error,
    errorMessage,
    startRecorder,
    stopRecorder,
  };
}
