<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FatturaLookup from '../../core/components/FatturaLookup.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { statoSistemazioneSeverity } from '../../core/utils/severity'
import {
  annullaSistemazione,
  creaSistemazione,
  listSistemazioniFattura,
} from '../api/pagamenti'
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

const props = defineProps({
  visible: { type: Boolean, default: false },
  // La riga dell'elenco eccedenze (`vw_eccedenze_da_sistemare`).
  eccedenza: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'cambiata'])

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const isReadonly = useInjectReadonly()

const atti = ref([])
const attiLetti = ref(false)
// ⛔ Tre casi, non due: atti presenti · nessun atto · non letti. L'ultimo NON si
//    spaccia per il secondo: «su questo documento non ha ancora deciso nessuno»
//    e' un'affermazione su cui qualcuno prende una decisione.
const erroreAtti = ref(false)

const form = ref(defaultForm())
const fatturaDestinazione = ref(null)
const confermaVisible = ref(false)
const attoDaConfermare = ref(null)
const annullaVisible = ref(false)
const attoDaAnnullare = ref(null)
const motivoAnnullo = ref('')

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

// ⛔ Cambiando destinazione il documento di destinazione si azzera: su RIMBORSO
//    e' VIETATO (il denaro esce, non c'e' un secondo documento) e mandarlo
//    sarebbe un rifiuto su un campo che a video non si vede piu'.
watch(() => form.value.destinazione, () => {
  if (!serveDestinatario.value) fatturaDestinazione.value = null
})

async function caricaAtti() {
  atti.value = []
  attiLetti.value = false
  erroreAtti.value = false
  if (!fatturaId.value) return
  const dati = await execute(() => listSistemazioniFattura(fatturaId.value))
  erroreAtti.value = dati === null
  atti.value = dati?.results || []
  attiLetti.value = true
}

watch(() => [props.visible, fatturaId.value], ([vis]) => {
  if (!vis) {
    atti.value = []
    return
  }
  form.value = defaultForm()
  // ⭐ L'importo nasce sull'INTERA eccedenza: e' il caso normale — si sistema
  //    tutto quello che e' di troppo — e resta modificabile, perche' si puo'
  //    rimborsare una parte e riportare il resto.
  form.value.importo = props.eccedenza?.eccedenza != null
    ? Number(props.eccedenza.eccedenza)
    : null
  fatturaDestinazione.value = null
  caricaAtti()
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
  await caricaAtti()
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
  motivoAnnullo.value = ''
  annullaVisible.value = true
}

async function onAnnulla() {
  const payload = {}
  // ⚠️ Il motivo si manda solo se scritto: il database sa se l'atto ne aveva
  //    gia' uno, e in quel caso il vuoto lascia quello che c'era. Ripetere qui
  //    l'obbligo sarebbe una seconda sede di una regola che il guard tiene.
  if (motivoAnnullo.value.trim()) payload.motivo = motivoAnnullo.value.trim()
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
  await caricaAtti()
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
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t('pagamenti.sistemazioni.titolo')"
        :icon="NAV_ICONS.ECCEDENZE"
      />
    </template>

    <div class="app-drawer-content">
      <template v-if="contentReady && eccedenza">
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

        <Message v-if="erroreAtti" severity="warn" :closable="false" size="small">
          {{ t('pagamenti.sistemazioni.atti_non_letti') }}
        </Message>
        <Message
          v-else-if="attiLetti && !atti.length"
          severity="info"
          :closable="false"
          size="small"
        >
          {{ t('pagamenti.sistemazioni.nessun_atto') }}
        </Message>

        <DataTable
          v-if="atti.length"
          :value="atti"
          class="app-datatable app-datatable--inner"
          data-key="id"
        >
          <Column field="destinazione" :header="t('pagamenti.sistemazioni.col_destinazione')">
            <template #body="{ data }">{{ etichettaDestinazione(data.destinazione) }}</template>
          </Column>
          <Column
            field="importo"
            :header="t('pagamenti.sistemazioni.col_importo')"
            style="text-align: right;"
          >
            <template #body="{ data }">{{ formatCurrency(data.importo) }}</template>
          </Column>
          <Column field="stato" :header="t('pagamenti.sistemazioni.col_stato')">
            <template #body="{ data }">
              <!-- ⚠️ Tradotto e fail-visible: uno stato nuovo si legge come
                   CODICE, non come una parola inglese lasciata a video. -->
              <Tag
                :value="etichettaStato(data.stato)"
                :severity="statoSistemazioneSeverity(data.stato)"
              />
            </template>
          </Column>
          <Column field="motivo" :header="t('pagamenti.sistemazioni.col_motivo')">
            <template #body="{ data }">{{ data.motivo || '—' }}</template>
          </Column>
          <Column field="data_esecuzione" :header="t('pagamenti.sistemazioni.col_eseguita')">
            <template #body="{ data }">
              <span v-if="data.data_esecuzione">
                {{ displayTimestamp(data.data_esecuzione) }}
              </span>
              <span v-else class="app-text-muted">—</span>
            </template>
          </Column>
          <Column
            :header="t('common.col_azioni')"
            class="app-col-actions"
            :exportable="false"
          >
            <!-- ⚠️ Niente componente quando non c'e' nessuna azione: in
                 variante compatta il kebab si disegna comunque, e aprirebbe un
                 menu vuoto su un atto terminale. -->
            <template #body="{ data }">
              <RowActionsMenu
                v-if="buildRowActions(data).length"
                :row="data"
                :actions="buildRowActions(data)"
              />
              <span v-else class="app-text-muted">—</span>
            </template>
          </Column>
        </DataTable>

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
                icon="pi pi-check"
                :loading="loading"
                :disabled="!canSave"
                @click="onRegistra"
              />
            </div>
          </div>
        </template>
      </template>
    </div>
  </Drawer>

  <ConfermaSistemazioneDialog
    v-model:visible="confermaVisible"
    :sistemazione="attoDaConfermare"
    @confermata="dopoConferma"
  />

  <!-- L'annullo chiede il PERCHE': una decisione scartata senza ragione non si
       ricostruisce, e resta a registro comunque. -->
  <AppDialog
    :visible="annullaVisible"
    :header="t('pagamenti.sistemazioni.annulla_titolo')"
    width="sm"
    :loading="loading"
    :save-label="t('pagamenti.sistemazioni.annulla_azione')"
    save-severity="danger"
    @update:visible="(v) => (annullaVisible = v)"
    @save="onAnnulla"
    @cancel="annullaVisible = false"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('pagamenti.sistemazioni.col_motivo') }}</label>
        <Textarea v-model="motivoAnnullo" rows="3" auto-resize />
        <small class="app-text-muted">{{ t('pagamenti.sistemazioni.annullo_aiuto') }}</small>
      </div>
    </div>
  </AppDialog>
</template>
