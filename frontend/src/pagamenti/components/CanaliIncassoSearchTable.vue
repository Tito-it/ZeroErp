<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: L'elenco dei CANALI DI INCASSO — la configurazione da cui il denaro
//        entra, e il conto su cui atterra.
//
// ⛔ Tabella semplice e non `<ListaConfigurabile>`: questa lista NON ha un seed
//    in `ui.lista_definizione` (verificato sul database il 2026-08-28). Montarla
//    sul BB manderebbe al backend il `campo_sorgente` di colonne che nessuno ha
//    dichiarato, e il click sull'intestazione risponderebbe **400** —
//    esattamente il difetto gia' pagato sulle altre quattro liste del dominio.
//
// ⭐ La colonna della UTILITY del conto c'e' anche qui, non solo nel drawer:
//    e' il modo per accorgersi da fuori che due canali puntano al conto
//    sbagliato, senza aprirli uno per uno.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useInjectBlocked, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { MANAGE_ICONS } from '../../core/constants'
import { useEtichettePagamenti } from '../etichette'
import { useCanaliIncassoStore } from '../stores/canaliIncasso'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useCanaliIncassoStore()
const isBlocked = useInjectBlocked()
const isReadonly = useInjectReadonly()

const { onPage, onSort, applyFilters, paginatorProps, reloadAction } = useSearchTable(store, {
  defaultSortField: 'codice',
  defaultSortOrder: 'asc',
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: tipoFilter, onChange: onTipoChange } = bindSelect('tipo')

const { tipoCanale: etichettaTipo, opzioniTipoCanale } = useEtichettePagamenti()
const opzioniTipo = opzioniTipoCanale()

// ⚠️ In sola lettura il «Nuovo» non si mostra: un pulsante che apre un form che
//    non salva e' peggio di un pulsante assente.
const pageActions = computed(() => {
  const azioni = []
  if (!isReadonly.value) {
    azioni.push({
      key: 'new',
      kind: 'primary',
      label: t('pagamenti.canali.nuovo'),
      icon: MANAGE_ICONS.ADD,
      command: () => emit('new'),
    })
  }
  azioni.push(reloadAction())
  return azioni
})

// ⚠️ L'icona dice che gesto e': in sola lettura si ISPEZIONA (occhio), non si
//    modifica (matita) — una matita su un drawer che non salva promette una cosa
//    che non succedera'.
function buildRowActions(riga) {
  return [{
    key: 'apri',
    label: t(isReadonly.value ? 'common.view' : 'common.edit'),
    icon: isReadonly.value ? MANAGE_ICONS.INSPECT : MANAGE_ICONS.EDIT,
    command: () => emit('row-click', riga),
  }]
}

function onRowClick(evento) { emit('row-click', evento.data) }

onMounted(() => store.fetchList())
// ⛔ NIENTE `onActivated` che ricarica: la freschezza al rientro nella scheda la
//    tiene gia' `useSearchTable` (refetch idempotente della pagina corrente,
//    saltato alla prima attivazione). Aggiungerne un secondo qui manderebbe DUE
//    richieste identiche a ogni rientro, e le loro risposte possono tornare in
//    ordine inverso — su una lista di denaro, l'ordine conta.
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <Select
            v-model="tipoFilter"
            :options="opzioniTipo"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.canali.filtro_tipo')"
            show-clear
            style="width: 200px;"
            @update:model-value="onTipoChange"
          />
        </div>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <DataTable
        v-bind="paginatorProps"
        :value="store.items"
        :loading="store.loading"
        class="app-datatable"
        data-key="id"
        lazy
        removable-sort
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
      >
        <Column field="codice" :header="t('pagamenti.canali.col_codice')" sortable />
        <Column field="descrizione" :header="t('pagamenti.canali.col_descrizione')" sortable />
        <Column field="tipo" :header="t('pagamenti.canali.col_tipo')" sortable>
          <template #body="{ data }">
            <!-- Fail-visible: un tipo nuovo si vede come CODICE, non come cella
                 vuota. -->
            <Tag :value="etichettaTipo(data.tipo)" severity="secondary" />
          </template>
        </Column>
        <Column field="conto_iban" :header="t('pagamenti.canali.col_conto')">
          <template #body="{ data }">{{ data.conto_iban || '—' }}</template>
        </Column>
        <!-- ⚠️ NULL qui non e' un buco: e' «nessuna utility» — il conto generico
             del ruolo, o un'istanza senza PDP. Due casi legittimi e diversi, e
             nessuno dei due e' un dato mancante. -->
        <Column
          field="conto_utility_descrizione"
          :header="t('pagamenti.canali.col_utility')"
        >
          <template #body="{ data }">
            <span v-if="data.conto_utility_descrizione">
              {{ data.conto_utility_descrizione }}
            </span>
            <span v-else class="app-text-muted">
              {{ t('pagamenti.canali.conto_senza_utility') }}
            </span>
          </template>
        </Column>
        <Column field="centro_descrizione" :header="t('pagamenti.canali.col_centro')">
          <template #body="{ data }">{{ data.centro_descrizione || '—' }}</template>
        </Column>
        <Column field="attivo" :header="t('pagamenti.canali.col_attivo')">
          <template #body="{ data }">
            <Tag
              :value="t(data.attivo ? 'common.yes' : 'common.no')"
              :severity="data.attivo ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </Column>

        <template #empty>
          <div class="app-empty-state">
            <i class="pi pi-inbox" />
            <!-- ⭐ Il vuoto qui ha una CONSEGUENZA, e va detta: senza canali non
                 si apre una distinta col canale, e la coda del denaro non
                 attribuito resta senza padrone. -->
            <p>{{ t('pagamenti.canali.nessun_canale') }}</p>
          </div>
        </template>
      </DataTable>
    </template>
  </div>
</template>
