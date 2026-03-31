<script setup>
// Scopo: Widget assistente AI — pannello flottante ancorato in basso a destra.
//        Non modale: l'utente continua a lavorare con il widget aperto.
import { ref, nextTick, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useAiAssistant } from '../composables/useAiAssistant'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, required: true }
})
const emit = defineEmits(['update:visible'])

const {
  messages, loading, pendingConfirmation,
  sendMessage, confirmOperation, cancelOperation,
  executeAction, clearConversation
} = useAiAssistant()

const inputText = ref('')
const messagesContainer = ref(null)
const minimized = ref(false)

// Scopo: Invia il messaggio e pulisce l'input.
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  await sendMessage(text)
  await nextTick()
  scrollToBottom()
}

// Scopo: Submit su Enter (senza Shift).
function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

// Scopo: Nuova conversazione.
function handleClear() {
  clearConversation()
  inputText.value = ''
}

// Scopo: Chiude il widget.
function handleClose() {
  emit('update:visible', false)
}

// Scopo: Minimizza/espandi il widget.
function toggleMinimize() {
  minimized.value = !minimized.value
}

// Scopo: Scroll automatico al fondo dell'area messaggi.
function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Scroll quando arrivano nuovi messaggi
watch(() => messages.value.length, () => {
  nextTick(() => scrollToBottom())
})

// Espandi automaticamente quando arriva un messaggio se minimizzato
watch(() => messages.value.length, () => {
  if (minimized.value) minimized.value = false
})
</script>

<template>
  <Transition name="ai-widget">
    <div v-if="visible" class="ai-widget" :class="{ 'ai-widget-minimized': minimized }">
      <!-- Header -->
      <div class="ai-widget-header" @click="toggleMinimize">
        <div class="ai-widget-header-left">
          <i class="pi pi-microchip-ai"></i>
          <span>{{ t('ai.title') }}</span>
        </div>
        <div class="ai-widget-header-actions">
          <button class="ai-widget-header-btn" @click.stop="handleClear" v-tooltip.top="t('ai.clear')">
            <i class="pi pi-refresh"></i>
          </button>
          <button class="ai-widget-header-btn" @click.stop="toggleMinimize">
            <i :class="minimized ? 'pi pi-window-maximize' : 'pi pi-window-minimize'"></i>
          </button>
          <button class="ai-widget-header-btn" @click.stop="handleClose">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <!-- Corpo (nascosto se minimizzato) -->
      <template v-if="!minimized">
        <!-- Area messaggi -->
        <div ref="messagesContainer" class="ai-messages">
          <!-- Messaggio di benvenuto se conversazione vuota -->
          <div v-if="messages.length === 0" class="ai-welcome">
            <i class="pi pi-microchip-ai ai-welcome-icon"></i>
            <p>{{ t('ai.welcome') }}</p>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="ai-message"
            :class="'ai-message-' + msg.role"
          >
            <!-- Icona ruolo -->
            <div class="ai-message-avatar">
              <i :class="msg.role === 'user' ? 'pi pi-user' : 'pi pi-microchip-ai'"></i>
            </div>

            <!-- Contenuto messaggio -->
            <div class="ai-message-body">
              <!-- Errore -->
              <div v-if="msg.error" class="ai-message-error">
                {{ t('ai.error') }}
              </div>

              <!-- Testo risposta -->
              <div v-else class="ai-message-text">{{ msg.content }}</div>

              <!-- Azioni di navigazione -->
              <div v-if="msg.actions && msg.actions.length > 0" class="ai-message-actions">
                <button
                  v-for="(action, ai) in msg.actions"
                  :key="ai"
                  class="ai-action-link"
                  @click="executeAction(action)"
                >
                  <i class="pi pi-external-link"></i>
                  {{ action.label }}
                </button>
              </div>

              <!-- Bottoni conferma/annulla per operazioni in scrittura -->
              <div v-if="msg.pendingConfirmation" class="ai-confirm-bar">
                <Button
                  :label="t('ai.confirm_cancel')"
                  severity="secondary"
                  size="small"
                  text
                  @click="cancelOperation"
                />
                <Button
                  :label="t('common.confirm')"
                  severity="primary"
                  size="small"
                  :loading="loading"
                  @click="confirmOperation"
                />
              </div>

              <!-- Indicatore tool usati -->
              <div v-if="msg.toolsUsed && msg.toolsUsed.length > 0" class="ai-message-tools">
                <i class="pi pi-cog"></i>
                <span>{{ msg.toolsUsed.join(', ') }}</span>
              </div>
            </div>
          </div>

          <!-- Indicatore caricamento -->
          <div v-if="loading" class="ai-message ai-message-assistant">
            <div class="ai-message-avatar">
              <i class="pi pi-microchip-ai"></i>
            </div>
            <div class="ai-message-body ai-message-loading">
              <ProgressSpinner
                style="width: 1.2rem; height: 1.2rem"
                strokeWidth="3"
              />
              <span>{{ t('ai.loading') }}</span>
            </div>
          </div>
        </div>

        <!-- Barra input -->
        <div class="ai-input-bar">
          <InputText
            v-model="inputText"
            :placeholder="t('ai.placeholder')"
            :disabled="loading"
            class="ai-input"
            @keydown="handleKeydown"
          />
          <Button
            icon="pi pi-send"
            rounded
            size="small"
            :disabled="loading || !inputText.trim()"
            v-tooltip.top="t('ai.send')"
            @click="handleSend"
          />
        </div>
      </template>
    </div>
  </Transition>
