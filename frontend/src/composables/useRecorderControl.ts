import { ref, onMounted } from 'vue'


export function useRecorderControl() {

    const active = ref<boolean>(false)
    const filename = ref<string | null>()
    const started_at = ref<number | null>()
    const recErr = ref<boolean>(false)
    const recErrMsg = ref<string>('')

    const fetchStatus = async () => {
        const response = await fetch('/recorder/status')
        if (!response.ok) {
            recErrMsg.value = await response.json().then(r => r.detail)
            recErr.value = true
            return
        }
        let status = await response.json()
        active.value = status.active
        filename.value = status.filename.replace('./', '')
        started_at.value = status.started_at
    }

    const startRecorder = async () => {
        const response = await fetch('/recorder/start', { method: 'POST' })
        if (!response.ok) {
            recErrMsg.value = await response.json().then(r => r.detail)
            recErr.value = true
            return
        }
        await fetchStatus()
    }

    const stopRecorder = async () => {
        const response = await fetch('/recorder/stop', { method: 'POST' })
        if (!response.ok) {
            recErrMsg.value = await response.json().then(r => r.detail)
            recErr.value = true
            return
        }
        await fetchStatus()
    }

    onMounted(async () => { 
        await fetchStatus()
    })


    return { active, filename, started_at, recErr, recErrMsg, startRecorder, stopRecorder }
}
