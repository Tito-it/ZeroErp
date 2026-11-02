<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: CHE COSA SI FA DEL DENARO DI TROPPO — il drawer in cui una persona
//        decide di un'eccedenza, e da cui gli atti gia' decisi si confermano o
//        si scartano.
//
// ⭐ Tre destinazioni, e non sono tre modi di dire la stessa cosa: il RIPORTO
//    genera un fondo fattura, il RIMBORSO una distinta a importi negativi, la
//    COMPENSAZIONE una distinta sul centro dedicato. Nessuna macchina nuova
//    sotto — mancavano l'elenco e il registro.
//
// ⚠️ REGISTRARE NON E' ESEGUIRE: l'atto nasce in BOZZA e il denaro si muove
//    alla conferma. Sono due gesti perche' sono due momenti, e in mezzo puo'
//    arrivare un altro incasso.
//
// ⛔ Cliente ed emittente NON si dichiarano: li deriva il backend dalla fattura
//    di origine, e il payload li rifiuta apposta. «Non li sceglie una persona in
//    un modulo, li deriva chi costruisce l'atto».
//
// ⚠️ Gli atti in BOZZA non tolgono la riga dall'elenco delle eccedenze: finche'
//    nessuno conferma, l'eccedenza c'e' ancora. Il contatore dice «ci sta gia'
//    lavorando qualcuno», che e' un'altra cosa.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import MotivoDialog from '../../core/components/MotivoDialog.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FatturaLookup from '../../vendite/components/FatturaLookup.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { statoSistemazioneSeverity } from '../../core/utils/severity'
import {
  annullaSistemazione,
  creaSistemazione,
  exportSistemazioniFattura,
} from '../api/pagamenti'
import { useSistemazioniFatturaStore } from '../stores/sistemazioniFattura'
import { useEtichettePagamenti } from '../etichette'
import { formatCurrency } from '../../core/utils/format'
import {
  DESTINAZIONE_CON_FONDO,
  DESTINAZIONI_CON_DESTINATARIO,
  SEVERITY_CHI_E_IN_CREDITO,
  STATO_SISTEMAZIONE_BOZZA,
  STATO_SISTEMAZIONE_CONFERMATA,
} from '../vocabolari'
import ConfermaSistemazioneDialog from './ConfermaSistemazioneDialog.vue'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // La riga dell'elenco eccedenze (`vw_eccedenze_da_sistemare`).
  eccedenza: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'cambiata'])

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

// ⭐ La lista degli atti vive in uno STORE dal 2026-09-02 (decisione di Tid):
//    prima erano tre `ref` locali e una fetch senza parametri — niente pagine,
//    niente «Personalizza colonne», niente export. La ragione scritta era «gli
//    atti di UNA fattura sono pochi per modello», che e' una previsione sui
//    DATI: non decide la forma della lista.
// ⛔ Tre casi restano tre, non due: atti presenti · nessun atto · non letti.
//    L'ultimo NON si spaccia per il secondo — «su questo documento non ha
//    ancora deciso nessuno» e' un'affermazione su cui qualcuno prende una
//    decisione — ed e' per questo che lo store tiene `erroreCaricamento`.
const store = useSistemazioniFatturaStore()

const form = ref(defaultForm())
const fatturaDestinazione = ref(null)
const confermaVisible = ref(false)
const attoDaConfermare = ref(null)
const annullaVisible = ref(false)
const attoDaAnnullare = ref(null)

function defaultForm() {
  return { destinazione: null, importo: null, motivo: '' }
}

const fatturaId = computed(() => props.eccedenza?.fattura_id ?? null)
const serveDestinatario = computed(
  () => DESTINAZIONI_CON_DESTINATARIO.includes(form.value.destinazione),
)

