<script setup>
// Scopo: Lista asset documentali configurabile
//        (`<ListaConfigurabile codice="documenti.template_asset">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Le righe non si possono
//        eliminare fisicamente (trigger DB A3): soft-disable via PATCH
//        `attivo=false` o `valido_al`. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se').
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateAssetDocumentiStore } from '../stores/templateAssetDocumenti'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { useLookupEtichettato } from '../../core/composables/useLookupEtichettato'
import { buildBoolOptions } from '../../core/utils/options'
import { formatSize } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'

const emit = defineEmits(['new', 'row-click'])
const { t, te } = useI18n()
// Il tipo di risorsa con l'etichetta che il DB dichiara riga per riga
// (BE13 di brief-db-revisione-documenti): il valore e' l'id, la chiave del
// filtro `asset_tipo_id`.
const { opzioni: tipoAssetOptions } = useLookupEtichettato(
  { rel: 'documenti.tipi_asset_documento' }, { campoCodice: 'id' },
)
const store = useTemplateAssetDocumentiStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindSelect } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: assetTipoFilter, onChange: onAssetTipoChange } = bindSelect('asset_tipo_id')
const boolOptions = buildBoolOptions(t)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="documenti.template_asset"
    :tab-entity="TAB_ENTITIES.TEMPLATE_ASSET_DOCUMENTI"
    :search-placeholder="t('config.modelli_documenti.asset.search_placeholder')"
    new-tooltip-key="config.modelli_documenti.asset.new"
    default-sort-field="codice"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
      <Select
        v-model="assetTipoFilter"
        class="app-filter-w-md"
        :options="tipoAssetOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('config.modelli_documenti.asset.filter_tipo')"
        show-clear
        @change="onAssetTipoChange"
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
    <!-- Il tipo con l'etichetta che il DB dichiara, come nel filtro: la
         `descrizione` del seed resta il ripiego (e l'ordinamento). -->
    <template #cell-asset_tipo_descrizione="{ data }">
      {{ labelOrCode(t, te, data.asset_tipo_etichetta_key, data.asset_tipo_descrizione) }}
    </template>
    <!-- Byte grezzi a video sono illeggibili: la cella resta formattata,
         ma l'ordinamento e' numerico sul campo (BE, `a.file_size_bytes`). -->
    <template #cell-file_size_bytes="{ data }">
      {{ formatSize(data.file_size_bytes) }}
    </template>
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
