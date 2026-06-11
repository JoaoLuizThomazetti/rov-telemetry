<script setup lang="ts">
import type {
  Heartbeat,
  Attitude,
  GlobalPosition,
  SysStatus,
  VfrHud,
  ScaledPressure2,
  BatteryStatus,
} from "../composables/useWebSocket";

const props = defineProps<{
  currentHeartbeat: Heartbeat | null;
  currentAttitude: Attitude | null;
  currentPosition?: GlobalPosition | null;
  currentSysStatus: SysStatus | null;
  currentVfrHud: VfrHud | null;
  currentPressure: ScaledPressure2 | null;
  currentBattery: BatteryStatus | null;
}>();
</script>

<template>
  <v-row dense align="stretch">
    <v-col cols="12">
      <v-card title="SYS STATUS" elevation="2" class="mt-2">
        <v-card-text>
          <v-row dense>
            <v-col cols="6">
              <div class="info-row">
                <span class="text-secondary">CPU load</span>
                <span class="info-value"
                  >{{ currentSysStatus ? (currentSysStatus.load / 10).toFixed(1) : "--" }} %</span
                >
              </div>
              <div class="info-row">
                <span class="text-secondary">Voltage</span>
                <span class="info-value"
                  >{{
                    currentSysStatus ? (currentSysStatus.voltage_battery / 1000).toFixed(2) : "--"
                  }}
                  V</span
                >
              </div>
              <div class="info-row">
                <span class="text-secondary">Current</span>
                <span class="info-value"
                  >{{
                    currentSysStatus ? (currentSysStatus.current_battery / 100).toFixed(2) : "--"
                  }}
                  A</span
                >
              </div>
            </v-col>
            <v-col cols="6">
              <div class="info-row">
                <span class="text-secondary">Battery</span>
                <span class="info-value">{{ currentSysStatus?.battery_remaining ?? "--" }} %</span>
              </div>
              <div class="info-row">
                <span class="text-secondary">Drop rate</span>
                <span class="info-value"
                  >{{
                    currentSysStatus ? (currentSysStatus.drop_rate_comm / 100).toFixed(1) : "--"
                  }}
                  %</span
                >
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="HEARTBEAT" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Status</span>
            <span
              class="info-value"
              :style="{ color: currentHeartbeat?.system_status === 4 ? '#1D9E75' : '#E24B4A' }"
            >
              {{ currentHeartbeat?.system_status ?? "--" }}
            </span>
          </div>
          <div class="info-row">
            <span class="text-secondary">System ID</span>
            <span class="info-value">{{ currentHeartbeat?.system_id ?? "--" }}</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Component ID</span>
            <span class="info-value">{{ currentHeartbeat?.component_id ?? "--" }}</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Base mode</span>
            <span class="info-value">{{ currentHeartbeat?.base_mode ?? "--" }}</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Time</span>
            <span class="info-value">{{
              currentHeartbeat
                ? new Date(currentHeartbeat.timestamp_ms / 1000).toLocaleString()
                : "--"
            }}</span>
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="ATTITUDE" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Roll</span>
            <span class="info-value">{{ currentAttitude?.roll?.toFixed(3) ?? "--" }} rad</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Pitch</span>
            <span class="info-value">{{ currentAttitude?.pitch?.toFixed(3) ?? "--" }} rad</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Yaw</span>
            <span class="info-value">{{ currentAttitude?.yaw?.toFixed(3) ?? "--" }} rad</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Roll speed</span>
            <span class="info-value"
              >{{ currentAttitude?.rollspeed?.toFixed(3) ?? "--" }} rad/s</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Pitch speed</span>
            <span class="info-value"
              >{{ currentAttitude?.pitchspeed?.toFixed(3) ?? "--" }} rad/s</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Yaw speed</span>
            <span class="info-value"
              >{{ currentAttitude?.yawspeed?.toFixed(3) ?? "--" }} rad/s</span
            >
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="POSITION" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Lat</span>
            <span class="info-value"
              >{{ currentPosition ? (currentPosition.lat / 1e7).toFixed(6) : "--" }}°</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Lon</span>
            <span class="info-value"
              >{{ currentPosition ? (currentPosition.lon / 1e7).toFixed(6) : "--" }}°</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Alt MSL</span>
            <span class="info-value"
              >{{ currentPosition ? (currentPosition.alt / 1000).toFixed(2) : "--" }} m</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Relative alt</span>
            <span class="info-value"
              >{{
                currentPosition ? (currentPosition.relative_alt / 1000).toFixed(2) : "--"
              }}
              m</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Heading</span>
            <span class="info-value"
              >{{
                currentPosition
                  ? currentPosition.hdg === 65535
                    ? "--"
                    : (currentPosition.hdg / 100).toFixed(1)
                  : "--"
              }}°</span
            >
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="VFR HUD" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Airspeed</span>
            <span class="info-value">{{ currentVfrHud?.airspeed?.toFixed(2) ?? "--" }} m/s</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Groundspeed</span>
            <span class="info-value">{{ currentVfrHud?.groundspeed?.toFixed(2) ?? "--" }} m/s</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Heading</span>
            <span class="info-value">{{ currentVfrHud?.heading ?? "--" }}°</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Throttle</span>
            <span class="info-value">{{ currentVfrHud?.throttle ?? "--" }} %</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Altitude</span>
            <span class="info-value">{{ currentVfrHud?.alt?.toFixed(2) ?? "--" }} m</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Climb rate</span>
            <span class="info-value">{{ currentVfrHud?.climb?.toFixed(2) ?? "--" }} m/s</span>
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="PRESSURE" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Abs pressure</span>
            <span class="info-value">{{ currentPressure?.press_abs?.toFixed(2) ?? "--" }} hPa</span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Diff pressure</span>
            <span class="info-value"
              >{{ currentPressure?.press_diff?.toFixed(2) ?? "--" }} hPa</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Temperature</span>
            <span class="info-value"
              >{{
                currentPressure ? (currentPressure.temperature / 100).toFixed(1) : "--"
              }}
              °C</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Depth</span>
            <span class="info-value"
              >{{
                currentPressure ? ((currentPressure.press_abs - 1013.25) / 9.8).toFixed(2) : "--"
              }}
              m</span
            >
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="6" class="d-flex">
      <v-card title="BATTERY" elevation="2" class="pa-1 flex-grow-1 telemetry-card">
        <v-card-text>
          <div class="info-row">
            <span class="text-secondary">Remaining</span>
            <span
              class="info-value"
              :style="{
                color: (currentBattery?.battery_remaining ?? 100) < 20 ? '#E24B4A' : '#1D9E75',
              }"
            >
              {{ currentBattery?.battery_remaining ?? "--" }} %
            </span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Current</span>
            <span class="info-value"
              >{{
                currentBattery ? (currentBattery.current_battery / 100).toFixed(2) : "--"
              }}
              A</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Temperature</span>
            <span class="info-value"
              >{{ currentBattery ? (currentBattery.temperature / 100).toFixed(1) : "--" }} °C</span
            >
          </div>
          <div class="info-row">
            <span class="text-secondary">Cells</span>
            <span class="info-value">
              {{
                currentBattery
                  ? currentBattery.voltages
                      .filter((v) => v !== 65535)
                      .map((v) => (v / 1000).toFixed(2))
                      .join(" | ")
                  : "--"
              }}
              V
            </span>
          </div>
          <div class="info-row">
            <span class="text-secondary">Consumed</span>
            <span class="info-value"
              >{{
                currentBattery?.current_consumed === -1
                  ? "--"
                  : (currentBattery?.current_consumed ?? "--")
              }}
              mAh</span
            >
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<style scoped>
.telemetry-card {
  min-width: 0;
  overflow: hidden;
  font-size: 0.78rem;
}

.telemetry-card :deep(.v-card-title) {
  font-size: 0.85rem;
  padding-bottom: 4px;
}

.telemetry-card :deep(.v-card-text) {
  padding: 8px 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 2px;
}

.info-value {
  text-align: right;
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 0.78rem;
}
</style>
