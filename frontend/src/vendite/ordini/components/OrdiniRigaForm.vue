<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Form singola riga ordine — articolo (autocomplete), UoM, quantita',
// prezzo, sconto, IVA. Pricing stile preventivo gestito lato BE: se il prezzo
// resta vuoto e l'articolo NON e' composito, gestisci_riga lo risolve via
// PricingService. Per articolo composito il prezzo padre e' SUM(componenti)
// (trigger DB): il campo prezzo e' nascosto. In CREATE, su articolo composito,
// si apre la ComponentiDialog pre-save per editare i prezzi componente (come
// preventivi/contratti): gli override viaggiano in `componenti_overrides`. In
// EDIT i prezzi componente si modificano via OrdiniRigaComponentiPanel.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { useOrdiniStore } from '../stores/ordini'
import { previewRigaComponenti } from '../api/ordiniApi'
import { useRigaArticoloComposito } from '../../_shared/righe/useRigaArticoloComposito'
import ArticoloLookup from '../../../catalogo/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import OrdiniRigaComponentiPanel from './OrdiniRigaComponentiPanel.vue'
import ComponentiCreateActionsPanel from '../../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../../_shared/componenti/ComponentiDialog.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useIvaRisolta } from '../../_shared/righe/useIvaRisolta'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { DATE_FORMAT } from '../../../core/constants'
import { parseIsoDate, toDateString } from '../../../core/utils/date'

const { t } = useI18n()
const store = useOrdiniStore()
const notify = useNotify()
const loading = ref(false)

const props = defineProps({
  ordineId: { type: Number, required: true },
  riga: { type: Object, default: null },
  // La data del documento (ISO, dal dettaglio): il minimo del calendario
  // delle date di consegna. Solo un aiuto: il rifiuto vero e' del DB
  // (`E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE`).
  dataDocumento: { type: String, default: null },
})
const {
  ivaOrigine,
  origineLabel: ivaOrigineLabel,
  risolviPer: risolviIvaPer,
  reset: resetIva,
} = useIvaRisolta({ documentoTipo: SORGENTE_CODES.ORDINE_VENDITA, documentoId: () => props.ordineId })

const emit = defineEmits(['saved', 'cancel', 'componenti-changed'])

// Le due date di consegna (brief-db-modifiche-certe-ciclo-vendita-e-articolo,
// Blocco A): la RICHIESTA e' del cliente, la CONFERMATA e' la nostra promessa.
// Stanno sulla RIGA e non sulla testata: una riga puo' essere pronta e un'altra
// no. Entrambe facoltative; nessun vincolo fra le due (si puo' confermare PRIMA
// di quanto chiesto, ed e' una buona notizia — brief §2.3).
const minDataConsegna = computed(() => parseIsoDate(props.dataDocumento))

const form = ref({
  articolo_id: null,
  descrizione: '',
  qta_operativa: 1,
  prezzo_unitario: null,
  sconto_percentuale: 0,
  iva_id: null,
  uom_operativa_id: null,
  data_consegna_richiesta_cliente: null,
  data_consegna_confermata: null,
})

// Articolo selezionato (per restore autocomplete).
const articoloObj = ref(null)

// Cuore riga articolo/composito condiviso con PreventiviRigaForm (B11, regola
// del 2): flag composito + wiring UoM + ComponentiDialog + submitRiga. Resolver
// listino e gate L2 (preventivi) restano fuori: l'ordine non li ha.
const {
  isEdit, isCasoA, isPadreComposito,
  uomOptions, uomLoading, uomLabel, caricaUomConPickBase, resetUomOptions,
  componentiDialogVisible, componentiPayload, showComponentiDialog,
  apriComponentiDialog, onComponentiConfirm,
  submitRiga,
  modificato, chiudiConConferma, seguiRiga,
} = useRigaArticoloComposito({
  store,
  parentId: () => props.ordineId,
  riga: () => props.riga,
  articoloObj,
  form,
})

