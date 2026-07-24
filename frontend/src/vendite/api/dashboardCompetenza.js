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

// GET /vendite/dashboard-competenza/errori/?competenza_mese=&page=&page_size=
// Errori vivi fatturazione (task run in ERRORE + fatture critical), blocco 4.
export function listDashboardCompetenzaErrori(params = {}) {
  return api.get('/vendite/dashboard-competenza/errori/', { params })
}
