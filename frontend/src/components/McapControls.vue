<script setup lang="ts">
import { ref } from "vue";
import { useMcapReplay } from "../composables/useMcapReplay.ts";

const props = defineProps<{
  mode: "live" | "replay";
}>();

const fileInput = ref<HTMLInputElement | null>(null);
const mcap = useMcapReplay();
const fileSelected = ref<boolean>(false)

function triggerFileInput() {
  fileInput.value?.click();
}

const formatTime = (us: number): string => {
  if (us === 0) return "00:00:00";
  return new Date(us / 1000).toLocaleString();
};

const handleDeleteFile = () => {
  fileSelected.value = false
  mcap.deleteFile()
}

const handleSelectMcap = () => {
  fileSelected.value = true
  mcap.fetchFile()
}

</script>

<template>
  <div style="border-top: 1px solid #2f2f2f; padding: 12px">
    <div class="d-flex justify-space-evenly align-center mt-1 mb-5">
      <!-- <v-btn width="130" @click="triggerFileInput">upload</v-btn> -->
      <!-- <input ref="fileInput" type="file" class="d-none" accept=".mcap" @change="mcap.uploadFile" /> -->
      <v-btn width="130" @click="mcap.downloadFile" :disabled="!mcap.selectedFile.value"
        >download</v-btn
      >
      <v-btn width="130" @click="mcap.confirmDelete.value = true" :disabled="!mcap.selectedFile.value"
        >delete</v-btn
      >
    </div>

    <div class="d-flex align-center gap-2 ma-2">
      <v-select
        v-model="mcap.selectedFile.value"
        label="Choose .mcap file"
        :items="mcap.files.value"
        style="width: 260px"
        class="mr-3"
        @update:modelValue="handleSelectMcap"
      />
      <v-text-field
        width="120"
        v-model="mcap.limit.value"
        type="number"
        label="Max messages"
        :rules="[(v) => v >= 1 || 'Min 1', (v) => v <= 10000 || 'Max 10000']"
      />
    </div>
  </div>
  <!-- <div class="d-flex align-center gap-2 ma-2 justify-space-between">
    <v-btn width="160" class="ml-8" @click="mcap.fetchFiles">Refresh list</v-btn>
    <v-btn width="160" class="mr-8" :disabled="!mcap.selectedFile.value" @click="mcap.fetchFile"
      >Read .mcap file</v-btn
    >
  </div> -->

  <v-card elevation="2" class="pa-2" v-if="fileSelected">
    <div class="d-flex align-center gap-2 ma-2 justify-space-between">
      <p class="text-subtitle-1">{{ formatTime(mcap.minTime.value) }}</p>
      <v-icon>mdi-arrow-right</v-icon>
      <p class="text-subtitle-1">{{ formatTime(mcap.maxTime.value) }}</p>
    </div>
    <v-slider
      class="ml-5 mr-5"
      v-model="mcap.currentTime.value"
      :min="mcap.minTime.value"
      :max="mcap.maxTime.value"
    />
    <div class="d-flex justify-center mb-5">
      <p class="text-h6">{{ formatTime(mcap.currentTime.value) }}</p>
    </div>
  </v-card>

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
