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
import { aspettoAzione } from '../aspettoAzioni'

// Scopo: i motivi per cui un'azione e' spenta, in testo leggibile — una riga
//   per motivo (join '\n' -> tooltip o avviso multi-riga). Sede UNICA del
//   perche' di un'azione negata: la usano il mapper qui sotto (tooltip di
//   `DrawerActionsBar`) e `useLottoAzioni` (avviso del kebab di lista).
//   Estratta il 2026-09-24 (regola del 2, ok Tid): la copia del lotto non
//   passava i `valori`, e le due rese avevano gia' cominciato a divergere.
// - `reasons` (array completo) oppure il motivo singolo dell'azione — che ha
//   gli STESSI campi reason/reason_key, quindi si normalizza a lista e si
//   rende con un percorso solo.
// - `labelOrCode` = fail-visible: chiave i18n mancante -> codice macchina,
//   mai il path della chiave a video (te di default => false: un caller
//   che non lo inietta degrada al codice, non crasha).
// - ⭐ `valori` (2026-09-24): i parametri della frase che il DB mette nel
//   motivo (forma di casa `{codice, reason, reason_key, dettaglio, valori}`,
//   gli stessi che riempiono il `%s` del messaggio d'errore) passano alla
//   traduzione come segnaposto posizionali `{0}`, `{1}`. Il tooltip e' il
//   canale unico del perche' di un pulsante spento (niente banner per un
//   motivo solo — brief-db-preventivi-congelamento-pricing, registro
//   24-09). Un testo senza `{0}` resta com'e'.
// Ritorna '' se non c'e' nessun motivo leggibile.
export function testoMotivi(t, te = () => false, action) {
  const reasons = action?.reasons?.length ? action.reasons : [action ?? {}]
  return reasons
    .map(r => (r.reason_key
      ? labelOrCode(t, te, r.reason_key, r.reason || '',
        Array.isArray(r.valori) && r.valori.length ? r.valori : undefined)
      : (r.reason || '')))
    .filter(Boolean)
    .join('\n')
}

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
//   ⛔ Nessun gate di permesso qui (il parametro `permission`, nato il
//   2026-07-27, e' ritirato il 2026-10-27 — ok Tid, brief-modello-documento-
//   vendita §14.7). Il permesso di un passaggio lo legge il DB dalla riga della
//   matrice, e la capability NASCONDE l'azione a chi non ce l'ha (permesso ⇒
//   nascondi): un'azione che arriva qui e' gia' una che l'operatore puo' fare.
//   Un codename stampato dal frontend sarebbe una seconda sede del permesso.
export function mapAvailableActionsToDrawerActions({
  availableActions,
  t,
  te = () => false,
  onAction,
  readonly = false,
}) {
  if (unref(readonly)) return []
  const list = unref(availableActions) || []

  return list.map(action => {
    // Icona e colore li da' il verbo (dal 2026-09-27 il DB non li decide).
    const aspetto = aspettoAzione(action.key)
    // Precondizioni data-driven (rev DB 2026-07-16 `requires_righe` +
    // Rev 2 2026-07-19 brief guard-righe): `enabled:false` +
    // `reason`/`reason_key` -> pulsante DISABILITATO con tooltip che spiega
    // il perche' (decisione Tid: disabled, mai nascosto). Confronto stretto
    // con `false`: i domini/azioni senza `enabled` degradano ad abilitato.
    const isDisabled = action.enabled === false
    // Il perche' di un pulsante spento: sede unica, `testoMotivi` qui sopra.
    const tooltip = !isDisabled ? undefined : testoMotivi(t, te, action)
    return {
      key: action.key || `state-${action.target_state}`,
      kind: 'state',
      label: t(action.label_key),
      icon: aspetto.icona,
      severity: aspetto.severity,
      // `outlined` pass-through dal BE (default false). Usato per le azioni
      // "secondarie pericolose" tipo Annulla DRAFT (rosso outlined invece di
      // rosso pieno), allineato al pattern Annulla offerte/contratti.
      outlined: action.outlined === true,
      disabled: isDisabled,
      tooltip,
      command: () => onAction?.(action),
    }
  })
}
