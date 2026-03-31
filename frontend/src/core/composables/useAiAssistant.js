// Scopo: Composable per la comunicazione con l'assistente AI.
//        Gestisce stato conversazione, invio messaggi, azioni di navigazione
//        e conferma operazioni in scrittura (Fase 4).
//        Lo stato conversazione e' condiviso (ref esterne) cosi' sopravvive
//        al ri-mount del componente widget.

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { queryAI } from '../api/ai-api'
import { useApiHandler } from './useApiHandler'

// Stato condiviso — sopravvive al ri-mount del widget
const conversationId = ref(null)
const messages = ref([])
const pendingConfirmation = ref(null)

export function useAiAssistant() {
  const router = useRouter()
  const { execute, loading } = useApiHandler()

  // Scopo: Processa la risposta del backend e aggiorna lo stato.
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

  // Scopo: Invia un messaggio all'assistente AI e aggiorna la conversazione.
  async function sendMessage(text) {
    if (!text || !text.trim()) return

    messages.value.push({ role: 'user', content: text.trim() })

    const data = await execute(
      () => queryAI(text.trim(), conversationId.value),
      { silent: true }
    )
    _handleResponse(data)
  }

  // Scopo: Conferma un'operazione in scrittura pendente.
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

  // Scopo: Annulla un'operazione in scrittura pendente (pulisce anche il backend).
  async function cancelOperation() {
    if (conversationId.value) {
      // Notifica il backend per pulire la conferma dalla memoria
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

  // Scopo: Esegue un'azione di navigazione suggerita dall'AI.
  function executeAction(action) {
    if (action.type === 'navigate' && action.route) {
      router.push(action.route)
    }
  }

  // Scopo: Resetta la conversazione per iniziarne una nuova.
  function clearConversation() {
    conversationId.value = null
    messages.value = []
    pendingConfirmation.value = null
  }

  return {
    messages,
    conversationId,
    loading,
    pendingConfirmation,
    sendMessage,
    confirmOperation,
    cancelOperation,
    executeAction,
    clearConversation
  }
}

// Scopo: Rimuove residui tecnici dalla risposta LLM (tag XML, blocchi tool_use).
function cleanResponse(text) {
  if (!text) return ''
  return text
    .replace(/<[a-z_]+>[\s\S]*?<\/[a-z_]+>/gi, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