const {
  destinazione: etichettaDestinazione,
  credito: etichettaCredito,
  statoSistemazione: etichettaStato,
  opzioniDestinazione: costruisciOpzioniDestinazione,
} = useEtichettePagamenti()
const opzioniDestinazione = costruisciOpzioniDestinazione()
const severityCredito = (c) => SEVERITY_CHI_E_IN_CREDITO[c] || 'secondary'

// ⚠️ `importo != null` e non un test di verita': lo zero e' rifiutato dal
//    database (`chk_sistemazioni_importo_non_zero`) con la sua frase — non si
//    nasconde spegnendo il pulsante senza dire perche'.
const canSave = computed(
  () =>
    !isReadonly.value &&
    form.value.destinazione != null &&
    form.value.importo != null &&
    (!serveDestinatario.value || fatturaDestinazione.value?.id != null),
)

// ⭐ La decisione in compilazione e' lavoro dell'operatore: uscire dal drawer
//    (X, ESC, clic fuori, Chiudi) con il form modificato chiede (2026-10-03).
//    Il documento di destinazione si fotografa per id: il lookup lo riemette
//    come oggetto nuovo. ⚠️ Dichiarata PRIMA dei watch `immediate` che la
//    fissano.
const decisione = computed(() => ({
  ...form.value,
  fattura_destinazione_id: fatturaDestinazione.value?.id ?? null,
}))
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(decisione, { visibile: () => props.visible })

// ⛔ Cambiando destinazione il documento di destinazione si azzera: su RIMBORSO
//    e' VIETATO (il denaro esce, non c'e' un secondo documento) e mandarlo
//    sarebbe un rifiuto su un campo che a video non si vede piu'.
watch(() => form.value.destinazione, () => {
  if (!serveDestinatario.value) fatturaDestinazione.value = null
})

// ⚠️ `parentId` porta l'id SOLO a drawer aperto, e il `null` non e' un
//    dettaglio: e' quello che dice allo scaffolding di chiamare `store.reset()`
//    alla chiusura. Senza, gli atti della fattura precedente resterebbero in
//    memoria e lampeggerebbero sotto la prossima che si apre — righe vere di un
//    documento sbagliato, che e' il difetto che non fallisce.
// ⛔ E la fetch NON si scrive piu' qui: il watch dello scaffolding e'
//    `immediate` e riscrive padre, offset e ricerca nell'ordine giusto. Un
//    secondo caricamento a mano sarebbe una seconda sede della stessa regola.
const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? fatturaId.value : null),
  parentField: 'fatturaId',
  exportFn: (params) => exportSistemazioniFattura(fatturaId.value, params),
  // L'export segue la lista a video — ordinamento compreso — dalla sede unica
  // dello store (`paramsFiltro`), non da un ripiego ricopiato qui.
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
})

// ⛔ NESSUN «Nuovo» nella barra, e non e' una dimenticanza: qui si registra un
//    atto dalla form che sta SOTTO la lista, dentro questo stesso drawer. Un
//    pulsante che aprisse un secondo posto per fare la stessa cosa sarebbe due
//    strade per un gesto solo.

watch(() => [props.visible, fatturaId.value], ([vis]) => {
  if (!vis) return
  form.value = defaultForm()
  // ⭐ L'importo nasce sull'INTERA eccedenza: e' il caso normale — si sistema
  //    tutto quello che e' di troppo — e resta modificabile, perche' si puo'
  //    rimborsare una parte e riportare il resto.
  form.value.importo = props.eccedenza?.eccedenza != null
    ? Number(props.eccedenza.eccedenza)
    : null
  fatturaDestinazione.value = null
  fissa()
}, { immediate: true })

