// Client API Lente 1 Competenza (funnel commessa → fattura per competenza).
// 3 endpoint GET read-only su vendite.vw_dash_competenza_* — doc BE:
// docs/it/backend/vendite/manual/api_dashboard_competenza.md
import api from '../../core/api'

// GET /vendite/dashboard-competenza/?anno=YYYY
// Aggregata 12 mesi × 4 stadi (mesi vuoti con zeri, contratto simmetrico DL-8).
export function getDashboardCompetenza(anno) {
  return api.get('/vendite/dashboard-competenza/', { params: { anno } })
}

// GET /vendite/dashboard-competenza/attivita/?competenza_mese=&stadio=&solo_ritardo=&page=&page_size=
// Drill-down paginato delle attivita' del mese (filtro stadio/ritardo opzionale).
export function listDashboardCompetenzaAttivita(params = {}) {
  return api.get('/vendite/dashboard-competenza/attivita/', { params })
}

// GET /vendite/dashboard-competenza/errori/?competenza_mese=&page=&page_size=
// Errori vivi fatturazione (task run in ERRORE + fatture critical), blocco 4.
export function listDashboardCompetenzaErrori(params = {}) {
  return api.get('/vendite/dashboard-competenza/errori/', { params })
}
