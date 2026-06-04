<script setup>
// Scopo: Drawer crea/modifica ordine di vendita.
// CREATE: form testata con auto-save BOZZA al primo set di campi minimi
//   (cliente) → "edit-evolved" interno (createdId + hasDetail), poi righe inline.
// EDIT: testata + righe + componenti BoM + azioni stato (conferma, push commessa).
// Niente revisioni ne' listino in testata (a differenza di preventivi/offerte):
// state machine semplice DRAFT → CONFERMATO + push singolo a commessa.
import { ref, watch, computed, nextTick, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdiniStore } from '../stores/ordini'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useEmittenteFiscaleField } from '../../../core/composables/useEmittenteFiscaleField'
import { useUtilityDefaultId } from '../../../core/composables/useUtilityDefaultId'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { statoOrdineSeverity } from '../../../core/utils/severity'
import {
  STATO_ORDINE,
  STATI_ORDINE_ANTEPRIMA_PDF,
  STATI_ORDINE_CON_DOCUMENTO,
} from '../constants'
import EntityPdfButton from '../../../documenti/components/EntityPdfButton.vue'
import { SORGENTE_CODES } from '../../../documenti/constants'
import { displayDate, toDateString } from '../../../core/utils/date'
import { getOrdineFormDefaults } from '../../api/formDefaults'
import { createOrdine } from '../api/ordiniApi'
import { getBillingAccountLookupById } from '../../../core/apiCore'
import { DRAWER_WIDTH, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import OrdiniForm from './OrdiniForm.vue'
import OrdiniRigheTable from './OrdiniRigheTable.vue'
import OrdineNoteDrawer from './OrdineNoteDrawer.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

const { t } = useI18n()
const store = useOrdiniStore()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const { emitDataChanged } = useTabEvents()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  ordineId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
const noteDrawerVisible = ref(false)

// Auto-save bozza: in CREATE, appena il cliente (BA) e' valorizzato, il drawer
// crea l'ordine in BOZZA e si comporta da "edit-evolved" (righe + azioni stato).
const createdId = ref(null)
// Stato form riga inline: quando si edita/aggiunge una riga, il FormFooter
// testata si nasconde per non duplicare i bottoni di OrdiniRigaForm.
const formRigaAperto = ref(false)
const effectiveOrdineId = computed(() => createdId.value ?? props.ordineId)
const hasDetail = computed(() => detail.value !== null)

// Readonly cumulativo: prop esplicita OR readonly area iniettato dal parent OR
// stato post-DRAFT (modifiche libere solo in bozza). Il gate di stato e' su
// `hasDetail` (NON su `props.mode === 'edit'`): in CREATE "edit-evolved" (bozza
// auto-salvata) un'eventuale transizione che porti fuori DRAFT deve bloccare
// subito il form, anche se il drawer e' tecnicamente in mode='create'. Le
// azioni di stato (conferma/push) restano cliccabili in readonly grazie a
// `app-escape` applicato da DrawerActionsBar. Provide ai sub-componenti (righe).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_ORDINE.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Capability data-driven dal detail BE (get_ordine). Niente
// fn_available_actions_ordine: flag booleani semplici.
const canEditTestata = computed(() => !!detail.value?.can_edit_testata)
const canEditTestataEffective = computed(() => !isEdit.value || canEditTestata.value)
const canEditRighe = computed(() => !!detail.value?.can_edit_righe)

// Campi bloccati lato UX. Una volta che l'ordine esiste (EDIT classico o CREATE
// post auto-save), il cliente NON e' piu' modificabile: il BE deriva
// `soggetto_ruolo_id` dal billing_account solo in create (crea_ordine), mentre
// aggiorna_ordine cambierebbe `billing_account_id` SENZA ri-derivare il
// soggetto_ruolo → incoerenza cliente↔soggetto. Difesa FE allineata a
// PreventiviDrawer (che blocca billing_account_id post-create). Cambiare cliente
// = nuovo ordine, non una modifica della testata.
const nonEditableFields = computed(() => (hasDetail.value ? ['billing_account_id'] : []))
const canConferma = computed(() => !!detail.value?.can_conferma)
const canPushCommessa = computed(() => !!detail.value?.can_push_commessa)

// Default emittente fiscale: operatore → id profilo; admin globale → null
// (sceglie via EmittenteFiscaleField in modalita' Select).
const { defaultEmittenteId } = useEmittenteFiscaleField()

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata); il composable lo risolve all'id locale. Stesso
// pattern di PreventiviDrawer — proposto in CREATE all'apertura del drawer.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

