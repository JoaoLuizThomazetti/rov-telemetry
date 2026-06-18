<script setup lang="ts">
import { ref, watch } from "vue";
import { useMcapReplay } from "../composables/useMcapReplay.ts";

const frameSrc = ref<string>("");
const mcap = useMcapReplay();

watch(() => mcap.currentTime.value, (time) => {
  if (!mcap.selectedFile.value) return;
  frameSrc.value = `/api/messages/${mcap.selectedFile.value}/frame?timestamp_us=${time}`;
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
