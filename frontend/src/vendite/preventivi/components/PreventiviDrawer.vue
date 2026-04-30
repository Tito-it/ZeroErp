<script setup>
// Scopo: Drawer crea/modifica preventivo vendita.
// CREATE: form testata semplice per creazione rapida.
// EDIT: testata + righe + totali + integrazione (con azioni stato).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { addDaysToToday, displayDate, toDateString } from '../../../core/utils/date'
import { formatCurrency } from '../../../core/utils/format'
import { paramBool, paramInt } from '../../../core/utils/parameterCast'
import { useParameterDefaults } from '../../../core/composables/useParameterDefaults'
import { getPreventivoFormDefaults } from '../../api/formDefaults'
import { getBillingAccountLookupById } from '../../../core/apiCore'
import { DRAWER_WIDTH } from '../../../core/constants'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../../core/components/DrawerFooter.vue'
import PreventiviForm from './PreventiviForm.vue'
import PreventiviRigheTable from './PreventiviRigheTable.vue'
import PreventiviIntegrazione from './PreventiviIntegrazione.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import Message from 'primevue/message'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  preventivoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura del drawer per evitare il rimbalzo iniziale (pattern adottato
// da ContrattoDrawer + memoria feedback_content_ready_after_show).
const contentReady = ref(false)
function onAfterShow() { contentReady.value = true }

// Capability dal detail backend (Fase 1: script.fn_available_actions_preventivo).
// Il drawer NON ricalcola lo stato: tutto deriva dai metadata API.
// Composable centralizzato (Fase 4.F2): availableActions/canEdit/flag/isLocked/
// nonEditableFields uniformi a Contratti/Promo. Qui editFlag = can_edit_testata.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
const canCreateRevisione = computed(() => caps.flag('can_create_revisione'))
const canPushCommessa = computed(() => caps.flag('can_push_commessa'))
const pushCommessaReasonKey = computed(() => detail.value?.can_push_commessa_reason_key || null)
// Per PreventiviForm passiamo l'array originale (no Set): il prop e' typed Array.
const nonEditableFields = computed(() => detail.value?.non_editable_fields || [])

// Defaults non-BA da config.parameters (Fase 2 refactor frontend vendite).
// Caricati on-open drawer prima di resetForm; cache modulo `useParameterDefaults`.
// I defaults BA-dipendenti (valuta_id, termine_pagamento_id) NON stanno qui:
// arriveranno dall'endpoint dedicato form-defaults?billing_account_id=... (2.B4).
const { defaults: paramDefaults, load: loadParamDefaults } = useParameterDefaults([
  'VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG',
  'VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA',
])

function defaultForm() {
  const p = paramDefaults.value
  // validita_al = oggi + N gg dal parameter; validita_dal resta null finche'
  // l'operatore non lo conferma (no presupposto di emissione immediata).
  const validitaGg = paramInt(p.VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG, 30)
  return {
    utility_id: null,
    billing_account_id: null,
    // _obj per BillingAccountLookup AutoComplete (pattern restore lookup ricco,
    // memoria feedback_autocomplete_restore). Popolato da onBaSelected (FE)
    // o da loadDetail() via getBillingAccountLookupById in edit.
    billing_account_obj: null,
    istanza_utility_id: null,
    valuta_id: null,
    termine_pagamento_id: null,
    validita_dal: null,
    validita_al: addDaysToToday(validitaGg),
    competenza_mese: null,
    fatturazione_immediata: paramBool(p.VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA, false),
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.preventivoId) return
  const data = await store.fetchDetail(props.preventivoId)
  if (!data) return
  detail.value = data
  form.value = {
    utility_id: data.utility_id,
    billing_account_id: data.billing_account_id,
    billing_account_obj: null,  // popolato sotto via getBillingAccountLookupById
    istanza_utility_id: data.istanza_utility_id,
    valuta_id: data.valuta_id,
    termine_pagamento_id: data.termine_pagamento_id,
    validita_dal: data.validita_dal ? new Date(data.validita_dal + 'T00:00:00') : null,
    validita_al: data.validita_al ? new Date(data.validita_al + 'T00:00:00') : null,
    competenza_mese: data.competenza_mese ? new Date(data.competenza_mese + 'T00:00:00') : null,
    fatturazione_immediata: data.fatturazione_immediata || false,
  }
  // Restore BillingAccountLookup _obj per visualizzazione ricca (codice, ragione
  // sociale, id fiscale, PDP). Best-effort: in caso di failure il drawer mostra
  // l'autocomplete vuoto e l'operatore puo' ri-selezionare. Skip se BA assente.
  if (data.billing_account_id) {
    try {
      const res = await getBillingAccountLookupById(data.billing_account_id)
      const ba = res?.data?.data
      if (ba) form.value.billing_account_obj = ba
    } catch {
      // Resto: form parte senza _obj, l'utente puo' rieseguire la ricerca.
    }
  }
}

