<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA TABELLA della «selezione righe con quantità» (estratta 2026-10-31,
//        regola del 2 alla 3ª copia, decisione Tid B6 del brief-db-liste-
//        datatable-grezze-secondo-giro). `useRigheSelezioneQta` ne possiede la
//        macchina; questo componente ne possiede l'impalcatura, che i tre
//        dialog d'azione (evasione ordine, riconsegna reso, reso da DDT)
//        ricopiavano identica: checkbox custom con «seleziona tutte», colonna
//        articolo, cella quantità editabile sul residuo, stato vuoto.
//
// ⭐ Le colonne di DOMINIO restano del chiamante, perché divergono davvero
//    (ordinata/evasa/residua, resa/riconsegnata/rinunciata, consegnata/gia'
//    resa più tipo e motivo): slot `colonne` fra l'articolo e la quantità,
//    slot `colonne-dopo` in fondo (il kebab della riapertura, tipo e motivo).
//
// ⛔ La macchina si passa INTERA (`:macchina`), non a pezzi: chiave di riga e
//    residuo li legge da lì (`rowKey`, `residuoDi`), cosi' la tabella non puo'
//    dire una cosa diversa dalla selezione che disegna.
//
// Checkbox custom e non `selectionMode`: PrimeVue 4 renderebbe spuntabili anche
// le righe esaurite (`useSelezioneToggle`). La colonna si nasconde quando non
// resta nulla da selezionare: la tabella e' allora un consuntivo.
//
// Uso:
//   const sel = useRigheSelezioneQta({ fetchRighe, residuoDi, ... })
//   <TabellaSelezioneRighe :macchina="sel"
//     :etichetta-qta="t('…col_qta')" :testo-vuoto="t('…nessuna_riga')">
//     <template #colonne> <Column …/> </template>
//   </TabellaSelezioneRighe>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
// DataTable grezza: e' la tabella di SELEZIONE dei tre dialog d'azione sulle
// righe di un documento (evasione, riconsegna, reso da DDT) — dettaglio del
// master, intera e non paginata perché si sceglie guardando tutto.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import { formatNumber } from '../../../core/utils/format'

const { t } = useI18n()

const props = defineProps({
  // Il ritorno di `useRigheSelezioneQta` (oggetto di ref: si legge con .value).
  // ⚠️ Niente prop `readonly`: la sola lettura e' quella della macchina.
  macchina: { type: Object, required: true },
  etichettaQta: { type: String, required: true },
  larghezzaQta: { type: String, default: '160px' },
  testoVuoto: { type: String, required: true },
})

const m = props.macchina
const righe = computed(() => m.righe.value)
const isReadonly = computed(() => m.readonly())
const conSelezione = computed(() => !isReadonly.value && m.righeSelezionabili.value.length > 0)
const chiave = (riga) => riga[m.rowKey]
const editabile = (riga) => !isReadonly.value && m.residuoDi(riga) > 0
</script>

<template>
  <DataTable v-if="righe.length" :value="righe"
    :data-key="m.rowKey" striped-rows size="small" class="app-datatable"
    :loading="m.loadingRighe.value" scrollable scroll-height="360px">
    <Column v-if="conSelezione" header-style="width: 3rem">
      <template #header>
        <Checkbox :model-value="m.allSelected.value" binary
          :indeterminate="m.anySelected.value" @update:model-value="m.toggleAll" />
      </template>
      <template #body="{ data }">
        <Checkbox :model-value="m.isSelected(data)" binary
          :disabled="!m.isSelectable(data)" @update:model-value="m.toggleRow(data)" />
      </template>
    </Column>
    <Column :header="t('vendite.righe_selezione.col_articolo')">
      <template #body="{ data }">
        {{ data.articolo_codice }} — {{ data.descrizione }}
      </template>
    </Column>
    <slot name="colonne" />
    <Column :header="etichettaQta" :style="{ width: larghezzaQta }">
      <template #body="{ data }">
        <InputNumber v-if="editabile(data)"
          v-model="m.qtaMap.value[chiave(data)]" :min="0" :max="m.residuoDi(data)"
          :min-fraction-digits="0" :max-fraction-digits="6"
          :input-style="{ width: '7rem' }" />
        <span v-else>{{ formatNumber(m.qtaMap.value[chiave(data)]) }}</span>
      </template>
    </Column>
    <slot name="colonne-dopo" />
  </DataTable>
  <div v-else-if="!m.loadingRighe.value" class="app-text-muted app-tabella-selezione-vuota">
    {{ testoVuoto }}
  </div>
</template>

<style scoped>
.app-tabella-selezione-vuota {
  font-style: italic;
}
</style>
