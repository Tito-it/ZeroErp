// Helper centralizzati per mappatura codici → severity PrimeVue Tag/Badge.
// Un solo punto di modifica per i colori di stato in tutta l'applicazione.
// Ogni mappa associa codice_interno (con trim) a una severity PrimeVue.

// --- Resolver generico ---
// Scopo: Risolve severity da una mappa. Trim automatico, fallback 'secondary'.
export function resolveSeverity(map, codice) {
  return map[(codice || '').trim()] || 'secondary'
}

// --- Mappa stati cliente ---
// AT=attivo(verde), CH/CF/CM/CW=chiuso(rosso), AN=annulla(arancio),
// PR=pre-contratto(blu), SC/SF=sospeso(secondario), RS=richiesta sosp.(arancio)
export const STATO_CLIENTE_MAP = {
  AT: 'success',
  CH: 'danger',
  CF: 'danger',
  CM: 'danger',
  CW: 'danger',
  AN: 'warn',
  RS: 'warn',
  PR: 'info',
  AG: 'secondary',
  SC: 'secondary',
  SF: 'secondary',
}

// Scopo: Shortcut per stato cliente (usabile direttamente nei template).
export function statoClienteSeverity(codice) {
  return resolveSeverity(STATO_CLIENTE_MAP, codice)
}

// --- Mappa stati fornitore ---
// VE=in verifica(blu), AT=attivo(verde), SO=sospeso(arancio),
// CE=cessato(rosso), BL=blacklist(rosso)
export const STATO_FORNITORE_MAP = {
  VE: 'info',
  AT: 'success',
  SO: 'warn',
  CE: 'danger',
  BL: 'danger',
}

// Scopo: Shortcut per stato fornitore (usabile direttamente nei template).
export function statoFornitoreSeverity(codice) {
  return resolveSeverity(STATO_FORNITORE_MAP, codice)
}
