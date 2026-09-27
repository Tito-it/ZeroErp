<script setup>
// Scopo: Lista conversioni UoM configurabile
//        (`<ListaConfigurabile codice="catalogo.conversioni_uom">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`. Paginazione,
//        sort e search sono server-side (endpoint allineato alle due sorelle
//        UoM il 2026-08-01). Nessuna colonna azioni: il catalogo non la
//        prevede, la riga si apre col click.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import AttivoTag from '../../core/components/AttivoTag.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useConversioniUomStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindToggle } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: mostraNonAttive, onChange: onMostraNonAttiveChange } = bindToggle(
  'attivo', { on: null, off: true },
)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="catalogo.conversioni_uom"
    :tab-entity="TAB_ENTITIES.CONVERSIONI_UOM"
    :search-placeholder="t('catalogo.conv_search_placeholder')"
    new-tooltip-key="catalogo.nuova_conversione"
    default-sort-field="valido_al"
    default-sort-order="desc"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
      <FiltroToggle
        v-model="mostraNonAttive"
        :label="t('catalogo.conv_mostra_non_attive')"
        @change="onMostraNonAttiveChange"
      />
    </template>
    <template #cell-fattore="{ data }">
      <span class="app-mono">{{ data.fattore }}</span>
    </template>
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
