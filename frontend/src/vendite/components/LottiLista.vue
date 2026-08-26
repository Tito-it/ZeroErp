<script setup>
// Scopo: LA LISTA DEI LOTTI DI FATTURAZIONE — colonne, celle decorate, spia
//        degli errori gravi e azioni di riga — resa una volta sola e montata da
//        DUE schede: «Lotti del mese» (i lotti della competenza filtrata) e
//        «Recuperi del mese» (i lotti di competenza PRECEDENTE che hanno emesso
//        documenti in quel mese).
//
// ⭐ ESTRATTO alla seconda occorrenza (regola del 2, ok Tid 2026-08-24). Le due
//    schede devono mostrare le STESSE informazioni e permettere le STESSE
//    azioni: due copie sarebbero identiche il primo giorno e divergenti al
//    primo ritocco.
//
// ⚠️ Prende PRIMITIVE ed emette eventi invece di ricevere un oggetto di stato,
//    perché le due sorgenti hanno forme diverse: la scheda principale viene da
//    `useListaConfigurabilePage` (store + `useSearchTable`), quella dei recuperi
//    da una lista paginata senza store. Un contratto a primitive le serve
//    entrambe senza sapere quale sta rendendo.
import Tag from 'primevue/tag'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { statoLottoSeverity } from '../../core/utils/severity'

defineProps({
  rows: { type: Array, required: true },
  total: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  paginatorOptions: { type: Object, required: true },
  page: { type: Number, default: 1 },
  sortField: { type: String, default: null },
  sortOrder: { type: Number, default: null },
  // Le azioni di riga le costruisce il chiamante: dipendono dallo stato della
  // riga e dai permessi, e sono le stesse per entrambe le schede.
  buildRowActions: { type: Function, required: true },
  azioniDisabled: { type: Boolean, default: false },
  emptyKey: { type: String, default: 'vendite.lotti.nessun_lotto' },
  emptyIcon: { type: String, default: 'pi pi-server' },
  // ⭐ SELEZIONE (numerazione su selezione). Il chiamante la governa: qui il
  //    componente rende solo le caselle, perché la selezione VIVE ATTRAVERSO LE
  //    DUE SCHEDE — un lotto di competenza precedente, spuntato nei «recuperi»,
  //    si numera insieme a quelli del mese. Tenerla dentro il wrapper
  //    significherebbe due selezioni separate che non si vedono fra loro.
  // ⚠️ `null` = nessuna selezione: la colonna non compare affatto. È il caso
  //    dell'operatore senza permesso di numerare, che non deve nemmeno vedere
  //    le caselle.
  selezione: { type: Object, default: null },
})

const emit = defineEmits(['page', 'sort', 'row-click', 'config-loaded', 'lista-pronta'])

const { t } = useI18n()

// ⚠️ `useListaAzioni` vuole l'istanza di `<ListaConfigurabile>`, non questo
// wrapper. 📌 `defineExpose` auto-unwrappa i ref: dal padre è `ref.value.lista`.
const listaRef = ref(null)
defineExpose({ lista: listaRef })

// ⚠️ ANNUNCIATA, non solo esposta. Chi ci monta sopra un `useListaAzioni` deve
// avere l'istanza di `<ListaConfigurabile>`, e leggerla da un `ref` sul wrapper
// significa leggerla UNA volta sperando che sia già popolata: se in
// quell'istante fosse `null`, resterebbe `null` per sempre e l'unico sintomo
// sarebbe un pulsante «Personalizza colonne» disabilitato, senza errori.
// ⭐ `onMounted` del wrapper scatta quando il figlio è certamente montato:
// niente ipotesi sull'ordine.
onMounted(() => emit('lista-pronta', listaRef.value))
</script>

