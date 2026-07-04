// Adapter di useEditableCollection per gli archi del grafo, a livello edizione
// (prerequisiti / formule-tempo / regole-generazione) — FE-3.4, anello BE 5.
// Endpoint /archi/<kind>/ (niente stepId nell'URL: l'ancora è uno step passato
// nel payload). La macchina CRUD vive nel generico.
import { createArco, updateArco, deleteArco } from '../api/definizioniWorkflow'
import { useEditableCollection } from './useEditableCollection'

export function useArchiCollection({ definizioneId, kind, messages, confirmDelete, onChanged }) {
  return useEditableCollection({
    create: (payload) => createArco(definizioneId(), kind, payload),
    update: (id, payload) => updateArco(definizioneId(), kind, id, payload),
    del: (id) => deleteArco(definizioneId(), kind, id),
    messages,
    confirmDelete,
    onChanged,
  })
}
