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
  <div style="border-top: 1px solid #2f2f2f; padding: 12px">
    <div class="d-flex justify-space-evenly align-center mt-1">
      <v-btn width="130" :disabled="active || !connected" @click="startRecorder">
        {{ recording ? "Recording" : "Record" }}
      </v-btn>
      <v-btn width="130" :disabled="!active" @click="handleStopRecorder">Stop</v-btn>
    </div>

    <v-card elevation="2" class="pa-3 mt-5 ml-10 mr-10">
      <div class="d-flex justify-center align-center">
        <span class="text-h6 mr-3">{{ elapsedFormatted }}</span>
        <v-icon :color="recording ? 'red' : 'grey'" size="20">mdi-circle</v-icon>
      </div>
    </v-card>
  </div>

  <v-snackbar v-model="error" color="error" location="bottom" class="mb-5" :timeout="3000">
    {{ errorMessage }}
  </v-snackbar>
</template>

<style scoped></style>
