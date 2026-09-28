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
// ⭐ La macchina del form (formMode, riga in modifica, nuova/apri/chiudi) NON
// e' scritta qui: e' il BB core `useFormInline` (sede unica, regola del 2, ok
// Tid 2026-09-28), e questo composable la restituisce con i suoi nomi —
// `rigaInModifica`, `nuovaRiga`, `apriRiga`, `chiudiForm` — aggiungendo cio'
// che e' suo: salvataggio, eliminazione, attivo, azioni di riga.
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
import { useFormInline } from '../../core/composables/useFormInline'
import { MANAGE_ICONS } from '../../core/constants'

export function useEditableCollection({ create, update, del, messages, confirmDelete, onChanged }) {
  const { t } = useI18n()
  const { execute } = useApiHandler()
  const { confirmAction } = useConfirmAction()

  const form = useFormInline()
  const { rigaInModifica, apriRiga, chiudiForm } = form
  const saving = ref(false)

  async function save(payload) {
    const isEdit = !!rigaInModifica.value?.id
    saving.value = true
    try {
      const res = await execute(
        isEdit ? () => update(rigaInModifica.value.id, payload) : () => create(payload),
        { successMessage: isEdit ? messages.saved : messages.created },
      )
      if (res !== null) {
        chiudiForm()
        await onChanged()
      }
    } finally {
      saving.value = false
    }
  }

  function remove(row) {
    confirmAction({
      header: t('confirm.delete_title'),
      message: confirmDelete(row),
      onAccept: async () => {
        const res = await execute(() => del(row.id), { successMessage: messages.deleted })
        if (res === null) return
        if (rigaInModifica.value?.id === row.id) chiudiForm()
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
      { key: 'edit', label: t('common.edit'), icon: MANAGE_ICONS.EDIT, command: () => apriRiga(row) },
      { key: 'delete', label: t('common.delete'), icon: MANAGE_ICONS.DELETE, severity: 'danger', command: () => remove(row) },
    ]
  }

  return {
    ...form, saving,
    save, remove, toggleAttivo, buildRowActions,
  }
}
