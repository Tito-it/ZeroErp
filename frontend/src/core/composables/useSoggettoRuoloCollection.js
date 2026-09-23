// Scopo: Backbone master-detail per le sotto-entita' soggetto/ruolo gestite a
//        card dentro un drawer (contatti, conti bancari). Centralizza la
//        macchina a stati duplicata bit-per-bit fra ContattiSoggettoDrawer e
//        ContiBancariDrawer (B4 2026-06-05, regola del 2): resolver API
//        soggetto/ruolo, caricamento con split fonte, stato form null/new/edit,
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
//   })

import { ref, watch } from 'vue'
import { useApiHandler } from './useApiHandler'
import { sortByFonte } from '../utils/string'

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
  } = config

  // `campiErrati`: i campi che il backend (o il DB) indica da correggere
  // sull'ultimo salvataggio — il drawer li unisce agli errori client del form.
  const { execute, loading: saving, campiErrati } = useApiHandler()

  // Lista card (in context ruolo contiene fonti editabili + ereditate readonly)
  const list = ref([])
  const listLoading = ref(false)

  // Modalita' form: null = lista, 'new' = aggiungi, 'edit' = modifica
  const formMode = ref(null)
  const editId = ref(null)
  const formErrors = ref([])

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
    formMode.value = 'new'
    editId.value = null
    resetErrori()
    resetForm()
    onAfterStartNew?.()
  }

  function startEdit(item) {
    formMode.value = 'edit'
    editId.value = item.id
    resetErrori()
    populateForm(item)
    onAfterStartEdit?.(item)
  }

  function cancelForm() {
    formMode.value = null
    editId.value = null
    resetErrori()
    resetForm()
  }

  async function saveForm() {
    formErrors.value = validateForm()
    if (formErrors.value.length > 0) return

    if (formMode.value === 'edit' && editId.value) {
      const result = await execute(
        () => apiFor('update')(ownerId(), editId.value, buildUpdatePayload()),
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

    formMode.value = null
    editId.value = null
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
      formMode.value = null
      editId.value = null
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
    editId,
    formErrors,
    campiErrati,
    loadList,
    startNew,
    startEdit,
    cancelForm,
    saveForm,
    deleteItem,
  }
}
