// Macchina a stati CRUD generica per una collezione editabile inline (tabella +
// form create/edit + delete con conferma + toggle attivo + reload via callback).
// Estratta alla 2ª occorrenza (regola del 2): condivisa da useStepFigliCollection
// (figli per-nodo, anello 4) e useArchiCollection (archi del grafo, anello 5).
//
// La lista NON è posseduta qui: le righe vivono nel payload dettaglio (store) e
// arrivano come props ai tab; ogni mutazione chiama `onChanged()` che nel parent
// ricarica il dettaglio. Le specifiche di endpoint (URL/kind) sono iniettate come
// closures `create/update/del`, così il resto della macchina è agnostico.
//
// Uso:
//   useEditableCollection({
//     create: (payload) => api.create(defId(), kind, payload),
//     update: (id, payload) => api.update(defId(), kind, id, payload),
//     del:    (id) => api.remove(defId(), kind, id),
//     messages: { created, saved, deleted },
//     confirmDelete: (row) => t('...'),
//     onChanged: () => emit('changed'),
//   })
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { MANAGE_ICONS } from '../../core/constants'

export function useEditableCollection({ create, update, del, messages, confirmDelete, onChanged }) {
  const { t } = useI18n()
  const { execute } = useApiHandler()
  const { confirmAction } = useConfirmAction()

  // formMode: null (nessun form) | 'create' | 'edit'. rowInForm = riga editata.
  const formMode = ref(null)
  const rowInForm = ref(null)
  const saving = ref(false)

  function startCreate() {
    rowInForm.value = null
    formMode.value = 'create'
  }
  function startEdit(row) {
    rowInForm.value = row
    formMode.value = 'edit'
  }
  function closeForm() {
    formMode.value = null
    rowInForm.value = null
  }

  async function save(payload) {
    const isEdit = !!rowInForm.value?.id
    saving.value = true
    try {
      const res = await execute(
        isEdit ? () => update(rowInForm.value.id, payload) : () => create(payload),
        { successMessage: isEdit ? messages.saved : messages.created },
      )
      if (res !== null) {
        closeForm()
        await onChanged()
      }
    } finally {
      saving.value = false
    }
  }

  function remove(row) {
    confirmAction({
      message: confirmDelete(row),
      onAccept: async () => {
        const res = await execute(() => del(row.id), { successMessage: messages.deleted })
        if (res === null) return
        if (rowInForm.value?.id === row.id) closeForm()
        await onChanged()
      },
    })
  }

  // Toggle rapido attivo/inattivo (PATCH attivo). Silenzioso (no toast success).
  async function toggleAttivo(row) {
    const res = await execute(() => update(row.id, { attivo: !row.attivo }), {})
    if (res !== null) await onChanged()
  }

  // Azioni riga standard (Modifica / Elimina) condivise da tutti i tab.
  function buildRowActions(row) {
    return [
      { key: 'edit', label: t('common.edit'), icon: MANAGE_ICONS.EDIT, command: () => startEdit(row) },
      { key: 'delete', label: t('common.delete'), icon: MANAGE_ICONS.DELETE, severity: 'danger', command: () => remove(row) },
    ]
  }

  return {
    formMode, rowInForm, saving,
    startCreate, startEdit, closeForm, save, remove, toggleAttivo, buildRowActions,
  }
}
