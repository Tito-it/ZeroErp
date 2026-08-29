<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista di PRESIDIO dei titoli IVA il cui consumo ha superato il tetto
// (Q4 del piano brief-be-fe-titoli-iva-soggetto).
//
// ⭐ ESISTE PERCHE' IL DB HA DECISO DI NON BLOCCARE lo sfondamento sulle
//   forzature, ed e' l'altra meta' di quella decisione: «una forzatura esiste
//   per registrare fatturazioni fuori dal sistema, e impedire di scriverla
//   impedirebbe di ACCORGERSENE. Il presidio giusto per quel caso e' una lista
//   di titoli sfondati che qualcuno guarda». Senza questa schermata, quella
//   decisione resterebbe una meta' sola.
//
// ⚠️ Lista SEMPLICE e non `<ListaConfigurabile>`, ed e' una scelta: quella si
//   registra con righe di seed in `ui.lista_definizione`/`lista_colonna`, cioe'
//   una dipendenza dal team DB, per una lista che si guarda e basta — non si
//   esporta e non si personalizza. Il giorno che servisse, il seed e' una cella
//   di CSV e la query BE e' gia' scritta.
//
// ⚠️ Il perimetro emittente lo fa la RLS: un operatore vede solo i titoli degli
//   emittenti che ha in whitelist. Qui non si filtra niente a mano.
import { ref, computed, onMounted, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { listTitoliIvaSfondati } from '../api/anagrafiche'
import { READONLY_DOMAINS, MANAGE_ICONS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import TitoloIvaDrawer from '../components/TitoloIvaDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE)
const { execute, loading } = useApiHandler()

const righe = ref([])
const drawerVisible = ref(false)
const titoloSelezionato = ref({ soggettoId: null, titoloId: null })

async function load() {
  const res = await execute(() => listTitoliIvaSfondati())
  righe.value = res === null ? [] : (res.data.data?.results || [])
}

onMounted(load)
// ⚠️ `onActivated` e non solo `onMounted`: sotto KeepAlive il rientro nella tab
//    non rimonta il componente, e una lista di presidio che mostra dati vecchi
//    e' peggio di una vuota (`feedback_keepalive_onactivated`).
onActivated(load)

function apri(riga) {
  titoloSelezionato.value = { soggettoId: riga.soggetto_id, titoloId: riga.id }
  drawerVisible.value = true
}

// ⚠️ `computed` e non un array costante: le label si risolvono al setup e non
//    seguirebbero il cambio lingua. E' la forma usata dalle altre toolbar.
const pageActions = computed(() => [{
  key: 'reload', kind: 'utility', label: t('common.reload_list'),
  icon: MANAGE_ICONS.RELOAD, command: load,
}])

// Di quanto si e' sfondato: il numero che interessa e' l'ECCEDENZA, non il
// residuo negativo — si legge senza dover fare il segno a mente.
function eccedenza(r) {
  return Number(r.imponibile_utilizzato) - Number(r.plafond)
}
</script>

<template>
  <div class="app-page">
    <PageActionsBar :actions="pageActions" />

    <Message severity="info" :closable="false" class="mb-2">
      {{ t('anagrafiche.titoli_iva.sfondati_hint') }}
    </Message>

    <DataTable :value="righe" :loading="loading" class="app-datatable"
      data-key="id" size="small" @row-click="apri($event.data)">
      <Column field="soggetto_ragione_sociale"
        :header="t('anagrafiche.titoli_iva.col_soggetto')" />
      <Column field="soggetto_id_fiscale"
        :header="t('anagrafiche.titoli_iva.col_id_fiscale')" />
      <Column field="tipo_descrizione" :header="t('anagrafiche.titoli_iva.col_tipo')" />
      <Column field="emittente_ragione_sociale"
        :header="t('anagrafiche.titoli_iva.col_emittente')" />
      <Column :header="t('anagrafiche.titoli_iva.col_validita')">
        <template #body="{ data }">
          {{ displayDate(data.valido_dal) }} —
          {{ data.valido_al ? displayDate(data.valido_al)
                            : t('anagrafiche.titoli_iva.senza_scadenza') }}
        </template>
      </Column>
      <Column :header="t('anagrafiche.titoli_iva.field_plafond')">
        <template #body="{ data }">{{ formatCurrency(data.plafond) }}</template>
      </Column>
      <Column :header="t('anagrafiche.titoli_iva.field_utilizzato')">
        <template #body="{ data }">{{ formatCurrency(data.imponibile_utilizzato) }}</template>
      </Column>
      <Column :header="t('anagrafiche.titoli_iva.col_eccedenza')">
        <template #body="{ data }">
          <Tag :value="formatCurrency(eccedenza(data))" severity="danger" />
        </template>
      </Column>
      <template #empty>{{ t('anagrafiche.titoli_iva.sfondati_vuoto') }}</template>
    </DataTable>

    <TitoloIvaDrawer
      v-model:visible="drawerVisible"
      :soggetto-id="titoloSelezionato.soggettoId"
      :titolo-id="titoloSelezionato.titoloId"
      @saved="load" />
  </div>
</template>
