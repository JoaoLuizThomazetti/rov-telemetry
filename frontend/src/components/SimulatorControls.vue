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
  <v-divider class="mt-1" />
  <div style="border-top: 1px solid #2f2f2f; padding: 12px">
    <div class="d-flex align-start gap-4 ml-2 mr-2">
      <div class="d-flex flex-column flex-grow-1">
        <v-radio-group v-model="source" hide-details inline class="ml-15">
          <v-radio label="Serial USB" value="serial" class="mr-4" />
          <v-radio label="Simulation" value="simulation" />
        </v-radio-group>

        <div v-if="source === 'serial'" class="d-flex align-center mt-2">
          <v-select
            v-model="selectedPort"
            :items="ports"
            label="Serial port"
            density="compact"
            hide-details
            :loading="loading"
            no-data-text="No MAVLink devices found"
            class="mr-2 ml-7"
          />
          <v-btn icon variant="text" class="mr-5" @click="fetchPorts" :loading="loading">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </div>
      </div>

      <div class="d-flex flex-column gap-2">
        <v-btn
          class="ma-1"
          width="130"
          :disabled="running || loading || (source === 'serial' && !selectedPort)"
          @click="startSimulator"
        >
          Start
        </v-btn>
        <v-btn class="ma-1" width="130" :disabled="!running || loading" @click="stopSimulator"
          >Stop</v-btn
        >
      </div>
    </div>
  </div>

  <v-snackbar v-model="error" color="error" location="bottom" class="mb-5" :timeout="3000">
    {{ errorMessage }}
  </v-snackbar>
</template>
