<script setup lang="ts">
import type { Heartbeat, Attitude, GlobalPosition } from "../composables/useWebSocket";

const props = defineProps<{
  currentHeartbeat: Heartbeat | null;
  currentAttitude: Attitude | null;
  currentPosition?: GlobalPosition | null;
}>();
</script>

<template>
  <v-card title="HEARTBEAT" elevation="2" class="pa-3 mb-1">
    <v-card-text>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Status</span>
        <span
          :style="{
            color: currentHeartbeat?.status === 'MAV_STATE_ACTIVE' || currentHeartbeat?.status === 'active' ? '#1D9E75' : '#E24B4A',
          }"
        >
          {{ currentHeartbeat?.status ?? "--" }}
        </span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">System ID</span>
        <span>{{ currentHeartbeat?.system_id ?? "--" }}</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Time</span>
        <span>{{ currentHeartbeat?.timestamp_us ?? "--" }}</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Time (readable)</span>
        <span>{{
          currentHeartbeat?.timestamp_us
            ? new Date(currentHeartbeat.timestamp_us / 1000).toLocaleString()
            : "--"
        }}</span>
      </div>
    </v-card-text>
  </v-card>
  <v-divider />

  <v-card title="ATTITUDE" elevation="2" class="pa-3 mb-1">
    <v-card-text>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Roll</span>
        <span>{{ currentAttitude?.roll?.toFixed(3) ?? "--" }} rad</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Pitch</span>
        <span>{{ currentAttitude?.pitch?.toFixed(3) ?? "--" }} rad</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Yaw</span>
        <span>{{ currentAttitude?.yaw?.toFixed(3) ?? "--" }} rad</span>
      </div>
    </v-card-text>
  </v-card>
  <v-divider />

  <v-card title="POSITION" elevation="2" class="pa-3 mb-1">
    <v-card-text>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Lat</span>
        <span>{{ currentPosition?.lat?.toFixed(6) ?? "--" }}</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Lon</span>
        <span>{{ currentPosition?.lon?.toFixed(6) ?? "--" }}</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Alt</span>
        <span>{{ currentPosition?.alt_m?.toFixed(1) ?? "--" }}m</span>
      </div>
      <div class="d-flex justify-space-between">
        <span class="text-secondary">Heading</span>
        <span>{{ currentPosition?.heading_deg?.toFixed(1) ?? "--" }}°</span>
      </div>
    </v-card-text>
  </v-card>
  <v-divider />
</template>

<style scoped></style>