watch(() => props.visible, async (v) => {
  if (!v) {
    contentReady.value = false
    return
  }
  // Carica i parameters una sola volta (cache nel composable). Sequenza:
  // load defaults -> reset/loadDetail, cosi' il form parte gia' valorizzato.
  await loadParamDefaults()
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

// Fase 2.B4 + 2.F6: quando l'operatore valorizza/cambia il BA in create,
// chiediamo al BE i defaults BA-derived (valuta_id, termine_pagamento_id,
// iva_id) dal cliente associato. Sovrascriviamo i campi solo se vuoti, per
// non distruggere scelte gia' fatte dall'utente. Skippiamo in edit (i campi
// sono gia' persistiti dal payload preventivo).
let _baDefaultsToken = 0
watch(() => form.value.billing_account_id, async (newBaId, oldBaId) => {
  if (isEdit.value) return
  if (!newBaId || newBaId === oldBaId) return
  const tk = ++_baDefaultsToken
  let res
  try {
    res = await getPreventivoFormDefaults(newBaId)
  } catch {
    return  // Best-effort: il fallback resta "form vuoto, l'operatore valorizza".
  }
  if (tk !== _baDefaultsToken) return  // Apertura/chiusura veloce: scarta stantio.
  const data = res?.data?.data
  if (!data) return
  if (form.value.valuta_id == null && data.valuta_id != null) {
    form.value.valuta_id = data.valuta_id
  }
  if (form.value.termine_pagamento_id == null && data.termine_pagamento_id != null) {
    form.value.termine_pagamento_id = data.termine_pagamento_id
  }
})

const canSave = computed(() => form.value.utility_id != null)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    // Backend whitelist (preventivi_service.aggiorna_preventivo): billing_account_id,
    // istanza_utility_id, valuta_id, termine_pagamento_id, validita_dal,
    // validita_al, competenza_mese, fatturazione_immediata, meta. utility_id
    // NON viene spedito: e' immutabile post-create (regola di dominio,
    // script.fn_available_actions_preventivo lo mette sempre in non_editable_fields).
    // Inviamo sempre tutti i campi della whitelist: il backend e' tollerante a NULL
    // (empty_to_none), cosi' un clear di valuta/termine viene davvero persistito.
    const payload = {
      billing_account_id: f.billing_account_id ?? null,
      istanza_utility_id: f.istanza_utility_id ?? null,
      valuta_id: f.valuta_id ?? null,
      termine_pagamento_id: f.termine_pagamento_id ?? null,
      validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
      validita_al: f.validita_al ? toDateString(f.validita_al) : null,
      competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
      fatturazione_immediata: f.fatturazione_immediata,
    }
    const result = await execute(
      () => store.update(props.preventivoId, payload),
      { successMessage: t('preventivi.preventivo_salvato') }
    )
    if (result !== null) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    const payload = {
      utility_id: f.utility_id,
      billing_account_id: f.billing_account_id || null,
      istanza_utility_id: f.istanza_utility_id || null,
      valuta_id: f.valuta_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
      validita_al: f.validita_al ? toDateString(f.validita_al) : null,
      competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
      fatturazione_immediata: f.fatturazione_immediata,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('preventivi.preventivo_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}

// --- Azioni stato (data-driven da detail.available_actions) ---

// Scopo: handler unico bottone azione. Usa requires_confirm dai metadata
//        per decidere se mostrare il dialog di conferma. La label nel
//        messaggio di conferma e' tradotta dalla label_key dell'azione.
function onCambiaStato(action) {
  if (action.requires_confirm) {
    confirmAction({
      message: t('preventivi.conferma_cambio_stato', { stato: t(action.label_key) }),
      accept: () => eseguiCambioStato(action.target_state),
    })
  } else {
    eseguiCambioStato(action.target_state)
  }
}

async function eseguiCambioStato(nuovoStato) {
  const result = await execute(
    () => store.cambiaStato(props.preventivoId, nuovoStato),
    { successMessage: t('preventivi.stato_cambiato') }
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Scopo: Crea nuova revisione del preventivo.
function onNuovaRevisione() {
  confirmAction({
    message: t('preventivi.conferma_revisione'),
    accept: async () => {
      const result = await execute(
        () => store.nuovaRevisione(props.preventivoId),
        { successMessage: t('preventivi.revisione_creata') }
      )
      if (result !== null) emit('saved', result)
    }
  })
}

</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('preventivi.preventivo')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info (solo edit) -->
      <div v-if="isEdit && detail" style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.5rem;">
        <Tag :value="`${detail.numero} rev.${detail.rev}`" severity="secondary" />
        <Tag :value="detail.stato_descrizione" :severity="statoPreventiveSeverity(detail.stato_codice_interno)" />
        <span v-if="detail.data" style="font-size: 0.85rem; color: var(--text-color-secondary);">
          {{ displayDate(detail.data) }}
        </span>
        <span v-if="detail.cliente_denominazione" style="font-size: 0.85rem;">
          {{ detail.cliente_denominazione }}
        </span>
      </div>

      <!-- Azioni stato (solo edit, non readonly): bottoni dai metadata API -->
      <div v-if="isEdit && detail && !isReadonly && (availableActions.length || canCreateRevisione)"
        style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
        <Button v-for="action in availableActions" :key="action.key"
          :icon="action.icon" :label="t(action.label_key)" :severity="action.severity"
          size="small" @click="onCambiaStato(action)" />
        <Button v-if="canCreateRevisione"
          icon="pi pi-copy" :label="t('preventivi.azione_revisione')" severity="secondary"
          size="small" @click="onNuovaRevisione" />
      </div>

      <Divider v-if="isEdit && detail" />

      <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup -->
      <PreventiviForm v-if="contentReady"
        :form="form" :is-modificabile="canEditTestata && !isReadonly"
        :non-editable-fields="nonEditableFields" />

      <!-- Righe (solo edit) -->
      <template v-if="contentReady && isEdit && detail">
        <Divider />
        <PreventiviRigheTable
          :preventivo-id="preventivoId"
          :is-modificabile="canEditRighe && !isReadonly" />

        <!-- Totali -->
        <div style="display: flex; justify-content: flex-end; gap: 1.5rem; padding: 0.75rem 0; font-size: 0.9rem;">
          <div><strong>{{ t('preventivi.totale_imponibile') }}:</strong> {{ formatCurrency(detail.totale_imponibile, { placeholder: '-' }) }}</div>
          <div><strong>{{ t('preventivi.totale_iva') }}:</strong> {{ formatCurrency(detail.totale_iva, { placeholder: '-' }) }}</div>
          <div><strong>{{ t('preventivi.totale_documento') }}:</strong> {{ formatCurrency(detail.totale_documento, { placeholder: '-' }) }}</div>
        </div>
      </template>

      <!-- Integrazione: visibile quando il backend conferma can_push_commessa.
           Se non ammessa ma con reason i18n-ready, mostriamo un Message hint. -->
      <template v-if="contentReady && isEdit && detail">
        <template v-if="canPushCommessa">
          <Divider />
          <PreventiviIntegrazione :preventivo-id="preventivoId" />
        </template>
        <Message v-else-if="pushCommessaReasonKey" severity="info" :closable="false"
          class="mt-1">
          {{ t(pushCommessaReasonKey) }}
        </Message>
      </template>

      <DrawerFooter v-if="canEditTestata && !isReadonly" :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
