// Scopo: config di presentazione per area del funnel vendite, condivisa dai
//        cruscotti fatturazione (dashboard 5-card e Lente Backlog): ordine
//        funnel, rotta lista FE per "apri documento" (null = area senza
//        view lista, riga consultiva), severity stato documento (shortcut
//        centralizzate in core/utils/severity.js) e tipo misura euro/count
//        (decisioni D-2/D-3/D-4). Estratta 2026-07-06 (regola del 2, ok
//        Tid): era duplicata in DashboardFatturazioneView e
//        DashboardBacklogView, con drift garantito su rinomina rotte o
//        nuova area.
import { MANAGE_ICONS } from '../core/constants'
import {
  statoCommessaSeverity,
  statoContrattoSeverity,
  statoOffertaSeverity,
  statoOrdineSeverity,
  statoPreventiveSeverity,
} from '../core/utils/severity'

// Ordine di iterazione = ordine funnel (allineato alla whitelist BE
// DASH_FATTURAZIONE_AREE).
export const DASH_AREA_CONFIG = {
  PREVENTIVI: { route: '/vendite/preventivi', severity: statoPreventiveSeverity, kind: 'euro' },
  ORDINI: { route: '/vendite/ordini', severity: statoOrdineSeverity, kind: 'euro' },
  OFFERTE: { route: '/vendite/offerte', severity: statoOffertaSeverity, kind: 'count' },
  CONTRATTI: { route: '/vendite/contratti', severity: statoContrattoSeverity, kind: 'count' },
  COMMESSE: { route: null, severity: statoCommessaSeverity, kind: 'euro' },
}

export const DASH_AREE = Object.keys(DASH_AREA_CONFIG)

// Scopo: severity Tag per lo stato documento di un'area (fallback secondary
//        per aree future non ancora mappate — fail-visible, mai crash).
export function dashAreaSeverity(area, statoCodiceInterno) {
  const fn = DASH_AREA_CONFIG[area]?.severity
  return fn ? fn(statoCodiceInterno) : 'secondary'
}

// Scopo: azione riga "apri documento" dei drill-down dashboard: naviga alla
//        lista dell'area con la ricerca precaricata (?search=, pattern
//        ricerca-universale; il deep-link azzera i default data della lista
//        target via useSearchTable). Nascosta se l'area non ha una view
//        lista o il documento non ha codice.
export function buildApriDocumentoAction({ area, codice, label, router }) {
  const route = DASH_AREA_CONFIG[area]?.route
  return {
    key: 'apri',
    label,
    icon: MANAGE_ICONS.LIST,
    visible: Boolean(route && codice),
    command: () => router.push({ path: route, query: { search: codice } }),
  }
}
