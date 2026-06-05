// Scopo: Composable per scaricare un file da un endpoint che ritorna
//        Blob (axios `responseType: 'blob'`). Estrae il filename dal
//        Content-Disposition (RFC 5987 + filename="..."), triggera il
//        download lato browser, espone stato `loading` reattivo e
//        gestione errori centralizzata via useApiHandler.
//
//        Strategia di download:
//          1. Se il browser supporta File System Access API
//             (`window.showSaveFilePicker`, Chrome/Edge moderni HTTPS),
//             apre il dialog NATIVO "Salva con nome" del sistema
//             operativo. L'utente sceglie cartella e nome.
//          2. Altrimenti (Firefox/Safari/HTTP) fallback al pattern
//             `<a download>` classico: file in cartella download
//             default del browser, filename dal Content-Disposition.
//          3. Cancel utente nel dialog nativo (AbortError) e' trattato
//             come "operazione completata senza errore" — niente toast.
//
// Uso tipico:
//   const { download, loading } = useFileDownload()
//   await download(
//     () => exportClienti({ formato: 'csv', search: 'mario' }),
//     { fallbackFilename: 'export.csv' },
//   )
//
// Building block riusabile da export liste (DEF-1) e in futuro da
// altri download (PDF documenti, log emails, ecc.).

import { ref } from 'vue'
import { useNotify } from './useNotify'
import { downloadBlob } from '../utils/download'

// Scopo: feature detection FS Access API. Disponibile su Chrome/Edge
//        moderni con HTTPS o localhost. Esposto come export per i
//        chiamanti che vogliono mostrare hint UX ("verra' aperto il
//        dialog di sistema") solo quando supportato.
export function isFileSystemAccessSupported() {
  return typeof window !== 'undefined'
    && typeof window.showSaveFilePicker === 'function'
}