// Deferimento contenuto: i LookupSelect/AutoComplete montano dopo l'animazione
// di apertura (pattern feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    // Utility default dal parameter DEFAULT_UTILITY (come preventivi/contratti).
    utility_id: utilityDefaultId.value ?? null,
    billing_account_id: null,
    // _obj per BillingAccountLookup (pattern restore lookup ricco,
    // memoria feedback_autocomplete_restore).
    billing_account_obj: null,
    valuta_id: null,
    modalita_pagamento_id: null,
    termine_pagamento_id: null,
    fatturazione_trigger: null,
    data: new Date(),
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
  createdId.value = null
}

async function loadDetail(id = null) {
  const targetId = id ?? effectiveOrdineId.value
  if (!targetId) return
  const data = await loadDetailOrClose(() => store.fetchDetail(targetId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    utility_id: data.utility_id ?? null,
    billing_account_id: data.billing_account_id ?? null,
    billing_account_obj: null,  // popolato sotto via getBillingAccountLookupById
    valuta_id: data.valuta_id ?? null,
    modalita_pagamento_id: data.modalita_pagamento_id ?? null,
    termine_pagamento_id: data.termine_pagamento_id ?? null,
    fatturazione_trigger: data.fatturazione_trigger ?? null,
    data: data.data ? new Date(data.data + 'T00:00:00') : null,
  }
  await nextTick()
  // Restore BillingAccountLookup _obj per visualizzazione ricca. Best-effort.
  if (data.billing_account_id) {
    try {
      const res = await getBillingAccountLookupById(data.billing_account_id)
      const ba = res?.data?.data
      if (ba) form.value.billing_account_obj = ba
    } catch {
      // Resto: l'autocomplete parte vuoto, l'operatore puo' ri-selezionare.
    }
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    // CREATE: risolve la utility di default (parameter DEFAULT_UTILITY) PRIMA di
    // resetForm, così defaultForm() la legge. Poi pre-popola la valuta dalla
    // catena EF (resolve_valuta_default lato BE), come preventivi/offerte.
    await loadUtilityDefault()
    resetForm()
    try {
      const res = await getOrdineFormDefaults(null)
      const data = res?.data?.data
      if (data && form.value.valuta_id == null && data.valuta_id != null) {
        form.value.valuta_id = data.valuta_id
      }
    } catch {
      // Best-effort: se l'API e' giu' il drawer si apre comunque (valuta vuota).
    }
  }
})

// Scopo: applica al form i default derivati dall'anagrafica del cliente (BA):
//        valuta (BA-wins, override), modalita/termine pagamento (solo se vuoti,
//        non si calpesta una scelta dell'operatore). Best-effort. Stessa catena
//        dei preventivi (vendite_form_defaults_service + get_cliente_defaults).
async function applyBaDefaults(baId) {
  if (!baId) return
  try {
    const res = await getOrdineFormDefaults(baId)
    const d = res?.data?.data
    if (!d) return
    const f = form.value
    if (d.valuta_id != null) f.valuta_id = d.valuta_id
    if (f.modalita_pagamento_id == null && d.modalita_pagamento_id != null) {
      f.modalita_pagamento_id = d.modalita_pagamento_id
    }
    if (f.termine_pagamento_id == null && d.termine_pagamento_id != null) {
      f.termine_pagamento_id = d.termine_pagamento_id
    }
  } catch {
    // Best-effort: se l'API e' giu' la bozza si crea senza i default cliente.
  }
}

// Auto-save bozza in CREATE quando il cliente (BA) e' valorizzato. Il BE deriva
// soggetto_ruolo_id dal billing_account. Pattern master-detail inline. Prima di
// creare applica i default da anagrafica cliente (valuta/modalita/termine) cosi'
// vengono persistiti nella bozza (e ricaricati coerentemente da loadDetail).
async function autoSaveBozza() {
  await applyBaDefaults(form.value.billing_account_id)
  const f = form.value
  const payload = {
    billing_account_id: f.billing_account_id || null,
    utility_id: f.utility_id || null,
    // Opzionale per BE: se omesso (operatore) il trigger DB lo deriva da GUC.
    // Per admin globale serve esplicito.
    emittente_fiscale_id: f.emittente_fiscale_id || null,
    valuta_id: f.valuta_id || null,
    modalita_pagamento_id: f.modalita_pagamento_id || null,
    termine_pagamento_id: f.termine_pagamento_id || null,
    fatturazione_trigger: f.fatturazione_trigger || null,
    data: f.data ? toDateString(f.data) : null,
  }
  // execute fa l'unwrap dell'envelope axios: chiamare la fn axios diretta
  // (NON store.create che ritorna gia' unwrappato — feedback_useapihandler_solo_axios).
  const result = await execute(
    () => createOrdine(payload),
    { successMessage: t('vendite.ordini.bozza_creata') }
  )
  if (result && result.id) {
    createdId.value = result.id
    emitDataChanged(TAB_ENTITIES.ORDINE, result.id)
    await loadDetail(result.id)
  }
}

