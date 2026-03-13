// Scopo: registra scorciatoie da tastiera globali per operatori ERP power user.
// Disattivato quando il focus e' su input/textarea/contenteditable.
import { onMounted, onUnmounted } from 'vue'

export function useKeyboardShortcuts(shortcuts) {
  function handler(e) {
    // Non intercettare se il focus e' su input/textarea/contenteditable
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
    if (e.target.isContentEditable) return

    for (const s of shortcuts) {
      const ctrlMatch = s.ctrl === (e.ctrlKey || e.metaKey)
      const shiftMatch = (s.shift || false) === e.shiftKey
      const keyMatch = s.key === e.key

      if (ctrlMatch && shiftMatch && keyMatch) {
        e.preventDefault()
        s.action()
        return
      }
    }
  }

  onMounted(() => document.addEventListener('keydown', handler))
  onUnmounted(() => document.removeEventListener('keydown', handler))
}