export function useFileDownload() {
  const loading = ref(false)
  const notify = useNotify()

  // Scopo: Esegue la chiamata API che ritorna un blob, estrae il
  //        filename dal Content-Disposition (con fallback) e triggera
  //        il download nel browser.
  //
  //        NB: NON usa `useApiHandler.execute` perche' quello fa
  //        l'unwrap dell'envelope `{data, meta}` ritornando `response.data`
  //        (utile per JSON ma rovina i blob: il chiamante perderebbe
  //        l'accesso a `response.headers` per il Content-Disposition e
  //        riceverebbe il blob al posto della response axios completa).
  //        Qui chiamiamo direttamente la `apiCall` e mostriamo i toast
  //        success/error in autonomia.
  //
  //        Argomenti:
  //          - apiCall: () => Promise<AxiosResponse> (deve avere
  //            `responseType: 'blob'` nel chiamante)
  //          - opts.fallbackFilename: usato se Content-Disposition
  //            assente o non parsabile (default 'download.bin')
  //          - opts.successMessage: opzionale, toast su successo
  //          - opts.silent: true = no toast errore (utile per polling)
  //
  //        Ritorna: AxiosResponse | null (null se errore gestito).
  async function download(apiCall, opts = {}) {
    loading.value = true
    try {
      const response = await apiCall()
      const filename = extractFileName(response)
        || opts.fallbackFilename
        || 'download.bin'
      // Path 1: dialog "Salva con nome" nativo OS via FS Access API.
      //         Se l'utente cancella, AbortError -> handled=true, niente
      //         errore. Mostriamo il toast success solo se il salvataggio
      //         e' effettivamente avvenuto (non se cancellato).
      if (isFileSystemAccessSupported()) {
        const result = await trySaveWithPicker(
          response.data,
          filename,
          response.headers?.['content-type'],
        )
        if (result === 'saved') {
          if (opts.successMessage) notify.success(opts.successMessage)
          return response
        }
        if (result === 'cancelled') {
          // Cancel utente: niente toast, ritorno null per coerenza con
          // pattern useApiHandler ("operazione non avvenuta").
          return null
        }
        // result === 'error': cadi nel fallback standard.
      }
      // Path 2: fallback classico download via <a download>.
      downloadBlob(response.data, filename)
      if (opts.successMessage) notify.success(opts.successMessage)
      return response
    } catch (err) {
      // Errore HTTP / network. Per blob downloads, il body errore puo'
      // essere a sua volta un Blob (axios non lo parsa come JSON con
      // responseType:blob): convertiamo per estrarre il messaggio
      // backend.
      if (!opts.silent) {
        const message = await extractErrorMessageFromBlobOrJson(err)
          || opts.errorMessage
          || 'Download non riuscito'
        notify.error(message)
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { download, loading }
}

// Scopo: Estrae il messaggio errore da una response axios. Per blob
//        downloads il body di errore arriva come Blob (axios non
//        switcha automaticamente a JSON parsing su responseType:blob).
//        Provo a leggerlo come testo e parsare l'envelope standard
//        backend `{ error: { message } }` o `{ detail }`.
async function extractErrorMessageFromBlobOrJson(err) {
  const data = err?.response?.data
  if (!data) return null
  // Caso JSON gia' parsato (responseType:blob non era settato lato call).
  if (typeof data === 'object' && !(data instanceof Blob)) {
    return data.error?.message
      || (typeof data.error === 'string' ? data.error : null)
      || data.detail
      || null
  }
  // Caso Blob: leggi come testo e parsa.
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      const json = JSON.parse(text)
      return json.error?.message
        || (typeof json.error === 'string' ? json.error : null)
        || json.detail
        || null
    } catch {
      return null
    }
  }
  return null
}

// Scopo: Tenta il salvataggio via File System Access API. Ritorna:
//          - 'saved'     : file salvato, mostra toast success
//          - 'cancelled' : utente ha cancellato il dialog (AbortError),
//                          niente toast, niente fallback
//          - 'error'     : API fallita per motivo tecnico, il chiamante
//                          deve fare fallback al download standard
async function trySaveWithPicker(blob, filename, contentType) {
  try {
    const accept = buildPickerAccept(filename, contentType)
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: accept ? [accept] : undefined,
    })
    const writable = await handle.createWritable()
    await writable.write(blob)
    await writable.close()
    return 'saved'
  } catch (e) {
    if (e?.name === 'AbortError') return 'cancelled'
    return 'error'
  }
}

// Scopo: Costruisce la voce `types` per `showSaveFilePicker` deducendo
//        l'estensione dal filename e il MIME dal Content-Type.
//        Tornare `null` lascia il dialog "All Files" — accettabile.
function buildPickerAccept(filename, contentType) {
  const ext = filename.includes('.')
    ? '.' + filename.split('.').pop().toLowerCase()
    : null
  if (!ext || !contentType) return null
  // Strip charset / boundary parameters dal Content-Type per ottenere
  // il MIME pulito (es. "text/csv; charset=utf-8" -> "text/csv").
  const mime = contentType.split(';')[0].trim()
  return {
    description: ext.toUpperCase().slice(1) + ' file',
    accept: { [mime]: [ext] },
  }
}

// Scopo: Estrae `filename` da un Content-Disposition. Gestisce sia
//        `filename="x.csv"` sia `filename*=UTF-8''x.csv` (RFC 5987).
//        Axios espone `response.headers` come oggetto plain-object
//        case-insensitive: niente Headers-API.
function extractFileName(response) {
  const cd = response.headers?.['content-disposition']
  if (!cd) return null
  // RFC 5987 ha priorita': se presente, gestisce caratteri non-ASCII.
  const m1 = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(cd)
  if (m1) {
    try { return decodeURIComponent(m1[1].trim()) } catch { /* fallback */ }
  }
  const m2 = /filename="?([^";]+)"?/i.exec(cd)
  if (m2) return m2[1].trim()
  return null
}
