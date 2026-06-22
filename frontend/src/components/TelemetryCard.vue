<script setup lang="ts">
import { useTelemetry } from "../composables/useTelemetry.ts";

const props = defineProps<{
  open: boolean
}>();
const emit = defineEmits<{
  "update:open": [value: boolean]
}>();

const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const { connected, systemData, containerData } = useTelemetry(
  `${protocol}//${window.location.host}/telemetry/ws/live`,
);

const formatUptime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
};

const statusColor = (status: string) =>
  status === "running" ? "success" : "error";
</script>

<template>
  <v-navigation-drawer
    :model-value="open"
    @update:model-value="emit('update:open', $event)"
    location="right"
    width="320"
    temporary
  >
    <v-list-item
      title="System Monitor"
      :subtitle="connected ? 'Connected' : 'Disconnected'"
    >
      <template #prepend>
        <v-icon :color="connected ? 'green' : 'red'" size="12" class="mr-2">mdi-circle</v-icon>
      </template>
      <template #append>
        <v-btn icon variant="text" @click="emit('update:open', false)">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </template>
    </v-list-item>

    <v-divider />

    <!-- system -->
    <v-list-subheader>System</v-list-subheader>
    <v-list-item v-if="!systemData">
      <span class="text-disabled">No data</span>
    </v-list-item>
    <template v-else>
      <v-list-item>
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-body-2">CPU</span>
          <span class="text-body-2">{{ systemData.cpu_percent.toFixed(1) }}%</span>
        </div>
        <v-progress-linear :model-value="systemData.cpu_percent" rounded height="6" />
      </v-list-item>
      <v-list-item>
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-body-2">Memory</span>
          <span class="text-body-2">{{ systemData.mem_percent.toFixed(1) }}%</span>
        </div>
        <v-progress-linear :model-value="systemData.mem_percent" rounded height="6" />
      </v-list-item>
      <v-list-item>
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-body-2">Disk</span>
          <span class="text-body-2">{{ systemData.disk_percent.toFixed(1) }}%</span>
        </div>
        <v-progress-linear :model-value="systemData.disk_percent" rounded height="6" />
      </v-list-item>
    </template>

    <v-divider class="mt-2" />

    <!-- containers -->
    <v-list-subheader>Containers</v-list-subheader>
    <v-list-item v-if="containerData.length === 0">
      <span class="text-disabled">No containers</span>
    </v-list-item>
    <v-list-item v-for="c in containerData" :key="c.name" class="py-1">
      <div class="d-flex justify-space-between align-center">
        <div class="d-flex align-center gap-2">
          <v-icon :color="statusColor(c.status)" size="10">mdi-circle</v-icon>
          <span class="text-body-2">{{ c.name }}</span>
        </div>
        <span class="text-caption text-disabled">
          {{ c.status === "running" ? formatUptime(c.uptime_s) : c.status }}
        </span>
      </div>
    </v-list-item>
  </v-navigation-drawer>
</template>
