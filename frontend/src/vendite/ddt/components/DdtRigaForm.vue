<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Form singola riga DDT — articolo (autocomplete), UoM, quantita',
// prezzo, sconto, IVA. Pricing stile ordini gestito lato BE: se il prezzo resta
// vuoto e l'articolo NON e' composito, gestisci_riga lo risolve via
// PricingService (richiede pero' emittente/BA/utility sulla testata DDT). Per
// articolo composito il prezzo padre e' SUM(componenti) (trigger DB): il campo
// prezzo e' nascosto. In CREATE, su articolo composito, si apre la
// ComponentiDialog pre-save per editare i prezzi componente; gli override
// viaggiano in `componenti_overrides`. In EDIT i prezzi componente si
// modificano via DdtRigaComponentiPanel. Clone di OrdiniRigaForm (§D-4).
// ⭐ LA RIGA EVASA (brief-db-ddt-righe-evase-dall-ordine, 2026-10-11): una
// riga legata a un ordine o a un reso da ri-consegnare (`evasa` della vista)
// ha articolo, UoM e quantita' FERMI — sono la fotografia di cio' che si
// spedisce per conto dell'origine. La quantita' si corregge dal verbo
// («Correggi quantita' evasa»), che cambia insieme riga, legame e ordine; il
// pulsante segue `correggi_qta_evasa_blocco` (NULL = acceso). Descrizione,
// prezzo e sconto restano del form. Le righe aggiunte a mano non cambiano.
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { useDdtStore } from '../stores/ddt'
import { previewRigaComponenti } from '../api/ddtApi'
import { useRigaArticoloComposito } from '../../_shared/righe/useRigaArticoloComposito'
import ArticoloLookup from '../../../catalogo/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import DdtRigaComponentiPanel from './DdtRigaComponentiPanel.vue'
import ComponentiCreateActionsPanel from '../../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../../_shared/componenti/ComponentiDialog.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useIvaRisolta } from '../../_shared/righe/useIvaRisolta'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { motivoDaCodiceBlocco } from '../../../core/utils/bloccoMotivo'
import DdtCorreggiQtaEvasaDialog from './dialogs/DdtCorreggiQtaEvasaDialog.vue'

const { t, te } = useI18n()
const store = useDdtStore()
const notify = useNotify()
const loading = ref(false)

const props = defineProps({
  ddtId: { type: Number, required: true },
  riga: { type: Object, default: null },
  // FE-A: la causale del DDT vende? Se no, il prezzo non e' obbligatorio —
  // ne' sulla riga ne' sui componenti del kit (FE-D4).
  causaleFatturabile: { type: Boolean, default: true },
})
const {
  ivaOrigine,
  origineLabel: ivaOrigineLabel,
  risolviPer: risolviIvaPer,
  reset: resetIva,
} = useIvaRisolta({ documentoTipo: SORGENTE_CODES.DDT_VENDITA, documentoId: () => props.ddtId })

const emit = defineEmits(['saved', 'cancel', 'componenti-changed'])

const form = ref({
  articolo_id: null,
  descrizione: '',
  qta_operativa: 1,
  prezzo_unitario: null,
  sconto_percentuale: 0,
  iva_id: null,
  uom_operativa_id: null,
})

// Articolo selezionato (per restore autocomplete).
const articoloObj = ref(null)

// La riga evasa (D-1): la dice il DB, il form non la deduce dai legami.
const isEvasa = computed(() => props.riga?.evasa === true)
// Il motivo per cui il verbo e' spento, e la frase del tooltip. La vista
// manda il solo codice (`correggi_qta_evasa_blocco`); la chiave e'
// `vendite.ddt.correggi_qta_evasa_reason.<codice minuscolo>` (contratto del
// DB, §6.1 del brief), fail-visible sul codice.
const correggiQtaBlocco = computed(() => props.riga?.correggi_qta_evasa_blocco || '')
const correggiQtaMotivo = computed(() => motivoDaCodiceBlocco(
  t, te, correggiQtaBlocco.value, 'vendite.ddt.correggi_qta_evasa_reason',
))
const correggiQtaVisible = ref(false)

