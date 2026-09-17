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
// ⚠️ Serve al TEMPLATE (la spia degli errori gravi). Fino al 2026-09-17 mancava:
//    in `<script setup>` un nome non importato nel template compila a
//    `_ctx.MANAGE_ICONS` = undefined, e `undefined.ERRORE` sollevava nel render
//    della PRIMA riga con `ha_errori_gravi` — lista bianca, senza un errore a
//    video, e solo nelle schede che avevano un lotto in ERRORE (i «Recuperi»).
import { MANAGE_ICONS } from '../../core/constants'
import { statoLottoSeverity } from '../../core/utils/severity'

// Scopo: il rapporto `completati/presi` degli ESITI di un lotto, o `null`
//        quando non c'e' niente da segnalare: lotto congelato (annullato,
//        definitivo — nessun giro da raccontare), nessun preso in carico (giri
//        precedenti al 2026-09-07), oppure tutti andati a buon fine.
// ⚠️ `=== false` e non `!`: `stato_congela_fiscale` a `null` e' «non lo so»,
//    e su un «non lo so» non si segnala niente (fail-closed).
function rapportoEsiti(row) {
  if (row?.stato_congela_fiscale !== false) return null
  const presi = row.n_presi_in_carico ?? 0
  const completati = row.n_esiti_completati ?? 0
  if (presi === 0 || completati === presi) return null
  return `${completati}/${presi}`
}

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
  // Predicato «questo lotto è dentro un giro di numerazione ancora vivo»:
  // alimenta la rotellina accanto al codice. Il chiamante lo governa (è la sua
  // macchina `useRigheInGiro`); qui si rende soltanto.
  // ⚠️ Default che risponde SEMPRE false, non `null`: così il template non
  //    ramifica e una scheda che non passa il predicato si comporta come prima.
  inGiro: { type: Function, default: () => false },
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

    <!-- ⭐ Rotellina sul lotto dentro un giro di numerazione vivo. Sta accanto
         al CODICE, dove l'occhio è già posato — stessa scelta della lista
         gruppi del cruscotto competenza, che ha lo stesso gesto.
         ⚠️ Dice «su questa riga si sta lavorando», non «non toccare»: i due
         verbi sono già spenti per conto loro mentre un giro è vivo. -->
    <template #cell-codice="{ data }">
      <span class="app-cella-con-spinner">
        <strong>{{ data.codice }}</strong>
        <i
          v-if="inGiro(data.id)"
          class="pi pi-spin pi-spinner app-spinner-in-corso"
          v-tooltip.right="t('vendite.lotti.lotto_in_giro_tooltip')"
          :aria-label="t('vendite.lotti.lotto_in_giro_tooltip')"
        />
      </span>
    </template>
    <template #cell-tipo_lotto="{ data }">
      <Tag :value="data.tipo_lotto" severity="secondary" />
    </template>
    <!-- ⭐ QUANTI DEI PRESI IN CARICO SONO ANDATI A BUON FINE (richiesta di
         Tid, 2026-09-12). Fino a quel giorno i presi in carico si vedevano
         SOLO nel drawer: un lotto in ERRORE con zero fatture non diceva
         «zero su due». Il rapporto e' `completati/presi` sugli ESITI — non
         `fatture/presi`: le fatture spariscono con l'annullo e possono essere
         meno dei presi anche a giro riuscito (fusioni) — e compare SOLO quando
         i due differiscono: e' un segnale di anomalia, non una colonna.
         ⛔ Niente su un lotto CONGELATO (annullato, definitivo): non ha piu' un
         giro da raccontare (decisione di Tid). Fail-closed come nel drawer:
         un dettaglio non ancora arrivato non e' «rimediabile».
         ⚠️ Rosso solo a giro fermo: mentre il lotto e' IN_ESECUZIONE i presi
         non ancora completati sono lavoro in corso, non un'anomalia.
         📌 Sulla cella di `n_fatture` e non in una colonna nuova, per la
         stessa ragione della spia degli errori: la lista e' a catalogo e una
         colonna in piu' e' una casella in piu' per ogni utente. -->
    <template #cell-n_fatture="{ data }">
      <!-- ⚠️ O il numero O il rapporto, mai tutti e due: «0 0/2» ripeteva lo
           zero e si leggeva come tre numeri (rilievo di Tid). Le fatture
           generate restano nel tooltip del badge, dove c'e' spazio per dirle
           per esteso. -->
      <Tag
        v-if="rapportoEsiti(data)"
        :value="rapportoEsiti(data)"
        :severity="data.stato_lotto === 'IN_ESECUZIONE' ? 'secondary' : 'danger'"
        v-tooltip.top="t('vendite.lotti.esiti_rapporto_tooltip', { n: data.n_esiti_completati, m: data.n_presi_in_carico, f: data.n_fatture })"
      />
      <span v-else>{{ data.n_fatture }}</span>
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
          :class="[MANAGE_ICONS.ERRORE, 'app-lotto-spia-errore']"
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

