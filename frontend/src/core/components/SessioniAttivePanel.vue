<script setup>
import { ref, onMounted, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useNotify } from '../composables/useNotify'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import { useApiHandler } from '../composables/useApiHandler'
import { MANAGE_ICONS } from '../constants'
import { listSessioni, revocaSessione as apiRevocaSessione, revocaTutteSessioni as apiRevocaTutte } from '../api/sessioni'

const { t } = useI18n()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const { execute } = useApiHandler()

const sessioni = ref([])
const loading = ref(false)
// ⚠️ La revoca non e' istantanea (blacklist di N token + diario): senza uno
//    stato a video l'operatore preme, non vede niente e conclude che il
//    pulsante non funziona — che e' esattamente quello che e' successo.
const azioneInCorso = ref(false)
const expanded = ref(false)

async function fetchSessioni() {
  loading.value = true
  try {
    // Silenziosa: un pannello di contorno non apre un toast a ogni lettura.
    const data = await execute(() => listSessioni(), { silent: true })
    if (data !== null) sessioni.value = data.sessioni || []
    // `null` = lettura fallita:
    // ⛔ NON si azzera la lista: `sessioni = []` fa sparire tutto il pannello
    //    (`v-if="sessioni.length > 0"`), cioe' dice «non hai altre sessioni
    //    attive» quando la verita' e' «non lo so, la lettura e' fallita». Su un
    //    pannello di sicurezza e' la bugia peggiore: si tiene l'ultimo dato
    //    noto e non si afferma niente di nuovo.
  } finally {
    loading.value = false
  }
}

function parseUserAgent(ua) {
  if (!ua) return '—'
  // Browser
  let browser = 'Sconosciuto'
  if (ua.includes('Firefox/')) browser = 'Firefox'
  else if (ua.includes('Edg/')) browser = 'Edge'
  else if (ua.includes('Chrome/')) browser = 'Chrome'
  else if (ua.includes('Safari/')) browser = 'Safari'
  // OS
  let os = ''
  if (ua.includes('Windows')) os = 'Windows'
  else if (ua.includes('Mac OS')) os = 'macOS'
  else if (ua.includes('Linux')) os = 'Linux'
  else if (ua.includes('Android')) os = 'Android'
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS'
  return os ? `${browser} / ${os}` : browser
}

function timeAgo(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return t('sessions.now')
  if (diffMin < 60) return t('sessions.minutes_ago', { n: diffMin })
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return t('sessions.hours_ago', { n: diffHours })
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return t('sessions.yesterday')
  return t('sessions.days_ago', { n: diffDays })
}

function confermaRevoca(sessione) {
  const device = parseUserAgent(sessione.user_agent)
  const ip = sessione.ip_address || '—'
  confirmAction({
    header: t('sessions.revoke_confirm_title'),
    message: t('sessions.revoke_confirm_message', { device, ip }),
    acceptLabel: t('sessions.revoke'),
    danger: true,
    onAccept: () => revocaSessione(sessione.jti),
  })
}

function confermaRevocaTutte() {
  confirmAction({
    header: t('sessions.revoke_all_confirm_title'),
    message: t('sessions.revoke_all_confirm_message', { count: sessioni.value.length }),
    acceptLabel: t('sessions.revoke_all'),
    danger: true,
    onAccept: revocaTutteSessioni,
  })
}

async function revocaSessione(jti) {
  azioneInCorso.value = true
  try {
    // L'errore lo mostra `execute` con il messaggio del backend.
    const esito = await execute(() => apiRevocaSessione(jti))
    if (esito === null) return
    notify.success(t('sessions.revoke_success'))
    await fetchSessioni()
  } finally {
    azioneInCorso.value = false
  }
}

// ⭐ Il conteggio lo DICE il backend (`revoked`), e fino al 2026-09-04 era un
//    campo emesso e mai letto: il toast diceva «sessioni remote revocate» senza
//    dire quante. E' l'informazione che distingue «ne ha revocata una» da «le
//    ha revocate tutte» — cioe' esattamente il dubbio da cui e' partita questa
//    correzione.
// ⛔ E il pannello NON si richiude piu' (`expanded = false`): chiudere la lista
//    subito dopo l'azione nasconde il suo risultato, e a video l'effetto e'
//    indistinguibile da «non e' successo niente».
async function revocaTutteSessioni() {
  azioneInCorso.value = true
  try {
    const esito = await execute(() => apiRevocaTutte())
    if (esito === null) return
    const revocate = esito.revoked ?? 0
    notify.success(t('sessions.revoke_all_success', { count: revocate }))
    await fetchSessioni()
  } finally {
    azioneInCorso.value = false
  }
}

// ⚠️ `onActivated` oltre a `onMounted`: la home vive sotto KeepAlive, quindi
//    tornandoci il componente non si rimonta e l'elenco resterebbe quello
//    dell'ultimo mount — su un pannello di sessioni attive, vecchio di ore.
onMounted(fetchSessioni)
onActivated(fetchSessioni)
</script>

<template>
  <div v-if="sessioni.length > 0" class="sessioni-panel">
    <div class="sessioni-header">
      <h3 class="sessioni-title">
        <i :class="MANAGE_ICONS.SESSIONI"></i>
        <span>{{ t('sessions.other_active_title') }}</span>
        <Badge :value="sessioni.length" severity="warn" />
      </h3>
      <div class="sessioni-actions">
        <Button
          :label="t('sessions.revoke_all')"
          :icon="MANAGE_ICONS.REVOCA"
          severity="danger"
          text
          size="small"
          :loading="azioneInCorso"
          :disabled="azioneInCorso"
          @click="confermaRevocaTutte"
        />
        <Button
          :icon="expanded ? MANAGE_ICONS.COLLAPSE : MANAGE_ICONS.EXPAND"
          text
          rounded
          size="small"
          :aria-label="expanded ? t('sessions.hide_list') : t('sessions.show_list')"
          v-tooltip.left="expanded ? t('sessions.hide_list') : t('sessions.show_list')"
          @click="expanded = !expanded"
        />
      </div>
    </div>
    <DataTable v-if="expanded" :value="sessioni" size="small" stripedRows class="app-datatable">
      <Column :header="t('sessions.device')">
        <template #body="{ data }">
          {{ parseUserAgent(data.user_agent) }}
        </template>
      </Column>
      <Column :header="t('sessions.ip_address')">
        <template #body="{ data }">
          {{ data.ip_address || '—' }}
        </template>
      </Column>
      <Column :header="t('sessions.last_access')">
        <template #body="{ data }">
          {{ timeAgo(data.data_ultimo_evento) }}
        </template>
      </Column>
      <Column :header="t('sessions.action')" style="width: 100px; text-align: center;">
        <template #body="{ data }">
          <Button
            :label="t('sessions.revoke')"
            :icon="MANAGE_ICONS.REVOCA"
            severity="danger"
            size="small"
            text
            :disabled="azioneInCorso"
            @click="confermaRevoca(data)"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.sessioni-panel {
  width: 100%;
  margin-bottom: 1.5rem;
}

/* Font e padding DataTable ereditati da .app-datatable (main.css) */

.sessioni-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.sessioni-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.sessioni-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--app-font-size-base);
  font-weight: 600;
  color: var(--app-text-color);
  margin: 0;
}

.sessioni-title i {
  color: var(--app-warning-color);
}
</style>