// Scopo: la quantita' e' cambiata dal verbo: la riga si rilegge come dopo un
//        salvataggio (lista, riepilogo IVA, stato dell'ordine nella barra).
function onQtaCorretta(esito) {
  emit('saved', esito)
}

// Cuore riga articolo/composito condiviso con Ordini/Preventivi (B11, regola del
// 2): flag composito + wiring UoM + ComponentiDialog + submitRiga.
const {
  isEdit, isCasoA, isPadreComposito,
  uomOptions, uomLoading, uomLabel, caricaUomConPickBase, resetUomOptions,
  componentiDialogVisible, componentiPayload, showComponentiDialog,
  apriComponentiDialog, onComponentiConfirm,
  submitRiga,
  modificato, chiudiConConferma, seguiRiga,
} = useRigaArticoloComposito({
  store,
  parentId: () => props.ddtId,
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
    }
    articoloObj.value = riga.articolo_id
      ? { id: riga.articolo_id, codice: riga.articolo_codice, descrizione: riga.articolo_descrizione }
      : null
  } else {
    form.value = {
      articolo_id: null, descrizione: '', qta_operativa: 1, prezzo_unitario: null,
      sconto_percentuale: 0, iva_id: null, uom_operativa_id: null,
    }
    articoloObj.value = null
    resetUomOptions()
  }
})

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // ⛔ NIENTE PIU' AUTO-FILL DALL'ARTICOLO: era una seconda risposta alla
  // stessa domanda, e ignorava sia l'uso della fornitura sia i titoli
  // documentati del cliente. Ora risponde la sede unica, col contesto derivato
  // dalla testata — la stessa che il backend leggera' al salvataggio.
  resetIva()
  risolviIvaPer(form.value, item.id)
  form.value.uom_operativa_id = null
  form.value.prezzo_unitario = null
  articoloObj.value = item
  // Create: autopick base; in edit l'articolo e' disabled e questo non scatta.
  caricaUomConPickBase(item.id)
}

// Validazione FE. Il BE richiede, IN CREATE: articolo, UoM operativa,
// qta_operativa <> 0, IVA. Il prezzo NON e' richiesto: se vuoto e articolo non
// composito, il BE lo risolve via PricingService; per articolo composito e'
// SUM(componenti).
//
// ⛔ In EDIT si valida SOLO cio' che l'EDIT invia. `buildRigaPayload` qui sotto,
// nel ramo `isEdit`, manda `{qta_operativa, sconto_percentuale, descrizione}` +
// il prezzo: articolo, UoM e IVA sono immutabili (i rispettivi campi sono
// `:disabled="isEdit"`) e non viaggiano. Pretenderli qui significa spegnere il
// pulsante Salva per un campo che il salvataggio non toccherebbe.
//
// ⚠️ Non e' un caso di scuola: `vendite.fn_genera_ddt_riconsegna` genera le
// righe di ri-consegna SENZA `iva_id` (ne' prezzo, ne' sconto — il gemello
// `fn_genera_ddt_da_ordine` invece li copia). Su quelle righe `iva_id` e' NULL,
// il select IVA e' disabilitato e l'auto-fill da articolo non scatta mai perche'
// passa da `onArticoloSelect`, che in EDIT non si puo' invocare. Risultato prima
// di questa riga: il form si apriva e il Salva era **morto per sempre** — non
// solo il prezzo, nemmeno la quantita' si poteva correggere. Rilievo in-app di
// Tid, 2026-08-27, prova 9 del collaudo righe-senza-prezzo.
// ⭐ Il rimedio a monte (la riga che nasce completa) e' chiesto al team DB in
// `brief-db-ddt-riconsegna-eredita-testata.md` §3-bis/R4: sono due difetti
// distinti e vanno chiusi entrambi — questo gate resterebbe sbagliato anche con
// le righe complete, semplicemente non lo si vedrebbe piu'.
const canSave = computed(() => {
  const f = form.value
  if (f.qta_operativa == null || Number(f.qta_operativa) === 0) return false
  if (!isEdit.value) {
    if (!f.articolo_id) return false
    if (!f.uom_operativa_id) return false
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
  }
  return true
})

