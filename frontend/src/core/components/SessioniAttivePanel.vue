<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pannello della home «altre sessioni attive» dell'operatore collegato:
//        `<ListaConfigurabile codice="core.sessioni_attive">` (colonne, ordine,
//        personalizzazione dal catalogo), revoca di una sessione o di tutte.
//
// ⭐ Dal 2026-09-27 e' una lista a catalogo (brief-db-liste-datatable-grezze
//    riga 1): fino a quel giorno una `DataTable` grezza su tutte le sessioni
//    in una volta, con la corrente tolta in Python DOPO la lettura. Ora pagina
//    il backend, e la corrente la toglie la SQL — cosi' il conteggio e' giusto.
// ⭐ Il pannello si mostra, il badge conta e «revoca tutte» conferma su
//    `store.totaleAttive` (le sessioni che ESISTONO), non su `totalRecords`
//    (quelle che la ricerca TROVA): una ricerca senza risultati non deve far
//    sparire il pannello con dentro la casella che l'ha svuotato.
// ⛔ Su una lettura fallita la lista NON si azzera (il core tiene l'ultimo
//    dato noto e alza `erroreCaricamento`): azzerarla farebbe sparire il
//    pannello, cioe' direbbe «non hai altre sessioni attive» quando la verita'
//    e' «non lo so». Su un pannello di sicurezza e' la bugia peggiore.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ListaConfigurabile from './ListaConfigurabile.vue'
import ListaConfigStatusTag from './ListaConfigStatusTag.vue'
import PageActionsBar from './PageActionsBar.vue'
import FiltriLista from './FiltriLista.vue'
import RowActionsMenu from './RowActionsMenu.vue'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useNotify } from '../composables/useNotify'
import { useApiHandler } from '../composables/useApiHandler'
import { useListaConfigurabilePage } from '../composables/useListaConfigurabilePage'
import { MANAGE_ICONS } from '../constants'
import { useSessioniAttiveStore } from '../stores/sessioniAttive'
import { revocaSessione as apiRevocaSessione, revocaTutteSessioni as apiRevocaTutte } from '../api/sessioni'
import { parseIstante, adesso } from '../utils/date'

const { t } = useI18n()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const { execute } = useApiHandler()
const store = useSessioniAttiveStore()

// Niente «Nuovo» ne' export: le sessioni nascono dal login, e l'elenco e' di
// consultazione con la sola revoca. Restano ricarica e personalizza.
const {
  searchText, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  // Allineato al preset `sessioni_attive_default` (`data_ultimo_evento desc`).
  // Pannello della home, non lista di rotta: niente ricerca universale.
  searchTableOptions: {
    defaultSortField: 'data_ultimo_evento', defaultSortOrder: 'desc', incorporata: true,
  },
})

// ⚠️ La revoca non e' istantanea (blacklist di N token + diario): senza uno
//    stato a video l'operatore preme, non vede niente e conclude che il
//    pulsante non funziona — che e' esattamente quello che e' successo.
const azioneInCorso = ref(false)
const expanded = ref(false)

// «Dispositivo» e' lo user agent grezzo a catalogo (`campo_sorgente =
// user_agent`, e la ricerca cerca li'): a video browser / sistema.
function parseUserAgent(ua) {
  if (!ua) return '—'
  // Browser
  let browser = t('sessions.unknown_browser')
  if (ua.includes('Firefox/')) browser = 'Firefox'
  else if (ua.includes('Edg/')) browser = 'Edge'
  else if (ua.includes('Chrome/')) browser = 'Chrome'
  else if (ua.includes('Safari/')) browser = 'Safari'
  // OS — ⚠️ i mobili PRIMA dei desktop: lo user agent Android contiene
  // «Linux», quello iPhone/iPad «like Mac OS X».
  let os = ''
  if (ua.includes('Windows')) os = 'Windows'
  else if (ua.includes('Android')) os = 'Android'
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS'
  else if (ua.includes('Mac OS')) os = 'macOS'
  else if (ua.includes('Linux')) os = 'Linux'
  return os ? `${browser} / ${os}` : browser
}

function timeAgo(dateStr) {
  if (!dateStr) return '—'
  const date = parseIstante(dateStr)
  if (!date) return '—'
  const diffMs = adesso() - date
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return t('sessions.now')
  if (diffMin < 60) return t('sessions.minutes_ago', { n: diffMin })
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return t('sessions.hours_ago', { n: diffHours })
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return t('sessions.yesterday')
  return t('sessions.days_ago', { n: diffDays })
}

// Scopo: l'unica azione di riga, la revoca — spenta mentre un'altra e' in corso.
function buildRowActions(data) {
  return [
    {
      key: 'revoca',
      label: t('sessions.revoke'),
      icon: MANAGE_ICONS.REVOCA,
      severity: 'danger',
      disabled: azioneInCorso.value,
      command: () => confermaRevoca(data),
    },
  ]
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

// ⚠️ Il numero e' quello delle sessioni ATTIVE, non delle trovate: «revoca
//    tutte» le revoca tutte, qualunque cosa ci sia nella casella di ricerca.
function confermaRevocaTutte() {
  confirmAction({
    header: t('sessions.revoke_all_confirm_title'),
    message: t('sessions.revoke_all_confirm_message', { count: store.totaleAttive }),
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
    await store.fetchList()
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
    await store.fetchList()
  } finally {
    azioneInCorso.value = false
  }
}

// ⚠️ Solo `onMounted`: il rientro sotto KeepAlive (la home ci vive) lo
//    rinfresca gia' `useSearchTable` dentro lo scaffolding, sulla pagina
//    corrente. Il pannello chiuso legge lo stesso: il badge deve contare.
onMounted(() => { store.fetchList() })
</script>

<template>
  <div v-if="store.totaleAttive > 0" class="sessioni-panel">
    <div class="sessioni-header">
      <h3 class="sessioni-title">
        <i :class="MANAGE_ICONS.SESSIONI"></i>
        <span>{{ t('sessions.other_active_title') }}</span>
        <Badge :value="store.totaleAttive" severity="warn" />
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
    <template v-if="expanded">
      <div class="app-page-toolbar">
        <FiltriLista :store="store">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('common.search')"
            />
          </template>
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
          </template>
        </PageActionsBar>
      </div>
      <!-- «Non so» non e' «nessuna sessione»: una lettura fallita lascia a
           video l'ultimo dato noto, e lo dice. -->
      <Message v-if="store.erroreCaricamento" severity="warn" :closable="false" size="small">
        {{ t('sessions.load_error') }}
      </Message>
      <ListaConfigurabile
        ref="listaRef"
        codice="core.sessioni_attive"
        data-key="jti"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :azioni-inline="1"
        @page="onPage"
        @sort="onSort"
        @config-loaded="onConfigLoaded"
      >
        <template #cell-dispositivo="{ data }">
          {{ parseUserAgent(data.user_agent) }}
        </template>
        <!-- A video il tempo trascorso («2 ore fa»): e' la domanda del
             pannello, «questa sessione e' viva?». L'export porta la data. -->
        <template #cell-data_ultimo_evento="{ data }">
          {{ timeAgo(data.data_ultimo_evento) }}
        </template>
        <!-- ⛔ Lo slot del kebab si chiama `#actions`: col nome sbagliato la
             colonna non viene resa affatto, e senza errori. -->
        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>

<style scoped>
.sessioni-panel {
  width: 100%;
  margin-bottom: 1.5rem;
}

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
