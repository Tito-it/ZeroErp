// Client API Lente 2 Backlog (non-collegati per anzianita' + classe).
// 2 endpoint GET read-only su vendite.vw_dash_backlog_* — doc BE:
// docs/it/backend/vendite/manual/api_dashboard_backlog.md
import api from '../../core/api'

// GET /vendite/dashboard-backlog/
// Contatori per classe di azionabilita' (3 classi sempre presenti + aree).
export function getDashboardBacklog() {
  return api.get('/vendite/dashboard-backlog/')
}

// GET /vendite/dashboard-backlog/documenti/?classe=&area=&order_by=&order_dir=&limit=&offset=
// Lista paginata; ordinamento server-side (order_by/order_dir, whitelist BE),
// default "fermo da" DESC (i piu' vecchi prima).
export function listDashboardBacklogDocumenti(params = {}) {
  return api.get('/vendite/dashboard-backlog/documenti/', { params })
}

// GET /vendite/dashboard-backlog/documenti/export/?formato=csv|xlsx&<stessi filtri>
// Export della STESSA lista: colonne/ordine dalla configurazione lista
// dell'operatore (catalogo `vendite.dash_backlog_documenti`).
// ⚠️ `formato`, non `format`: quest'ultimo e' magic per DRF.
export function exportDashboardBacklogDocumenti(params = {}) {
  return api.get('/vendite/dashboard-backlog/documenti/export/', {
    params,
    responseType: 'blob',
  })
}
