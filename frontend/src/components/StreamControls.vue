<script setup lang="ts">
import { ref, computed, watch, watchEffect } from "vue";
import { useWebRTC } from "../composables/useWebRTC.ts";

const videoInput = ref<HTMLInputElement | null>(null);
const sourceType = ref<"video" | "camera">("camera");

const rtc = useWebRTC();

function triggerVideoInput() {
  videoInput.value?.click();
}

watch(sourceType, () => {
  rtc.sourceId.value = null;
});

const typeSource = computed(() => {
  if (sourceType.value === "video")
    return (rtc.sources.value?.videos ?? []).map((v) => ({ title: v, value: v }));
  return (rtc.sources.value?.cameras ?? []).map((i) => ({ title: `Camera ${i}`, value: i }));
});
</script>

<template>
  <div class="d-flex align-center gap-3">
    <v-radio-group v-model="sourceType" inline hide-details class="ma-4">
      <v-radio class="mr-3" label="Camera" value="camera" />
      <v-radio class="mr-3" label="Video" value="video" />
    </v-radio-group>

    <v-btn icon class="mr-2" @click="rtc.fetchSources" variant="text">
      <v-icon>mdi-refresh</v-icon>
    </v-btn>

    <v-select
      v-model="rtc.sourceId.value"
      :label="sourceType === 'video' ? 'Choose file' : 'Choose camera'"
      :items="typeSource"
      width="250px"
      density="compact"
      hide-details
      class="mr-8"
    />

    <v-checkbox
      v-model="rtc.yolo.value"
      label="AI detection"
      hide-details
      :disabled="rtc.connected.value"
    />

    <div v-if="sourceType === 'video'">
      <v-btn width="130" class="ml-3" @click="triggerVideoInput">Upload</v-btn>
      <input ref="videoInput" type="file" class="d-none" accept=".mp4" @change="rtc.uploadVideo" />
      <v-btn
        width="130"
        class="ml-3"
        :disabled="!rtc.sourceId.value"
        @click="rtc.confirmDelVideo.value = true"
        >Delete</v-btn
      >
    </div>

    <v-btn
      width="130"
      class="ml-3"
      :disabled="rtc.connected.value || rtc.sourceId.value == null"
      @click="rtc.connect(sourceType, rtc.sourceId.value)"
    >
      {{ sourceType === "camera" ? "Connect" : "Play" }}
    </v-btn>

    <v-btn width="130" class="ml-3" :disabled="!rtc.connected.value" @click="rtc.disconnect">
      {{ sourceType === "camera" ? "Disconnect" : "Stop" }}
    </v-btn>
  </div>

  <v-dialog v-model="rtc.confirmDelVideo.value" max-width="400">
    <v-card>
      <v-card-title>Delete video?</v-card-title>
      <v-card-text>Confirm deleting: {{ rtc.sourceId.value }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="rtc.confirmDelVideo.value = false">No</v-btn>
        <v-btn color="error" @click="rtc.deleteVideo">Yes</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar
    v-model="rtc.error.value"
    color="error"
    location="bottom"
    class="mb-5"
    :timeout="2000"
  >
    {{ rtc.errorMessage.value }}
  </v-snackbar>
</template>

<style scoped></style>
