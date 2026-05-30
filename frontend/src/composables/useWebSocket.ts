import { ref, onMounted, onUnmounted } from 'vue'

interface TelemetryMessage {
    topic: string
    data: unknown
}

export interface Heartbeat {
    system_id: number
    status: string
    timestamp_us: number
}

export interface Attitude {
    roll: number
    pitch: number
    yaw: number
    timestamp_us: number
}

export interface GlobalPosition {
    lat: number
    lon: number
    alt_m: number
    heading_deg: number
    timestamp_us: number
}

export function useWebSocket(url: string) {
    const heartbeat = ref<Heartbeat | null >(null)
    const attitude  = ref<Attitude | null>(null)
    const position  = ref<GlobalPosition | null>(null)
    const connected = ref<boolean>(false)

    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
        ws = new WebSocket(url)

        ws.onopen  = () => connected.value = true
        ws.onclose = () => {
            connected.value = false
            reconnectTimer = setTimeout(connect, 3000)
        }
        ws.onerror = (error) => {
            console.error('ws error:', error)
            connected.value = false
        }

        ws.onmessage = (event) => {
            const msg: TelemetryMessage = JSON.parse(event.data)
            if (msg.topic === 'rov/heartbeat') heartbeat.value = msg.data as Heartbeat
            if (msg.topic === 'rov/attitude')  attitude.value  = msg.data as Attitude
            if (msg.topic === 'rov/position')  position.value  = msg.data as GlobalPosition
        }
    }

    onMounted(() => connect())

    onUnmounted(() => {
        if (reconnectTimer) clearTimeout(reconnectTimer)
        ws?.close()
    })

    return { heartbeat, attitude, position, connected }
}