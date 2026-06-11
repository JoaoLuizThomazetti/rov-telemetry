<script setup lang="ts">
import { useRecorderControl } from "../composables/useRecorderControl.ts";
import { useMcapReplay } from "../composables/useMcapReplay.ts";

const props = defineProps<{
  connected: boolean;
}>();

const { active, recording, elapsedFormatted, error, errorMessage, startRecorder, stopRecorder } =
  useRecorderControl();
const { fetchFiles } = useMcapReplay();

const handleStopRecorder = async () => {
  await stopRecorder();
  await fetchFiles();
};
</script>

<template>
  <div style="padding: 12px">
    <v-divider />
    <div class="d-flex align-center mt-2 mb-1 ml-2 mr-2 gap-2">
      <v-card elevation="2" class="flex-grow-1 pa-5 ml-15 mr-15 d-flex justify-center align-center">
        <span class="text-h6">{{ elapsedFormatted }}</span>
        <v-icon :color="recording ? 'red' : 'grey'" size="20" class="ml-3">mdi-circle</v-icon>
      </v-card>

      <div class="d-flex flex-column gap-2">
        <v-btn class="ma-1" width="130" :disabled="active || !connected" @click="startRecorder">
          {{ recording ? "Recording" : "Record" }}
        </v-btn>
        <v-btn class="ma-1" width="130" :disabled="!active" @click="handleStopRecorder">Stop</v-btn>
      </div>
    </div>
  </div>
  <v-snackbar v-model="error" color="error" location="bottom" class="mb-5" :timeout="3000">
    {{ errorMessage }}
  </v-snackbar>
</template>

<style scoped></style>
