<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il tab «Di sistema» dell'area Accessi (brief-db-be-fe-area-accessi,
//        A-6): le credenziali delle MACCHINE — gli utenti tecnici dei processi
//        automatici e i sistemi esterni (API_CLIENT). Lista a catalogo
//        `anagrafiche.accessi_sistema`.
// ⛔ SOLA LETTURA, per decisione (A-6): il proprietario di queste credenziali
//    e' il pannello dei processi automatici. Bloccare un utente di sistema da
//    qui fermerebbe un automatismo a sua insaputa, e il secondo fattore su una
//    macchina non ha senso. Il clic sulla riga apre il drawer del processo
//    (la vista d'insieme non lo duplica: quello mostra gli utenti di UN processo).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import FiltriLista from '../../core/components/FiltriLista.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { buildBoolOptions, buildOptionsConTutti } from '../../core/utils/options'
import { TIPO_ACCESSO_SISTEMA } from '../constants'
import { useAccessiSistemaStore } from '../stores/accessiSistema'
import ProcessoDrawer from './ProcessoDrawer.vue'

const { t } = useI18n()
const notify = useNotify()
const store = useAccessiSistemaStore()
const drawer = useDrawerState()

// Nessuna azione oltre a «Ricarica»: niente `onNew`, niente `exportFn`.
const {
  searchText, applyFilters, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'username' },
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: tipoFilter, onChange: onTipoChange } = bindSelect('tipo')
const { value: attivaFilter, onChange: onAttivaChange } = bindSelect('identita_attiva')
const { value: bloccataFilter, onChange: onBloccataChange } = bindSelect('bloccata')

const tipoOptions = buildOptionsConTutti(t,
  Object.values(TIPO_ACCESSO_SISTEMA).map(v => ({ value: v, label: t(`amministrazione.accessi.tipo.${v}`) })),
)
const boolOptions = buildBoolOptions(t)

onMounted(() => {
  store.fetchList()
})

// Scopo: apre il processo automatico della credenziale. Un sistema esterno
//        (API_CLIENT) non ha un processo: lo si dice, invece di non fare niente.
function onRowClick(data) {
  if (!data.processo_codice) {
    notify.info(t('amministrazione.accessi.sistema_senza_processo'))
    return
  }
  drawer.editRow(data, 'processo_codice')
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <FiltriLista :store="store">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('amministrazione.accessi.search_sistema')"
          />
        </template>
        <Select
          v-model="tipoFilter" class="app-filter-w-sm"
          :options="tipoOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_tipo')"
          @change="onTipoChange"
        />
        <Select
          v-model="attivaFilter" class="app-filter-w-sm"
          :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_identita_attiva')"
          @change="onAttivaChange"
        />
        <Select
          v-model="bloccataFilter" class="app-filter-w-sm"
          :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_bloccata')"
          @change="onBloccataChange"
        />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.accessi_sistema"
      data-key="auth_user_id"
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
      <template #cell-tipo="{ data }">
        <Tag :value="t(`amministrazione.accessi.tipo.${data.tipo}`)" severity="secondary" />
      </template>
    </ListaConfigurabile>

    <ProcessoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :codice="drawer.state.itemId"
    />
  </div>
</template>
