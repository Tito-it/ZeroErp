<script setup>
// Scopo: Drawer del reso di vendita (SOLO edit: il reso nasce dal pannello
// "crea reso" nel drawer DDT, mai standalone). Testata quasi tutta display
// (ereditata dal DDT sorgente), righe master-detail (solo DRAFT), azioni
// data-driven dalla matrice (conferma/annulla → endpoint DEDICATI: le fn
// madri DB applicano gli effetti — residuo, proiezione stato ordine, flip
// DDT), pannello ri-spedizione post-conferma. Clone ridotto di DdtDrawer:
// niente PDF/note/indirizzi/riepilogo IVA/push/autosave-bozza.
import { ref, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

import { useResiStore } from '../stores/resi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useDrawerContentReady } from '../../../core/composables/useDrawerContentReady'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { statoResoSeverity } from '../../../core/utils/severity'
import { displayDate, toDateString } from '../../../core/utils/date'
import { DRAWER_WIDTH } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import FormFooter from '../../../core/components/FormFooter.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import { STATO_RESO } from '../constants'
import ResoForm from './ResoForm.vue'
import ResoRigheTable from './ResoRigheTable.vue'
import ResoRiconsegnaPanel from './ResoRiconsegnaPanel.vue'

const { t } = useI18n()
const store = useResiStore()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  resoId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const form = ref({})
const detail = ref(null)
// Stato form riga inline: quando si edita/aggiunge una riga, il FormFooter
// testata si nasconde per non duplicare i bottoni di ResoRigaForm.
const formRigaAperto = ref(false)
const hasDetail = computed(() => detail.value !== null)
const isConfermato = computed(
  () => detail.value?.stato_codice_interno === STATO_RESO.CONFERMATO,
)

// Readonly cumulativo: prop esplicita OR readonly area iniettato OR stato
// post-DRAFT (modifiche libere solo in bozza). Le azioni di stato restano
// cliccabili in readonly grazie ad `app-escape` di DrawerActionsBar.
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => props.readonly
    || parentReadonly.value
    || (detail.value !== null
        && detail.value.stato_codice_interno !== STATO_RESO.DRAFT),
)
provide(READONLY_KEY, isReadonly)

// Capability data-driven dal detail BE (script.fn_available_actions_reso):
// availableActions (conferma/annulla dalla matrice) + can_edit_testata/righe.
const caps = useEntityCapabilities(detail, { editFlag: 'can_edit_testata' })
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
const canEditRighe = computed(() => caps.flag('can_edit_righe'))

// Deferimento contenuto: monta dopo l'animazione drawer (pattern
// feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const righeTableRef = ref(null)

function resetForm() {
  form.value = { emittente_fiscale_id: null, data: null }
  detail.value = null
}

