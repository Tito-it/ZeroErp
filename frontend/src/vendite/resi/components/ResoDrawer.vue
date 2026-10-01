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
import { useDrawerFormPreserve, gestoreVisibile } from '../../../core/composables/useDrawerFormPreserve'
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
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import { STATO_RESO } from '../constants'
import ResoForm from './ResoForm.vue'
import ResoRigheTable from './ResoRigheTable.vue'
import ResoRiconsegnaDialog from './dialogs/ResoRiconsegnaDialog.vue'

const { t, te } = useI18n()
const store = useResiStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  resoId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved', 'changed', 'cancelled'])
const onClose = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)

const form = ref({})
// Modifiche non salvate: fotografia a ogni caricamento del dettaglio,
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { preserva, fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const chiudi = () => chiudiConConferma(onClose)
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
// Readonly PURO: permessi soltanto, senza il lock-di-stato. Lo consumano le
// dialog di processo lanciate dal drawer, che devono restare operabili su un
// documento post-DRAFT — che per loro e' il caso normale, non l'eccezione.
const isReadonlyPuro = computed(() => props.readonly || parentReadonly.value)
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
const capabilities = caps.capabilities
const availableActions = caps.availableActions
const canEditTestata = caps.canEdit
const canEditRighe = computed(() => caps.flag('can_edit_righe'))

// Deferimento contenuto: monta dopo l'animazione drawer (pattern
// feedback_content_ready_after_show).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const righeTableRef = ref(null)
// Ref alla barra collegamenti (chip pratica/origine/destinazioni).
const collegamentiRef = ref(null)
// Dialog "DDT ri-spedizione": aperta dal pulsante in barra azioni (2026-07-25).
// Era un pannello in coda al contenuto del drawer — le azioni di processo
// stanno in alto, come «Genera reso» del DDT e «Genera DDT» dell'ordine.
const riconsegnaDialogVisible = ref(false)

function resetForm() {
  form.value = { emittente_fiscale_id: null, data: null }
  detail.value = null
}

async function loadDetail() {
  if (!props.resoId) return
  // `preserva`: salvare una riga o cambiare stato ricarica la testata, e senza
  // la modifica di testata non ancora salvata tornava com'era, in silenzio
  // (stesso difetto gia' corretto su ordini/DDT/preventivi, 2026-09-26).
  const applica = preserva()
  const data = await loadDetailOrClose(() => store.fetchDetail(props.resoId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    data: data.data ? new Date(data.data + 'T00:00:00') : null,
  }
  applica()
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
    // Salvato: fotografia PRIMA della ricarica, o `preserva` riprenderebbe
    // la data appena salvata per una modifica pendente.
    fissa()
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

// Scopo: il nome dello STATO di destinazione per la frase di conferma («Portare
//   il documento nello stato {stato}?»). La descrizione leggibile la sa solo il
//   database (`DRAFT` -> «Bozza», `ALLOCATO` -> «Allocato a magazzino»: non e'
//   derivabile dal codice), quindi arriva dalla capability come
//   `target_state_descrizione`. Finche' il DB non la espone si ripiega sulla
//   label dell'azione — comportamento invariato, nessun testo mancante.
function statoDestinazione(action) {
  return action.target_state_descrizione || t(action.label_key)
}

function onAction(action) {
  if (action.requires_confirm) {
    confirmAction({
      header: t('confirm.cambio_stato_title'),
      message: t('vendite.resi.conferma_cambio_stato', { stato: statoDestinazione(action) }),
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
  const stateActions = mapAvailableActionsToDrawerActions({
    availableActions: availableActions.value,
    t,
    te,
    onAction,
    readonly: readonlyPuro,
  })
  return [
    ...stateActions,
    // DDT ri-spedizione: apre la dialog dedicata (righe con copertura ancora
    // pendente). Solo post-conferma; per i resi solo-credito la dialog si
    // presenta vuota e in sola chiusura (nessuna riga riapre_residuo).
    ...(isConfermato.value
      ? [{
          key: 'ddt-rispedizione',
          kind: 'manage',
          label: t('vendite.resi.riconsegna_azione'),
          icon: NAV_ICONS.DDT,
          command: () => { riconsegnaDialogVisible.value = true },
        }]
      : []),
  ]
})

// Scopo: la copertura ri-consegna e' cambiata (DDT generato, quota resa
//        definitiva o rinuncia riaperta): in tutti e tre i casi stato reso,
//        righe e collegamenti possono essere diversi — reload di tutti e tre.
async function onCoperturaRiconsegnaCambiata() {
  await loadDetail()
  righeTableRef.value?.loadRighe()
  collegamentiRef.value?.reload()
  // ⭐ Era `emit('saved', {})`, e la lista si aggiornava — ma il drawer si
  // CHIUDEVA: una ri-spedizione parziale lascia il resto in coda, quindi
  // l'operatore era ancora dentro a lavorare. `changed` ricarica e lascia
  // aperto. Difetto gemello di quello degli ordini, con il segno opposto.
  emit('changed')
}
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer :visible="visible" @update:visible="suVisibile"
    @after-show="onAfterShow"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE_PLUS }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :modificato="modificato"
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
          <!-- La provenienza (DDT sorgente) NON e' piu' un chip d'header
               dedicato: e' assorbita dai chip di DocumentoCollegamentiBar sotto
               la barra azioni, dove sta l'origine di TUTTI i domini (2026-07-25). -->

          <template #status>
            <Tag
              :value="detail.stato_descrizione"
              :severity="statoResoSeverity(detail.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <DrawerActionsBar :actions="drawerActions" :info-key="capabilities.stato_info_key || ''" />

        <!-- Collegamenti diretti: per il reso la catena significativa e'
             l'ORIGINE (reso <- DDT <- ordine), qui riassunta nei chip; il
             grafo completo si apre dai chip in dialog. -->
        <DocumentoCollegamentiBar
          ref="collegamentiRef"
          v-if="props.resoId"
          base-path="/vendite/resi"
          :doc-id="props.resoId"
          :readonly="readonly || parentReadonly" />
      </template>

      <Divider v-if="hasDetail" />

      <!-- Form testata (data editabile in DRAFT, resto display). -->
      <ResoForm
        :campi-errati="campiErrati" v-if="contentReady && hasDetail"
        :form="form"
        :is-modificabile="canEditTestata && !isReadonly"
        :record="detail" />

      <template v-if="contentReady && hasDetail">
        <Divider />
        <ResoRigheTable
          ref="righeTableRef"
          :reso-id="props.resoId"
          :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
          :ddt-origine-id="detail?.ddt_origine_id ?? null"
          :is-modificabile="canEditRighe && !isReadonly"
          :readonly="isReadonlyPuro"
          @changed="loadDetail()"
          @form-aperto="(v) => { formRigaAperto = v }" />

      </template>

      <FormFooter v-if="canEditTestata && !isReadonly && !formRigaAperto"
        :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="chiudi" />
      <FormFooter v-else-if="hasDetail && !formRigaAperto" close-only @cancel="chiudi" />
    </div>
  </Drawer>

  <!-- Dialog "DDT ri-spedizione": righe reso con copertura ancora pendente.
       Il DDT nasce DRAFT e si rifinisce dal tab DDT; una ri-spedizione parziale
       lascia il resto in coda (la riga resta con `qta_residua` ridotta).
       `readonly` = quello PURO del chiamante: il lock di stato del drawer
       (CONFERMATO) non deve disabilitare un'azione legittima in quello stato. -->
  <ResoRiconsegnaDialog
    v-if="props.resoId && isConfermato"
    v-model:visible="riconsegnaDialogVisible"
    :reso-id="props.resoId"
    :readonly="props.readonly || parentReadonly"
    @aggiornato="onCoperturaRiconsegnaCambiata"
  />
</template>
