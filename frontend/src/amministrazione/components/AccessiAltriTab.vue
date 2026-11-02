<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il tab «Altri accessi» dell'area Accessi (brief-db-be-fe-area-accessi,
//        A-2/A-4): le persone senza veste operatore — clienti e fornitori del
//        portale, clienti dello shop — e le credenziali senza alcuna veste,
//        con il badge «Nessun accesso». Lista a catalogo
//        `anagrafiche.accessi_altri`.
// ⭐ Le vesti sono badge della riga (tipo + stato, una per veste): si leggono
//    qui, si governano dalla scheda del cliente o del fornitore (kebab «Apri la
//    scheda», o il drawer). Le azioni della CREDENZIALE (blocco, secondo
//    fattore) stanno nel drawer, come per gli operatori (A-5); «Elimina
//    accesso» sta anche nel kebab, spento col motivo dalla capability di riga
//    (brief-db-elimina-credenziale-senza-veste §6).
// ⚠️ Niente `useReadonlyMode`: in `amm-software` non c'e' un livello d'area da
//    risolvere — o sei super admin e vedi tutto, o non arrivi alla pagina.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import FiltriLista from '../../core/components/FiltriLista.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { MANAGE_ICONS, RUOLO_APPLICATIVO, STATO_SECONDO_FATTORE, STATO_VESTE } from '../../core/constants'
import { etichettaRuoloApplicativo } from '../../core/utils/i18nLabel'
import { buildBoolOptions, buildOptionsConTutti } from '../../core/utils/options'
import { statoVesteSeverity } from '../../core/utils/severity'
import { useAccessiAltriStore } from '../stores/accessiAltri'
import { useEliminaCredenziale } from '../composables/useEliminaCredenziale'
import { destinazioneVeste, useSchedaVeste } from '../composables/useSchedaVeste'
import AccessoAltroDrawer from './AccessoAltroDrawer.vue'

const { t, te } = useI18n()
const store = useAccessiAltriStore()
const drawer = useDrawerState()
const { apriSchedaVeste } = useSchedaVeste()
const { eliminaSpenta, motivoEliminaSpenta, chiediElimina } = useEliminaCredenziale()

// ⛔ Nessun `onNew` e nessun `exportFn`: una credenziale non nasce da qui (la
//    veste la crea l'invito, dalla scheda del soggetto), e l'export non ha
//    endpoint. Lo scaffolding omette da se' le azioni che non gli si passano.
const {
  searchText, applyFilters, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'nome_visualizzato' },
})

// I filtri passano dai binder (frontend-standards §«Un filtro si lega con un
// binder»): la casella segue lo store anche quando lo cambia «Pulisci filtri».
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: vesteFilter, onChange: onVesteChange } = bindSelect('ruolo_applicativo')
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_accesso')
const { value: nessunoFilter, onChange: onNessunoChange } = bindSelect('nessun_accesso')
const { value: fattoreFilter, onChange: onFattoreChange } = bindSelect('secondo_fattore_stato')
const { value: bloccataFilter, onChange: onBloccataChange } = bindSelect('bloccata')

// Le vesti che una persona di questo tab puo' avere: tutte tranne quella
// operatore (la sua categoria e' l'altro tab) e quella di una macchina.
const vesteOptions = buildOptionsConTutti(t,
  [RUOLO_APPLICATIVO.CLIENTE_PORTALE, RUOLO_APPLICATIVO.FORNITORE_PORTALE, RUOLO_APPLICATIVO.SHOP_CUSTOMER]
    .map(r => ({ value: r, label: etichettaRuoloApplicativo(t, te, r) })),
)
// Gli stati del riassunto: il vocabolario intero (NESSUNO compreso), non le
// chiavi della mappa dei colori.
const statoOptions = buildOptionsConTutti(t,
  Object.values(STATO_VESTE)
    .map(s => ({ value: s, label: t(`auth.stato_veste.${s}`) })),
)
const fattoreOptions = buildOptionsConTutti(t,
  Object.values(STATO_SECONDO_FATTORE)
    .map(s => ({ value: s, label: t(`amministrazione.secondo_fattore.stato.${s}`) })),
)
const boolOptions = buildBoolOptions(t)

onMounted(() => {
  store.fetchList()
})

// Il drawer legge la RIGA (la vista porta gia' tutto): `editRow` la consegna
// intera in `itemData`.
function onRowClick(data) {
  drawer.editRow(data, 'auth_user_id')
}

// Scopo: il kebab della riga: si va alla scheda del soggetto della veste, una
//        voce per veste che ne ha una (le vesti si governano li', A-4), e
//        «Elimina accesso», spento col motivo quando la check lo rifiuta.
function buildRowActions(data) {
  const schede = (data.vesti || [])
    .filter(v => destinazioneVeste(v))
    .map(v => ({
      key: `scheda-${v.identita_id}`,
      label: t('amministrazione.accessi.apri_scheda_di', {
        veste: etichettaRuoloApplicativo(t, te, v.ruolo_applicativo),
        soggetto: v.soggetto,
      }),
      icon: MANAGE_ICONS.VAI_A,
      command: () => apriSchedaVeste(v),
    }))
  return [
    ...schede,
    {
      key: 'elimina',
      label: t('amministrazione.accessi.elimina'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: eliminaSpenta(data),
      tooltip: motivoEliminaSpenta(data),
      command: () => chiediElimina(data, { onEliminata: () => store.fetchList() }),
    },
  ]
}

function onDrawerChanged() {
  store.fetchList()
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
            :placeholder="t('amministrazione.accessi.search_altri')"
          />
        </template>
        <Select
          v-model="vesteFilter" class="app-filter-w-md"
          :options="vesteOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_vesti')"
          @change="onVesteChange"
        />
        <Select
          v-model="statoFilter" class="app-filter-w-sm"
          :options="statoOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.filter_stato')"
          @change="onStatoChange"
        />
        <Select
          v-model="nessunoFilter" class="app-filter-w-sm"
          :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_nessun_accesso')"
          @change="onNessunoChange"
        />
        <Select
          v-model="fattoreFilter" class="app-filter-w-sm"
          :options="fattoreOptions" option-label="label" option-value="value"
          :placeholder="t('amministrazione.accessi.col_secondo_fattore')"
          @change="onFattoreChange"
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
      codice="anagrafiche.accessi_altri"
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
      <!-- La colonna «Accessi» filtra e cerca su `vesti_elenco`; a video le
           vesti sono badge, una per veste, col colore del suo stato. -->
      <template #cell-vesti="{ data }">
        <div class="app-accessi-badges">
          <Tag
            v-for="v in data.vesti" :key="v.identita_id"
            :value="etichettaRuoloApplicativo(t, te, v.ruolo_applicativo)"
            :severity="statoVesteSeverity(v.stato)"
            v-tooltip.top="t(`auth.stato_veste.${v.stato}`)"
          />
          <Tag v-if="data.nessun_accesso" :value="t('amministrazione.accessi.col_nessun_accesso')" severity="warn" />
        </div>
      </template>
      <template #cell-stato_accesso="{ data }">
        <Tag :value="t(`auth.stato_veste.${data.stato_accesso}`)" :severity="statoVesteSeverity(data.stato_accesso)" />
      </template>
      <template #cell-secondo_fattore_stato="{ data }">
        {{ t(`amministrazione.secondo_fattore.stato.${data.secondo_fattore_stato}`) }}
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

    <AccessoAltroDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :riga="drawer.state.itemData"
      @changed="onDrawerChanged"
    />
  </div>
</template>

<style scoped>
.app-accessi-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
</style>