function buildRigaPayload() {
  const f = form.value
  if (isEdit.value) {
    const base = {
      sconto_percentuale: f.sconto_percentuale,
      descrizione: f.descrizione || null,
    }
    // ⛔ La riga evasa non manda la quantita': e' ferma (E_DDT_RIGA_EVASA_FERMA)
    //    e cambia solo dal verbo. Mandarla invariata passerebbe, ma direbbe al
    //    lettore che il form la salva.
    if (!isEvasa.value) {
      base.qta_operativa = f.qta_operativa
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
    ? t('vendite.ddt.riga_salvata')
    : t('vendite.ddt.riga_aggiunta')
  loading.value = true
  try {
    const result = await submitRiga(buildRigaPayload())
    notify.success(successMessage)
    // FE-B1: la riga E' salvata, quindi il verde ci va. Se il prezzo non si e'
    // risolto arriva anche `prezzo_esito`: e' un AVVISO, non un errore — il
    // rosso e' dell'emissione, che ha gia' il suo messaggio parlante.
    // Il testo lo manda il BE (DEC-4): qui non si riscrive e non si traduce.
    if (result?.prezzo_esito?.messaggio) {
      notify.warn(result.prezzo_esito.messaggio)
    }
    emit('saved', result)
  } catch (err) {
    notify.error(extractApiError(err, t('vendite.ddt.errore_generico')))
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
      <label>{{ t('vendite.ddt.riga_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        documento="DDT_VENDITA" :documento-id="ddtId"
        :placeholder="t('vendite.ddt.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <!-- Perche' articolo e quantita' sono spenti: lo si dice, non lo si lascia
         indovinare. -->
    <small v-if="isEvasa" class="app-field-hint">{{ t('vendite.ddt.riga_evasa_hint') }}</small>

    <div class="form-field">
      <label>{{ t('vendite.ddt.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.riga_quantita') }} *</label>
        <InputNumber v-model="form.qta_operativa" :min-fraction-digits="2" :max-fraction-digits="6"
          :disabled="isEvasa" />
        <!-- La riga evasa: la quantita' passa dal verbo. Tooltip sull'involucro:
             un Button disabilitato non emette eventi del mouse. -->
        <span v-if="isEvasa" class="app-action-tooltip-wrap"
          v-tooltip.top="correggiQtaMotivo || null">
          <Button :label="t('vendite.ddt.correggi_qta_evasa')" size="small" link
            class="app-correggi-qta-link"
            :disabled="Boolean(correggiQtaBlocco)"
            @click="correggiQtaVisible = true" />
        </span>
      </div>
      <div class="form-field">
        <label style="display: flex; align-items: center; gap: 0.5rem;">
          {{ t('vendite.ddt.riga_prezzo') }}
          <Tag v-if="isPadreComposito"
            severity="secondary"
            :value="t('vendite.ddt.componenti_padre_calcolato')"
            v-tooltip.top="t('vendite.ddt.componenti_section_hint')" />
        </label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT"
          :min-fraction-digits="6" :max-fraction-digits="6"
          :disabled="isPadreComposito" />
        <!-- FE-B2/B3: in CREATE il campo vuoto significa «risolvilo tu», in
             EDIT significa «nessun prezzo» — `aggiorna_riga` non ha auto-fill.
             Due frasi diverse perche' sono due comportamenti diversi:
             l'asimmetria esiste da sempre, questo e' il punto in cui si vede. -->
        <small v-if="!isPadreComposito" class="app-text-muted">
          {{ isEdit ? t('vendite.ddt.riga_prezzo_edit_hint') : t('vendite.ddt.riga_prezzo_auto_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ddt.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ddt.riga_iva') }} *</label>
        <!-- ⛔ `I6`: LA CASELLA E' CHIUSA, sempre — anche in creazione.
             L'aliquota la decide il risolutore, e lasciarla modificabile
             riaprirebbe la seconda risposta alla stessa domanda che tutto
             questo cantiere e' servito a togliere. Il campo resta a VIDEO, e
             spento: l'operatore deve poter vedere cosa gli viene applicato.
             ⚠️ Se serve cambiarla, si cambia sull'ARTICOLO — ed e' quello che
             dicono ora i messaggi dei gate all'emissione. -->
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('vendite.ddt.riga_iva')" disabled />
        <!-- ⭐ IL PERCHE' DI QUEL NUMERO. `I6` sta per togliere all'operatore
             la casella: un'aliquota che non si puo' cambiare E che non viene
             spiegata e' la forma peggiore. La label la compone il composable —
             qui non si costruisce nessun percorso i18n. -->
        <small v-if="ivaOrigine" class="app-field-hint">{{ ivaOrigineLabel }}</small>
      </div>
      <div class="form-field" v-if="!isEdit">
        <label>{{ t('vendite.ddt.riga_uom') }} *</label>
        <Select v-model="form.uom_operativa_id"
          :options="uomOptions" :option-label="uomLabel" option-value="uom_id"
          :loading="uomLoading"
          :disabled="!form.articolo_id || uomLoading"
          :placeholder="form.articolo_id
            ? t('vendite.ddt.riga_uom')
            : t('vendite.ddt.riga_uom_articolo_first')" />
      </div>
    </div>

    <!-- Componenti BoM CREATE (articolo composito): dialog pre-save per editare
         i prezzi componente. BB condiviso con ordini/preventivi/contratti. Gli
         override confermati viaggiano in `componenti_overrides` nel payload. -->
    <ComponentiCreateActionsPanel
      v-if="!isEdit && articoloObj?.is_composito"
      section-title-key="vendite.ddt.componenti_section_title"
      :disabled="!form.articolo_id || !form.uom_operativa_id
        || ((form.qta_operativa || 0) <= 0)"
      :componenti-payload="componentiPayload"
      @apri-dialog="apriComponentiDialog"
    />

    <ComponentiDialog
      v-if="showComponentiDialog"
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="ddtId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      :prezzo-richiesto="causaleFatturabile"
      @confirm="onComponentiConfirm"
    />

    <!-- Componenti BoM CASO A (solo EDIT): pannello componenti persistiti,
         modifica prezzo per singolo componente via PATCH. In CREATE i componenti
         sono inizializzati dal BE al save della riga composita. -->
    <div v-if="isCasoA" class="app-drawer-section" style="margin-top: 1rem;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem;">
        {{ t('vendite.ddt.componenti_section_title') }}
      </h4>
      <!-- ⭐ La frase sta QUI e non dentro `ComponentiPanel`: quel componente e'
           condiviso con preventivi, ordini, contratti e listino bundle, e un
           testo che parla di «causale del DDT» dentro un BB e' un dominio che
           tracima. Il BB riceve un booleano, non una spiegazione. -->
      <small v-if="!causaleFatturabile" class="app-text-muted"
             style="display: block; margin-bottom: 0.5rem;">
        {{ t('vendite.ddt.componenti_senza_prezzo_hint') }}
      </small>
      <DdtRigaComponentiPanel
        :ddt-id="ddtId"
        :riga-id="props.riga.id"
        :readonly="false"
        :prezzo-richiesto="causaleFatturabile"
        @changed="emit('componenti-changed')" />
    </div>

    <DdtCorreggiQtaEvasaDialog
      v-if="isEvasa"
      v-model:visible="correggiQtaVisible"
      :ddt-id="ddtId"
      :riga="props.riga"
      @corretta="onQtaCorretta" />

    <!-- Bottoni Salva/Annulla della riga: sempre visibili in edit-riga. I bottoni
         del FormFooter testata si nascondono via `formRigaAperto` lato DdtDrawer. -->
    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="chiudiConConferma(() => emit('cancel'))" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>

<style scoped>
/* «Correggi quantita' evasa» e' un'azione, ma accanto ai campi un Button
   `text` sembrava una scritta (rilievo in-app di Tid, 2026-10-11): link verde
   sottolineato SEMPRE, come i link dei passaggi lineage. Da spento resta
   senza sottolineatura: non promette un click che non c'e'. */
.app-correggi-qta-link:not(:disabled) :deep(.p-button-label) {
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
