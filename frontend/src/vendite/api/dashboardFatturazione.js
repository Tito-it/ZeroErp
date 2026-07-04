// Client API Dashboard Fatturazione (controllo del transito per competenza).
// 2 endpoint GET read-only su vendite.vw_dash_fatturazione_* — doc BE:
// docs/it/backend/vendite/manual/api_dashboard_fatturazione.md
import api from '../../core/api'

// GET /vendite/dashboard-fatturazione/?anno=YYYY
// Matrice 12 mesi × 5 aree (mesi vuoti con zeri, decisione D-5).
export function getDashboardFatturazione(anno) {
  return api.get('/vendite/dashboard-fatturazione/', { params: { anno } })
}

// GET /vendite/dashboard-fatturazione/fermi/?competenza_mese=&area=&page=&page_size=
// Drill-down paginato degli elementi fermi di un'area nel mese.
export function listDashboardFatturazioneFermi(params = {}) {
  return api.get('/vendite/dashboard-fatturazione/fermi/', { params })
}
