<script setup lang="ts">
import { ref, computed, watchEffect, watch } from 'vue'
import { useWebSocket } from './composables/useWebSocket.ts'
import { useMcapReplay } from './composables/useMcapReplay.ts'
import { useRecorderControl } from './composables/useRecorderControl.ts'
import { useWebRTC } from './composables/useWebRTC.ts'

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const ws = useWebSocket(`${protocol}//${window.location.host}/ws/live`)

const mode = ref<'live' | 'replay'>('live')
const fileInput = ref<HTMLInputElement | null>(null)
const videoInput = ref<HTMLInputElement | null>(null)
const sourceType = ref<'video' | 'camera'>('camera')

const videoEl = ref<HTMLVideoElement | null>(null)



function triggerFileInput() {
  fileInput.value?.click()
}

function triggerVideoInput() {
  videoInput.value?.click()
}

async function handleStopRecorder() {
  await stopRecorder()
  await fetchFiles()
}


const formatTime = (us: number): string => {
  if (us === 0) return '--'
    return new Date(us / 1000).toLocaleString()
}

const { active, filename, started_at, recErr, recErrMsg, startRecorder, stopRecorder } = useRecorderControl()

const {
  stream,
  connected,
  sources,
  sourceId,
  rtcErr,
  rtcMsgErr,
  confirmDelVideo,
  connect,
  disconnect,
  fetchSources,
  uploadVideo, 
  deleteVideo
} = useWebRTC()

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
  fetchFile,
  fetchFiles 
} = useMcapReplay()

const currentHeartbeat = computed(() => mode.value === 'live' ? ws.heartbeat.value : heartbeat.value)
const currentAttitude  = computed(() => mode.value === 'live' ? ws.attitude.value  : attitude.value)
const currentPosition  = computed(() => mode.value === 'live' ? ws.position.value  : position.value)

const typeSource = computed(() => {
  if (sourceType.value === 'video') return (sources.value?.videos ?? []).map(v => ({ title: v, value: v }))
  return (sources.value?.cameras ?? []).map(i => ({ title: `Camera ${i}`, value: i }))
})

watchEffect(() => {
  if (videoEl.value) videoEl.value.srcObject = stream.value
})

watch(sourceType, () => { sourceId.value = null })

</script>

