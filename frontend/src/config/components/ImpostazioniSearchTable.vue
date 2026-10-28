<script setup>
// Scopo: DataTable parametri di sistema con ricerca e colonne multi-livello.
// Mostra: codice, descrizione, default, emittente, gruppo, mio override, valore attivo.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../../core/constants'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { resolveParameterLevel, parameterLevelSeverity, ammettePersonalizzazione } from '../../core/utils/parameterLevel'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['edit-override', 'remove-override', 'remove-emittente-override'])
const { t } = useI18n()
const store = useImpostazioniStore()
const auth = useAuthStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: store.fetchList,
  },
])

function levelLabel(level) {
  return t(`config.impostazioni.level_${level}`)
}

// Scopo: click riga = modifica override (pattern standard liste). Su un
// parametro che vale per tutti il drawer si apre in sola consultazione.
function onRowClick(event) {
  if (isReadonly.value) return
  emit('edit-override', event.data)
}

// Scopo: azioni secondarie di riga — rimozione override (admin/utente),
// condizionate alla presenza dell'override corrispondente. La modifica e'
// sul click riga, non in questo menu.
function buildRowActions(data) {
  return [
    {
      key: 'remove-emittente-override',
      label: t('config.impostazioni.remove_emittente_override'),
      icon: MANAGE_ICONS.BUILDING,
      severity: 'danger',
      visible: auth.isSuperAdmin && !!data.emittente_override_id,
      command: () => emit('remove-emittente-override', data),
    },
    {
      key: 'remove-override',
      label: t('config.impostazioni.remove_override'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !!data.user_override_id,
      command: () => emit('remove-override', data),
    },
  ]
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <!-- ⚠️ Nessuno `:store`: questa lista non ha FILTRI, solo la ricerca — che
           per D2 non e' un filtro. Senza slot di default il building block non
           rende ne' l'imbuto ne' il drawer. -->
      <FiltriLista>
        <template #sempre>
          <InputText v-model="store.searchText" class="app-filter-w-lg"
            :placeholder="t('config.impostazioni.search_placeholder')" />
        </template>
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <DataTable
      :value="store.filteredParameters"
      :loading="store.loading"
      striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      data-key="code"
      @row-click="onRowClick"
      selection-mode="single"
    >
      <template #empty>
        <div class="app-empty-state">{{ t('config.impostazioni.empty_state') }}</div>
      </template>

      <Column field="code" :header="t('config.impostazioni.col_code')" sortable style="width: 220px;">
        <template #body="{ data }">
          <span class="app-mono">{{ data.code }}</span>
        </template>
      </Column>
      <Column field="description" :header="t('config.impostazioni.col_description')" style="min-width: 250px;" />
      <Column field="default_value" :header="t('config.impostazioni.col_default')" style="width: 130px;">
        <template #body="{ data }">
          <span class="app-mono text-muted">{{ data.default_value ?? '—' }}</span>
        </template>
      </Column>
      <Column field="emittente_value" :header="t('config.impostazioni.col_emittente')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.emittente_value != null" class="app-mono">{{ data.emittente_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="group_value" :header="t('config.impostazioni.col_group')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.group_value != null" class="app-mono">{{ data.group_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <!-- Cascata: il livello categoria_cliente sta fra group e user
           (post brief DB 2026-05-19, migration 20260519-01). Compare con
           valore solo se la chiamata /settings/ ha passato categoria_cliente_id
           o billing_account_id; altrimenti '—'. -->
      <Column field="categoria_cliente_value" :header="t('config.impostazioni.col_categoria_cliente')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.categoria_cliente_value != null" class="app-mono">{{ data.categoria_cliente_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="user_value" :header="t('config.impostazioni.col_user')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.user_value != null" class="app-mono">{{ data.user_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="resolved_value" :header="t('config.impostazioni.col_resolved')" style="width: 160px;">
        <template #body="{ data }">
          <span class="parameter-resolved">
            <span class="app-mono font-bold">{{ data.resolved_value ?? '—' }}</span>
            <Tag :value="levelLabel(resolveParameterLevel(data))" :severity="parameterLevelSeverity(resolveParameterLevel(data))"
              class="parameter-level-tag" />
            <Tag v-if="!ammettePersonalizzazione(data)" :value="t('config.impostazioni.per_tutti')"
              severity="contrast" class="parameter-level-tag" />
          </span>
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>

<style scoped>
.text-muted { color: var(--app-text-muted); }
.parameter-resolved {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.parameter-level-tag { font-size: 0.7rem; }
.app-row-actions {
  display: flex;
  gap: 0.25rem;
}
.app-empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--app-text-muted);
}
</style>
