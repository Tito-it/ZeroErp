// Client API Lente 1 Competenza (funnel commessa → fattura per competenza).
// 3 endpoint GET read-only su vendite.vw_dash_competenza_* — doc BE:
// docs/it/backend/vendite/manual/api_dashboard_competenza.md
import api from '../../core/api'

// GET /vendite/dashboard-competenza/?anno=YYYY
// Aggregata 12 mesi × 4 stadi (mesi vuoti con zeri, contratto simmetrico DL-8).
export function getDashboardCompetenza(anno) {
  return api.get('/vendite/dashboard-competenza/', { params: { anno } })
}

// GET /vendite/dashboard-competenza/attivita/?competenza_mese=&stadio=&solo_ritardo=&order_by=&order_dir=&page=&page_size=
// Drill-down paginato delle attivita' del mese (filtro stadio/ritardo opzionale);
// ordinamento server-side (order_by/order_dir, whitelist BE), default
// "data attivita'" DESC.
export function listDashboardCompetenzaAttivita(params = {}) {
  return api.get('/vendite/dashboard-competenza/attivita/', { params })
}

// GET /vendite/dashboard-competenza/commesse/?competenza_mese=&stadio=&solo_ritardo=&order_by=&order_dir=&page=&page_size=
// Drill-down AGGREGATO per commessa (DEC-4): una riga per commessa nel perimetro
// (mese + stadio), con n attivita', totali valore/fatturato ed estremi data. Il
// dettaglio a grana attivita' resta nel drawer di gestione. Ordinamento
// server-side (order_by whitelist BE: valore_tot default), tiebreak su commessa.
export function listDashboardCompetenzaCommesse(params = {}) {
  return api.get('/vendite/dashboard-competenza/commesse/', { params })
}

// GET /vendite/dashboard-competenza/gruppi/?competenza_mese=&stadio=&order_by=&order_dir=&page=&page_size=
// Elenco dei GRUPPI FATTURABILI: l'unita' su cui l'operatore decide nella card
// «Da emettere» — un documento sorgente (PRV-0012, CTR-0007…) oppure gli oneri
// di una commessa, che documento non hanno e senza questa lista resterebbero
// lavoro conteggiato ma non azionabile.
//
// La `gruppo_key` di ogni riga e' la STESSA che si rimanda a runFatturazione
// nel campo `gruppi`: non va costruita ne' trasformata lato FE.
// La risposta porta anche `riepilogo` (n gruppi/attivita'/valore di TUTTO il
// perimetro, non della pagina): e' la riga di totali del cockpit.
export function listDashboardCompetenzaGruppi(params = {}) {
  return api.get('/vendite/dashboard-competenza/gruppi/', { params })
}

// GET /vendite/dashboard-competenza/errori/?competenza_mese=&page=&page_size=
// Errori vivi fatturazione (task run in ERRORE + fatture critical), blocco 4.
export function listDashboardCompetenzaErrori(params = {}) {
  return api.get('/vendite/dashboard-competenza/errori/', { params })
}
