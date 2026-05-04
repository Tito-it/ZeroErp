<script setup>
// Scopo: DataTable parametri di sistema con ricerca e colonne multi-livello.
// Mostra: codice, descrizione, default, emittente, gruppo, mio override, valore attivo.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../../core/constants'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { resolveParameterLevel, parameterLevelSeverity } from '../../core/utils/parameterLevel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const emit = defineEmits(['edit-override', 'remove-override', 'remove-emittente-override'])
const { t } = useI18n()
const store = useImpostazioniStore()
const auth = useAuthStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()

function levelLabel(level) {
  return t(`impostazioni.level_${level}`)
}

// Scopo: click riga = modifica override (pattern standard liste).
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
      label: t('impostazioni.remove_emittente_override'),
      icon: MANAGE_ICONS.BUILDING,
      severity: 'danger',
      visible: auth.isAdmin && !!data.emittente_override_id,
      command: () => emit('remove-emittente-override', data),
    },
    {
      key: 'remove-override',
      label: t('impostazioni.remove_override'),
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
      <div class="app-page-filters">
        <InputText v-model="store.searchText" :placeholder="t('impostazioni.search_placeholder')" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="store.fetchList" />
      </div>
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
        <div class="app-empty-state">{{ t('impostazioni.empty_state') }}</div>
      </template>

      <Column field="code" :header="t('impostazioni.col_code')" sortable style="width: 220px;">
        <template #body="{ data }">
          <span class="font-mono">{{ data.code }}</span>
        </template>
      </Column>
      <Column field="description" :header="t('impostazioni.col_description')" style="min-width: 250px;" />
      <Column field="default_value" :header="t('impostazioni.col_default')" style="width: 130px;">
        <template #body="{ data }">
          <span class="font-mono text-muted">{{ data.default_value ?? '—' }}</span>
        </template>
      </Column>
      <Column field="emittente_value" :header="t('impostazioni.col_emittente')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.emittente_value != null" class="font-mono">{{ data.emittente_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="group_value" :header="t('impostazioni.col_group')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.group_value != null" class="font-mono">{{ data.group_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="user_value" :header="t('impostazioni.col_user')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.user_value != null" class="font-mono">{{ data.user_value }}</span>
          <span v-else class="text-muted">—</span>
        </template>
      </Column>
      <Column field="resolved_value" :header="t('impostazioni.col_resolved')" style="width: 160px;">
        <template #body="{ data }">
          <span class="parameter-resolved">
            <span class="font-mono font-bold">{{ data.resolved_value ?? '—' }}</span>
            <Tag :value="levelLabel(resolveParameterLevel(data))" :severity="parameterLevelSeverity(resolveParameterLevel(data))"
              class="parameter-level-tag" />
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
.font-mono { font-family: monospace; }
.font-bold { font-weight: 600; }
.text-muted { color: var(--p-text-muted-color); }
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
  color: var(--p-text-muted-color);
}
</style>
