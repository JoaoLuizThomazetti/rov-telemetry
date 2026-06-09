<script setup lang="ts">
import { watch } from "vue";
import { useSimulator } from "../composables/useSimulator.ts";

const {
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
} = useSimulator();

watch(source, () => {
  selectedPort.value = null;
  if (source.value === "serial") fetchPorts();
});
</script>

<template>
  <div style="border-top: 1px solid #2f2f2f; padding: 12px">
    <div class="d-flex align-center justify-space-between mb-3 ml-2 mr-2">
      <span class="text-h6">MAVLink Source</span>
      <div class="d-flex align-center">
        <v-icon :color="running ? 'green' : 'grey'" size="15" class="mr-1">mdi-circle</v-icon>
        <span class="text-h6">{{ running ? "Transmitting" : "Idle" }}</span>
      </div>
    </div>

<div class="d-flex align-center mb-3 ml-2 mr-2">
  <v-radio-group v-model="source" hide-details class="mr-4">
    <v-radio label="Simulation" value="simulation" />
    <v-radio label="Serial" value="serial" />
  </v-radio-group>

  <div v-if="source === 'serial'" class="d-flex align-center flex-grow-1">
    <v-select
      v-model="selectedPort"
      :items="ports"
      label="Serial port"
      density="compact"
      hide-details
      :loading="loading"
      no-data-text="No MAVLink devices found"
      class="mr-2"
    />
    <v-btn icon variant="text" size="small" @click="fetchPorts" :loading="loading">
      <v-icon>mdi-refresh</v-icon>
    </v-btn>
  </div>
</div>

    <div class="d-flex justify-space-evenly">
      <v-btn
        width="130"
        :disabled="running || loading || (source === 'serial' && !selectedPort)"
        @click="startSimulator"
      >
        Start
      </v-btn>
      <v-btn width="130" :disabled="!running || loading" @click="stopSimulator">Stop</v-btn>
    </div>
  </div>

  <v-snackbar v-model="error" color="error" location="bottom" class="mb-5" :timeout="3000">
    {{ errorMessage }}
  </v-snackbar>
</template>