async function loadDetail() {
  if (!props.resoId) return
  const data = await loadDetailOrClose(() => store.fetchDetail(props.resoId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    data: data.data ? new Date(data.data + 'T00:00:00') : null,
  }
}

watch(() => props.visible, (v) => {
  if (!v) return
  resetForm()
  loadDetail()
})

const canSave = computed(
  () => !isReadonly.value && canEditTestata.value && form.value.data != null,
)

// Scopo: salva la testata (solo `data`: il resto e' ereditato/immutabile).
async function handleSave() {
  const result = await execute(
    () => store.update(props.resoId, { data: toDateString(form.value.data) }),
    { successMessage: t('vendite.resi.reso_salvato') },
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// --- Azioni di dominio (dispatch per action.key) ---

// Mappa ESPLICITA action_key → runner/toast. Conferma e annullo non passano
// da un cambio stato generico: gli endpoint dedicati invocano le fn madri DB
// (numero, residuo, proiezioni, flip DDT). Un'azione futura della matrice
// (es. slice nota di credito) NON deve degradare su un runner sbagliato:
// chiave ignota → warn parlante, nessuna chiamata.
const _AZIONI = {
  conferma: { run: (id) => store.conferma(id), successKey: 'vendite.resi.reso_confermato' },
  annulla: { run: (id) => store.annulla(id), successKey: 'vendite.resi.reso_annullato' },
}

async function eseguiAzione(action) {
  const azione = _AZIONI[action.key]
  if (!azione) {
    notify.warn(t('vendite.resi.azione_non_gestita', { azione: action.key }))
    return
  }
  const result = await execute(
    () => azione.run(props.resoId),
    { successMessage: t(azione.successKey) },
  )
  if (result !== null) {
    await loadDetail()
    righeTableRef.value?.loadRighe()
    emit('saved', result)
  }
}

// Smista le azioni data-driven (`available_actions`, matrice reso). Le due
// azioni note (conferma/annulla) hanno `requires_confirm` nel seed.
function onAction(action) {
  if (action.requires_confirm) {
    confirmAction({
      message: t('vendite.resi.conferma_cambio_stato', { stato: t(action.label_key) }),
      onAccept: () => eseguiAzione(action),
    })
  } else {
    eseguiAzione(action)
  }
}

// Azioni del drawer consumate da DrawerActionsBar (data-driven dalla
// matrice; in readonly puro sono nascoste).
const drawerActions = computed(() => {
  if (!hasDetail.value) return []
  const readonlyPuro = props.readonly || parentReadonly.value
  return mapAvailableActionsToDrawerActions({
    availableActions: availableActions.value,
    t,
    onAction,
    readonly: readonlyPuro,
  })
})

// Scopo: post ri-spedizione — il flip/stati possono essere cambiati: reload.
async function onRiconsegnaGenerata() {
  await loadDetail()
  righeTableRef.value?.loadRighe()
  emit('saved', {})
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="(v) => { if (!v) onClose() }"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE_PLUS }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="t('common.edit')"
        :title="t('vendite.resi.reso')"
        :icon="NAV_ICONS.RESI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <template v-if="hasDetail">
        <DrawerEntityHeader>
          <!-- Numero: "—" finche' il reso e' in DRAFT (assegnato a CONFERMATO). -->
          <Tag :value="detail.numero || '—'" severity="secondary" />
          <span v-if="detail.data" class="app-drawer-header-muted font-bold">
            {{ displayDate(detail.data) }}
          </span>
          <!-- Provenienza: chip read-only del DDT sorgente. -->
          <Tag
            v-if="detail.ddt_origine_numero"
            :value="t('vendite.resi.origine_chip', { numero: detail.ddt_origine_numero })"
            severity="info"
            icon="pi pi-link"
            v-tooltip.bottom="t('vendite.resi.origine_chip_tooltip')"
          />

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoResoSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions" />
      </template>

      <Divider v-if="hasDetail" />

      <!-- Form testata (data editabile in DRAFT, resto display). -->
      <ResoForm v-if="contentReady && hasDetail"
        :form="form"
        :is-modificabile="canEditTestata && !isReadonly"
        :record="detail" />

      <template v-if="contentReady && hasDetail">
        <Divider />
        <ResoRigheTable
          ref="righeTableRef"
          :reso-id="props.resoId"
          :ddt-origine-id="detail?.ddt_origine_id ?? null"
          :is-modificabile="canEditRighe && !isReadonly"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />

        <!-- Ri-spedizione: solo post-conferma (il pannello si auto-svuota a
             copertura completa; per i resi solo-credito non compare). In
             CONFERMATO il contenuto e' `app-readonly` (lock-di-stato) ma la
             ri-spedizione e' un'azione di processo legittima → `app-escape`
             la mantiene cliccabile (mirror pannello evasione ordini). In
             readonly PURO il pannello e' consuntivo (niente azioni). -->
        <template v-if="isConfermato">
          <Divider />
          <div class="app-escape">
            <ResoRiconsegnaPanel
              :reso-id="props.resoId"
              :readonly="props.readonly || parentReadonly"
              @generato="onRiconsegnaGenerata" />
          </div>
        </template>
      </template>

      <FormFooter v-if="canEditTestata && !isReadonly && !formRigaAperto"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="onClose" />
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>
