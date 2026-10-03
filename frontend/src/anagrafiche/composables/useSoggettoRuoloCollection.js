// Scopo: Backbone master-detail per le sotto-entita' soggetto/ruolo gestite a
//        card dentro un drawer (contatti, conti bancari). Centralizza la
//        macchina a stati duplicata bit-per-bit fra ContattiSoggettoDrawer e
//        ContiBancariDrawer (B4 2026-06-05, regola del 2): resolver API
//        soggetto/ruolo, caricamento con split fonte, verbi del form (la macchina
//        null/create/edit e' il BB core `useFormInline`),
//        e i 5 handler start-new/start-edit/cancel/save/delete con
//        execute()+emit('saved')+reload.
//
// Il composable possiede SOLO la logica: la lista card e il form restano
// per-drawer (markup legittimamente diverso). Le divergenze reali sono
// iniettate via callback:
//   - buildCreatePayload/buildUpdatePayload (Contatti spread inline vs Conti
//     toCreatePayload/toUpdatePayload);
//   - confirmDelete opzionale (Conti conferma con IBAN mascherato, Contatti
//     elimina diretto);
//   - onAfterStartNew/onAfterStartEdit (Contatti carica sub-lookup
//     tipiContatto/unitaOrganizzative; Conti non ha side-effect).
//
// ⭐ Modifiche non salvate del form inline (2026-09-26, regola del 2, ok Tid):
//   le tiene la collection, che possiede `formMode` e l'avvio del form. Il
//   drawer passa `formDaConfrontare` (cio' che il Salva manda) e riceve
//   `modificato` (per <DrawerTitle>), `annullaForm` (Annulla del form, con
//   conferma) e `chiudiConConferma` (per le uscite dal drawer). La fotografia
//   si fissa dopo `onAfterStartNew/Edit`, conta solo a form aperto e si
//   azzera quando torna la lista (BB useDrawerFormPreserve).
//
// NON adottato da IndirizziSoggettoDrawer (falso positivo parziale: matrice
// tipi + mode replace + multi-riga divergono troppo).
//
// Uso (vedi ContiBancariDrawer / ContattiSoggettoDrawer):
//   const coll = useSoggettoRuoloCollection({
//     visible: () => props.visible,
//     context: () => props.context,
//     ownerId: () => props.ownerId,
//     istanzaUtilityId: () => props.istanzaUtilityId,
//     apiMap: { soggetto: {...}, ruolo: {...} },
//     splitKeys: { propri: 'conti_ruolo', ereditati: 'conti_ereditati' },
//     flatSort: (a, b) => (a.uso || '').localeCompare(b.uso || ''),
//     resetForm: () => conto.reset(props.ownerName),
//     validateForm: () => conto.validate(),
//     populateForm: (item) => conto.populate(item),
//     buildCreatePayload: () => conto.toCreatePayload(),
//     buildUpdatePayload: () => conto.toUpdatePayload(),
//     confirmDelete: (item, doDelete) => confirmDelete(label(item), doDelete),
//     messages: { created, saved, deleted },
//     onSaved: () => emit('saved'),
//     formDaConfrontare: () => ({ ...conto.form }),
//   })

import { computed, ref, watch } from 'vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useFormInline } from '../../core/composables/useFormInline'
import { sortByFonte } from '../../core/utils/string'

