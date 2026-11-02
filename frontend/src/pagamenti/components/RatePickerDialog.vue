<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL PICKER DELLE RATE — «quale rata?» (D19-c, Tid 2026-09-15): la
//        lista `pagamenti.rate` (`GET /pagamenti/rate/`, vista
//        `vw_fatture_scadenze_lista` + saldi dalla base unica) montata in un
//        dialog, con un criterio OBBLIGATORIO — il cliente o il numero della
//        fattura — e la scelta che torna al form della riga.
//
// ⭐ E' UNA LISTA, quindi `<ListaConfigurabile>` (regola zero) attraverso lo
//    scheletro dei tab-lista di drawer (`useDrawerTabLista` + `<DrawerTabLista>`):
//    non e' un tab e non e' un drawer, ma e' la stessa forma — «lista di
//    sotto-entita' con un ciclo di apertura» — e il BB serve la forma, non il
//    posto in cui vive (cfr. `TitoliIvaSoggettoDrawer`). Il «padre» qui e'
//    l'apertura stessa: a dialog chiuso la lista si azzera, cosi' le rate del
//    giro precedente non lampeggiano sotto il prossimo.
//
// ⭐ IL CRITERIO OBBLIGATORIO e' il cancello empty-state dello store
//    (`startsEmpty` + `gateKeys`): senza cliente o numero la lista non chiede
//    niente e lo DICE — si sta registrando il pagamento di QUESTO cliente, non
//    guardando lo scadenzario.
// ⛔ Le rate ESAURITE si vedono e non si scelgono (spazio = 0, Q-B): nascondere
//    una rata saldata e' quello che un picker dei pagamenti NON deve fare — chi
//    guarda deve poter vedere che quel documento e' a posto.
// ⛔ I documenti NON NUMERATI invece non si vedono (Tid, rilievo in-app
//    2026-09-18): una bozza non e' ancora un documento fiscale, e la sua rata
//    non e' un credito su cui registrare un incasso. ⭐ E dal 2026-09-23 qui non
//    c'e' niente da scrivere DAVVERO: la regola e' un perimetro del BACKEND
//    (`list_rate`, `solo_numerate` default `True`), non un filtro che il picker
//    manda. Prima stava nei `filterDefaults` dello store, e da li' contava come
//    filtro attivo nel segno dell'imbuto — un «1» su un filtro che a video non
//    esiste. ⏳ La regola di Tid e' piu' stretta — «solo le definitive, inviate
//    a SDI» — e arrivera' come predicato di dominio, in una sede sola a DB
//    (piano D19 §8), non come un secondo booleano.
// ⭐ IL DIALOG E' ALTO DIECI RIGHE, DA SUBITO: la lista nasce a dieci righe
//    per pagina (`limit` dello store) e il blocco lista ha un'altezza DEFINITA
//    (`app-dialog-lista`, main.css) — cosi' la pagina vuota e la pagina piena
//    sono alte uguali, e il dialog non salta quando arrivano le righe.
// ⭐ La natura si SEGNALA (D19-e): sulla nota di credito — che dal 2026-09-17
//    ha la sua rata negativa — il residuo si dice «da rimborsare», e la rata
//    E' selezionabile (spazio ≠ 0, non > 0): il rimborso e' un incasso a segno
//    invertito, e il segno lo porta il numero.
//
// ⭐ DUE MODALITA' (prop `modalita`):
//    · SINGOLA (dal form della riga): click sulla riga → `scelta(rata)` e
//      chiusura. La riga porta TUTTE le colonne della lista: il form ne
//      ricava fattura e rata nella forma di `FatturaLookup`/`RataSelect`.
//    · MULTIPLA (dalla toolbar delle righe del drawer, D19-d): le rate si
//      SPUNTANO attraverso le pagine e si accumulano nell'AREA TEMPORANEA
//      sotto la lista, ciascuna col suo importo proposto dallo spazio; in
//      testa i fatti comuni; il Salva scrive N righe con `da-rate/`. E' D1
//      reso a video — *«un incasso che copre tre rate resta tre righe»*.
//      La macchina e' `useRigheDaRate` (telaio `useSelezioneLista` + valori
//      `useSelezioneConValore`): qui c'e' solo il markup.
//    🔴 L'esito e' PER RIGA: le riuscite escono dall'area (sono gia' righe
//      del foglio, e il drawer ricarica), le fallite restano con la FRASE del
//      database; quelle confermabili offrono «Forza» + motivo, e il Salva
//      successivo rimanda le sole rimaste. Il dialog si chiude da solo SOLO a
//      esito completo. Chiudere con rate in area chiede conferma: un'area
//      temporanea persa in silenzio e' lavoro perso.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import AppDialog from '../../core/components/AppDialog.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import ResiduoCella from './ResiduoCella.vue'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useNotify } from '../../core/composables/useNotify'
import { spazioSaldo } from '../composables/useSaldi'
import { DATE_FORMAT, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { formatCurrency } from '../../core/utils/format'
import { rataEsaurita, useRigheDaRate } from '../composables/useRigheDaRate'
import { useEtichettePagamenti } from '../etichette'
import { useRateStore } from '../stores/rate'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // `singola` (compila il form) · `multipla` (N rate → N righe).
  modalita: {
    type: String,
    default: 'singola',
    validator: (v) => ['singola', 'multipla'].includes(v),
  },
  // La distinta su cui scrivere: serve alla sola modalita' multipla.
  contabileId: { type: [Number, null], default: null },
  // ⚠️ Il readonly da PERMESSI, esplicito: il drawer che lo apre e' spesso
  //    «locked-by-stato», e il dialog d'azione non deve ereditare quel
  //    combinato o il footer nasconde il Salva (cfr. `AppDialog`).
  readonly: { type: Boolean, default: false },
  // Il cliente proposto all'apertura, quando il form ne ha gia' uno (la
  // fattura scelta dal lookup): si parte da li', e si puo' cambiare.
  billingAccountIniziale: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'scelta', 'righe-create'])