// Il legame con la riga (fotografia, riga riletta dal server) e' del cuore
// condiviso: qui solo come si popola il form.
seguiRiga((riga) => {
  if (riga) {
    form.value = {
      articolo_id: riga.articolo_id,
      descrizione: riga.descrizione || '',
      qta_operativa: Number(riga.qta_operativa) || 1,
      prezzo_unitario: riga.prezzo_unitario != null ? Number(riga.prezzo_unitario) : null,
      sconto_percentuale: Number(riga.sconto_percentuale) || 0,
      iva_id: riga.iva_id || null,
      uom_operativa_id: riga.uom_operativa_id || null,
      data_consegna_richiesta_cliente: parseIsoDate(riga.data_consegna_richiesta_cliente),
      data_consegna_confermata: parseIsoDate(riga.data_consegna_confermata),
    }
    articoloObj.value = riga.articolo_id
      ? { id: riga.articolo_id, codice: riga.articolo_codice, descrizione: riga.articolo_descrizione }
      : null
  } else {
    form.value = {
      articolo_id: null, descrizione: '', qta_operativa: 1, prezzo_unitario: null,
      sconto_percentuale: 0, iva_id: null, uom_operativa_id: null,
      data_consegna_richiesta_cliente: null, data_consegna_confermata: null,
    }
    articoloObj.value = null
    resetUomOptions()
  }
})

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // ⛔ NIENTE PIU' AUTO-FILL DALL'ARTICOLO. Copiare `articolo.iva_id` era una
  // SECONDA risposta alla stessa domanda, e sbagliata in due casi che non danno
  // nessun sintomo: ignora l'uso della fornitura (`config.tipi_utenze`, dove
  // l'articolo tace) e ignora i titoli documentati del cliente — su un
  // esportatore abituale proponeva l'aliquota piena.
  // ⭐ Ora risponde la sede unica (`vendite.fn_resolve_iva_riga`), e il
  // contesto lo deriva il backend dalla testata del documento: e' la stessa che
  // leggera' al salvataggio, quindi cio' che si vede e cio' che viene scritto
  // non possono divergere.
  // ⚠️ Best-effort: se l'anteprima non risponde il campo resta vuoto e
  // l'operatore lo compila — che fino a `I6` e' ancora un suo diritto.
  resetIva()
  risolviIvaPer(form.value, item.id)
  form.value.uom_operativa_id = null
  form.value.prezzo_unitario = null
  articoloObj.value = item
  // Create: autopick base; in edit l'articolo e' disabled e questo non scatta.
  caricaUomConPickBase(item.id)
}

