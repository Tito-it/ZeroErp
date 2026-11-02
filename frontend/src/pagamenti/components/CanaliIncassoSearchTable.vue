<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: L'elenco dei CANALI DI INCASSO — la configurazione da cui il denaro
//        entra, e il conto su cui atterra.
//
// ⭐ MONTATA su `<ListaConfigurabile>` il 2026-09-02 (lista 60). Il commento
//    precedente diceva «non ha un seed in `ui.lista_definizione`, montarla sul
//    BB risponderebbe 400 al click»: era vero e ora non lo e' piu' — il seed
//    c'e' e `ENTI_INCASSO_SORT_COLUMNS` e' stata ri-chiavata sui
//    `campo_sorgente` fisici (richiesta BE-2), che era la meta' mancante.
// ⚠️ Solo `codice`, `descrizione`, `tipo` e `centro_descrizione` sono
//    `ordinabile = t` a catalogo: le altre non hanno una colonna ordinabile
//    dietro, e seminarle `t` avrebbe messo a video una freccia che risponde 400.
//
// ⭐ La colonna della UTILITY del conto c'e' anche qui, non solo nel drawer:
//    e' il modo per accorgersi da fuori che due canali puntano al conto
//    sbagliato, senza aprirli uno per uno.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useInjectBlocked, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { MANAGE_ICONS } from '../../core/constants'
import { useEtichettePagamenti } from '../etichette'
import { useCanaliIncassoStore } from '../stores/canaliIncasso'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useCanaliIncassoStore()
const isBlocked = useInjectBlocked()
const isReadonly = useInjectReadonly()

// Scaffolding della lista configurabile: `useSearchTable` + le due azioni di
// utility + `pageActions`. ⚠️ Niente `exportFn`: la lista non ha endpoint di
// export, e il BB rende l'azione condizionale.
const {
  onPage, onSort, applyFilters, paginatorProps, reloadAction, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions: azioniScaffolding,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'codice', defaultSortOrder: 'asc' },
})

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: tipoFilter, onChange: onTipoChange } = bindSelect('tipo')

const { tipoCanale: etichettaTipo, opzioniTipoCanale } = useEtichettePagamenti()
// ⚠️ «Tutti i tipi» e' una VOCE dell'elenco (`value: null`), non la X di
//    `show-clear`: sono due modi di dire la stessa cosa, e la X non si vede
//    finche' non hai gia' scelto — cioe' proprio quando serve sapere che
//    «nessun filtro» e' una scelta possibile. Stessa forma di `ritardoOptions`
//    in `SituazioneApertaView` e del filtro stato dei registri.
// ⚠️ `computed` e non un array fisso: le etichette vengono da `t()`, e al
//    cambio lingua un array costruito una volta resterebbe indietro in silenzio.
const opzioniTipo = computed(() => [
  { value: null, label: t('pagamenti.canali.filtro_tipo_tutti') },
  ...opzioniTipoCanale(),
])

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
  // ⭐ Le due azioni di utility della lista configurabile — «Personalizza
  //    colonne» e (quando ci sara' un endpoint) «Esporta» — arrivano dallo
  //    scaffolding: non si riscrivono qui, o divergono dalle altre 40 liste.
  //    ⚠️ Lo scaffolding porta anche il proprio `reload`: si filtra, perche'
  //    questa toolbar ha gia' il suo `reloadAction()`, che sa disabilitarsi su
  //    lista vuota.
  azioni.push(...azioniScaffolding.value.filter((a) => a.key !== 'reload' && a.key !== 'new'))
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
        <FiltriLista :store="store">
          <Select
            v-model="tipoFilter"
            class="app-filter-w-md"
            :options="opzioniTipo"
            option-label="label"
            option-value="value"
            :placeholder="t('pagamenti.canali.filtro_tipo')"
            @update:model-value="onTipoChange"
          />
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
        codice="pagamenti.canali_incasso"
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
          <!-- Fail-visible: un tipo nuovo si vede come CODICE, non come cella
               vuota. -->
          <Tag :value="etichettaTipo(data.tipo)" severity="secondary" />
        </template>
        <template #cell-conto_iban="{ data }">{{ data.conto_iban || '—' }}</template>
        <!-- ⚠️ NULL qui non e' un buco: e' «nessuna utility» — il conto generico
             del ruolo, o un'istanza senza PDP. Due casi legittimi e diversi, e
             nessuno dei due e' un dato mancante. -->
        <template #cell-conto_utility="{ data }">
          <span v-if="data.conto_utility_descrizione">
            {{ data.conto_utility_descrizione }}
          </span>
          <span v-else class="app-text-muted">
            {{ t('pagamenti.canali.conto_senza_utility') }}
          </span>
        </template>
        <template #cell-centro="{ data }">{{ data.centro_descrizione || '—' }}</template>
        <template #cell-attivo="{ data }">
          <Tag
            :value="t(data.attivo ? 'common.yes' : 'common.no')"
            :severity="data.attivo ? 'success' : 'secondary'"
          />
        </template>
        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