const { t } = useI18n()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const store = useRateStore()
const { rata: etichettaRata } = useEtichettePagamenti()
const multipla = computed(() => props.modalita === 'multipla')

// ⭐ Il «padre» e' l'apertura: `true` a dialog aperto, `null` a dialog chiuso.
//    Il BB azzera pagina e ricerca all'apertura e resetta lo store alla
//    chiusura — le rate del giro precedente non restano sotto il prossimo.
const { onPage, onSort, applyFilters, reloadAll, paginatorProps, tablePage,
        listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato } =
  useDrawerTabLista(store, {
    parentId: () => (props.visible ? true : null),
  })

// ── la macchina della modalita' multipla ───────────────────────────
const macchina = useRigheDaRate({
  contabileId: () => props.contabileId,
  righeVisibili: computed(() => store.items),
  abilitata: computed(() => props.visible && multipla.value),
})

// ── i criteri ──────────────────────────────────────────────────────
// ⛔ I TRE CRITERI LEGGONO LO STORE, non lo copiano in tre `ref`, ed e' la
//    correzione del 2026-09-23. Questa lista parte VUOTA e non chiede niente al
//    backend finche' non c'e' un criterio (`startsEmpty` + `gateKeys`): con tre
//    `ref` che spingevano e basta, il «Pulisci filtri» del drawer compatto
//    svuotava lo store — e quindi l'elenco — mentre il lookup continuava a
//    mostrare il cliente scelto. Un dialog che dice «nessuna rata» mentre il
//    cliente non e' piu' fra i criteri, e nessun errore da nessuna parte.
// ⭐ Il cliente passa da `bindLookup`, che sa gia' le due cose che servono qui:
//    il verso store → widget e la memoria dell'OGGETTO scelto
//    (`<chiave>_obj`), cioe' cio' che permette al lookup di rendersi quando il
//    dialog si riapre.
const { bindLookup } = useStoreFilterBindings(store, applyFilters)
const { value: cliente, onChange: onClienteChange } = bindLookup('billing_account_id')

const numeroFattura = computed({
  get: () => store.filters.fattura_numero,
  set: (v) => { store.filters.fattura_numero = v ?? null },
})
// ⚠️ La stringa vuota diventa `null`: il core manda ogni filtro `!= null`, e
//    una serie vuota sul filo sarebbe un parametro che non filtra niente.
const serie = computed({
  get: () => store.filters.serie ?? '',
  set: (v) => { store.filters.serie = v?.trim() || null },
})

// Scopo: rilancia dalla pagina 1 dopo un cambio di criterio.
// ⚠️ `applyFilters` azzera l'offset: la pagina 3 del cliente precedente non
//    esiste per il prossimo.
// ⚠️ Nel template `v-model` PRECEDE il listener: quando questa parte, lo store
//    e' gia' stato scritto dal setter del `computed`.
function applicaCriteri() {
  applyFilters()
}

watch(
  () => props.visible,
  (aperto) => {
    if (!aperto) return
    macchina.azzera()
    // I criteri si azzerano nella SEDE UNICA (lo store): le caselle sono
    // `computed`/binder e ci si riallineano da se'.
    numeroFattura.value = null
    serie.value = ''
    cliente.value = props.billingAccountIniziale ?? null
    // ⚠️ `onClienteChange` scrive l'id E l'oggetto ricordato, poi rilancia;
    //    senza cliente non si rilancia affatto, perche' la lista parte vuota.
    if (cliente.value?.id != null) onClienteChange()
    else store.filters.billing_account_id = null
  },
)

