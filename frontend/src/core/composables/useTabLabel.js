// Scopo: aggiorna dinamicamente la label della content tab corrente
// (es. "Fattura #127" invece del generico "Fattura")
import { useRoute } from 'vue-router'
import { useTabsStore } from '../../stores/tabs'

export function useTabLabel() {
  const route = useRoute()
  const tabs = useTabsStore()

  // Aggiorna la label della tab che corrisponde alla route corrente
  function setLabel(newLabel) {
    tabs.updateLabel(route.path, newLabel)
  }

  return { setLabel }
}