</template>

<style scoped>
/* Widget flottante — ancorato in basso a destra, stile drawer scuro */
.ai-widget {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  width: 420px;
  max-height: 520px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-surface-700);
  border-radius: 0.75rem;
  background: var(--p-surface-900);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.25);
  z-index: 1100;
  overflow: hidden;
}

.ai-widget-minimized {
  max-height: none;
}

/* Header */
.ai-widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--p-surface-700);
  background: var(--p-surface-800);
  cursor: pointer;
  user-select: none;
}

.ai-widget-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--app-font-size-sm);
  font-weight: 600;
  color: var(--p-primary-color);
}

.ai-widget-header-left i {
  font-size: 1rem;
}

.ai-widget-header-actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.ai-widget-header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: color var(--app-transition-fast), background var(--app-transition-fast);
}

.ai-widget-header-btn:hover {
  color: var(--p-text-color);
  background: var(--p-surface-700);
}

/* Area messaggi */
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  min-height: 200px;
  max-height: 360px;
}

/* Benvenuto */
.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1.5rem 1rem;
  font-size: var(--app-font-size-sm);
}

.ai-welcome-icon {
  font-size: 1.5rem;
  color: var(--p-primary-color);
  opacity: 0.4;
}

/* Messaggio */
.ai-message {
  display: flex;
  gap: 0.4rem;
  max-width: 100%;
}

.ai-message-user {
  flex-direction: row-reverse;
}

.ai-message-avatar {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  font-size: 0.65rem;
  padding-top: 0.3rem;
}

.ai-message-user .ai-message-avatar {
  color: var(--p-blue-400);
  border: 1px solid var(--p-blue-800);
}

.ai-message-assistant .ai-message-avatar {
  color: var(--p-primary-color);
  border: 1px solid var(--p-primary-800);
}

.ai-message-body {
  padding: 0.4rem 0.6rem;
  border-radius: 0.5rem;
  max-width: 85%;
  font-size: var(--app-font-size-sm);
  line-height: 1.45;
}

.ai-message-user .ai-message-body {
  border: 1px solid var(--p-blue-800);
  color: var(--p-text-color);
}

.ai-message-assistant .ai-message-body {
  border: 1px solid var(--p-surface-700);
  color: var(--p-text-color);
}

.ai-message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-message-error {
  color: var(--p-red-500);
  font-style: italic;
}

.ai-message-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}

/* Azioni navigazione */
.ai-message-actions {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-top: 0.4rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--p-surface-700);
}

.ai-action-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0;
  font-size: var(--app-font-size-sm);
  color: var(--p-primary-color);
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: color var(--app-transition-fast);
}

.ai-action-link:hover {
  color: var(--p-primary-700);
  text-decoration: underline;
}

.ai-action-link i {
  font-size: 0.65rem;
}

/* Tool usati */
.ai-message-tools {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.25rem;
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
}

.ai-message-tools i {
  font-size: 0.6rem;
}

/* Barra conferma operazione */
.ai-confirm-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--p-surface-700);
}

/* Barra input */
.ai-input-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--p-surface-700);
}

.ai-input {
  flex: 1;
  font-size: var(--app-font-size-sm);
}

/* Animazione ingresso/uscita */
.ai-widget-enter-active {
  animation: ai-slide-up 0.25s ease-out;
}

.ai-widget-leave-active {
  animation: ai-slide-down 0.2s ease-in;
}

@keyframes ai-slide-up {
  from {
    opacity: 0;
    transform: translateY(1rem) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes ai-slide-down {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(1rem) scale(0.95);
  }
}

/* Mobile — widget a schermo pieno */
@media (max-width: 767px) {
  .ai-widget {
    bottom: 0;
    right: 0;
    width: 100%;
    max-height: 60vh;
    border-radius: 0.75rem 0.75rem 0 0;
  }
}
</style>