// Il criterio c'e'? Decide quale frase mostrare a lista vuota.
const haCriterio = computed(
  () => store.filters.billing_account_id != null || store.filters.fattura_numero != null,
)

// ── la riga ────────────────────────────────────────────────────────
// «Esaurita» e' il predicato di dominio della macchina (`rataEsaurita`, una
// sede): qui si legge, non si riscrive.
function onRowClick(riga) {
  if (!riga) return
  if (rataEsaurita(riga)) {
    notify.info(t('pagamenti.rate.esaurita'))
    return
  }
  if (multipla.value) {
    macchina.perLista.value?.toggle(riga)
    return
  }
  emit('scelta', riga)
  emit('update:visible', false)
}

// ── la modalita' multipla: area, Salva, chiusura ───────────────────
const nScelte = computed(() => macchina.selezione.value.length)

// Scopo: l'importo di una rata nell'area — `null` = casella svuotata.
function onImporto(riga, valore) {
  macchina.impostaImporto(riga.scadenza_id, valore)
}

// Il secondo tempo per riga: conferma e motivo vivono nella macchina, il
// template li legge e li scrive — nessuno stato parallelo qui.
function onForza(riga, acceso) {
  if (acceso) macchina.forza(riga.scadenza_id)
  else macchina.annullaForzatura(riga.scadenza_id)
}

async function onSalva() {
  const esito = await macchina.salva()
  if (esito === null) return
  if (esito.esito === 'COMPLETATO') {
    // Le riuscite sono gia' righe del foglio: il drawer ricarica.
    emit('righe-create')
    macchina.azzera()
    emit('update:visible', false)
    return
  }
  // ⚠️ PARZIALE con qualcosa di scritto: il dialog resta aperto E la lista
  //    ricarica — le rate appena diventate righe hanno un altro spazio
  //    (sono «in lavorazione»), e una lista ferma le mostrerebbe ancora
  //    aperte, rispuntabili, con un rifiuto pronto al giro dopo. Il prune del
  //    telaio rilegge la pagina fresca; le fallite, che non hanno scritto
  //    niente, restano in area com'erano.
  if (esito.riuscite > 0) {
    emit('righe-create')
    reloadAll()
  }
}

// Scopo: la chiusura — con rate in area chiede conferma, perche' un'area
//        temporanea persa in silenzio e' lavoro perso. In modalita' singola
//        si sceglie una rata e basta: niente da perdere.
// ⭐ E' la `conferma-uscita` di AppDialog (D-14, 2026-10-03): ci passano X,
//    ESC, maschera e «Chiudi». Fino a quel giorno ci si arrivava di sponda,
//    intercettando `update:visible(false)` gia' emesso dal guscio.
// ⚠️ I filtri (cliente, numero, serie) non contano: cercare e' leggere.
function confermaUscita(procedi) {
  if (multipla.value && nScelte.value > 0) {
    confirmAction({
      header: t('pagamenti.rate.abbandona_titolo'),
      message: t('pagamenti.rate.abbandona_msg', { n: nScelte.value }),
      acceptLabel: t('common.close'),
      danger: true,
      onAccept: () => {
        macchina.azzera()
        procedi()
      },
    })
    return
  }
  procedi()
}

</script>

