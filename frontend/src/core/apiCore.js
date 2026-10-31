// Scopo: API client per endpoint core cross-dominio (lookup, search).
// Usa l'istanza axios condivisa con interceptor JWT.

import api from './api'

const BASE = '/core'

// --- Emittenti fiscali: il vocabolario che ogni dominio usa per il campo
//     «emittente» (`useEmittenteFiscaleField`). L'endpoint lo serve
//     `amm_software`, ma il lookup e' di tutti: per questo sta qui. ---
export function listEmittentiFiscali() {
  return api.get('/amm-software/lookup/emittenti-fiscali/')
}

// --- Lookup codici generico (qualifiche, stati, ecc.) ---

export function lookupCodici(rel, params = {}) {
  return api.get(`${BASE}/lookup/codici/`, { params: { rel, ...params } })
}

// --- Lookup anagrafiche cross-dominio (Sprint 3) ---

export function lookupTipiSoggettoDettaglio() {
  return api.get(`${BASE}/lookup/tipi-soggetto-dettaglio/`)
}

export function lookupTipiRuoliPerNatura(naturaSoggetto = null) {
  const params = {}
  if (naturaSoggetto) params.natura_soggetto = naturaSoggetto
  return api.get(`${BASE}/lookup/tipi-ruoli-natura/`, { params })
}

export function lookupFormeGiuridiche(tipoSoggettoDettaglioId = null) {
  const params = {}
  if (tipoSoggettoDettaglioId) params.tipo_soggetto_dettaglio_id = tipoSoggettoDettaglioId
  return api.get(`${BASE}/lookup/forme-giuridiche/`, { params })
}

export function lookupMatriceIndirizzi(tipoSoggettoDettaglioId) {
  return api.get(
    `${BASE}/lookup/tipi-soggetto-dettaglio/${tipoSoggettoDettaglioId}/indirizzi/`
  )
}

export function lookupMatriceIndirizziRuolo(tipoRuoloCodice) {
  return api.get(
    `${BASE}/lookup/tipi-ruolo/${tipoRuoloCodice}/indirizzi/`
  )
}

// Scopo: Lookup utility ammesse per un ruolo soggetto (es. CL), filtrate
// per l'emittente dell'utente corrente (intersezione ruolo + EF + configurazione).
// Usata dalle combo filtro nelle liste (clienti, fornitori, ecc.).
export function lookupUtilitiesPerEmittente(ruolo) {
  return api.get(`${BASE}/lookup/utilities-per-emittente/`, { params: { ruolo } })
}

// Scopo: Lookup dedicato conti contabili con filtro tipo (A=Acquisto, V=Vendita).
// Espone tipo_conto che il lookup generico config.conti_contabili non ritorna.
export function lookupContiContabili(tipo) {
  const params = tipo ? { tipo } : {}
  return api.get(`${BASE}/lookup/conti-contabili/`, { params })
}

// Scopo: il vocabolario di `config.tipi_entita` — codice, `etichetta_key`
//        (l'indirizzo i18n che il DB dichiara), `key_selector` — solo i tipi
//        vivi. Lookup dedicato: la tabella non ha `id`/`descrizione` e il
//        generico non la serve. Envelope `{"results": [...]}`.
export function lookupTipiEntita() {
  return api.get(`${BASE}/lookup/tipi-entita/`)
}

// Scopo: il registro delle AZIONI DI RIGA (`config.azioni_riga`) — per ogni
//        azione attiva, `codice_interno` e le due colonne della sua superficie
//        col motivo del pulsante spento (`colonna_motivo`) e la sua chiave i18n
//        (`colonna_motivo_chiave`). Lookup dedicato, envelope `{"results"}`.
//        Lo legge il BB `useAzioneRiga`.
export function lookupAzioniRiga() {
  return api.get(`${BASE}/lookup/azioni-riga/`)
}

// --- Sistema codici ---

export function lookupSistemaCodici(schema, tabella, colonna = 'codice') {
  return api.get(`${BASE}/lookup/sistema-codici/`, { params: { schema, tabella, colonna } })
}

export function searchComuni(search, limit = 20) {
  return api.get(`${BASE}/lookup/comuni/`, { params: { search, limit } })
}

export function searchStradario(comuneId, search, limit = 20) {
  return api.get(`${BASE}/search/stradario/`, {
    params: { comune_id: comuneId, search, limit }
  })
}

export function searchStradarioGenerale(search, limit = 30) {
  return api.get(`${BASE}/search/stradario-generale/`, {
    params: { search, limit }
  })
}

// --- Parametri di sistema ---

export function fetchParameterDefaults(codes) {
  return api.get(`${BASE}/parameters/defaults/`, {
    params: { codes: codes.join(',') }
  })
}

// La pagina della lista `config.parametri_impostazioni` (dal 2026-10-31): i
// parametri di lista (`search`, `limit`/`offset`, `order_by`/`order_dir`)
// passano come sono. In piu', tutte opzionali:
//   - categoria_cliente_id (number): attiva il livello categoria_cliente nella
//     cascata visualizzata (post brief DB 2026-05-19, migration 20260519-01).
//   - billing_account_id (number): alternativa al precedente; il BE risolve la
//     categoria dal BA (BB `categoria_cliente_da_query`): BA inesistente o
//     fuori scope → 404 E_ANAG_NOT_FOUND. Ignorato se categoria_cliente_id
//     e' valorizzato.
export function fetchParameterSettings(options = {}) {
  const { categoria_cliente_id, billing_account_id, ...params } = options
  if (categoria_cliente_id != null) {
    params.categoria_cliente_id = categoria_cliente_id
  } else if (billing_account_id != null) {
    params.billing_account_id = billing_account_id
  }
  return api.get(`${BASE}/parameters/settings/`, { params })
}