<template>
  <v-app>

    <!-- =========== Header =========== -->
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
          <v-btn icon @click="fetchFiles" variant="text" class="mr-2">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
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
            <v-btn class="mr-5" @click="triggerFileInput">upload</v-btn>
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
            <p class="text-h6">{{ formatTime(minTime) }}</p>
          </v-col>
          <v-col cols="12" md="6">
            <v-slider v-model="currentTime" :min="minTime" :max="maxTime"/>
          </v-col>
          <v-col cols="auto">
            <p class="text-h6">{{ formatTime(maxTime) }}</p>
          </v-col>
        </v-row>

        <!-- =========== Live pannel =========== -->
        <v-row justify="center" align="center" class="mt-5 mb-5 position-relative" v-if="mode === 'live'" >
          <v-icon :color="ws.connected ? 'green' : 'red'" class="mr-4">mdi-circle</v-icon>
          <p class="text-h6 mr-5">{{ws.connected ? 'Connected' : 'Disconnected'}}</p>
          <div style="width: 2px; height: 35px; background-color: #2F2F2F; border-radius: 2px;" class="mx-5"></div>
          <v-btn class="ml-3" :disabled="active" @click="startRecorder">Start recorder</v-btn>
          <v-btn class="ml-5 mr-5" :disabled="!active" @click="handleStopRecorder">stop recorder</v-btn>
          <v-icon :color="active ? 'red' : 'grey'">mdi-circle</v-icon>
          <div v-if="active" style="position: absolute; left: calc(50% + 330px); white-space: nowrap" class="d-flex align-center">
            <v-icon color="grey" class="mr-2">mdi-chevron-right</v-icon>
            <span class="text-h6">{{ filename }}</span>
          </div>
          <v-snackbar v-model="recErr" color="error" location="bottom" class="mb-5" :timeout="2000">
            {{ recErrMsg }}
          </v-snackbar>
        </v-row>

        <!-- =========== ROV Cards =========== -->
        <v-divider class="my-6 mx-0"/>
        <v-row justify="center" style="align-items: stretch">
          <v-col cols="12" md="4">
            <v-card title="HEARTBEAT" elevation="2" class="pa-4 h-100">
              <v-card-text>
                <div>Status: {{ currentHeartbeat?.status ?? '--' }}</div>
                <div>System ID: {{ currentHeartbeat?.system_id ?? '--' }}</div>
                <div>Time: {{ currentHeartbeat?.timestamp_us ?? '--' }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card title="ATTITUDE" elevation="2" class="pa-4 h-100">
              <v-card-text>
                <div>Roll: {{ currentAttitude?.roll?.toFixed(3) ?? '--' }} rad</div>
                <div>Pitch: {{ currentAttitude?.pitch?.toFixed(3) ?? '--' }} rad</div>
                <div>Yaw: {{ currentAttitude?.yaw?.toFixed(3) ?? '--' }} rad</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card title="POSITION" elevation="2" class="pa-4 h-100">
              <v-card-text>
                <div>Lat: {{ currentPosition?.lat?.toFixed(6) ?? '--' }}</div>
                <div>Lon: {{ currentPosition?.lon?.toFixed(6) ?? '--' }}</div>
                <div>Alt: {{ currentPosition?.alt_m?.toFixed(1) ?? '--' }} m</div>
                <div>Heading: {{ currentPosition?.heading_deg?.toFixed(1) ?? '--' }}°</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-divider class="my-6 mx-0"/>

        <v-row justify="center" align="center" class="mt-5 mb-5 position-relative" v-if="mode === 'live'" >
            <v-col cols="auto">
              <v-radio-group v-model="sourceType">
                <v-radio class="mr-5" label="Camera" value="camera"/>
                <v-radio class="mr-5" label="Video" value="video" />
              </v-radio-group>
            </v-col>
            <v-col cols="auto">
              <v-select v-model="sourceId" label="Choose source" :items="typeSource" style="width: 300px"/>
            </v-col>
            <v-btn icon @click="fetchSources" variant="text" class="mr-2">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>

            <v-col cols="auto">
              <v-row justify="center" class="mb-2">
                <v-btn class="mr-3" :disabled="(sourceType === 'camera')" @click="triggerVideoInput">upload</v-btn>
                <input ref="videoInput" type="file" class="d-none" accept=".mp4" @change="uploadVideo" />
                <v-btn @click="confirmDelVideo = true" :disabled="(sourceType === 'camera') || !sourceId?.toString().trim()">delete</v-btn>
                <v-dialog v-model="confirmDelVideo" max-width="400">
                  <v-card>
                    <v-card-title>Delete video?</v-card-title>
                    <v-card-text>Confirm deleting: {{ sourceId }}</v-card-text>
                    <v-card-actions>
                      <v-spacer />
                      <v-btn @click="confirmDelVideo = false">No</v-btn>
                      <v-btn color="error" @click="deleteVideo">Yes</v-btn>
                    </v-card-actions>
                  </v-card>
                </v-dialog>
              </v-row>

              <v-row justify="center">
                <v-btn class="ml-3" :disabled="connected || !sourceId?.toString().trim()" @click="connect(sourceType, sourceId)">connect</v-btn>
                <v-btn class="ml-3" :disabled="!connected" @click="disconnect">disconnect</v-btn>
                <v-snackbar v-model="rtcErr" color="error" location="bottom" class="mb-5" :timeout="2000">
                  {{ rtcMsgErr }}
                </v-snackbar>
              </v-row>
              
            </v-col>
        </v-row>
        <v-row justify="center" align="center" class="mt-5 mb-5 position-relative" v-if="mode === 'live'" >
          <video v-if="connected" ref="videoEl" autoplay playsinline muted style="width: 100%; max-width: 500px;"></video>
          <v-img v-else src="/disconnected.jpeg" style="max-width: 500px;" class="mx-auto"/>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>
