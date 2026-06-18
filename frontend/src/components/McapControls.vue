<script setup lang="ts">
import { ref } from "vue";
import { useMcapReplay } from "../composables/useMcapReplay.ts";

const props = defineProps<{
  mode: "live" | "replay";
}>();

const mcap = useMcapReplay();
const fileInput = ref<HTMLInputElement | null>(null);
const fileSelected = ref<boolean>(false);
const intervalId = ref<number | null>(null);

function triggerFileInput() {
  fileInput.value?.click();
}

const formatTime = (us: number): string => {
  if (us === 0) return "00:00:00";
  return new Date(us / 1000).toLocaleString();
};

const handleDeleteFile = () => {
  fileSelected.value = false;
  mcap.deleteFile();
};

const handleSelectMcap = () => {
  fileSelected.value = true;
  mcap.fetchFile();
};

const startPlayback = () => {
  if (intervalId.value) return;
  intervalId.value = setInterval(() => {
    mcap.currentTime.value += 100_000;
    console.log(`${mcap.currentTime.value}`)
    if (mcap.currentTime.value >= mcap.maxTime.value) {
      stopPlayback();
    }
  }, 100);
};

const stopPlayback = () => {
  if (intervalId.value) {
    clearInterval(intervalId.value);
    intervalId.value = null;
    console.log(`==> STOPPED`)
  }
};

const restartPlayback = () => {
  mcap.currentTime.value = mcap.minTime.value
};

</script>

<template>
  <v-divider class="mt-1" />
  <div style="border-top: 1px solid #2f2f2f; padding: 12px">
    <div class="d-flex align-start gap-4 ma-2 mb-3">
      <div class="d-flex flex-column flex-grow-1 gap-2">
        <v-select
          width="350px"
          class="mr-2 mb-1"
          v-model="mcap.selectedFile.value"
          label="Choose .mcap file"
          :items="mcap.files.value"
          hide-details
          @update:modelValue="handleSelectMcap"
        />
        <div class="d-flex justify-space-between ma-2 mr-8">
          <v-text-field
            style="max-width: 150px;"
            v-model="mcap.limit.value"
            type="number"
            label="Max messages"
            hide-details
          />
          <div class="mt-2">
            <v-btn 
              icon="mdi-play"
              :disabled="!mcap.selectedFile.value || intervalId != null"
              class="mr-5" @click="startPlayback"
            />
            <v-btn
              icon="mdi-pause"
              :disabled="!mcap.selectedFile.value || intervalId == null"
              class="mr-5" @click="stopPlayback"
            />
            <v-btn
              icon="mdi-restart"
              :disabled="!mcap.selectedFile.value || mcap.currentTime.value === mcap.minTime.value"
              @click="restartPlayback"
            />
          </div>
        </div>
      </div>

      <div class="d-flex flex-column gap-2 mt-2">
        <v-btn
          class="ma-1 mb-4"
          width="130"
          @click="mcap.downloadFile"
          :disabled="!mcap.selectedFile.value"
          >Download</v-btn
        >
        <v-btn
          class="ma-1"
          width="130"
          @click="mcap.confirmDelete.value = true"
          :disabled="!mcap.selectedFile.value"
          >Delete</v-btn
        >
      </div>
    </div>

    <v-card elevation="2" class="mt-1" v-if="fileSelected">
      <div class="d-flex align-center gap-2 ma-2 mb-0 justify-space-between">
        <p class="text-subtitle-1">{{ formatTime(mcap.minTime.value) }}</p>
        <p class="text-h6" style="color: #1D9E75">{{ formatTime(mcap.currentTime.value).split(", ")[1] }}</p>
        <p class="text-subtitle-1">{{ formatTime(mcap.maxTime.value) }}</p>
      </div>
      <v-slider
        class="ml-5 mr-5"
        v-model="mcap.currentTime.value"
        :min="mcap.minTime.value"
        :max="mcap.maxTime.value"
      />
    </v-card>
  </div>

  <v-dialog v-model="mcap.confirmDelete.value" max-width="400">
    <v-card>
      <v-card-title>Delete file?</v-card-title>
      <v-card-text>Confirm deleting: {{ mcap.selectedFile.value }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="mcap.confirmDelete.value = false">No</v-btn>
        <v-btn color="error" @click="handleDeleteFile">Yes</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar
    v-model="mcap.error.value"
    color="error"
    location="bottom"
    class="mb-5"
    :timeout="2000"
  >
    {{ mcap.errorMessage.value }}
  </v-snackbar>
</template>

<style scoped></style>
