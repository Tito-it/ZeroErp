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
import { labelOrCode } from '../utils/i18nLabel'

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
//   `permission` (2026-07-27, opzionale): codename dell'azione di processo che
//   autorizza le transizioni di questo dominio (es. `cambia_stato_commessa`).
//   Viene stampato come `action` su OGNI azione mappata, e da lì il filtro di
//   `DrawerActionsBar`/`useActionBar` (`auth.isActionAllowed`) nasconde i
//   pulsanti a chi non ha il permesso. Ortogonale a `enabled`/`reasons` del BE:
//   quelli dicono se l'azione e' eseguibile ADESSO (disabled + motivo), il
//   permesso dice se quell'operatore puo' eseguirla (pulsante assente).
//   Omesso = nessun gate di processo, comportamento invariato.
export function mapAvailableActionsToDrawerActions({
  availableActions,
  t,
  te = () => false,
  onAction,
  readonly = false,
  permission = null,
}) {
  if (unref(readonly)) return []
  const list = unref(availableActions) || []

  return list.map(action => {
    // Precondizioni data-driven (rev DB 2026-07-16 `requires_righe` +
    // Rev 2 2026-07-19 brief guard-righe): `enabled:false` +
    // `reason`/`reason_key` -> pulsante DISABILITATO con tooltip che spiega
    // il perche' (decisione Tid: disabled, mai nascosto). Confronto stretto
    // con `false`: i domini/azioni senza `enabled` degradano ad abilitato.
    const isDisabled = action.enabled === false
    // Motivi ostativi: `reasons` (array completo, oggi solo l'azione emetti
    // del DDT via fn_check_ddt_emittibile) oppure il motivo singolo — che ha
    // gli STESSI campi reason/reason_key, quindi si normalizza a lista e si
    // rende con un percorso solo (join '\n' -> tooltip multi-riga).
    // `labelOrCode` = fail-visible: chiave i18n mancante -> codice macchina,
    // mai il path della chiave a video (te di default => false: un caller
    // che non lo inietta degrada al codice, non crasha).
    const reasons = action.reasons?.length ? action.reasons : [action]
    const tooltip = !isDisabled
      ? undefined
      : reasons
          .map(r => (r.reason_key
            ? labelOrCode(t, te, r.reason_key, r.reason || '')
            : (r.reason || '')))
          .filter(Boolean)
          .join('\n')
    return {
      key: action.key || `state-${action.target_state}`,
      kind: 'state',
      label: t(action.label_key),
      icon: action.icon,
      severity: action.severity,
      // `outlined` pass-through dal BE (default false). Usato per le azioni
      // "secondarie pericolose" tipo Annulla DRAFT (rosso outlined invece di
      // rosso pieno), allineato al pattern Annulla offerte/contratti.
      outlined: action.outlined === true,
      disabled: isDisabled,
      tooltip,
      // Gate permesso di processo (solo se il dominio lo dichiara): la chiave
      // `action` e' quella che DrawerActionsBar passa ad `auth.isActionAllowed`.
      ...(permission ? { action: permission } : {}),
      command: () => onAction?.(action),
    }
  })
}
