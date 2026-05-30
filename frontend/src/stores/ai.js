// Scopo: Store Pinia per l'assistente AI — stato conversazione, invio
//        messaggi, conferma operazioni in scrittura.
//
//        Convertito da composable module-scope (`core/composables/useAiAssistant.js`)
//        in pinia store per rientrare nel reset centralizzato al logout
//        (plugin `autoResetPlugin`, flag `userScoped: true`). Prima del
//        refactor, lo state era `const ref()` a livello di modulo e
//        sopravviveva al logout causando leak cross-user sullo stesso
//        browser.
//
//        API esposta identica al vecchio composable (messages, loading,
//        pendingConfirmation, sendMessage, confirmOperation, cancelOperation,
//        executeAction, clearConversation): i consumer (AiAssistantDrawer.vue)
//        devono solo sostituire l'import + usare storeToRefs per gli state
//        reattivi.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import router from '../router'
import { queryAI } from '../core/api/ai-api'
import { useApiHandler } from '../core/composables/useApiHandler'

// Scopo: rimuove residui tecnici dalla risposta LLM (tag XML, blocchi tool_use).
function cleanResponse(text) {
  if (!text) return ''
  return text
    .replace(/<[a-z_]+>[\s\S]*?<\/[a-z_]+>/gi, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export const useAiStore = defineStore('ai', () => {
  const conversationId = ref(null)
  const messages = ref([])
  const pendingConfirmation = ref(null)

  // useApiHandler espone un ref `loading` locale: lo proxiamo come
  // ref dello store cosi' i consumer hanno un loading coerente con
  // le chiamate AI orchestrate qui.
  const { execute, loading } = useApiHandler()

  // Scopo: processa la risposta del backend e aggiorna lo stato.
  function _handleResponse(data) {
    if (!data) {
      messages.value.push({ role: 'assistant', content: '', error: true })
      return
    }

    conversationId.value = data.conversation_id

    const confirmAction = (data.actions || []).find(a => a.type === 'confirm')
    if (confirmAction) {
      pendingConfirmation.value = {
        confirmationId: confirmAction.confirmation_id,
        summary: confirmAction.label,
      }
    }

    messages.value.push({
      role: 'assistant',
      content: cleanResponse(data.response),
      actions: (data.actions || []).filter(a => a.type !== 'confirm'),
      toolsUsed: data.tools_used || [],
      hasMore: data.has_more || false,
      pendingConfirmation: confirmAction ? pendingConfirmation.value : null,
    })
  }

  // Scopo: invia un messaggio all'assistente AI e aggiorna la conversazione.
  async function sendMessage(text) {
    if (!text || !text.trim()) return

    messages.value.push({ role: 'user', content: text.trim() })

    const data = await execute(
      () => queryAI(text.trim(), conversationId.value),
      { silent: true }
    )
    _handleResponse(data)
  }

  // Scopo: conferma un'operazione in scrittura pendente.
  async function confirmOperation() {
    if (!pendingConfirmation.value || !conversationId.value) return

    messages.value.push({ role: 'user', content: 'Confermo l\'operazione.' })

    const data = await execute(
      () => queryAI('__confirm__', conversationId.value),
      { silent: true }
    )
    pendingConfirmation.value = null
    _handleResponse(data)
  }

  // Scopo: annulla un'operazione in scrittura pendente (pulisce anche il backend).
  async function cancelOperation() {
    if (conversationId.value) {
      await execute(
        () => queryAI('__cancel__', conversationId.value),
        { silent: true }
      )
    }
    pendingConfirmation.value = null
    messages.value.push({
      role: 'assistant',
      content: 'Operazione annullata.',
    })
  }

  // Scopo: esegue un'azione di navigazione suggerita dall'AI.
  function executeAction(action) {
    if (action.type === 'navigate' && action.route) {
      router.push(action.route)
    }
  }

  // Scopo: resetta la conversazione per iniziarne una nuova (azione utente).
  function clearConversation() {
    conversationId.value = null
    messages.value = []
    pendingConfirmation.value = null
  }

  return {
    // state
    conversationId,
    messages,
    loading,
    pendingConfirmation,
    // actions
    sendMessage,
    confirmOperation,
    cancelOperation,
    executeAction,
    clearConversation,
    // Contratto plugin autoReset: `clearUserState` e' la primitiva che il
    // reset centralizzato chiama al logout. Alias di clearConversation
    // perche' sono effettivamente lo stesso reset (tutti i ref a initial).
    clearUserState: clearConversation
  }
}, {
  userScoped: true
})
