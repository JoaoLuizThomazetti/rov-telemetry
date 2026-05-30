<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWebSocket } from './composables/useWebSocket.ts'
import { useMcapReplay } from './composables/useMcapReplay.ts'

const ws = useWebSocket(`ws://${window.location.host}/ws/live`)
const { files, selectedFile, currentTime, minTime, maxTime,
          heartbeat: replayHeartbeat, attitude: replayAttitude, position: replayPosition } = useMcapReplay()

const mode = ref<'live' | 'replay'>('live')

const heartbeat = computed(() => mode.value === 'live' ? ws.heartbeat.value : replayHeartbeat.value)
const attitude  = computed(() => mode.value === 'live' ? ws.attitude.value  : replayAttitude.value)
const position  = computed(() => mode.value === 'live' ? ws.position.value  : replayPosition.value)


</script>

<template>
  <v-app>
    <v-app-bar title="ROV Telemetry">
      <v-icon :color="ws.connected ? 'green' : 'red'" class="mr-4">mdi-circle</v-icon>
      <v-btn-toggle v-model="mode" mandatory>
        <v-btn value="live">Live</v-btn>
        <v-btn value="replay">Replay</v-btn>
      </v-btn-toggle>
    </v-app-bar>

    <v-main>
      <v-container>
        <v-row justify="center" v-if="mode === 'replay'">
          <v-col>
            <h3>File</h3>
            <v-select v-model="selectedFile" :items="files"/>
          </v-col>
          <v-col justify="center">
            <v-row justify="center">
              <h3>Time: </h3>
              <h3>{{ currentTime }}</h3>
            </v-row>
            <v-slider v-model="currentTime" :min="minTime" :max="maxTime"/>
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col cols="12" md="4">
            <v-card title="HEARTBEAT" elevation="2" class="pa-4">
              <v-card-text>
                <div>Status: {{ heartbeat?.status ?? '--' }}</div>
                <div>System ID: {{ heartbeat?.system_id ?? '--' }}</div>
                <div>Time: {{ heartbeat?.timestamp_us ?? '--' }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card title="ATTITUDE" elevation="2" class="pa-4">
              <v-card-text>
                <div>Roll: {{ attitude?.roll?.toFixed(3) ?? '--' }} rad</div>
                <div>Pitch: {{ attitude?.pitch?.toFixed(3) ?? '--' }} rad</div>
                <div>Yaw: {{ attitude?.yaw?.toFixed(3) ?? '--' }} rad</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card title="POSITION" elevation="2" class="pa-4">
              <v-card-text>
                <div>Lat: {{ position?.lat?.toFixed(6) ?? '--' }}</div>
                <div>Lon: {{ position?.lon?.toFixed(6) ?? '--' }}</div>
                <div>Alt: {{ position?.alt_m?.toFixed(1) ?? '--' }} m</div>
                <div>Heading: {{ position?.heading_deg?.toFixed(1) ?? '--' }}°</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>