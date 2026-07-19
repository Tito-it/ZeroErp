// Scopo: config di presentazione per area del funnel vendite, condivisa dai
//        cruscotti fatturazione (Situazione aperta e Lente Backlog): ordine
//        funnel, rotta lista FE per "apri documento" (null = area senza
//        view lista, riga consultiva) e severity stato documento (shortcut
//        centralizzate in core/utils/severity.js). La misura euro/count NON
//        vive qui: la decide il BE nel payload (valore_* null = area a
//        conteggi, DL-11) — il FE legge, non ri-decide. Estratta 2026-07-06
//        (regola del 2, ok Tid): era duplicata in DashboardFatturazioneView
//        (poi trasformata in SituazioneApertaView, Fase 3) e
//        DashboardBacklogView, con drift garantito su rinomina rotte o
//        nuova area.
import { MANAGE_ICONS } from '../core/constants'
import { labelOrCode } from '../core/utils/i18nLabel'
import {
  statoCommessaSeverity,
  statoContrattoSeverity,
  statoDdtSeverity,
  statoOffertaSeverity,
  statoOrdineSeverity,
  statoPreventiveSeverity,
  statoResoSeverity,
} from '../core/utils/severity'

// Ordine di iterazione = ordine funnel (allineato alla whitelist BE
// DASH_FATTURAZIONE_AREE). DDT dopo ORDINI (e' il suo veicolo di
// fatturazione differita, DL-21); RESI in coda (flusso inverso, vive solo
// nel Backlog — DL-24).
// `apertoHintKey` (opzionale): chiave i18n dell'hint mostrato sulla card
// della Situazione aperta quando la misura dell'area non e' ovvia — oggi
// solo ORDINI (misura MISTA, DL-23 emendato: netta per trigger S/C, piena
// per CONFERMATO). Vive qui e non nella view: la semantica e' per-area,
// come route e severity.
export const DASH_AREA_CONFIG = {
  PREVENTIVI: { route: '/vendite/preventivi', severity: statoPreventiveSeverity },
  ORDINI: {
    route: '/vendite/ordini',
    severity: statoOrdineSeverity,
    apertoHintKey: 'situazione_aperta.card_ordini_hint',
  },
  DDT: { route: '/vendite/ddt', severity: statoDdtSeverity },
  OFFERTE: { route: '/vendite/offerte', severity: statoOffertaSeverity },
  CONTRATTI: { route: '/vendite/contratti', severity: statoContrattoSeverity },
  COMMESSE: { route: null, severity: statoCommessaSeverity },
  RESI: { route: '/vendite/resi', severity: statoResoSeverity },
}

export const DASH_AREE = Object.keys(DASH_AREA_CONFIG)

// Scopo: severity Tag per lo stato documento di un'area (fallback secondary
//        per aree future non ancora mappate — fail-visible, mai crash).
export function dashAreaSeverity(area, statoCodiceInterno) {
  const fn = DASH_AREA_CONFIG[area]?.severity
  return fn ? fn(statoCodiceInterno) : 'secondary'
}

// Scopo: decodifiche i18n fail-visible dei vocabolari condivisi dei cruscotti
//        (gruppo dash_comune: aree, fasi, motivi fermo) — label tradotta se la
//        chiave esiste, altrimenti il codice grezzo. Estratte 2026-07-07
//        (regola del 2, ok Tid): erano duplicate in DashboardBacklogView e
//        SituazioneApertaView. I caller passano (t, te) di useI18n.
export function dashAreaLabel(t, te, area) {
  return labelOrCode(t, te, `dash_comune.area_${String(area).toLowerCase()}`, area)
}

export function dashFaseLabel(t, te, fase) {
  return labelOrCode(t, te, `dash_comune.fase_${String(fase).toLowerCase()}`, fase)
}

export function dashMotivoLabel(t, te, motivo) {
  return labelOrCode(t, te, `dash_comune.motivo_fermo.${motivo}`, motivo)
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
