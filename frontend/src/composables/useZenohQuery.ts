import { ref, onMounted, onUnmounted } from "vue";


export function useZenohQuery<T>(topic: string, intervalMs = 5000) {
  const data = ref<T | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;

  const fetch_ = async () => {
    try {
      const res = await fetch(`/api/topic?topic=${topic}`);
      if (res.ok) {
        data.value = await res.json() as T;
      }
    } catch (e) { console.error("useZenohQuery error:", e); }
    timer = setTimeout(fetch_, intervalMs);
  };

  onMounted(fetch_);
  onUnmounted(() => { if (timer) clearTimeout(timer); });

  return { data };
}
