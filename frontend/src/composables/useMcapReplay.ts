import { ref, computed, onMounted } from 'vue'
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
    const limit = ref<number>(1000)
    const currentTime = ref<number>(0)
    const minTime = ref<number>(0)
    const maxTime = ref<number>(0)
    const error = ref<boolean>(false)
    const errorMessage = ref<string>('')
    const confirmDelete = ref<boolean>(false)

    const messagesByTopic = computed((): Record<string, McapMessage[]> => {
        return messages.value.reduce((topicMessages, msg) => {
            (topicMessages[msg.topic] ??= []).push(msg)
            return topicMessages
        }, {} as Record<string, McapMessage[]>)
    })

    const timeMessage = (topicMessages: McapMessage[]): McapMessage | null => {
        if (!topicMessages) return null
        let lower = 0
        let higher = topicMessages.length - 1
        let candidate = null
        while (lower <= higher) {
            const middle = Math.floor((lower + higher) / 2)
            const message = topicMessages[middle]
            if (!message) break
            if (message.timestamp_us <= currentTime.value) {
                candidate = middle
                lower = middle + 1
            } else {
                higher = middle - 1
            }
        }
        return candidate !== null ? topicMessages[candidate] ?? null : null
    }

    const heartbeat = computed((): Heartbeat | null =>
        timeMessage(messagesByTopic.value['rov/heartbeat'] ?? [])?.data as Heartbeat ?? null
    )
    
    const attitude = computed((): Attitude | null  =>
        timeMessage(messagesByTopic.value['rov/attitude'] ?? [])?.data as Attitude ?? null
    )

    const position = computed((): GlobalPosition | null  =>
        timeMessage(messagesByTopic.value['rov/position'] ?? [])?.data as GlobalPosition ?? null
    )

    const downloadFile = () => {
        if (!selectedFile.value) return
        const a = document.createElement('a')
        a.href = `/mcap/files/${selectedFile.value}`
        a.download = selectedFile.value
        a.click()
    }

    const uploadFile = async (event: Event) => {
        const input = event.target as HTMLInputElement
        const file = input.files?.[0]
        if (!file) return
        const form = new FormData()
        form.append("file", file)
        try {
            const response = await fetch("/mcap/files", {
                method: "POST",
                body: form
            })
            if (!response.ok) throw new Error(await response.json().then(r => r.detail))
            selectedFile.value = file.name
            await fetchFiles()
        } catch (e) {
            error.value = true
            errorMessage.value = e instanceof Error ? e.message : String(e)
        } finally {
            input.value = ''
        }
    }

    const deleteFile = async () => {
        if (!selectedFile.value) return
        const response = await fetch(`/mcap/files/${selectedFile.value}`, {
            method: "DELETE",
        })
        confirmDelete.value = false
        if (!response.ok) {
            errorMessage.value = await response.json().then(r => r.detail)
            error.value = true
            return
        }
        selectedFile.value = ''
        messages.value = []
        currentTime.value = 0
        minTime.value = 0
        maxTime.value = 0
        await fetchFiles()
    }

    const fetchFiles = async () => {
        const response = await fetch('/mcap/files')
        if (!response.ok) {
            errorMessage.value = await response.json().then(r => r.detail)
            error.value = true
            return
        }
        files.value = await response.json()
    }

    onMounted(async () => { 
        await fetchFiles()
    })

    const fetchFile = async () => {
        if (!selectedFile.value) return
        const response = await fetch(`/mcap/messages/${selectedFile.value}?limit=${limit.value}`)
        if (!response.ok) {
            errorMessage.value = await response.json().then(r => r.detail)
            error.value = true
            return
        }
        messages.value = await response.json()
        currentTime.value = minTime.value = messages.value[0]?.timestamp_us ?? 0
        maxTime.value = messages.value?.at(-1)?.timestamp_us ?? 0
    }

    return { 
        files,
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
        fetchFile
    }
}