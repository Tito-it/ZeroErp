// Adapter di useEditableCollection per i figli per-nodo di uno step (canali /
// handler-eventi / competenze) — FE-3.3, anello BE 4. Inietta le closures di
// endpoint (URL include stepId + kind kebab); la macchina CRUD vive nel generico.
//
// Uso (in un tab): vedi StepCanaliTab / StepHandlerEventiTab / StepCompetenzeTab.
import {
  createStepFiglio,
  updateStepFiglio,
  deleteStepFiglio,
} from '../api/definizioniWorkflow'
import { useEditableCollection } from './useEditableCollection'

export function useStepFigliCollection({
  definizioneId,
  stepId,
  kind,
  messages,
  confirmDelete,
  onChanged,
}) {
  return useEditableCollection({
    create: (payload) => createStepFiglio(definizioneId(), stepId(), kind, payload),
    update: (id, payload) => updateStepFiglio(definizioneId(), stepId(), kind, id, payload),
    del: (id) => deleteStepFiglio(definizioneId(), stepId(), kind, id),
    messages,
    confirmDelete,
    onChanged,
  })
}
