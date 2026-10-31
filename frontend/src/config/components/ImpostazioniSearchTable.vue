<script setup>
// Scopo: Lista configurabile dei parametri di sistema
//        (`<ListaConfigurabile codice="config.parametri_impostazioni">`, 108)
//        con ricerca lato server e i valori di ogni livello della cascata come
//        colonne (B1 di Tid: i livelli sono colonne). Click riga = modifica
//        override; il kebab rimuove gli override.
//        ⭐ Dal 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro riga
//        2): prima una `DataTable` grezza sulla lista intera, filtrata nel
//        browser.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../../core/constants'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import { resolveParameterLevel, parameterLevelSeverity, ammettePersonalizzazione } from '../../core/utils/parameterLevel'
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

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, { searchTableOptions: { defaultSortField: 'code' } })

// I quattro livelli di override della cascata sono colonne: lo stesso
// rendering per tutti («—» dove il livello non ha un valore). Il quinto, il
// default, ha la sua cella (`#cell-default_value`, sotto): e' il valore di
// partenza, non un override.
const COLONNE_LIVELLO = ['emittente_value', 'group_value', 'categoria_cliente_value', 'user_value']

function levelLabel(level) {
  return t(`config.impostazioni.level_${level}`)
}

// Scopo: click riga = modifica override (pattern standard liste). Su un
// parametro che vale per tutti il drawer si apre in sola consultazione.
// `<ListaConfigurabile>` emette la riga, non l'evento PrimeVue.
function onRowClick(data) {
  if (isReadonly.value) return
  emit('edit-override', data)
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
      <!-- ⚠️ Nessuno slot di default: questa lista non ha FILTRI, solo la
           ricerca — che per D2 non e' un filtro. -->
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText v-model="searchText" class="app-filter-w-lg"
            :placeholder="t('config.impostazioni.search_placeholder')" />
        </template>
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="config.parametri_impostazioni"
      data-key="code"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-code="{ data }">
        <span class="app-mono">{{ data.code }}</span>
      </template>
      <template #cell-default_value="{ data }">
        <span class="app-mono text-muted">{{ data.default_value ?? '—' }}</span>
      </template>
      <!-- Cascata: il livello categoria_cliente sta fra group e user (post
           brief DB 2026-05-19): ha un valore solo se la chiamata ha passato
           categoria_cliente_id o billing_account_id; altrimenti '—'. -->
      <template v-for="col in COLONNE_LIVELLO" :key="col" #[`cell-${col}`]="{ data }">
        <span v-if="data[col] != null" class="app-mono">{{ data[col] }}</span>
        <span v-else class="text-muted">—</span>
      </template>
      <template #cell-resolved_value="{ data }">
        <span class="parameter-resolved">
          <span class="app-mono font-bold">{{ data.resolved_value ?? '—' }}</span>
          <Tag :value="levelLabel(resolveParameterLevel(data))" :severity="parameterLevelSeverity(resolveParameterLevel(data))"
            class="parameter-level-tag" />
          <Tag v-if="!ammettePersonalizzazione(data)" :value="t('config.impostazioni.per_tutti')"
            severity="contrast" class="parameter-level-tag" />
        </span>
      </template>
      <template v-if="!isReadonly" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>
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
</style>
