<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWebSocket } from './composables/useWebSocket.ts'
import { useMcapReplay } from './composables/useMcapReplay.ts'

const ws = useWebSocket(`ws://${window.location.host}/ws/live`)
const mode = ref<'live' | 'replay'>('live')
const fileInput = ref<HTMLInputElement | null>(null)

function triggerInput() {
  fileInput.value?.click()
}

const formatTime = (us: number): string => {
  if (us === 0) return '--'
    return new Date(us / 1000).toLocaleString()
}

const { files,
  selectedFile,
  messages,
  limit,
  currentTime,
  minTime,
  maxTime,
  error,
  errorMessage,
  confirmDelete,
  heartbeat,
  attitude,
  position,
  downloadFile,
  uploadFile,
  deleteFile,
  fetchFile } = useMcapReplay()

const currentHeartbeat = computed(() => mode.value === 'live' ? ws.heartbeat.value : heartbeat.value)
const currentAttitude  = computed(() => mode.value === 'live' ? ws.attitude.value  : attitude.value)
const currentPosition  = computed(() => mode.value === 'live' ? ws.position.value  : position.value)

</script>

<template>
  <v-app>
    <v-app-bar title="ROV Telemetry">

      <v-btn-toggle v-model="mode" mandatory>
        <v-btn value="live">Live</v-btn>
        <v-btn value="replay">Replay</v-btn>
      </v-btn-toggle>



    </v-app-bar>

    <v-main>
      <v-container>

        <!-- =========== File Load =========== -->
        <v-row align="center" justify="center" v-if="mode === 'replay'">
          <v-col cols="auto">
            <v-select v-model="selectedFile" label="Choose .mcap file" :items="files" style="width: 300px"/>
          </v-col>

          <v-col cols="auto">
            <v-text-field v-model="limit" type="number" label="Max messages" style="width: 120px" 
            :rules="[v => v >= 1 || 'Min 1', v => v <= 10000 || 'Max 10000']" />
          </v-col>

          <v-btn class="ml-3" :disabled="!selectedFile" @click="fetchFile">load file</v-btn>
        </v-row>

        <!-- =========== File Buttons =========== -->
        <v-row align="center" justify="center" v-if="mode === 'replay'">
          <v-col cols="auto">
            <v-btn class="mr-5" @click="triggerInput">upload</v-btn>
            <input ref="fileInput" type="file" class="d-none" accept=".mcap" @change="uploadFile" />
            
            <v-btn class="mr-5" @click="downloadFile" :disabled="!selectedFile">download</v-btn>
            <v-snackbar v-model="error" color="error" location="bottom" class="mb-5" :timeout="2000">
              {{ errorMessage }}
            </v-snackbar>

            <v-btn @click="confirmDelete = true" :disabled="!selectedFile">delete</v-btn>
            <v-dialog v-model="confirmDelete" max-width="400">
              <v-card>
                <v-card-title>Delete file?</v-card-title>
                <v-card-text>Confirm deleting: {{ selectedFile }}</v-card-text>
                <v-card-actions>
                  <v-spacer />
                  <v-btn @click="confirmDelete = false">No</v-btn>
                  <v-btn color="error" @click="deleteFile">Yes</v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>

          </v-col>

        </v-row>

        <!-- =========== Time slide =========== -->
        <v-row justify="center" v-if="mode === 'replay'">

          <v-col cols="auto">
            <h3>{{ formatTime(minTime) }}</h3>
          </v-col>

          <v-col cols="12" md="6">
            <v-slider v-model="currentTime" :min="minTime" :max="maxTime"/>
          </v-col>

          <v-col cols="auto">
            <h3>{{ formatTime(maxTime) }}</h3>
          </v-col>

        </v-row>

        <!-- =========== ROV Cards =========== -->
        <v-row justify="center" class="mt-5 mb-5" v-if="mode === 'live'" >
          <v-col cols="auto">
            <h2>{{ws.connected ? 'Connected' : 'Disconnected'}}</h2>
          </v-col>
          <v-col cols="auto">
            <v-icon :color="ws.connected ? 'green' : 'red'" class="mr-4">mdi-circle</v-icon>
          </v-col> 
        </v-row>

        <v-divider class="my-4 mx-0" />

        <v-row justify="center">
          <v-col cols="12" md="4">
            <v-card title="HEARTBEAT" elevation="2" class="pa-4">
              <v-card-text>
                <div>Status: {{ currentHeartbeat?.status ?? '--' }}</div>
                <div>System ID: {{ currentHeartbeat?.system_id ?? '--' }}</div>
                <div>Time: {{ currentHeartbeat?.timestamp_us ?? '--' }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card title="ATTITUDE" elevation="2" class="pa-4">
              <v-card-text>
                <div>Roll: {{ currentAttitude?.roll?.toFixed(3) ?? '--' }} rad</div>
                <div>Pitch: {{ currentAttitude?.pitch?.toFixed(3) ?? '--' }} rad</div>
                <div>Yaw: {{ currentAttitude?.yaw?.toFixed(3) ?? '--' }} rad</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card title="POSITION" elevation="2" class="pa-4">
              <v-card-text>
                <div>Lat: {{ currentPosition?.lat?.toFixed(6) ?? '--' }}</div>
                <div>Lon: {{ currentPosition?.lon?.toFixed(6) ?? '--' }}</div>
                <div>Alt: {{ currentPosition?.alt_m?.toFixed(1) ?? '--' }} m</div>
                <div>Heading: {{ currentPosition?.heading_deg?.toFixed(1) ?? '--' }}°</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>