// Validazione FE. Il BE richiede: articolo, UoM operativa, qta_operativa <> 0,
// IVA. Il prezzo NON e' richiesto: se vuoto e articolo non composito, il BE lo
// risolve via PricingService; per articolo composito e' SUM(componenti).
const canSave = computed(() => {
  const f = form.value
  if (!f.articolo_id) return false
  if (!f.uom_operativa_id) return false
  if (f.qta_operativa == null || Number(f.qta_operativa) === 0) return false
  // ⛔ `I6`: l'IVA NON e' piu' un requisito per salvare, e toglierlo e'
  //    obbligatorio — non un ripulisti. Con la casella spenta e
  //    l'auto-fill morto, se l'anteprima non risponde il campo resta
  //    vuoto e la riga non si potrebbe piu' salvare: la creazione si
  //    bloccherebbe DA SOLA, senza che nulla lo spieghi.
  //    A rispondere e' comunque il backend al salvataggio; a fermare
  //    una riga senza aliquota e' il gate all'emissione (`I9`).
  // CREATE su articolo composito: blocca il save finche' la ComponentiDialog
  // non e' stata confermata almeno una volta (componentiPayload valorizzato).
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

// Scopo: le date di consegna nel payload — ISO o `null` (`toDateString` di un
//        DatePicker vuoto e' gia' `null`). Il `null` esplicito AZZERA in PATCH
//        (semantica dei documenti vendite), quindi si mandano sempre: svuotare
//        il DatePicker deve togliere la data, non lasciarla.
function dateConsegnaPayload(f) {
  return {
    data_consegna_richiesta_cliente: toDateString(f.data_consegna_richiesta_cliente),
    data_consegna_confermata: toDateString(f.data_consegna_confermata),
  }
}

function buildRigaPayload() {
  const f = form.value
  if (isEdit.value) {
    const base = {
      qta_operativa: f.qta_operativa,
      sconto_percentuale: f.sconto_percentuale,
      descrizione: f.descrizione || null,
      ...dateConsegnaPayload(f),
    }
    // Per riga CASO A il prezzo padre e' SUM(componenti) via trigger DB:
    // l'edit del prezzo avviene per componente nel pannello sotto.
    if (!isCasoA.value) {
      base.prezzo_unitario = f.prezzo_unitario
    }
    return base
  }
  const payload = {
    articolo_id: f.articolo_id,
    descrizione: f.descrizione || null,
    qta_operativa: f.qta_operativa,
    sconto_percentuale: f.sconto_percentuale,
    uom_operativa_id: f.uom_operativa_id,
    ...dateConsegnaPayload(f),
  }
  // Articolo composito CREATE: il prezzo padre e' SUM(componenti) — non inviarlo
  // (il BE inizializza i componenti). Per articoli semplici: solo se valorizzato
  // (vuoto → il BE risolve via PricingService).
  if (!isPadreComposito.value && f.prezzo_unitario != null) {
    payload.prezzo_unitario = f.prezzo_unitario
  }
  // Override prezzi componente dal dialog pre-save (se confermato).
  if (showComponentiDialog.value && componentiPayload.value?.overrides) {
    payload.componenti_overrides = componentiPayload.value.overrides
  }
  return payload
}

async function handleSave() {
  const successMessage = isEdit.value
    ? t('vendite.ordini.riga_salvata')
    : t('vendite.ordini.riga_aggiunta')
  loading.value = true
  try {
    const result = await submitRiga(buildRigaPayload())
    notify.success(successMessage)
    emit('saved', result)
  } catch (err) {
    notify.error(extractApiError(err, t('vendite.ordini.errore_generico')))
  } finally {
    loading.value = false
  }
}

// ⭐ D-13 (2026-10-03): la fotografia della riga la tiene il cuore comune
//    (`useRigaArticoloComposito`). Il contenitore la legge da qui per chiedere
//    prima di cambiare riga o di uscire dal drawer.
defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('vendite.ordini.riga_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        documento="ORDINE_VENDITA" :documento-id="ordineId"
        :placeholder="t('vendite.ordini.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('vendite.ordini.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_quantita') }} *</label>
        <InputNumber v-model="form.qta_operativa" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label style="display: flex; align-items: center; gap: 0.5rem;">
          {{ t('vendite.ordini.riga_prezzo') }}
          <Tag v-if="isPadreComposito"
            severity="secondary"
            :value="t('vendite.ordini.componenti_padre_calcolato')"
            v-tooltip.top="t('vendite.ordini.componenti_section_hint')" />
        </label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT"
          :min-fraction-digits="6" :max-fraction-digits="6"
          :disabled="isPadreComposito" />
        <small v-if="!isPadreComposito" class="app-text-muted">
          {{ t('vendite.ordini.riga_prezzo_auto_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_iva') }} *</label>
        <!-- ⛔ `I6`: LA CASELLA E' CHIUSA, sempre — anche in creazione.
             L'aliquota la decide il risolutore, e lasciarla modificabile
             riaprirebbe la seconda risposta alla stessa domanda che tutto
             questo cantiere e' servito a togliere. Il campo resta a VIDEO, e
             spento: l'operatore deve poter vedere cosa gli viene applicato.
             ⚠️ Se serve cambiarla, si cambia sull'ARTICOLO — ed e' quello che
             dicono ora i messaggi dei gate all'emissione. -->
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('vendite.ordini.riga_iva')" disabled />
        <!-- ⭐ IL PERCHE' DI QUEL NUMERO. `I6` sta per togliere all'operatore
             la casella: un'aliquota che non si puo' cambiare E che non viene
             spiegata e' la forma peggiore. La label la compone il composable —
             qui non si costruisce nessun percorso i18n. -->
        <small v-if="ivaOrigine" class="app-field-hint">{{ ivaOrigineLabel }}</small>
      </div>
      <div class="form-field" v-if="!isEdit">
        <label>{{ t('vendite.ordini.riga_uom') }} *</label>
        <Select v-model="form.uom_operativa_id"
          :options="uomOptions" :option-label="uomLabel" option-value="uom_id"
          :loading="uomLoading"
          :disabled="!form.articolo_id || uomLoading"
          :placeholder="form.articolo_id
            ? t('vendite.ordini.riga_uom')
            : t('vendite.ordini.riga_uom_articolo_first')" />
      </div>
    </div>

    <!-- Le due date di consegna della riga (Blocco A): quando il cliente la
         vuole e quando ci si impegna a darla. La differenza fra le due E' la
         promessa; il ritardo lo calcola la vista situazione merce contro la
         promessa (o, senza promessa, contro la richiesta). -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_data_consegna_richiesta_cliente') }}</label>
        <DatePicker v-model="form.data_consegna_richiesta_cliente"
          :date-format="DATE_FORMAT" :min-date="minDataConsegna" show-icon show-button-bar />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_data_consegna_confermata') }}</label>
        <DatePicker v-model="form.data_consegna_confermata"
          :date-format="DATE_FORMAT" :min-date="minDataConsegna" show-icon show-button-bar />
      </div>
    </div>

    <!-- Componenti BoM CREATE (articolo composito): dialog pre-save per editare
         i prezzi componente. BB condiviso con preventivi/contratti. Gli override
         confermati viaggiano in `componenti_overrides` nel payload. -->
    <ComponentiCreateActionsPanel
      v-if="!isEdit && articoloObj?.is_composito"
      section-title-key="vendite.ordini.componenti_section_title"
      :disabled="!form.articolo_id || !form.uom_operativa_id
        || ((form.qta_operativa || 0) <= 0)"
      :componenti-payload="componentiPayload"
      @apri-dialog="apriComponentiDialog"
    />

    <ComponentiDialog
      v-if="showComponentiDialog"
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="ordineId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm"
    />

    <!-- Componenti BoM CASO A (solo EDIT): pannello componenti persistiti,
         modifica prezzo per singolo componente via PATCH. In CREATE i componenti
         sono inizializzati dal BE al save della riga composita. -->
    <div v-if="isCasoA" class="app-drawer-section" style="margin-top: 1rem;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem;">
        {{ t('vendite.ordini.componenti_section_title') }}
      </h4>
      <OrdiniRigaComponentiPanel
        :ordine-id="ordineId"
        :riga-id="props.riga.id"
        :readonly="false"
        @changed="emit('componenti-changed')" />
    </div>

    <!-- Bottoni Salva/Annulla della riga: sempre visibili in edit-riga. I bottoni
         del FormFooter testata si nascondono via `formRigaAperto` lato OrdiniDrawer. -->
    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="chiudiConConferma(() => emit('cancel'))" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>
