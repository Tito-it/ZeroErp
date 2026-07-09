// Scopo: client API Situazione aperta (stock documenti per fase, senza asse
//        temporale) — terza vista dei cruscotti fatturazione. Contratto BE:
//        docs/it/backend/vendite/manual/api_dashboard_aperto.md
import api from '../../core/api'

// GET /vendite/dashboard-aperto/
// Riepilogo stock: 4 aree documento sempre presenti, griglia per fase.
export function getDashboardAperto() {
  return api.get('/vendite/dashboard-aperto/')
}

// GET /vendite/dashboard-aperto/documenti/?area=&fase=&ritardo_giorni=&order_by=&order_dir=&page=&page_size=
// Drill-down paginato; ordinamento server-side (order_by/order_dir, whitelist
// BE), default "aperto da" DESC (i piu' in essere da prima).
export function listDashboardApertoDocumenti(params) {
  return api.get('/vendite/dashboard-aperto/documenti/', { params })
}
