// Scopo: event bus inter-tab per invalidazione dati — emette eventi quando
// un'entita' viene modificata, le altre tab ascoltano e fanno refresh lazy
import { ref } from 'vue'
import { registerUserScopedResetter } from '../pinia-plugins/auto-reset'

const listeners = ref(new Map())

export function useTabEvents() {
  // Emette un evento di modifica dati (chiamato dalla tab che salva)
  function emitDataChanged(entityType, entityId) {
    const event = {
      type: 'data-changed',
      entityType,
      entityId,
      timestamp: Date.now()
    }
    listeners.value.forEach((cb) => cb(event))
  }

  // Registra un listener per eventi data-changed (chiamato dalle tab che vogliono aggiornarsi)
  // Ritorna la funzione di cleanup da chiamare in onUnmounted
  function onDataChanged(callback) {
    const id = Symbol()
    listeners.value.set(id, callback)
    return () => listeners.value.delete(id)
  }

  return { emitDataChanged, onDataChanged }
}

// Registrazione al reset centralizzato: al logout la Map di listener viene
// svuotata. I componenti gia' montati che avessero ancora callback attivi
// nella sessione chiusa non riceveranno piu' eventi — corretto, poiche' il
// reset fa parte di un logout che unmount-era comunque le viste operative.
// Previene anche memory leak in scenari logout-senza-reload.
registerUserScopedResetter(() => {
  listeners.value.clear()
})