<template>
  <AppDialog
    :conferma-uscita="confermaUscita"
    :visible="visible"
    :header="t(multipla ? 'pagamenti.rate.titolo_righe_da_rate' : 'pagamenti.rate.titolo_picker')"
    width="xl"
    :close-only="!multipla"
    :readonly="readonly"
    :save-label="t('pagamenti.rate.crea_righe', nScelte)"
    :save-disabled="!macchina.canSave.value"
    :loading="macchina.loading.value"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSalva"
  >
    <!-- `app-dialog-lista`: l'altezza definita del blocco lista (dieci righe,
         main.css) — senza, la lista si rende all'altezza del contenuto e il
         dialog salta quando le righe arrivano. -->
    <DrawerTabLista
      ref="listaRef"
      class="app-dialog-lista"
      codice="pagamenti.rate"
      data-key="scadenza_id"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <!-- ⭐ I due criteri, e ne basta uno: il cliente (lookup ricco) o il
           numero ESATTO della fattura (con la serie per disambiguare). -->
      <!-- ⭐ IL CLIENTE STA IN `filtri-sempre` COME UNA RICERCA, e non e' una
           forzatura: qui il gesto principale e' lui — finche' non si sceglie un
           cliente (o si digita un numero) la lista NON chiede niente al backend
           (`startsEmpty` + `gateKeys`). In modalita' compatta, dentro il
           drawer, l'operatore vedrebbe un elenco vuoto e un'icona a imbuto,
           cioe' un dialog che non dice come si usa. -->
      <template #filtri-sempre>
        <BillingAccountLookup
          v-model="cliente"
          class="app-filter-w-lg"
          @update:model-value="onClienteChange"
        />
      </template>
      <template #filtri>
        <!-- ⚠️ La taglia sta sull'INVOLUCRO e l'<input> la segue per regola di
             foglio (`.p-inputnumber[class*="app-filter-w-"] > input`): la
             larghezza scritta sul wrapper `.p-inputnumber` non arriva
             all'<input>, che tiene la sua larghezza intrinseca e SBORDA — a
             video il bordo del numero finiva addosso al campo Serie e si
             vedevano due bordi (rilievo di Tid, 2026-09-18). -->
        <InputNumber
          v-model="numeroFattura"
          class="app-filter-w-sm"
          :placeholder="t('pagamenti.rate.filtro_numero')"
          :use-grouping="false"
          :min="1"
          @update:model-value="applicaCriteri"
        />
        <InputText
          v-model="serie"
          class="app-filter-w-sm"
          :placeholder="t('pagamenti.rate.filtro_serie')"
          @change="applicaCriteri"
        />
      </template>

      <!-- Le caselle della selezione (chrome della lista, slot `#selection` col
           gemello `#selection-header`): SOLO in multipla. Il seleziona-tutto
           e' di PAGINA, mai sostituisce cio' che e' spuntato altrove. -->
      <template v-if="macchina.perLista.value" #selection-header>
        <Checkbox
          :model-value="macchina.perLista.value.tuttiInPagina.value"
          :indeterminate="macchina.perLista.value.alcuniInPagina.value"
          binary
          :aria-label="t('pagamenti.rate.seleziona_pagina')"
          @update:model-value="macchina.perLista.value.toggleTuttiInPagina"
        />
      </template>
      <template v-if="macchina.perLista.value" #selection="{ data }">
        <Checkbox
          :model-value="macchina.perLista.value.isSelezionato(data)"
          :disabled="!macchina.perLista.value.isSelezionabile(data)"
          binary
          v-tooltip.right="macchina.perLista.value.motivoNonSelezionabile(data)"
          :aria-label="data.numero_documento || String(data.scadenza_id)"
          @update:model-value="() => macchina.perLista.value.toggle(data)"
        />
      </template>

      <!-- ⭐ La natura si SEGNALA e NON ha slot: il seed dichiara
           `formato = natura_doc` e `CellaConfigurabile` la rende con
           `NaturaDocTag sempre` (dal 18/09, come `yesno`) — e' la colonna che
           dice «questa e' una nota di credito» prima che la si scelga. -->

      <!-- ⛔ Il residuo NEGATIVO non si mostra come numero negativo: si dice
           cosa significa, PER NATURA — nel BB `ResiduoCella`, la stessa cella
           della lista fuori capienza. La rata ESAURITA lo dichiara (si vede, e
           non si sceglie): il predicato e la frase restano qui, del picker. -->
      <template #cell-residuo="{ data }">
        <ResiduoCella
          :residuo="data.residuo"
          :natura-codice="data.natura_doc_codice_interno"
          :nota="rataEsaurita(data) ? t('pagamenti.rate.esaurita') : null"
        />
      </template>

      <!-- ⭐ Tre frasi diverse per tre stati diversi: «indica un criterio»
           (niente e' stato chiesto), «nessuna rata» (chiesto, vuoto), «non
           lette» (chiesto, fallito). La seconda detta al posto della prima e'
           un'affermazione falsa. -->
      <template #empty>
        <div class="app-empty-state">
          <template v-if="store.erroreCaricamento">
            <i :class="STATUS_ICONS.ERRORE" />
            <p>{{ t('pagamenti.rate.non_lette') }}</p>
          </template>
          <template v-else-if="haCriterio && store.hasSearched">
            <i :class="STATUS_ICONS.VUOTO" />
            <p>{{ t('pagamenti.rate.nessuna_rata') }}</p>
          </template>
          <template v-else>
            <i :class="MANAGE_ICONS.RICERCA" />
            <p>{{ t('pagamenti.rate.criterio_obbligatorio') }}</p>
          </template>
        </div>
      </template>
    </DrawerTabLista>

    <!-- ══ L'AREA TEMPORANEA (multipla): le rate scelte, attraverso le pagine ══
         ⚠️ NON e' una `DataTable` — ne' grezza ne' configurabile: e' l'ANTEPRIMA
         di cio' che il Salva scrivera', con un campo per riga. Un elenco di
         righe a griglia (`app-righe-scelte`, main.css), come le card delle
         sotto-entita' nei drawer. -->
    <template v-if="multipla">
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.rate.area_titolo', nScelte) }}</h4>
      </div>

      <!-- I fatti COMUNI: valgono per tutte le righe del giro. -->
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('pagamenti.righe.col_data_pagamento') }}</label>
          <DatePicker v-model="macchina.fatti.value.data_pagamento" :date-format="DATE_FORMAT" show-icon />
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.righe.col_data_valuta') }}</label>
          <DatePicker
            v-model="macchina.fatti.value.data_valuta"
            :date-format="DATE_FORMAT"
            show-icon
            show-button-bar
          />
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.righe.col_riferimento_ente') }}</label>
          <InputText v-model="macchina.fatti.value.riferimento_ente" />
        </div>
      </div>

      <p v-if="nScelte === 0" class="app-text-muted">
        {{ t('pagamenti.rate.nessuna_scelta') }}
      </p>
      <div v-else class="app-righe-scelte">
        <div
          v-for="riga in macchina.selezione.value"
          :key="riga.scadenza_id"
          class="app-righe-scelte__riga"
          :class="{ 'app-righe-scelte__riga--fallita': macchina.errore(riga.scadenza_id) }"
        >
          <!-- Il documento e la rata, com'e' scritta: la stessa etichetta della
               tendina e del blocco «Destinazione». -->
          <div class="app-righe-scelte__doc">
            <span class="font-bold">{{ riga.numero_documento || t('fattura_lookup.senza_numero') }}</span>
            <NaturaDocTag
              :codice="riga.natura_doc_codice_interno"
              :descrizione="riga.natura_doc_descrizione"
            />
            <span class="app-text-muted">{{ riga.ragione_sociale_completa }}</span>
            <span>{{ etichettaRata(riga) }}</span>
            <span class="app-text-muted">
              {{ t('pagamenti.rate.spazio') }}: {{ formatCurrency(spazioSaldo(riga)) }}
            </span>
          </div>

          <!-- L'importo: proposto dallo spazio, modificabile. Vuoto = il Salva
               resta spento (non si salta una riga in silenzio). -->
          <div class="form-field app-righe-scelte__importo">
            <label>{{ t('pagamenti.righe.col_importo') }}</label>
            <InputNumber
              :model-value="macchina.importoDi(riga.scadenza_id)"
              mode="currency"
              currency="EUR"
              locale="it-IT"
              :invalid="macchina.importoDi(riga.scadenza_id) == null"
              @update:model-value="(v) => onImporto(riga, v)"
            />
          </div>

          <!-- 🔴 L'esito dell'ultimo giro, PER RIGA: la frase del database e,
               se confermabile, il secondo tempo — «Forza» + motivo. -->
          <div class="app-righe-scelte__esito">
            <template v-if="macchina.errore(riga.scadenza_id)">
              <Tag severity="warn" :value="macchina.errore(riga.scadenza_id).message" />
              <template v-if="macchina.confermabile(riga.scadenza_id)">
                <div class="app-form-inline-toggle">
                  <ToggleSwitch
                    :model-value="macchina.forzata(riga.scadenza_id)"
                    :input-id="`forza-${riga.scadenza_id}`"
                    @update:model-value="(v) => onForza(riga, v)"
                  />
                  <label :for="`forza-${riga.scadenza_id}`">{{ t('pagamenti.abbina.forza') }}</label>
                </div>
                <Textarea
                  v-if="macchina.forzata(riga.scadenza_id)"
                  :model-value="macchina.motivoDi(riga.scadenza_id)"
                  rows="2"
                  auto-resize
                  :placeholder="t('pagamenti.abbina.campo_motivo')"
                  @update:model-value="(v) => macchina.impostaMotivo(riga.scadenza_id, v)"
                />
              </template>
            </template>
          </div>

          <div class="app-righe-scelte__azioni">
            <Button
              v-tooltip.left="t('pagamenti.rate.rimuovi')"
              :icon="MANAGE_ICONS.DELETE"
              text
              rounded
              size="small"
              class="app-delete-btn"
              :aria-label="t('pagamenti.rate.rimuovi')"
              @click="macchina.rimuovi(riga)"
            />
          </div>
        </div>
      </div>
    </template>
  </AppDialog>
</template>
