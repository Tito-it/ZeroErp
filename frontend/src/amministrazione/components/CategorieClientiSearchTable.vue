<script setup>
// Scopo: Lista admin categorie cliente, configurabile
//        (`<ListaConfigurabile codice="anagrafiche.categorie_clienti">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente.
//        Nessun export: il dominio non ha endpoint (lo scaffolding omette
//        l'azione da se', non ricevendo `exportFn`).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useCategorieClientiStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.categorie_clienti.new',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'ordinamento' },
})

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: partecipaPromoFilter, onChange: onPartecipaPromoChange } = bindSelect('partecipa_promo')

const boolOptions = buildBoolOptions(t)

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.CATEGORIE_CLIENTI)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('amministrazione.categorie_clienti.search_placeholder')"
          />
        </template>
        <Select
          v-model="partecipaPromoFilter"
          class="app-filter-w-sm"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.categorie_clienti.filter_partecipa_promo')"
          @change="onPartecipaPromoChange"
        />
        <Select
          v-model="attivoFilter"
          class="app-filter-w-sm"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
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
      codice="anagrafiche.categorie_clienti"
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
      <!-- ⛔ Nessuno slot per `partecipa_promo` (220): e' `formato=yesno` a
           catalogo e lo rende `SiNoTag` dal BB. Fino al 2026-09-14 qui c'era
           lo stesso Tag scritto a mano SOPRA quel formato. -->
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>
