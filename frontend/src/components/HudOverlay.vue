<script setup lang="ts">

import type { VfrHud, BatteryStatus } from "../composables/useWebSocket";

defineProps<{
  vfrHud: VfrHud | null;
  battery: BatteryStatus | null;
}>();

</script>

<template>
    
  <div class="hud-box">
    <div class="hud-row">
      <span class="hud-label">Airspeed</span>
      <span class="hud-value">{{ vfrHud ? vfrHud.airspeed.toFixed(1) : "--" }} m/s</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Groundspeed</span>
      <span class="hud-value">{{ vfrHud ? vfrHud.groundspeed.toFixed(1) : "--" }} m/s</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Heading</span>
      <span class="hud-value">{{ vfrHud?.heading ?? "--" }}°</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Throttle</span>
      <span class="hud-value">{{ vfrHud?.throttle ?? "--" }} %</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Altitude</span>
      <span class="hud-value">{{ vfrHud ? vfrHud.alt.toFixed(1) : "--" }} m</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Climb</span>
      <span class="hud-value">{{ vfrHud ? vfrHud.climb.toFixed(2) : "--" }} m/s</span>
    </div>
    <div class="hud-divider"></div>
    <div class="hud-row">
      <span class="hud-label">Battery</span>
      <span
        class="hud-value"
        :style="{ color: (battery?.battery_remaining ?? 100) < 20 ? '#E24B4A' : '#1D9E75' }"
      >{{ battery?.battery_remaining ?? "--" }} %</span>
    </div>
    <div class="hud-row">
      <span class="hud-label">Voltage</span>
      <span class="hud-value">
        {{ battery ? (battery.voltages.filter(v => v !== 65535).reduce((a, b) => a + b, 0) / 1000).toFixed(2) : "--" }} V
      </span>
    </div>
  </div>

</template>


<style scoped>
.hud-box {
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  padding: 8px 12px;
  min-width: 160px;
  font-family: monospace;
  font-size: 0.78rem;
  color: #e0e0e0;
}

.hud-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 2px;
}

.hud-label {
  color: rgba(255, 255, 255, 0.5);
}

.hud-value {
  color: #ffffff;
  text-align: right;
}

.hud-divider {
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  margin: 4px 0;
}
</style>