async function onRegistra() {
  const payload = {
    fattura_origine_id: fatturaId.value,
    destinazione: form.value.destinazione,
    importo: form.value.importo,
  }
  if (serveDestinatario.value) {
    payload.fattura_destinazione_id = fatturaDestinazione.value.id
  }
  if (form.value.motivo?.trim()) payload.motivo = form.value.motivo.trim()

  const esito = await execute(() => creaSistemazione(payload), {
    successMessage: t('pagamenti.sistemazioni.registrata'),
  })
  if (esito === null) return
  form.value = defaultForm()
  fatturaDestinazione.value = null
  fissa()
  reloadAll()
  // ⚠️ Si avvisa la lista anche se la riga NON sparira': i contatori delle
  //    bozze cambiano, e un elenco fermo direbbe «nessuno ci sta lavorando».
  emit('cambiata')
}

function apriConferma(atto) {
  attoDaConfermare.value = atto
  confermaVisible.value = true
}

function apriAnnullo(atto) {
  attoDaAnnullare.value = atto
  annullaVisible.value = true
}

async function onAnnulla(motivo) {
  const payload = {}
  // ⚠️ Il motivo si manda solo se scritto: il database sa se l'atto ne aveva
  //    gia' uno, e in quel caso il vuoto lascia quello che c'era. Ripetere qui
  //    l'obbligo sarebbe una seconda sede di una regola che il guard tiene.
  if (motivo) payload.motivo = motivo
  const esito = await execute(
    () => annullaSistemazione(attoDaAnnullare.value.id, payload),
    { successMessage: t('pagamenti.sistemazioni.annullata') },
  )
  if (esito === null) return
  // ⭐ Se l'atto era CONFERMATO il denaro si e' MOSSO ALL'INDIETRO: il fondo e'
  //    stato cancellato e l'eccedenza e' tornata al suo posto, quindi il numero
  //    in testata — che arriva dalla riga di elenco caricata all'apertura — e'
  //    vecchio. Stessa scelta gia' fatta dopo la conferma: si chiude, e chi
  //    vuole sistemare il resto riapre dalla lista e vede il residuo vero.
  // ⚠️ Scartare una BOZZA invece NON chiude: li' il denaro non si era mosso.
  const eraConfermata =
    attoDaAnnullare.value?.stato === STATO_SISTEMAZIONE_CONFERMATA
  annullaVisible.value = false
  emit('cambiata')
  if (eraConfermata) {
    emit('update:visible', false)
    return
  }
  reloadAll()
}

// ⛔ Dopo una CONFERMA il drawer si chiude, e non e' pigrizia: il denaro si e'
//    mosso, quindi l'eccedenza in testata — che arriva dalla riga di elenco
//    caricata all'apertura — e' vecchia. Tenerla a video mostrerebbe un numero
//    falso proprio accanto ai pulsanti per decidere di nuovo. Chi vuole
//    sistemare anche il resto riapre dalla lista, che intanto si e' ricaricata,
//    e vede il residuo vero.
// ⚠️ Registrare e scartare NON chiudono: li' il denaro non si e' mosso, quindi
//    i numeri in testata sono ancora quelli.
async function dopoConferma() {
  emit('cambiata')
  emit('update:visible', false)
}