watch(
  () => form.value.billing_account_id,
  async (baId) => {
    if (isEdit.value) return
    if (createdId.value !== null) return
    if (baId == null) return
    if (!contentReady.value) return
    if (loading.value) return
    await autoSaveBozza()
  },
)

const canSave = computed(() => {
  if (isReadonly.value) return false
  return form.value.billing_account_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value || createdId.value !== null) {
    // UPDATE testata (DRAFT). emittente_fiscale_id NON e' aggiornabile (whitelist
    // BE _UPDATE_KEYS_ORDINE). Inviamo la whitelist: il BE normalizza empty→NULL.
    const payload = {
      billing_account_id: f.billing_account_id ?? null,
      utility_id: f.utility_id ?? null,
      valuta_id: f.valuta_id ?? null,
      modalita_pagamento_id: f.modalita_pagamento_id ?? null,
      termine_pagamento_id: f.termine_pagamento_id ?? null,
      fatturazione_trigger: f.fatturazione_trigger ?? null,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.update(effectiveOrdineId.value, payload),
      { successMessage: t('vendite.ordini.ordine_salvato') }
    )
    if (result !== null) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    // Fallback CREATE manuale (auto-save non scattato): chiude dopo create.
    const payload = {
      billing_account_id: f.billing_account_id || null,
      utility_id: f.utility_id || null,
      emittente_fiscale_id: f.emittente_fiscale_id || null,
      valuta_id: f.valuta_id || null,
      modalita_pagamento_id: f.modalita_pagamento_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      fatturazione_trigger: f.fatturazione_trigger || null,
      data: f.data ? toDateString(f.data) : null,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('vendite.ordini.ordine_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// --- Chiusura con guard bozza orfana ---

const hasOrphanedDraft = computed(() => {
  if (createdId.value === null) return false
  return (detail.value?.righe_count ?? 0) === 0
})

function close() {
  attemptClose()
}

function attemptClose() {
  if (!hasOrphanedDraft.value) {
    emit('update:visible', false)
    emit('cancelled')
    return
  }
  confirmAction({
    title: t('vendite.ordini.abbandono_bozza_titolo'),
    message: t('vendite.ordini.conferma_abbandono_bozza'),
    acceptLabel: t('vendite.ordini.abbandono_bozza_conferma'),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => store.elimina(createdId.value),
        { successMessage: t('vendite.ordini.bozza_eliminata') }
      )
      if (result !== null) {
        emit('update:visible', false)
        emit('cancelled')
      }
    },
  })
}

function onVisibleChange(v) {
  if (v) {
    emit('update:visible', true)
    return
  }
  attemptClose()
}

// --- Azioni stato ---

function onConferma() {
  confirmAction({
    message: t('vendite.ordini.conferma_ordine_messaggio'),
    onAccept: async () => {
      const result = await execute(
        () => store.conferma(effectiveOrdineId.value),
        { successMessage: t('vendite.ordini.ordine_confermato') }
      )
      if (result !== null) {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Push singolo a commessa. Toast differenziato per `report.stato` (l'orchestrator
// risponde 200 anche con esito PARZIALE/ERRORE per riga — gemello preventivi).
function onPush() {
  confirmAction({
    message: t('vendite.ordini.push_commessa_messaggio'),
    onAccept: async () => {
      const result = await execute(() => store.push(effectiveOrdineId.value))
      if (result === null) return  // errore HTTP gia' gestito da useApiHandler

      const stato = result?.stato
      const pushLogId = result?.push_log_id
      const righe = result?.handlers?.reduce(
        (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
        0,
      ) ?? result?.righe_pushable ?? 0

      if (stato === 'COMPLETATO') {
        notify.success(t('vendite.ordini.push_commessa_ok', { righe, push_log_id: pushLogId }))
      } else if (stato === 'PARZIALE') {
        notify.warn(t('vendite.ordini.push_commessa_parziale', { righe, push_log_id: pushLogId }))
      } else if (stato === 'ERRORE') {
        const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.generic_error')
        notify.error(t('vendite.ordini.push_commessa_errore', { primo_errore: firstError }))
      } else if (stato === 'SKIPPED') {
        notify.warn(t('vendite.ordini.push_commessa_skipped'))
      } else {
        notify.success(t('vendite.ordini.push_commessa_ok_generico'))
      }

      if (stato === 'COMPLETATO' || stato === 'PARZIALE') {
        await loadDetail()
        emit('saved', result)
      }
    },
  })
}

// Azioni del drawer ordine consumate da DrawerActionsBar. Build manuale dai
// flag capability (no fn_available_actions_ordine). In readonly puro (LETTURA /
// split) le transizioni vengono nascoste; il BE resta come difesa.
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const list = []
  const readonlyPuro = props.readonly || parentReadonly.value
  if (!readonlyPuro && canConferma.value) {
    list.push({
      key: 'conferma',
      kind: 'state',
      label: t('vendite.ordini.azione_conferma'),
      icon: MANAGE_ICONS.CONFIRM,
      severity: 'success',
      command: onConferma,
    })
  }
  if (!readonlyPuro && canPushCommessa.value) {
    list.push({
      key: 'push',
      kind: 'state',
      label: t('vendite.ordini.azione_push_commessa'),
      icon: MANAGE_ICONS.SEND,
      severity: 'info',
      command: onPush,
    })
  }
  list.push({
    key: 'manage-note',
    kind: 'manage',
    label: t('vendite.ordini.gestisci_note'),
    icon: MANAGE_ICONS.NOTE,
    command: () => { noteDrawerVisible.value = true },
  })
  return list
})
</script>

<template>
  <Drawer :visible="visible" @update:visible="onVisibleChange"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE_PLUS }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('vendite.ordini.ordine')"
        :icon="NAV_ICONS.ORDINI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info: visibile in EDIT classico e in CREATE post auto-save. -->
      <template v-if="hasDetail">
        <DrawerEntityHeader>
          <Tag :value="detail.numero" severity="secondary" />
          <span v-if="detail.data" class="app-drawer-header-muted font-bold">
            {{ displayDate(detail.data) }}
          </span>
          <!-- Provenienza upstream (A1): chip read-only quando l'ordine nasce da
               un preventivo/offerta. Lo scheletro non valorizza queste colonne
               (le usera' la conversione upstream), ma il drawer le mostra. -->
          <Tag
            v-if="detail.documento_origine_tipo"
            :value="t('vendite.ordini.origine_chip', {
              tipo: detail.documento_origine_tipo,
              codice: detail.documento_origine_codice || detail.documento_origine_id,
            })"
            severity="info"
            icon="pi pi-link"
            v-tooltip.bottom="t('vendite.ordini.origine_chip_tooltip')"
          />

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoOrdineSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions">
          <template #suffix>
            <!-- Stampa conferma d'ordine: anteprima PDF on-demand
                 (ristampabile, §12.4(a)). BB EntityPdfButton riusato 1:1. -->
            <EntityPdfButton
              :sorgente-code="SORGENTE_CODES.ORDINE_VENDITA"
              :entity-id="effectiveOrdineId"
              :stato-codice="detail.stato_codice_interno"
              :stati-preview="STATI_ORDINE_ANTEPRIMA_PDF"
              :stati-con-documento="STATI_ORDINE_CON_DOCUMENTO"
              i18n-prefix="vendite.ordini.pdf"
              :dialog-title="detail.numero
                ? t('vendite.ordini.pdf.dialog_title', { numero: detail.numero })
                : ''"
            />
          </template>
        </DrawerActionsBar>
      </template>

      <Divider v-if="hasDetail" />

      <!-- Form testata: monta dopo l'animazione drawer per evitare rimbalzo lookup. -->
      <OrdiniForm v-if="contentReady"
        :form="form" :is-modificabile="canEditTestataEffective && !isReadonly"
        :non-editable-fields="nonEditableFields"
        :is-edit="isEdit || createdId !== null"
        :record="detail" />

      <!-- Righe: visibili appena c'e' detail (EDIT classico o CREATE post auto-save). -->
      <template v-if="contentReady && hasDetail">
        <Divider />
        <OrdiniRigheTable
          :ordine-id="effectiveOrdineId"
          :is-modificabile="canEditRighe && !isReadonly"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />
      </template>

      <FormFooter v-if="canEditTestataEffective && !isReadonly && !formRigaAperto"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="close" />
    </div>
  </Drawer>

  <!-- Sub-drawer note: cablato sull'id effettivo dell'ordine. -->
  <OrdineNoteDrawer
    v-if="effectiveOrdineId"
    v-model:visible="noteDrawerVisible"
    :ordine-id="effectiveOrdineId"
  />
</template>
