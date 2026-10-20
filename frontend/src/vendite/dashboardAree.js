// Scopo: config di presentazione per area del funnel vendite, condivisa dai
//        cruscotti fatturazione (Situazione aperta e Lente Backlog): ordine
//        funnel, drawer di dettaglio + icona per "apri documento" e severity
//        stato documento (shortcut centralizzate in core/utils/severity.js).
//        La misura euro/count NON vive qui: la decide il BE nel payload
//        (valore_* null = area a conteggi, DL-11) — il FE legge, non ri-decide.
//        Estratta 2026-07-06 (regola del 2, ok Tid): era duplicata in
//        DashboardFatturazioneView (poi trasformata in SituazioneApertaView,
//        Fase 3) e DashboardBacklogView, con drift garantito su rinomina rotte
//        o nuova area.
import { MANAGE_ICONS } from '../core/constants'
import { NAV_ICONS } from '../core/navigation'
import { labelOrCode } from '../core/utils/i18nLabel'
import { DOCUMENTO_DRAWER_TIPI } from '../core/drawerEntita'
import {
  statoCommessaSeverity,
  statoContrattoSeverity,
  statoDdtSeverity,
  statoOffertaSeverity,
  statoOrdineSeverity,
  statoPreventiveSeverity,
  statoResoSeverity,
} from '../core/utils/severity'

// ⭐ La chiave e' il codice della SORGENTE (`config.sorgenti.codice_interno`),
// lo stesso che il BE mette in `area`: dal 2026-10-20 il plurale (`ORDINI`,
// `RESI`…) e' ritirato (brief-db-grammatica-unica-documenti, 2d / G-6). Per
// questo coincide con le chiavi di DOCUMENTO_DRAWER_TIPI, salvo la commessa,
// che dal cruscotto apre il drawer di GESTIONE.
// Ordine di iterazione = ordine funnel (allineato alla whitelist BE
// DASH_FATTURAZIONE_AREE). Il DDT dopo l'ordine (e' il suo veicolo di
// fatturazione differita, DL-21); il reso in coda (flusso inverso, vive solo
// nel Backlog — DL-24).
// `drawerTipo`: chiave del registro dei drawer (`core/drawerEntita.js`) — il drawer di
// dettaglio che l'azione "apri documento" apre sull'id di riga (null = area
// senza drawer, riga consultiva). COMMESSA usa il drawer di GESTIONE, non
// quello leggero dei passaggi: dal Backlog si governa la commessa.
// `icon`: icona dell'azione, quella dell'area (le stesse della sidebar) —
// nelle liste drill-down, che sono cross-area, l'icona dice quale documento
// si sta per aprire. COMMESSA non ha voce di navigazione: MANAGE_ICONS.
// `apertoHintKey` (opzionale): chiave i18n dell'hint mostrato sulla card
// della Situazione aperta quando la misura dell'area non e' ovvia — oggi
// solo ORDINE_VENDITA (misura MISTA, DL-23 emendato: netta per trigger S/C, piena
// per CONFERMATO). Vive qui e non nella view: la semantica e' per-area,
// come drawer, icona e severity.
export const DASH_AREA_CONFIG = {
  [DOCUMENTO_DRAWER_TIPI.PREVENTIVO]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.PREVENTIVO,
    icon: NAV_ICONS.PREVENTIVI,
    severity: statoPreventiveSeverity,
  },
  [DOCUMENTO_DRAWER_TIPI.ORDINE_VENDITA]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.ORDINE_VENDITA,
    icon: NAV_ICONS.ORDINI,
    severity: statoOrdineSeverity,
    apertoHintKey: 'vendite.situazione_aperta.card_ordini_hint',
  },
  [DOCUMENTO_DRAWER_TIPI.DDT_VENDITA]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.DDT_VENDITA,
    icon: NAV_ICONS.DDT,
    severity: statoDdtSeverity,
  },
  [DOCUMENTO_DRAWER_TIPI.OFFERTA_COMMERCIALE]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.OFFERTA_COMMERCIALE,
    icon: NAV_ICONS.OFFERTE,
    severity: statoOffertaSeverity,
  },
  [DOCUMENTO_DRAWER_TIPI.CONTRATTO]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.CONTRATTO,
    icon: NAV_ICONS.CONTRATTI,
    severity: statoContrattoSeverity,
  },
  [DOCUMENTO_DRAWER_TIPI.COMMESSA]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.COMMESSA_GESTIONE,
    icon: MANAGE_ICONS.COMMESSA,
    severity: statoCommessaSeverity,
  },
  [DOCUMENTO_DRAWER_TIPI.RESO_VENDITA]: {
    drawerTipo: DOCUMENTO_DRAWER_TIPI.RESO_VENDITA,
    icon: NAV_ICONS.RESI,
    severity: statoResoSeverity,
  },
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
  return labelOrCode(t, te, `vendite.dash_comune.area_${String(area).toLowerCase()}`, area)
}

export function dashFaseLabel(t, te, fase) {
  return labelOrCode(t, te, `vendite.dash_comune.fase_${String(fase).toLowerCase()}`, fase)
}

export function dashMotivoLabel(t, te, motivo) {
  return labelOrCode(t, te, `vendite.dash_comune.motivo_fermo.${motivo}`, motivo)
}

// Scopo: azione riga "apri documento" dei drill-down dashboard: apre il DRAWER
//        di gestione del documento della riga, per id — stesso meccanismo delle
//        tappe del pannello "Passaggi" (DocumentoDrawerHost + registry
//        registro dei drawer). Prima navigava alla lista d'area con
//        ?search=<codice>: l'operatore atterrava su una lista filtrata e doveva
//        comunque aprire la riga a mano, perdendo il contesto del cruscotto
//        (cambio rotta). Nascosta se l'area non ha un drawer o la riga non ha
//        id di dominio. `onApri(drawerTipo, documentoId)` lo passa il caller:
//        tipicamente `apri` di useDocumentoDrawer.
export function buildApriDocumentoAction({ area, documentoId, label, onApri }) {
  const config = DASH_AREA_CONFIG[area]
  const drawerTipo = config?.drawerTipo ?? null
  return {
    key: 'apri',
    label,
    // Icona dell'area (la lista e' cross-area: dice quale documento si apre).
    // Fallback generico per aree future non ancora mappate — fail-visible,
    // mai un'azione senza icona.
    icon: config?.icon ?? MANAGE_ICONS.INSPECT,
    visible: Boolean(drawerTipo && documentoId != null),
    command: () => onApri(drawerTipo, documentoId),
  }
}
