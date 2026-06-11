<script setup lang="ts">
import { ref, computed, watchEffect } from "vue";

import { useWebRTC } from "./composables/useWebRTC.ts";
import { useWebSocket } from "./composables/useWebSocket.ts";
import { useMcapReplay } from "./composables/useMcapReplay.ts";

import McapControls from "./components/McapControls.vue";
import MavLinkCards from "./components/MavLinkCards.vue";
import StreamControls from "./components/StreamControls.vue";
import RecorderControls from "./components/RecorderControls.vue";
import SimulatorControls from "./components/SimulatorControls.vue";

const mode = ref<"live" | "replay">("live");
const videoElement = ref<HTMLVideoElement | null>(null);
const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

const ws = useWebSocket(`${protocol}//${window.location.host}/ws/live`);

const { connected, stream } = useWebRTC();
const { heartbeat, attitude, position, sysStatus, vfrHud, pressure, battery } = useMcapReplay();

const currentHeartbeat = computed(() =>
  mode.value === "live" ? ws.heartbeat.value : heartbeat.value,
);
const currentAttitude = computed(() =>
  mode.value === "live" ? ws.attitude.value : attitude.value,
);
const currentPosition = computed(() =>
  mode.value === "live" ? ws.position.value : position.value,
);
const currentSysStatus = computed(() =>
  mode.value === "live" ? ws.sysStatus.value : sysStatus.value,
);
const currentVfrHud = computed(() => (mode.value === "live" ? ws.vfrHud.value : vfrHud.value));
const currentPressure = computed(() =>
  mode.value === "live" ? ws.pressure.value : pressure.value,
);
const currentBattery = computed(() => (mode.value === "live" ? ws.battery.value : battery.value));

watchEffect(() => {
  if (videoElement.value) videoElement.value.srcObject = stream.value;
});
</script>

<template>
  <v-app>
    <v-app-bar>
      <div class="d-flex align-center ml-4">
        <span class="text-h6 mr-5 ml-2">Backend server:</span>
        <v-icon :color="ws.connected ? 'green' : 'red'" size="15" class="mr-1"> mdi-circle </v-icon>
        <span class="text-h6">{{ ws.connected ? "Connected" : "Disconnected" }}</span>
      </div>

      <div class="position-absolute w-100 d-flex justify-center" style="pointer-events: none">
        <span class="text-h5">ROV Telemetry</span>
      </div>

      <v-btn-toggle v-model="mode" mandatory class="ml-auto mr-4">
        <v-btn class="pa-3 pl-10 pr-10" value="live">Live</v-btn>
        <v-btn class="pa-3 pl-7 pr-7" value="replay">Replay</v-btn>
      </v-btn-toggle>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-0" style="height: calc(100vh - 64px)">
        <v-row no-gutters style="height: 100%">
          <v-col style="border-right: 1px solid #2f2f2f; height: 100%; flex: 0 0 600px">
            <MavLinkCards
              :currentHeartbeat="currentHeartbeat"
              :currentAttitude="currentAttitude"
              :currentPosition="currentPosition"
              :currentSysStatus="currentSysStatus"
              :currentVfrHud="currentVfrHud"
              :currentPressure="currentPressure"
              :currentBattery="currentBattery"
            />
            <SimulatorControls v-if="mode === 'live'" />
            <RecorderControls :connected="ws.connected.value" v-if="mode === 'live'" />
            <McapControls :mode="mode" v-if="mode === 'replay'" />
          </v-col>

          <v-col style="height: 100%; display: flex; flex-direction: column">
            <v-row no-gutters style="flex: 1; min-height: 0">
              <v-col
                cols="12"
                style="
                  background: #000000;
                  height: 100%;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                "
              >
                <video
                  v-if="connected"
                  ref="videoElement"
                  autoplay
                  playsinline
                  muted
                  style="width: 100%; height: 100%; display: block; object-fit: contain"
                ></video>
                <v-img v-else src="/disconnected.jpeg" style="max-width: 500px" class="mx-auto" />
              </v-col>
            </v-row>
            <div
              class="pl-10"
              style="
                border-top: 1px solid #2f2f2f;
                height: 110px;
                flex-shrink: 0;
                padding: 0 12px;
                display: flex;
                align-items: center;
              "
            >
              <StreamControls />
            </div>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>
