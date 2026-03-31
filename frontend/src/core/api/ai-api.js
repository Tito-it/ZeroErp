// Scopo: API client per l'assistente AI.
//        Comunica con /api/v1/ai-assistant/ endpoints.

import api from '../api'

const BASE = '/ai-assistant'

// Timeout esteso per query AI — il loop tool_call richiede
// piu' chiamate API al provider LLM (~5s ciascuna).
const AI_TIMEOUT = 60000

// Scopo: Invia una query in linguaggio naturale all'assistente AI.
export function queryAI(message, conversationId = null) {
  const payload = { message }
  if (conversationId) {
    payload.conversation_id = conversationId
  }
  return api.post(`${BASE}/query/`, payload, { timeout: AI_TIMEOUT })
}

// Scopo: Verifica se l'assistente AI e' attivo e disponibile.
export function getAIStatus() {
  return api.get(`${BASE}/status/`)
}