<template>
  <ListaConfigurabile
    ref="listaRef"
    codice="vendite.lotti"
    :rows="rows"
    :total="total"
    :loading="loading"
    :paginator-options="paginatorOptions"
    :page="page"
    :sort-field="sortField"
    :sort-order="sortOrder"
    @page="$emit('page', $event)"
    @sort="$emit('sort', $event)"
    @row-click="$emit('row-click', $event)"
    @config-loaded="$emit('config-loaded', $event)"
  >
    <!-- Casella di selezione. ⚠️ Slot `#selection` (col gemello
         `#selection-header`), non una colonna di catalogo: la selezione non è
         un dato del lotto.
         ⛔ `disabled` sulle righe NON numerabili invece di nasconderle: la riga
         resta a video con la sua ragione, e l'operatore vede PERCHÉ non la può
         spuntare. Nasconderle darebbe una lista che cambia sotto gli occhi a
         seconda del verbo. -->
    <template v-if="selezione" #selection-header>
      <Checkbox
        :model-value="selezione.tuttiInPagina.value"
        :indeterminate="selezione.alcuniInPagina.value"
        binary
        :aria-label="t('vendite.lotti.seleziona_pagina')"
        @update:model-value="selezione.toggleTuttiInPagina"
      />
    </template>
    <template v-if="selezione" #selection="{ data }">
      <Checkbox
        :model-value="selezione.isSelezionato(data)"
        :disabled="!selezione.isSelezionabile(data)"
        binary
        v-tooltip.right="selezione.motivoNonSelezionabile(data)"
        :aria-label="data.codice"
        @update:model-value="() => selezione.toggle(data)"
      />
    </template>

    <template #cell-codice="{ data }">
      <strong>{{ data.codice }}</strong>
    </template>
    <template #cell-tipo_lotto="{ data }">
      <Tag :value="data.tipo_lotto" severity="secondary" />
    </template>
    <!-- ⭐ La spia degli errori gravi vive SULLO STATO (richiesta di Tid,
         2026-08-21): basta UN documento fallito nel dettaglio per accenderla.
         È la forma dei gestionali a lotti — la testata avvisa, il dettaglio
         spiega — e il dettaglio è a un click.
         📌 Sullo stato e non in una colonna nuova: la lista è a catalogo
         (`ui.lista_colonna`), quindi una colonna in più è un seed del team DB e
         una casella in più da spuntare per ogni utente. -->
    <template #cell-stato_lotto="{ data }">
      <span class="app-lotto-stato-cella">
        <Tag :value="data.stato_lotto" :severity="statoLottoSeverity(data.stato_lotto)" />
        <i
          v-if="data.ha_errori_gravi"
          class="pi pi-exclamation-triangle app-lotto-spia-errore"
          v-tooltip.top="t('vendite.lotti.spia_errori_gravi')"
        />
      </span>
    </template>
    <!-- Stato operativo: informazione interna della pipeline, resa come Tag
         neutro — non è uno stato di dominio come `stato_lotto` e non deve
         competere con lui a colpo d'occhio. -->
    <template #cell-stato_operativo="{ data }">
      <Tag v-if="data.stato_operativo" :value="data.stato_operativo" severity="secondary" />
      <span v-else>—</span>
    </template>
    <template #cell-stato_doc_fiscale="{ data }">
      <Tag
        v-if="data.stato_doc_fiscale_descrizione"
        :value="data.stato_doc_fiscale_descrizione"
        severity="info"
      />
      <span v-else>—</span>
    </template>

    <!-- Azioni di governo del lotto senza passare dal drawer: avanza /
         rilancia step, rendi definitive, ristampa, annulla, riporta in
         lavorazione. Le voci proposte dipendono dallo stato della riga; il
         verdetto vero (e il motivo di un rifiuto) arriva dal DB al click. -->
    <template #actions="{ data, compact }">
      <RowActionsMenu
        :row="data"
        :actions="buildRowActions(data)"
        :disabled="azioniDisabled"
        :force-compact="compact"
      />
    </template>

    <template #empty>
      <div class="app-empty-state">
        <i :class="emptyIcon" />
        <p>{{ t(emptyKey) }}</p>
      </div>
    </template>
  </ListaConfigurabile>
</template>