// Scope ammessi: 'user' (default, personale) | 'emittente' (admin, aziendale)
// | 'categoria_cliente' (admin, per categoria — Phase B 2026-05-19, richiede
// `categoriaClienteId` esplicito; il BE rifiuta valori non-positivi).
// Il default 'user' e' definito anche in PARAMETER_SCOPE.USER
// (composables/useParameterSettings.js); teniamo qui la stringa letterale solo
// come fallback difensivo: le chiamate dovrebbero sempre passare un valore
// esplicito tramite il composable.
export function upsertParameterOverride(
  parameterCode, value, scope = 'user', { categoriaClienteId = null } = {},
) {
  const payload = { parameter_code: parameterCode, value, scope }
  if (scope === 'categoria_cliente' && categoriaClienteId != null) {
    payload.categoria_cliente_id = categoriaClienteId
  }
  return api.post(`${BASE}/parameters/settings/override/`, payload)
}

export function deleteParameterOverride(
  overrideId, scope = 'user', { categoriaClienteId = null } = {},
) {
  const params = { scope }
  if (scope === 'categoria_cliente' && categoriaClienteId != null) {
    params.categoria_cliente_id = categoriaClienteId
  }
  return api.delete(`${BASE}/parameters/settings/override/${overrideId}/`, {
    params
  })
}

// --- Billing account lookup (ricerca ricca cross-dominio) ---

// Scopo: Cerca billing_account per autocomplete.
//        Backend: GET /api/v1/anagrafiche/billing-account/lookup/
//        Ricerca multi-campo (codice, ragione sociale, id fiscale, PDP).
//        Filtro utility e scope emittente automatici lato backend.
export function lookupBillingAccount(params = {}) {
  return api.get('/anagrafiche/billing-account/lookup/', { params })
}

// Scopo: Restituisce un singolo BA arricchito per restore dell'AutoComplete in edit.
//        Backend: GET /api/v1/anagrafiche/billing-account/{id}/lookup/
export function getBillingAccountLookupById(id) {
  return api.get(`/anagrafiche/billing-account/${id}/lookup/`)
}

// --- Risorse umane lookup (picker «chi governa»: responsabile commessa) ---

// Scopo: Le risorse umane ATTIVE per un picker di selezione, con ricerca
//        libera opzionale (min 3 caratteri). Envelope `{"results": [...]}`,
//        righe `{id, display, attivo, qualifica_descrizione,
//        unita_organizzativa_descrizione}`.
//        Backend: GET /api/v1/anagrafiche/risorse-umane/lookup/ (cross-dominio,
//        skip_area_check). Nasce per il responsabile della commessa
//        (brief-db-modifiche-certe-ciclo-vendita-e-articolo §5.5 voce 4).
export function lookupRisorseUmane(params = {}) {
  return api.get('/anagrafiche/risorse-umane/lookup/', { params })
}

// --- Istanze utility lookup: le forniture (preventivo, pratica) ---

// Scopo: Cerca le forniture per autocomplete: una riga per billing account,
//        cioe' per coppia istanza+utility (`id` = istanza, `billing_account_id`).
//        Backend: GET /api/v1/anagrafiche/istanze-utility/lookup/
//        Ricerca multi-campo (codice istanza, ragione sociale, indirizzo).
//        Filtri utility, soggetto e ruolo opzionali.
//        Scope emittente automatico lato backend (sul BA della riga).
export function lookupIstanzeUtility(params = {}) {
  return api.get('/anagrafiche/istanze-utility/lookup/', { params })
}

// Scopo: Restituisce una singola istanza arricchita per restore AutoComplete
//        (i campi del BA solo se l'istanza ne ha uno).
//        Backend: GET /api/v1/anagrafiche/istanze-utility/{id}/lookup/
export function getIstanzaUtilityLookupById(id) {
  return api.get(`/anagrafiche/istanze-utility/${id}/lookup/`)
}

// --- Soggetti-ruoli lookup (selezione contesto pratica) ---

// Scopo: Cerca soggetti-ruoli per autocomplete: una riga per soggetto_ruolo
//        + riga "senza ruolo" per i soggetti privi di ruoli (senza istanze).
//        Backend: GET /api/v1/anagrafiche/soggetti-ruoli/lookup/
//        Ricerca su ragione sociale, CF, P.IVA. Scope emittente sul ruolo CL.
export function lookupSoggettiRuoli(params = {}) {
  return api.get('/anagrafiche/soggetti-ruoli/lookup/', { params })
}

// Scopo: Restore by-id della riga lookup (riapertura form in edit).
//        Backend: GET /api/v1/anagrafiche/soggetti-ruoli/lookup-by-id/
//        Chiavi alternative: { soggetto_ruolo_id } oppure { soggetto_id }.
export function getSoggettoRuoloLookupById(params = {}) {
  return api.get('/anagrafiche/soggetti-ruoli/lookup-by-id/', { params })
}
