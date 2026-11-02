<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script>
// Le colonne di `vendite.contratti` che hanno una cella propria: il caller le
// cabla con `<template v-for="c in CELLE_CONTRATTO" #[`cell-${c}`]>`.
// ⚠️ Una colonna nuova con una cella sua si aggiunge QUI e nel ramo sotto:
//    l'elenco e il disegno stanno nello stesso file apposta.
export const CELLE_CONTRATTO = ['stato', 'pratica', 'fase', 'transito']
</script>

<script setup>
// Scopo: la cella di una riga contratto per le colonne che non sono un valore
//        semplice (stato, lineage). Estratta il 2026-09-26 (regola del 2, ok
//        Tid): la lista `vendite.contratti` la montano la schermata Contratti
//        (`ContrattiSearchTable`) e i contratti del cliente
//        (`ContrattiBillingAccountDrawer`), e due copie dei quattro slot
//        avrebbero divergito alla prima colonna nuova.
import Tag from 'primevue/tag'
import { statoContrattoSeverity } from '../../core/utils/severity'
import LineagePraticaCell from '../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../_shared/lineage/LineageFaseTag.vue'
import LineageFrontieraChip from '../_shared/lineage/LineageFrontieraChip.vue'

defineProps({
  colonna: { type: String, required: true },
  data: { type: Object, required: true },
})
</script>

<template>
  <Tag v-if="colonna === 'stato'" :value="data.stato_descrizione" :severity="statoContrattoSeverity(data.stato_codice_interno)" />
  <LineagePraticaCell v-else-if="colonna === 'pratica'" :pratica-id="data.pratica_id" :pratica-numero="data.pratica_numero" :n-pratiche="data.n_pratiche" />
  <LineageFaseTag v-else-if="colonna === 'fase'" :fase="data.fase" />
  <LineageFrontieraChip v-else-if="colonna === 'transito'" :is-transitato="data.is_transitato" :tipo-codice="data.frontiera_tipo_codice_interno"
    :natura-codice="data.frontiera_natura_doc_codice_interno"
    :codice="data.frontiera_codice" :stato="data.frontiera_stato_codice_interno"
    :fase="data.frontiera_fase" :n-attivi="data.n_discendenti_attivi" />
</template>
