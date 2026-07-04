// Deriva opzioni Select e risoluzione codice dagli step di un'edizione. Estratto
// nel controllo qualità Fase 3 (regola del 2): stessa mappa id→codice + opzioni
// {value,label} duplicata in ArchiFormuleTab / ArchiRegoleTab / StepPrerequisitiTab.
//
// `steps` è un getter reattivo (es. `() => props.steps`).
import { computed } from 'vue'

export function useStepOptions(steps) {
  const stepMap = computed(() => new Map(steps().map((s) => [s.id, s.codice])))
  const stepOptions = computed(() => steps().map((s) => ({ value: s.id, label: s.codice })))
  function stepCodice(id) {
    return stepMap.value.get(id) ?? (id != null ? `#${id}` : '—')
  }
  return { stepMap, stepOptions, stepCodice }
}
