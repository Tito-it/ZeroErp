// Scopo: auto-save BOZZA + "edit-evolved" + abbandono bozza orfana per i drawer
//        testata documento (B13 2026-06-05, regola del 2). Pattern
//        `feedback_drawer_create_autosave_bozza`, finora copiato tra OrdiniDrawer
//        e PreventiviDrawer: in CREATE, appena i campi-trigger minimi sono
//        valorizzati, crea automaticamente la BOZZA (così l'operatore inserisce
//        subito le righe) → il drawer passa a "edit-evolved" interno (`createdId`
//        valorizzato, niente emit 'saved'). Alla chiusura, se la bozza è rimasta
//        senza righe, chiede conferma e la elimina.
//
// `createdId` è un ref del CHIAMANTE (intrecciato in computed/handleSave/template
// del drawer): qui lo riceviamo e lo valorizziamo, come `l2Error` in useL2SaveFlow.
// Il payload, i campi-trigger e i side-effect divergono per dominio → iniettati.
//
// Parametri:
//   emit             component emit (update:visible / cancelled)
//   execute          useApiHandler().execute del drawer (loading condiviso)
//   loading          ref loading del drawer (guard re-entrancy del trigger)
//   createdId        ref del drawer (id bozza creata; null = non ancora)
//   isEdit           getter () => bool (skip in EDIT classico)
//   contentReady     getter () => bool (drawer ancora in animazione → skip)
//   triggerSources   getter () => value | [values] osservati per l'auto-save
//   isReady          (values) => bool: i campi-trigger sono tutti valorizzati
//   createDraftApi   (payload) => Promise axios (NON store.create: serve l'envelope)
//   buildDraftPayload async () => payload (può fare preamboli, es. applyBaDefaults)
//   tabEntity        TAB_ENTITIES.X (notifica cross-tab del nuovo documento)
//   fetchDetail      (id) => Promise (loadDetail del drawer)
//   deleteDraft      (id) => Promise axios (store.elimina)
//   righeCountGetter () => number (per hasOrphanedDraft)
//   messages         { bozzaCreata, abbandonoTitolo, abbandonoMessage, abbandonoConferma, bozzaEliminata }
//
// Ritorna: { hasOrphanedDraft, autoSaveBozza, close, attemptClose, onVisibleChange }

import { computed, watch } from 'vue'
import { useConfirmAction } from './useConfirmAction'
import { useTabEvents } from './useTabEvents'

export function useDrawerAutosaveBozza({
  emit,
  execute,
  loading,
  createdId,
  isEdit,
  contentReady,
  triggerSources,
  isReady,
  createDraftApi,
  buildDraftPayload,
  tabEntity,
  fetchDetail,
  deleteDraft,
  righeCountGetter,
  messages,
}) {
  const { confirmAction } = useConfirmAction()
  const { emitDataChanged } = useTabEvents()

  // Crea la bozza e passa a "edit-evolved": NON emette 'saved' (transizione
  // interna; il prossimo 'saved' parte da handleSave manuale del drawer).
  async function autoSaveBozza() {
    const payload = await buildDraftPayload()
    const result = await execute(
      () => createDraftApi(payload),
      { successMessage: messages.bozzaCreata },
    )
    if (result && result.id) {
      createdId.value = result.id
      emitDataChanged(tabEntity, result.id)
      await fetchDetail(result.id)
    }
  }

  // Osserviamo ANCHE contentReady, non solo i triggerSources. Nel flusso
  // "prefill" (es. preventivo aperto da una pratica: cliente/istanza ereditati
  // dal contesto) i campi-trigger vengono valorizzati PROGRAMMATICAMENTE durante
  // l'apertura del drawer, PRIMA che l'animazione di slide finisca
  // (contentReady=false). Con il watch sui soli triggerSources il callback
  // scattava a contentReady=false → veniva skippato → e non ripartiva più (i
  // trigger non cambiano più): la bozza non veniva mai auto-creata e il drawer
  // restava in stato "nuovo" (niente edit-evolved, niente sezione righe).
  // Includendo contentReady, quando l'animazione finisce e i trigger sono già
  // pronti la bozza viene comunque creata. Nel flusso manuale (utente digita i
  // campi a drawer già aperto) il comportamento è invariato: i guard sotto
  // (isReady/contentReady/createdId) evitano doppie creazioni.
  watch([triggerSources, contentReady], async () => {
    if (isEdit()) return
    if (createdId.value !== null) return
    if (!isReady(triggerSources())) return
    if (!contentReady()) return
    if (loading.value) return
    await autoSaveBozza()
  })

  // Bozza creata via auto-save ma rimasta senza righe.
  const hasOrphanedDraft = computed(() => {
    if (createdId.value === null) return false
    return righeCountGetter() === 0
  })

  // Intercetta ogni chiusura (Annulla, ESC, click outside, X header): se la
  // bozza è orfana chiede conferma e la elimina; in caso di reject lascia il
  // drawer aperto (NON emette update:visible(false)).
  function attemptClose() {
    if (!hasOrphanedDraft.value) {
      emit('update:visible', false)
      emit('cancelled')
      return
    }
    confirmAction({
      title: messages.abbandonoTitolo,
      message: messages.abbandonoMessage,
      acceptLabel: messages.abbandonoConferma,
      danger: true,
      onAccept: async () => {
        const result = await execute(
          () => deleteDraft(createdId.value),
          { successMessage: messages.bozzaEliminata },
        )
        if (result !== null) {
          emit('update:visible', false)
          emit('cancelled')
        }
      },
    })
  }

  function close() {
    attemptClose()
  }

  function onVisibleChange(v) {
    if (v) {
      emit('update:visible', true)
      return
    }
    attemptClose()
  }

  return { hasOrphanedDraft, autoSaveBozza, close, attemptClose, onVisibleChange }
}
