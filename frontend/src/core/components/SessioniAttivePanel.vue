<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useNotify } from '../composables/useNotify'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import api from '../api'

const { t } = useI18n()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const sessioni = ref([])
const loading = ref(false)
const expanded = ref(false)

async function fetchSessioni() {
  loading.value = true
  try {
    const response = await api.get('/core/me/sessioni/')
    sessioni.value = response.data.data.sessioni || []
  } catch {
    sessioni.value = []
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
    title: t('sessions.revoke_confirm_title'),
    message: t('sessions.revoke_confirm_message', { device, ip }),
    acceptLabel: t('sessions.revoke'),
    danger: true,
    onAccept: () => revocaSessione(sessione.jti),
  })
}

function confermaRevocaTutte() {
  confirmAction({
    title: t('sessions.revoke_all_confirm_title'),
    message: t('sessions.revoke_all_confirm_message', { count: sessioni.value.length }),
    acceptLabel: t('sessions.revoke_all'),
    danger: true,
    onAccept: revocaTutteSessioni,
  })
}

async function revocaSessione(jti) {
  try {
    await api.post(`/core/me/sessioni/${jti}/revoca/`)
    notify.success(t('sessions.revoke_success'))
    await fetchSessioni()
  } catch {
    notify.error()
  }
}

async function revocaTutteSessioni() {
  try {
    await api.post('/core/me/sessioni/revoca-tutte/')
    notify.success(t('sessions.revoke_all_success'))
    expanded.value = false
    await fetchSessioni()
  } catch {
    notify.error()
  }
}

onMounted(fetchSessioni)
</script>

<template>
  <div v-if="sessioni.length > 0" class="sessioni-panel">
    <div class="sessioni-header">
      <h3 class="sessioni-title">
        <i class="pi pi-shield"></i>
        <span>{{ t('sessions.other_active_title') }}</span>
        <Badge :value="sessioni.length" severity="warn" />
      </h3>
      <div class="sessioni-actions">
        <Button
          :label="t('sessions.revoke_all')"
          icon="pi pi-times"
          severity="danger"
          text
          size="small"
          @click="confermaRevocaTutte"
        />
        <Button
          :icon="expanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
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
            icon="pi pi-times"
            severity="danger"
            size="small"
            text
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
  color: var(--p-text-color);
  margin: 0;
}

.sessioni-title i {
  color: var(--p-orange-400);
}
</style>
