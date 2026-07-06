// Client API Lente 2 Backlog (non-collegati per anzianita' + classe).
// 2 endpoint GET read-only su vendite.vw_dash_backlog_* — doc BE:
// docs/it/backend/vendite/manual/api_dashboard_backlog.md
import api from '../../core/api'

// GET /vendite/dashboard-backlog/
// Contatori per classe di azionabilita' (3 classi sempre presenti + aree).
export function getDashboardBacklog() {
  return api.get('/vendite/dashboard-backlog/')
}

// GET /vendite/dashboard-backlog/documenti/?classe=&area=&page=&page_size=
// Lista paginata per anzianita' (i piu' vecchi prima), filtri opzionali.
export function listDashboardBacklogDocumenti(params = {}) {
  return api.get('/vendite/dashboard-backlog/documenti/', { params })
}
