// Scopo: Utility centralizzate per formattazione valori.
// Un solo punto di modifica per formati numerici/dimensioni in tutta l'applicazione.

/**
 * Formatta una dimensione in byte in formato leggibile (B, KB, MB, GB).
 *
 * @param {number|null} bytes - Dimensione in byte
 * @returns {string} - Stringa formattata o vuota se null/0
 */
export function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}
