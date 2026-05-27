import { ref, computed, onMounted, watch } from 'vue'
import type { Heartbeat, Attitude, GlobalPosition } from './useWebSocket'


interface McapMessage {
    topic: string
    timestamp_us: number
    data: unknown
}


export function useMcapReplay() {

    const files = ref<string[]>([])
    const selectedFile = ref<string>('')
    const messages = ref<McapMessage[]>([])
    const currentTime = ref<number>(0)
    const minTime = ref<number>(0)
    const maxTime = ref<number>(0)
  
    const heartbeat = computed((): Heartbeat | null  =>
        messages.value.filter( message => 
            message.topic === 'rov/heartbeat' && message.timestamp_us <= (currentTime.value ?? 0)
        ).at(-1)?.data as Heartbeat ?? null
    )
    const attitude = computed((): Attitude | null  =>
        messages.value.filter( message => 
            message.topic === 'rov/attitude' && message.timestamp_us <= (currentTime.value ?? 0)
        ).at(-1)?.data as Attitude ?? null
    )
    const position = computed((): GlobalPosition | null  =>
        messages.value.filter( message => 
            message.topic === 'rov/position' && message.timestamp_us <= (currentTime.value ?? 0)
        ).at(-1)?.data as GlobalPosition ?? null
    )

    onMounted(async () => { 
        const response = await fetch('http://localhost:8000/mcap/files')
        if (!response.ok) throw new Error(`${response.status}`)
        files.value = await response.json()
    })

    watch(selectedFile, async () => {
        const response = await fetch(`http://localhost:8000/mcap/messages?file=${selectedFile.value}&limit=100`)
        if (!response.ok) throw new Error(`${response.status}`)
        messages.value = await response.json()
        currentTime.value = minTime.value = messages.value[0]?.timestamp_us ?? 0
        maxTime.value = messages.value?.at(-1)?.timestamp_us ?? 0
    })

    return { files, selectedFile, messages, currentTime, minTime, maxTime, heartbeat, attitude, position }
}