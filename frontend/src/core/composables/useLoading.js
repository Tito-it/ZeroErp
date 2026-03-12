// Scopo: gestione stato di caricamento con distinzione primo/successivi.
// Primo caricamento -> Skeleton, successivi -> ProgressBar sottile.
import { ref, readonly } from 'vue'

export function useLoading() {
  const loading = ref(false)
  const firstLoad = ref(true)

  async function withLoading(asyncFn) {
    loading.value = true
    try {
      return await asyncFn()
    } finally {
      loading.value = false
      firstLoad.value = false
    }
  }

  return {
    loading: readonly(loading),
    firstLoad: readonly(firstLoad),
    withLoading
  }
}
