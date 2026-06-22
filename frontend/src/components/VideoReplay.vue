<script setup lang="ts">
import { ref, watch } from "vue";
import { useMcapReplay } from "../composables/useMcapReplay.ts";

const frameSrc = ref<string>("");
const mcap = useMcapReplay();
let abortController: AbortController | null = null;

watch(() => mcap.currentTime.value, (time) => {
    if (!mcap.selectedFile.value) return;
    abortController?.abort();
    abortController = new AbortController();

    fetch(`/api/messages/${mcap.selectedFile.value}/frame?timestamp_us=${time}`, {
        signal: abortController.signal
    })
    .then(r => { if (!r.ok) throw new Error(); return r.blob(); })
    .then(blob => {
        if (frameSrc.value) URL.revokeObjectURL(frameSrc.value);
        frameSrc.value = URL.createObjectURL(blob);
    })
    .catch(() => {});
});


</script>

<template>
    <v-img v-if="frameSrc"
        :src="frameSrc"
        style="width: 100%; height: 100%; display: block; object-fit: contain"
    />
    <v-img v-else
        src="img_plc.png"
        style="max-width: 150px"
        class="mx-auto" 
    />
</template>

<style scoped></style>
