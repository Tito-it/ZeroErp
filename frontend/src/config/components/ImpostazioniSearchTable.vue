<script setup>
// Scopo: DataTable parametri di sistema con ricerca e colonne multi-livello.
// Mostra: codice, descrizione, default, emittente, gruppo, mio override, valore attivo.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { resolveParameterLevel, parameterLevelSeverity } from '../../core/utils/parameterLevel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const emit = defineEmits(['edit-override', 'remove-override', 'remove-emittente-override'])
const { t } = useI18n()
const store = useImpostazioniStore()
const auth = useAuthStore()
const isReadonly = useInjectReadonly()

function levelLabel(level) {
  return t(`impostazioni.level_${level}`)
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="store.searchText" :placeholder="t('impostazioni.search_placeholder')" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn"
          v-tooltip.bottom="t('common.reload_list')" @click="store.fetchList" />
      </div>
    </div>

    <DataTable
      :value="store.filteredParameters"
      :loading="store.loading"
      striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      data-key="code"
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
      <Column v-if="!isReadonly" :header="t('impostazioni.col_actions')" style="width: 100px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <div class="app-row-actions">
            <Button icon="pi pi-pencil" text rounded size="small" class="app-edit-btn"
              v-tooltip.bottom="t('impostazioni.edit_override')"
              @click="emit('edit-override', data)" />
            <Button v-if="auth.isAdmin && data.emittente_override_id" icon="pi pi-building" text rounded size="small"
              class="app-delete-btn"
              v-tooltip.bottom="t('impostazioni.remove_emittente_override')"
              @click="emit('remove-emittente-override', data)" />
            <Button v-if="data.user_override_id" icon="pi pi-trash" text rounded size="small"
              class="app-delete-btn"
              v-tooltip.bottom="t('impostazioni.remove_override')"
              @click="emit('remove-override', data)" />
          </div>
        </template>
      </Column>
    </DataTable>
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
