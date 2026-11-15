<script setup>
// Scopo: Lista articoli configurabile
//        (`<ListaConfigurabile codice="catalogo.articoli">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Lista a ricerca obbligatoria: resta
//        nascosta finche' non si e' cercato. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se').
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildAttivoOptions, buildBoolOptions } from '../../core/utils/options'
import { labelOrCode } from '../../core/utils/i18nLabel'
import FiltriLista from '../../core/components/FiltriLista.vue'
import EstensioneDrawerHost from '../../core/components/EstensioneDrawerHost.vue'
import { useAzioniEstese } from '../../core/composables/useAzioniEstese'
import { PUNTI_ESTENSIONE } from '../../core/estensioni'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const emit = defineEmits(['new', 'row-click', 'manage-uom', 'manage-bom', 'manage-note'])

// Le azioni di riga che altri domini contribuiscono all'articolo (oggi: i lotti
// di magazzino), col drawer che aprono (core/estensioni.js).
const {
  voci: azioniEstese, aperto: drawerEsteso, impostaVisibile: visibileEsteso,
} = useAzioniEstese(PUNTI_ESTENSIONE.ARTICOLO_AZIONI_RIGA)
const { t, te } = useI18n()
const store = useArticoliStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  mostraLista, mostraSearchHint,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'catalogo.nuovo_articolo',
  onNew: () => emit('new'),
  // Allineato al preset del seed (`codice asc`); lo store parte gia' da qui.
  searchTableOptions: { defaultSortField: 'codice' },
})

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: tipologiaFilter, onChange: onTipologiaChange } = bindSelect('tipo_voce_id')
const { value: compositoFilter, onChange: onCompositoChange } = bindSelect('is_composito')
const { value: gruppoFilter, onChange: onGruppoChange } = bindSelect('gruppo_voce_id')

const boolOptions = buildBoolOptions(t)
// ⛔ «TUTTI» C'E', ED E' LA CORREZIONE DEL 2026-09-23 (rilievo in-app di Tid).
//    Senza quella voce — e senza `show-clear` — questo filtro NON si poteva
//    togliere: nasce a `Attivo` e le uniche due scelte erano `Attivo` e `Non
//    attivo`, cioe' contava un'unita' nel segno dei filtri attivi su cui
//    l'operatore non aveva nessun gesto.
// ⚠️ Il backend lo ammette: la lista applica `attivo` solo se valorizzato
//    (`qp_bool_optional` nella view, `if attivo is not None` nel repository),
//    quindi «Tutti» mostra attivi e disattivati insieme.
// ⭐ La terna sta nel BB `buildAttivoOptions` (regola del 2, ok Tid: era scritta
//    a mano in cinque sedi): etichette di DOMINIO, non `Sì`/`No` di
//    `buildBoolOptions` — qui il filtro e' lo STATO dell'articolo, le stesse
//    parole che `AttivoTag` scrive nella colonna.
const attivoOptions = buildAttivoOptions(t)

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// Scopo: azioni di riga dell'articolo (sub-drawer gestionali).
// Capability BoM (Fase 6) letta dalla vista DB: data.puo_gestire_bom +
// data.motivo_non_gestibile_bom. Tooltip mostra il motivo quando disabled.
function manageBomTooltip(data) {
  if (data.puo_gestire_bom) return t('catalogo.gestisci_bom')
  const motivo = data.motivo_non_gestibile_bom
  if (!motivo) return t('catalogo.gestisci_bom')
  // Difensivo: se il DB introduce un nuovo motivo non mappato i18n,
  // fallback alla label generica invece di mostrare la chiave raw.
  const key = `catalogo.motivo_${motivo.toLowerCase()}`
  return labelOrCode(t, te, key, t('catalogo.gestisci_bom'))
}

function buildRowActions(data) {
  return [
    {
      key: 'manage-uom',
      label: t('catalogo.gestisci_uom'),
      icon: MANAGE_ICONS.UOM,
      command: () => emit('manage-uom', data),
    },
    {
      key: 'manage-bom',
      label: t('catalogo.gestisci_bom'),
      icon: MANAGE_ICONS.BOM,
      disabled: !data.puo_gestire_bom,
      tooltip: manageBomTooltip(data),
      command: () => emit('manage-bom', data),
    },
    {
      key: 'manage-note',
      label: t('catalogo.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => emit('manage-note', data),
    },
    ...azioniEstese(data),
  ]
}

useTabFreshness(store, TAB_ENTITIES.ARTICOLO)
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('catalogo.search_placeholder')" />
        </template>
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          class="app-filter-w-sm"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" />
        <Select v-model="compositoFilter" :options="boolOptions" option-label="label" option-value="value"
          class="app-filter-w-sm"
          :placeholder="t('catalogo.filtro_composito')" show-clear @change="onCompositoChange" />
        <LookupSelect v-model="tipologiaFilter" rel="vendite.articoli_tipologie"
          class="app-filter-w-md"
          :placeholder="t('catalogo.filtro_tipologia')" show-clear @change="onTipologiaChange" />
        <LookupSelect v-model="gruppoFilter" rel="vendite.articoli_gruppi"
          class="app-filter-w-md"
          :placeholder="t('catalogo.filtro_gruppo')" show-clear @change="onGruppoChange" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <SearchHint v-if="mostraSearchHint" />

    <ListaConfigurabile
      v-show="mostraLista"
      ref="listaRef"
      codice="catalogo.articoli"
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
      <template #cell-codice="{ data }">
        <span class="codice-truncate" :title="data.codice">{{ data.codice }}</span>
        <!-- Ritirato alla data operativa (`e_obsoleto` della vista: lo calcola
             il DB, qui non si confrontano date). Sta sotto il codice perche'
             la lista non ha una colonna sua. -->
        <Tag v-if="data.e_obsoleto" :value="t('catalogo.tag_ritirato')" severity="warn" class="mt-025" />
      </template>
      <!-- La colonna IVA porta `iva_ref_id` come campo (e' quello che il seed
           dichiara), ma a video vale l'aliquota: senza slot si vedrebbe l'id. -->
      <template #cell-iva_ref_id="{ data }">
        {{ data.iva_aliquota_iva != null ? `${data.iva_aliquota_iva}%` : '' }}
      </template>
      <!-- ⛔ Nessuno slot per `is_solo_componente` (327) e `gestito_a_magazzino`
           (748): sono `formato=yesno` a catalogo e li rende `SiNoTag` dal BB.
           Fino al 2026-09-14 erano due slot con lo stesso Tag scritto a mano. -->
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>
    </template>
    <EstensioneDrawerHost :stato="drawerEsteso" @update:visible="visibileEsteso" />
  </div>
</template>

<style scoped>
/* Solo il codice (identificatore) tronca con ellipsis: e' un token,
   andare a capo non ha senso. La descrizione invece wrappa per parole
   in modo naturale (default browser, white-space: normal): la cella
   cresce in altezza su schermi stretti, niente sovrapposizioni. */
.codice-truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
