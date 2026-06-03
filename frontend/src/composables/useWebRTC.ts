import { ref, onMounted } from 'vue'


interface VideoSources {
    videos: string[]
    cameras: number[]
}


export function useWebRTC() {
    const stream = ref<MediaStream | null>(null)
    const connected = ref<boolean>(false)
    const sources = ref<VideoSources>()
    const sourceId = ref<string | number | null>(null)
    const rtcErr = ref<boolean>(false)
    const rtcMsgErr = ref<string>('')
    const confirmDelVideo = ref<boolean>(false)
    let pc: RTCPeerConnection | null = null
    
    const connect = async (sourceType: 'video' | 'camera', sourceId: string | number | null) => {
        pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] })
        pc.onconnectionstatechange = () => {
            if (pc?.connectionState === 'connected') {
                connected.value = true
            }
            if (pc?.connectionState === 'failed' || pc?.connectionState === 'disconnected') {
                connected.value = false
                stream.value = null
                pc = null
            }
        }
        pc.addTransceiver('video', { direction: 'recvonly' })
        pc.ontrack = (e) => { stream.value = e.streams?.[0] ?? null }
        const offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        const payload = {
            sdp: offer.sdp,
            type: offer.type,
            source_type: sourceType,
            source_id: sourceId,
        }
        const response = await fetch('/vision/offer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        if (!response.ok) {
            rtcMsgErr.value = await response.json().then((r: any) => r.detail)
            rtcErr.value = true
            pc?.close()
            pc = null
            return
        }
        const answer = await response.json()
        await pc.setRemoteDescription(new RTCSessionDescription(answer))
        connected.value = true
    }

    const disconnect = async () => {
        pc?.close()
        pc = null
        stream.value = null
        connected.value = false
    }
    
    const fetchSources = async () => {
        const response = await fetch('/vision/sources')
        if (!response.ok) {
            rtcMsgErr.value = await response.json().then((r: any) => r.detail)
            rtcErr.value = true
            return
        }
        sources.value = await response.json()
    }

    const uploadVideo = async (event: Event) => {
        const input = event.target as HTMLInputElement
        const file = input.files?.[0]
        if (!file) return
        const form = new FormData()
        form.append("file", file)
        try {
            const response = await fetch("/vision/videos", {
                method: "POST",
                body: form
            })
            if (!response.ok) throw new Error(await response.json().then(r => r.detail))
            await fetchSources()
        } catch (e) {
            rtcErr.value = true
            rtcMsgErr.value = e instanceof Error ? e.message : String(e)
        } finally {
            input.value = ''
        }
    }

    const deleteVideo = async () => {
        if (!sourceId.value) return
        const response = await fetch(`/vision/videos/${sourceId.value}`, {
            method: "DELETE",
        })
        confirmDelVideo.value = false
        if (!response.ok) {
            rtcMsgErr.value = await response.json().then(r => r.detail)
            rtcErr.value = true
            return
        }
        sourceId.value = null
        await fetchSources()
    }

    onMounted(async () => { 
        await fetchSources()
    })


    return {
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
    }
}