export function useSoggettoRuoloCollection(config) {
  const {
    visible,
    context,
    ownerId,
    istanzaUtilityId = () => null,
    apiMap,
    splitKeys,
    flatSort,
    resetForm,
    validateForm,
    populateForm,
    buildCreatePayload,
    buildUpdatePayload,
    onAfterStartNew,
    onAfterStartEdit,
    confirmDelete,
    messages,
    onSaved,
    formDaConfrontare = () => null,
  } = config

  // `campiErrati`: i campi che il backend (o il DB) indica da correggere
  // sull'ultimo salvataggio — il drawer li unisce agli errori client del form.
  const { execute, loading: saving, campiErrati } = useApiHandler()

  // Lista card (in context ruolo contiene fonti editabili + ereditate readonly)
  const list = ref([])
  const listLoading = ref(false)

  // ⭐ La macchina del form (null = lista, 'create' = aggiungi, 'edit' =
  //    modifica) e' il BB core `useFormInline` (sede unica, ok Tid
  //    2026-09-28). Qui restano i VERBI della collezione — startNew,
  //    startEdit, cancelForm — che la chiamano e aggiungono il loro mestiere:
  //    errori, popolamento, fotografia.
  //    ⚠️ Fino a quel giorno il valore di «aggiungi» era 'new', l'unico nel
  //    progetto: allineato a 'create' insieme ai drawer che lo leggevano.
  //    ⭐ Il padre e' il proprietario, a drawer aperto: un altro soggetto sotto
  //    lo stesso drawer chiude il form.
  const form = useFormInline({
    padre: () => (visible() ? ownerId() : null),
    // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
    confermaCambio: (p) => fotografia.chiudiConConferma(p),
  })
  const { formMode, formAperto, rigaInModifica } = form
  const formErrors = ref([])

  // Fotografia del form inline: vive solo a form aperto.
  const fotografia = useDrawerFormPreserve(computed(formDaConfrontare), {
    visibile: () => visible() && formAperto.value,
  })

  // Scopo: Azzera gli errori client E quelli del server. `campiErrati` si
  //        azzera da se' solo al prossimo `execute`: senza questo, il campo
  //        rosso di un salvataggio fallito resterebbe sul form nuovo, su un
  //        altro record o alla riapertura del drawer.
  function resetErrori() {
    formErrors.value = []
    campiErrati.value = []
  }

  // Scopo: Risolve il set di funzioni API in base al context corrente.
  function apiFor(action) {
    return apiMap[context()][action]
  }

  // Scopo: Carica la lista. In context 'ruolo' la risposta porta le due chiavi
  //        splitKeys.propri/ereditati con campo 'fonte' (ordina via sortByFonte);
  //        in context 'soggetto' una lista piatta ordinata da flatSort.
  async function loadList() {
    if (!ownerId()) return
    listLoading.value = true
    try {
      const listParams =
        context() === 'ruolo' && istanzaUtilityId()
          ? { istanza_utility_id: istanzaUtilityId() }
          : {}
      const res = await apiFor('list')(ownerId(), listParams)
      const payload = res.data?.data
      if (context() === 'ruolo' && payload?.[splitKeys.propri]) {
        list.value = sortByFonte([
          ...payload[splitKeys.propri],
          ...(payload[splitKeys.ereditati] || []),
        ])
      } else {
        const items = payload?.results || payload || []
        list.value = [...items].sort(flatSort)
      }
    } catch {
      list.value = []
    } finally {
      listLoading.value = false
    }
  }

  // === Azioni ===

  function startNew() {
    form.nuovaRiga()
    resetErrori()
    resetForm()
    onAfterStartNew?.()
    fotografia.fissa()
  }

  function startEdit(item) {
    form.apriRiga(item, () => {
      resetErrori()
      populateForm(item)
      onAfterStartEdit?.(item)
      fotografia.fissa()
    })
  }

  function cancelForm() {
    form.chiudiForm()
    resetErrori()
    resetForm()
  }

  async function saveForm() {
    formErrors.value = validateForm()
    if (formErrors.value.length > 0) return

    const editId = rigaInModifica.value?.id
    if (formMode.value === 'edit' && editId) {
      const result = await execute(
        () => apiFor('update')(ownerId(), editId, buildUpdatePayload()),
        { successMessage: messages.saved },
      )
      if (result === null) return
    } else {
      const payload = buildCreatePayload()
      // In context ruolo, propaga istanza_utility_id (cascata a 3 livelli).
      if (context() === 'ruolo' && istanzaUtilityId()) {
        payload.istanza_utility_id = istanzaUtilityId()
      }
      const result = await execute(
        () => apiFor('create')(ownerId(), payload),
        { successMessage: messages.created },
      )
      if (result === null) return
    }

    form.chiudiForm()
    resetErrori()
    resetForm()
    await loadList()
    onSaved?.()
  }

  async function _doDelete(item) {
    const result = await execute(() => apiFor('remove')(ownerId(), item.id), {
      successMessage: messages.deleted,
    })
    if (result !== null) {
      await loadList()
      onSaved?.()
    }
  }

  function deleteItem(item) {
    // confirmDelete opzionale: se presente apre il dialog di conferma e
    // delega la delete vera al callback; altrimenti elimina diretto.
    if (confirmDelete) {
      confirmDelete(item, () => _doDelete(item))
    } else {
      _doDelete(item)
    }
  }

  // Apertura drawer: reset stato + form e ricarica lista.
  watch(
    () => visible(),
    (val) => {
      if (!val) return
      form.chiudiForm()
      resetErrori()
      resetForm()
      loadList()
    },
  )

  return {
    list,
    listLoading,
    saving,
    formMode,
    formErrors,
    campiErrati,
    loadList,
    startNew,
    startEdit,
    cancelForm,
    saveForm,
    deleteItem,
    modificato: fotografia.modificato,
    annullaForm: () => fotografia.chiudiConConferma(cancelForm),
    chiudiConConferma: fotografia.chiudiConConferma,
  }
}
