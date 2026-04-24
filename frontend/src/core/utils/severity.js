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

// --- Mappa azioni giornale pratica ---
// Associa azione giornale a severity e icona per la timeline audit.
export const AZIONE_GIORNALE_MAP = {
  CREAZIONE: { severity: 'info', icon: 'pi pi-plus-circle' },
  CAMBIO_STATO: { severity: 'warn', icon: 'pi pi-sync' },
  ASSEGNAZIONE: { severity: 'secondary', icon: 'pi pi-user' },
  CAMBIO_PRIORITA: { severity: 'secondary', icon: 'pi pi-flag' },
  NOTA: { severity: 'secondary', icon: 'pi pi-comment' },
  ALLEGATO: { severity: 'secondary', icon: 'pi pi-paperclip' },
  SOSPENSIONE: { severity: 'warn', icon: 'pi pi-pause' },
  RIATTIVAZIONE: { severity: 'success', icon: 'pi pi-play' },
  CREAZIONE_FLUSSO: { severity: 'info', icon: 'pi pi-sitemap' },
  CAMBIO_STATO_FLUSSO: { severity: 'warn', icon: 'pi pi-sync' },
  GENERAZIONE: { severity: 'info', icon: 'pi pi-copy' },
}

const _AZIONE_DEFAULT = { severity: 'secondary', icon: 'pi pi-circle' }

// Scopo: Risolve severity+icon per azione giornale. Trim automatico, fallback secondario.
export function azioneGiornaleStyle(azione) {
  return AZIONE_GIORNALE_MAP[(azione || '').trim()] || _AZIONE_DEFAULT
}

// --- Mappa stati versione listino ---
// BOZZA=grigio, ATTIVA=verde, CHIUSA=arancio
export const STATO_VERSIONE_LISTINO_MAP = {
  BOZZA: 'secondary',
  ATTIVA: 'success',
  CHIUSA: 'warn',
}
export function statoVersioneListinoSeverity(codice) {
  return resolveSeverity(STATO_VERSIONE_LISTINO_MAP, codice)
}

// Scopo: Calcola lo stato "visibile" di una versione listino in modo data-driven:
//        se `valido_al` e` valorizzato e strettamente minore di oggi, la versione
//        e` operativamente CHIUSA anche se lo stato persistito in DB dice ancora
//        ATTIVA (il job notturno non e` ancora passato). Altrimenti restituisce
//        lo stato DB. Coerente con il principio fail-safe del brief listini v5
//        (brief-db-listini-stato-chiusa-sync.md §2): data = fonte di verita`
//        operativa, stato = flag informativo.
export function statoVersioneVisibile(versione) {
  if (!versione) return null
  const validoAl = versione.valido_al
  if (validoAl) {
    // Parsing tollerante: stringa ISO YYYY-MM-DD o Date
    const dataAl = validoAl instanceof Date ? validoAl : new Date(validoAl)
    const oggi = new Date()
    oggi.setHours(0, 0, 0, 0)
    dataAl.setHours(0, 0, 0, 0)
    if (dataAl < oggi) return 'CHIUSA'
  }
  return versione.stato
}

// --- Mappa stati preventivo vendita ---
// DRAFT=grigio, EMESSO=azzurro, ACCETTATO=verde, RIFIUTATO=rosso,
// SCADUTO=arancio, ANNULLATO=rosso
export const STATO_PREVENTIVO_MAP = {
  DRAFT: 'secondary',
  EMESSO: 'info',
  ACCETTATO: 'success',
  RIFIUTATO: 'danger',
  SCADUTO: 'warn',
  ANNULLATO: 'danger',
}

// Scopo: Shortcut per stato preventivo vendita.
export function statoPreventiveSeverity(codice) {
  return resolveSeverity(STATO_PREVENTIVO_MAP, codice)
}

// --- Mappa domini listino ---
// UTILITY=azzurro, COMMERCIO=arancio
export const DOMINIO_LISTINO_MAP = {
  UTILITY: 'info',
  COMMERCIO: 'warn',
}
export function dominioListinoSeverity(codice) {
  return resolveSeverity(DOMINIO_LISTINO_MAP, codice)
}

// --- Mappa stati contratto (v5) ---
// DRAFT=grigio, ATTIVO=verde, SOSPESO=arancio, CESSATO=rosso
export const STATO_CONTRATTO_MAP = {
  DRAFT: 'secondary',
  ATTIVO: 'success',
  SOSPESO: 'warn',
  CESSATO: 'danger',
}
export function statoContrattoSeverity(codice) {
  return resolveSeverity(STATO_CONTRATTO_MAP, codice)
}
