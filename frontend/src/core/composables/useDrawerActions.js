// Scopo: helper per costruire l'array `actions` di DrawerActionsBar a partire
//   dal payload `availableActions` esposto dal BE (script.fn_available_actions_*).
//
// Una entry availableActions BE = una azione kind:'state' lato FE. Il dettaglio
// `requires_date` / `requires_confirm` resta opaco al BB: il chiamante riceve
// l'azione intera nel callback `onAction` e decide se aprire dialog/confirm.
//
// Centralizza il pattern duplicato in PreventiviDrawer/ContrattoDrawer
// (template `<Button v-for="action in availableActions" ...>` + handler
// `onCambiaStato(action)` parametrizzato).

import { unref } from 'vue'

// Scopo: trasforma availableActions (ref/computed o array) in azioni
//   DrawerActionsBar kind:'state'. Il chiamante poi le compone con eventuali
//   altre azioni (manage sub-drawer, secondary export) nel computed finale.
//
//   `readonly` (2026-06-01): in PURE read-only — permesso LETTURA, pannello
//   split, oppure readonly forzato via prop (es. ispezione di un'entita'
//   "altra") — le azioni di stato che abilitano un AGGIORNAMENTO spariscono
//   del tutto (allineamento ai drawer senza barra azioni, es. soggetti/BA).
//   NB: il chiamante DEVE passare il readonly "puro"
//   (`parentReadonly || props.readonly`), NON l'isReadonly del drawer che
//   include anche il lock-di-stato: un contratto ATTIVO ha la form bloccata
//   ma deve comunque mostrare "Cessa".
export function mapAvailableActionsToDrawerActions({
  availableActions,
  t,
  onAction,
  readonly = false,
}) {
  if (unref(readonly)) return []
  const list = unref(availableActions) || []
  return list.map(action => ({
    key: action.key || `state-${action.target_state}`,
    kind: 'state',
    label: t(action.label_key),
    icon: action.icon,
    severity: action.severity,
    // `outlined` pass-through dal BE (default false). Usato per le azioni
    // "secondarie pericolose" tipo Annulla DRAFT (rosso outlined invece di
    // rosso pieno), allineato al pattern Annulla offerte/contratti.
    outlined: action.outlined === true,
    command: () => onAction?.(action),
  }))
}
