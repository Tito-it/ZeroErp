<script setup>
// Scopo: Lista admin categorie cliente, configurabile
//        (`<ListaConfigurabile codice="anagrafiche.categorie_clienti">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente.
//        Nessun export: il dominio non ha endpoint (lo scaffolding omette
//        l'azione da se', non ricevendo `exportFn`).
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useCategorieClientiStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindSelect } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: partecipaPromoFilter, onChange: onPartecipaPromoChange } = bindSelect('partecipa_promo')
const boolOptions = buildBoolOptions(t)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="anagrafiche.categorie_clienti"
    :tab-entity="TAB_ENTITIES.CATEGORIE_CLIENTI"
    :search-placeholder="t('amministrazione.categorie_clienti.search_placeholder')"
    new-tooltip-key="amministrazione.categorie_clienti.new"
    default-sort-field="ordinamento"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
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
    </template>
    <!-- ⛔ Nessuno slot per `partecipa_promo` (220): e' `formato=yesno` a
         catalogo e lo rende `SiNoTag` dal BB. Fino al 2026-09-14 qui c'era
         lo stesso Tag scritto a mano SOPRA quel formato. -->
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