// ⚠️ CONFERMARE vale SOLO su un atto in BOZZA. ⭐ ANNULLARE no, e dal
//    2026-08-31 non piu': il varco `CONFERMATA -> ANNULLATA` e' aperto per il
//    solo `RIPORTO` (D-25), perche' e' l'unica destinazione che lascia dietro
//    un FONDO — e un fondo si disfa solo da qui. Rimborso e compensazione
//    lasciano una distinta, che si corregge con la correzione guidata.
// ⭐ Qui si DISABILITA col motivo, non si nasconde: e' la regola del progetto —
//    il permesso nasconde, lo STATO disabilita e spiega. Uno stato puo'
//    cambiare, e un'azione sparita non dice a nessuno perche' non c'e'.
//    ⛔ In sola lettura invece si nasconde: li' non e' lo stato, e' il permesso.
function buildRowActions(atto) {
  if (isReadonly.value) return []
  const bozza = atto.stato === STATO_SISTEMAZIONE_BOZZA
  const motivoTerminale = t('pagamenti.sistemazioni.gia_terminale', {
    stato: atto.stato,
  })
  // ⛔ IL FRONTEND NON RICALCOLA LA REGOLA, e qui e' la scelta che conta.
  //    Questa condizione apre il gesto sui casi in cui ha SENSO — un riporto
  //    confermato — e si ferma li'. Se poi quel fondo sia gia' finito su una
  //    fattura emessa, o lo trattenga qualcos'altro, lo sa solo il database:
  //    il predicato `fn_check_fondo_cancellabile` ha SEI motivi, e riscriverne
  //    anche uno solo qui sarebbe una seconda copia che diverge al primo
  //    cambio. Si prova, e si LEGGE IL RIFIUTO — che arriva col suo messaggio
  //    e la sua soluzione.
  const confermata = atto.stato === STATO_SISTEMAZIONE_CONFERMATA
  const annullabile =
    bozza || (confermata && atto.destinazione === DESTINAZIONE_CON_FONDO)
  // ⭐ Due ragioni diverse, due frasi diverse. Su rimborso e compensazione il
  //    rifiuto NOMINA L'ALTERNATIVA — e' la stessa scelta fatta a database su
  //    `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO`: «questo atto e' immutabile» e'
  //    vero e non aiuta chi sta provando a correggere un importo.
  const spiegazioneAnnullo = confermata
    ? t('pagamenti.sistemazioni.annullo_solo_riporto')
    : t('pagamenti.sistemazioni.annullo_gia_annullata')
  return [
    {
      key: 'conferma',
      label: t('pagamenti.sistemazioni.conferma_azione'),
      icon: MANAGE_ICONS.CONFIRM,
      disabled: !bozza,
      tooltip: bozza ? undefined : motivoTerminale,
      command: () => apriConferma(atto),
    },
    {
      key: 'annulla',
      label: t('pagamenti.sistemazioni.annulla_azione'),
      icon: MANAGE_ICONS.CANCEL,
      severity: 'danger',
      disabled: !annullabile,
      tooltip: annullabile ? undefined : spiegazioneAnnullo,
      command: () => apriAnnullo(atto),
    },
  ]
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <!-- Footer «Chiudi» dal 2026-10-03 (AppDrawer): prima si usciva solo dalla
       X. La sola lettura nasconde le azioni: il corpo resta cliccabile. -->
  <AppDrawer
    :visible="visible"
    :title="t('pagamenti.sistemazioni.titolo')"
    :icon="NAV_ICONS.ECCEDENZE"
    :width="DRAWER_WIDTH.WIDE"
    :proteggi-corpo="false"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <template v-if="eccedenza">
      <DrawerEntityHeader>
        <Tag :value="eccedenza.fattura_numero || t('fattura_lookup.senza_numero')"
          severity="secondary" />
        <span class="app-drawer-header-muted">
          {{ displayDate(eccedenza.fattura_data) }}
        </span>
        <span>{{ eccedenza.cliente_ragione_sociale || '—' }}</span>

        <template #status>
          <!-- ⛔ IL VERSO PRIMA DI TUTTO: sbagliarlo significa rimborsare cio'
               che si deve incassare. -->
          <Tag
            v-if="eccedenza.chi_e_in_credito"
            :value="etichettaCredito(eccedenza.chi_e_in_credito)"
            :severity="severityCredito(eccedenza.chi_e_in_credito)"
          />
        </template>
      </DrawerEntityHeader>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.eccedenze.col_eccedenza') }}</label>
          <span>{{ formatCurrency(eccedenza.eccedenza) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.eccedenze.col_totale_a_pagare') }}</label>
          <span>{{ formatCurrency(eccedenza.totale_a_pagare) }}</span>
        </div>
        <!-- ⭐ Il totale del CLIENTE accanto a quello del documento: e' il
             numero su cui la compensazione ha senso, e senza non si vede che
             lo stesso cliente ha altri documenti scoperti. -->
        <div class="form-field">
          <label>{{ t('pagamenti.eccedenze.col_eccedenza_cliente') }}</label>
          <span>{{ formatCurrency(eccedenza.eccedenza_cliente) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.eccedenze.col_documenti_cliente') }}</label>
          <span>{{ eccedenza.documenti_cliente ?? 0 }}</span>
        </div>
      </div>

      <!-- ══ Che cosa e' stato deciso finora ══ -->
      <div class="app-drawer-section">
        <h4>{{ t('pagamenti.sistemazioni.sezione_atti') }}</h4>
      </div>

      <!-- ⛔ IL TERZO CASO HA LA SUA FRASE. «Non sono riuscito a leggerli»
           non e' «non ce ne sono»: il secondo e' un'affermazione su cui
           qualcuno decide di registrarne uno, il primo dice solo che non si
           sa. Il BB della lista non puo' distinguerli — a lista vuota
           mostrerebbe lo stesso empty-state — quindi la distinzione vive qui,
           sopra la lista, e lo stato lo tiene lo store. -->
      <Message
        v-if="store.erroreCaricamento"
        severity="warn"
        :closable="false"
        size="small"
      >
        {{ t('pagamenti.sistemazioni.atti_non_letti') }}
      </Message>

      <!-- ⭐ PAGINATA dal 2026-09-02 (decisione di Tid), e col pacchetto
           standard: pagine, «Personalizza colonne», export. La ragione per
           cui non lo era — «gli atti di UNA fattura sono pochi» — era una
           previsione sui dati, e le previsioni sui dati non decidono la forma
           di una lista.
           ⚠️ `@row-click` non e' agganciato: la riga non apre niente, le
           azioni stanno nel kebab. -->
      <DrawerTabLista
        ref="listaRef"
        codice="pagamenti.sistemazioni_fattura"
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
        @config-loaded="onConfigLoaded"
      >
        <!-- La frase del dominio al posto dell'empty-state generico: «su
             questo documento non ha ancora deciso nessuno» e' cio' che
             l'operatore deve sapere per decidere lui.
             ⛔ MA SOLO SE LA LETTURA E' RIUSCITA. Con `erroreCaricamento` la
             tabella e' vuota per un'altra ragione, e affermare «non ce ne
             sono» sotto un avviso che dice «non sono riuscito a leggerli»
             sarebbe la contraddizione che quell'avviso esiste per evitare:
             due frasi, una sola vera, e nessuna indicazione su quale. -->
        <template #empty>
          <span v-if="!store.erroreCaricamento">
            {{ t('pagamenti.sistemazioni.nessun_atto') }}
          </span>
        </template>
        <!-- FE-1: `destinazione` e `stato` sono codici grezzi
             (`RIPORTO`/`BOZZA`…), non hanno un display field in JOIN: il
             vocabolario vive in `pagamenti/vocabolari.js`. Senza questi due
             slot la cella mostrerebbe il codice. -->
        <template #cell-destinazione="{ data }">
          {{ etichettaDestinazione(data.destinazione) }}
        </template>
        <template #cell-stato="{ data }">
          <!-- ⚠️ Tradotto e fail-visible: uno stato nuovo si legge come
               CODICE, non come una parola inglese lasciata a video. -->
          <Tag
            :value="etichettaStato(data.stato)"
            :severity="statoSistemazioneSeverity(data.stato)"
          />
        </template>
        <template #cell-motivo="{ data }">{{ data.motivo || '—' }}</template>
        <template #cell-data_esecuzione="{ data }">
          <span v-if="data.data_esecuzione">
            {{ displayTimestamp(data.data_esecuzione) }}
          </span>
          <span v-else class="app-text-muted">—</span>
        </template>
        <!-- ⚠️ Niente componente quando non c'e' nessuna azione: in variante
             compatta il kebab si disegna comunque, e aprirebbe un menu vuoto
             su un atto terminale. -->
        <template #actions="{ data }">
          <RowActionsMenu
            v-if="buildRowActions(data).length"
            :row="data"
            :actions="buildRowActions(data)"
          />
          <span v-else class="app-text-muted">—</span>
        </template>
      </DrawerTabLista>

      <!-- ══ La decisione ══ -->
      <template v-if="!isReadonly">
        <div class="app-drawer-section">
          <h4>{{ t('pagamenti.sistemazioni.sezione_decisione') }}</h4>
        </div>

        <div class="form-grid">
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('pagamenti.sistemazioni.col_destinazione') }}</label>
              <Select
                v-model="form.destinazione"
                :options="opzioniDestinazione"
                option-label="label"
                option-value="value"
                :placeholder="t('pagamenti.sistemazioni.campo_destinazione_placeholder')"
                :invalid="campiErrati.includes('destinazione')"
              />
            </div>
            <div class="form-field">
              <label>{{ t('pagamenti.sistemazioni.col_importo') }}</label>
              <InputNumber
                v-model="form.importo"
                mode="currency"
                currency="EUR"
                locale="it-IT"
                :invalid="campiErrati.includes('importo')"
              />
              <!-- ⭐ Si puo' sistemare una PARTE: gli atti su un documento
                   sono piu' di uno per natura. -->
              <small class="app-text-muted">
                {{ t('pagamenti.sistemazioni.importo_aiuto') }}
              </small>
            </div>
          </div>

          <!-- ⛔ Solo dove il denaro va da qualche parte. Sul rimborso esce
               dal sistema, e un secondo documento non esiste. -->
          <div v-if="serveDestinatario" class="form-field">
            <label>{{ t('pagamenti.sistemazioni.campo_destinatario') }}</label>
            <FatturaLookup
              v-model="fatturaDestinazione"
              :params="eccedenza.billing_account_id != null
                ? { billing_account_id: eccedenza.billing_account_id }
                : {}"
              :invalid="campiErrati.includes('fattura_destinazione_id')"
            />
            <!-- ⚠️ La frase si mostra SOLO se il filtro c'e' davvero: dire
                 «solo documenti dello stesso cliente» quando la tendina non e'
                 ristretta sarebbe un'affermazione falsa proprio sul campo in
                 cui l'errore costa di piu'. -->
            <small v-if="eccedenza.billing_account_id != null" class="app-text-muted">
              {{ t('pagamenti.sistemazioni.destinatario_aiuto') }}
            </small>
          </div>

          <div class="form-field">
            <label>{{ t('pagamenti.sistemazioni.col_motivo') }}</label>
            <Textarea v-model="form.motivo" rows="2" auto-resize />
            <small class="app-text-muted">
              {{ t('pagamenti.sistemazioni.motivo_aiuto') }}
            </small>
          </div>

          <div class="app-form-footer">
            <Button
              size="small"
              :label="t('pagamenti.sistemazioni.registra_azione')"
              :icon="MANAGE_ICONS.REGISTRA"
              :loading="loading"
              :disabled="!canSave"
              @click="onRegistra"
            />
          </div>
        </div>
      </template>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @confirm="onExportConfirm" />
  </AppDrawer>

  <ConfermaSistemazioneDialog
    v-model:visible="confermaVisible"
    :sistemazione="attoDaConfermare"
    @confermata="dopoConferma"
  />

  <!-- L'annullo chiede il PERCHE': una decisione scartata senza ragione non si
       ricostruisce, e resta a registro comunque. -->
  <MotivoDialog
    v-model:visible="annullaVisible"
    :header="t('pagamenti.sistemazioni.annulla_titolo')"
    :label="t('pagamenti.sistemazioni.col_motivo')"
    :aiuto="t('pagamenti.sistemazioni.annullo_aiuto')"
    :loading="loading"
    :save-label="t('pagamenti.sistemazioni.annulla_azione')"
    save-severity="danger"
    @conferma="onAnnulla"
  />
</template>
