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

// --- Mappa stati pratica ---
// BOZZA=secondario, APERTA=info, SOSPESA=arancio, CHIUSA=verde, ANNULLATA=rosso
export const STATO_PRATICA_MAP = {
  BOZZA: 'secondary',
  APERTA: 'info',
  SOSPESA: 'warn',
  CHIUSA: 'success',
  ANNULLATA: 'danger',
}

// Scopo: Shortcut per stato pratica.
export function statoPraticaSeverity(codice) {
  return resolveSeverity(STATO_PRATICA_MAP, codice)
}

// --- Mappa priorita' pratica ---
// BASSA=secondario, NORMALE=info, ALTA=arancio, URGENTE=rosso
export const PRIORITA_PRATICA_MAP = {
  BASSA: 'secondary',
  NORMALE: 'info',
  ALTA: 'warn',
  URGENTE: 'danger',
}
// Scala cromatica: grigio(bassa) → azzurro(normale) → arancio(alta) → rosso(urgente)

// Scopo: Shortcut per priorita' pratica.
export function prioritaPraticaSeverity(codice) {
  return resolveSeverity(PRIORITA_PRATICA_MAP, codice)
}

// --- Mappa stati flusso pratica ---
// DA_ESEGUIRE=secondario, IN_CORSO=info, COMPLETATO=verde, SOSPESO=arancio,
// ANNULLATO=rosso, ERRORE=rosso
export const STATO_FLUSSO_MAP = {
  DA_ESEGUIRE: 'secondary',
  IN_CORSO: 'info',
  COMPLETATO: 'success',
  SOSPESO: 'warn',
  ANNULLATO: 'danger',
  ERRORE: 'danger',
}

// Scopo: Shortcut per stato flusso pratica.
export function statoFlussoSeverity(codice) {
  return resolveSeverity(STATO_FLUSSO_MAP, codice)
}

// --- Mappa esiti flusso ---
// POSITIVO=verde, NEGATIVO=rosso, PARZIALE=arancio, NON_APPLICABILE=secondario
export const ESITO_FLUSSO_MAP = {
  POSITIVO: 'success',
  NEGATIVO: 'danger',
  PARZIALE: 'warn',
  NON_APPLICABILE: 'secondary',
}

// Scopo: Shortcut per esito flusso.
export function esitoFlussoSeverity(codice) {
  return resolveSeverity(ESITO_FLUSSO_MAP, codice)
}
