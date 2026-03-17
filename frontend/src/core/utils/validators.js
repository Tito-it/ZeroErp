// Scopo: Validatori generici riutilizzabili per campi form.

/**
 * Scopo: Validazione formato email/PEC base.
 * Controlla: non vuoto, niente spazi, presenza "@", parte locale non vuota,
 * dominio con almeno un ".", parti dominio non vuote.
 * Non e' una validazione RFC completa — e' un controllo UX pratico.
 *
 * @param {string} value - valore da validare
 * @returns {boolean} true se il formato e' accettabile
 */
export function isEmailValid(value) {
  if (!value || typeof value !== 'string') return false
  const trimmed = value.trim()
  if (!trimmed || trimmed.includes(' ')) return false

  const atIndex = trimmed.indexOf('@')
  // deve avere esattamente un @, non all'inizio ne' alla fine
  if (atIndex < 1 || atIndex !== trimmed.lastIndexOf('@')) return false

  const local = trimmed.substring(0, atIndex)
  const domain = trimmed.substring(atIndex + 1)

  // parte locale non vuota
  if (!local) return false

  // dominio deve contenere almeno un punto
  const dotIndex = domain.indexOf('.')
  if (dotIndex < 1) return false

  // nessuna parte del dominio vuota (no ".." e non finisce con ".")
  const parts = domain.split('.')
  if (parts.some(p => !p)) return false

  // estensione almeno 2 caratteri
  if (parts[parts.length - 1].length < 2) return false

  return true
}
