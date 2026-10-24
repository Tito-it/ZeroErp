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
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'

import { useResiStore } from '../stores/resi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useNotify } from '../../../core/composables/useNotify'
import { useInjectReadonly, READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../../core/composables/useDrawerClose'
import { useDrawerFormPreserve } from '../../../core/composables/useDrawerFormPreserve'
import { useDrawerDetailLoad } from '../../../core/composables/useDrawerDetailLoad'
import { useEntityCapabilities } from '../../../core/composables/useEntityCapabilities'
import { useTestataDocumento } from '../../../core/composables/useTestataDocumento'
import { mapAvailableActionsToDrawerActions } from '../../../core/composables/useDrawerActions'
import { useRigheDocumento } from '../../../core/composables/useRigheDocumento'
import { statoResoSeverity } from '../../../core/utils/severity'
import { displayDate, toDateString, parseIsoDate } from '../../../core/utils/date'
import { DRAWER_WIDTH } from '../../../core/constants'
import { NAV_ICONS } from '../../../core/navigation'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../../core/components/DrawerActionsBar.vue'
import DocumentoCollegamentiBar from '../../_shared/lineage/DocumentoCollegamentiBar.vue'
import { CAMPI_FORM_TESTATA_RESO, STATO_RESO } from '../constants'
import ResoForm from './ResoForm.vue'
import ResoRigheTable from './ResoRigheTable.vue'
import ResoRientriSection from './ResoRientriSection.vue'
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
const detail = ref(null)
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
const canEditRighe = computed(() => caps.flag('can_edit_righe'))
// La testata dopo la bozza: quali campi del form si cambiano, dalla capability
// (brief-db-testata-dopo-emissione, R-FE-3). Il form del reso mostra data e
// magazzino di rientro, fermi fuori bozza: lo dice la capability, non lo stato.
const testata = useTestataDocumento({
  caps,
  campi: CAMPI_FORM_TESTATA_RESO,
  readonlyPuro: () => isReadonlyPuro.value,
  // Il reso non si crea da qui: con un id il documento esiste anche prima che
  // arrivi il dettaglio, e la capability ancora vuota tiene il form fermo.
  presente: () => props.resoId !== null || hasDetail.value,
  corpoProtetto: () => isReadonly.value,
})

// ⭐ D-13 (2026-10-03, analisi-fe-chrome-drawer): testata E riga aperta, una
//    domanda sola all'uscita. La fotografia della riga la tiene il suo form.
// Tabella-righe, fotografia unita (testata + riga aperta) e footer secondo lo
// stato: il legame e' del BB `useRigheDocumento` (regola del 2).
const { righeTableRef, onFormAperto, documento, footerDrawer } = useRigheDocumento({
  testata: { modificato, chiudiConConferma },
  modificabile: () => testata.modificabile.value,
  presente: () => hasDetail.value,
})
const modificatoDocumento = documento.modificato
// Scopo: si e' chiuso un documento aperto dalla barra collegamenti (passaggi
//        lineage): li' l'operatore puo' aver agito — annullare il DDT di un
//        ordine riapre il residuo e riaccende «Genera DDT» — quindi si
//        rileggono testata (stato, capability), righe. I chip li rilegge la
//        barra da se'. Le liste in ascolto le ha gia' avvisate lo store del
//        verbo, nel drawer impilato.
async function onDocumentoCollegatoChiuso() {
  await loadDetail()
  righeTableRef.value?.loadRighe()
}
// Dialog "DDT ri-spedizione": aperta dal pulsante in barra azioni (2026-07-25).
// Era un pannello in coda al contenuto del drawer — le azioni di processo
// stanno in alto, come «Genera reso» del DDT e «Genera DDT» dell'ordine.
const riconsegnaDialogVisible = ref(false)

// Rientri: la sezione e' montata col dettaglio e alla prima apertura legge da
// se'; dopo, la rilegge `loadDetail` (righe e magazzino cambiano le voci).
const rientriRef = ref(null)

function resetForm() {
  form.value = { emittente_fiscale_id: null, data: null, magazzino_id: null }
  detail.value = null
}

async function loadDetail() {
  if (!props.resoId) return
  // `preserva`: salvare una riga o cambiare stato ricarica la testata, e senza
  // la modifica di testata non ancora salvata tornava com'era, in silenzio
  // (stesso difetto gia' corretto su ordini/DDT/preventivi, 2026-09-26).
  const applica = preserva()
  // Come i prelievi della bolla: la sezione rientri si rilegge solo se c'era
  // gia' (alla prima apertura legge da se').
  const rientriGiaMontati = rientriRef.value != null
  const data = await loadDetailOrClose(() => store.fetchDetail(props.resoId))
  if (!data) return
  detail.value = data
  form.value = {
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    data: parseIsoDate(data.data),
    magazzino_id: data.magazzino_id ?? null,
  }
  applica()
  if (rientriGiaMontati) rientriRef.value?.carica()
}

watch(() => props.visible, (v) => {
  if (!v) return
  resetForm()
  loadDetail()
})

const canSave = computed(
  () => testata.modificabile.value && form.value.data != null,
)

// Scopo: salva la testata (data e magazzino di rientro: il resto e'
//        ereditato/immutabile; le regole del magazzino le applica il DB).
async function handleSave() {
  const result = await execute(
    () => store.update(props.resoId, {
      data: toDateString(form.value.data),
      magazzino_id: form.value.magazzino_id || null,
    }),
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
  // ⭐ Era `emit('saved', {})`, e la lista si aggiornava — ma il drawer si
  // CHIUDEVA: una ri-spedizione parziale lascia il resto in coda, quindi
  // l'operatore era ancora dentro a lavorare. `changed` ricarica e lascia
  // aperto. Difetto gemello di quello degli ordini, con il segno opposto.
  emit('changed')
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.resi.reso')"
    :icon="NAV_ICONS.RESI"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :modificato="modificatoDocumento"
    :conferma-uscita="documento.chiudiConConferma"
    :footer="footerDrawer"
    :footer-readonly="testata.footerReadonly.value"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >

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
        v-if="props.resoId"
        base-path="/vendite/resi"
        :versione="detail"
        :doc-id="props.resoId"
        @documento-chiuso="onDocumentoCollegatoChiuso"
        :readonly="readonly || parentReadonly" />
    </template>

    <Divider v-if="hasDetail" />

    <!-- Form testata (data editabile in DRAFT, resto display). -->
    <div v-if="hasDetail" :class="{ 'app-escape': testata.sopraCorpoProtetto.value }">
      <ResoForm
        :campi-errati="campiErrati"
        :form="form"
        :is-modificabile="testata.modificabile.value"
        :non-editable-fields="testata.campiBloccati.value"
        :record="detail" />
    </div>

    <template v-if="hasDetail">
      <Divider />
      <ResoRigheTable
        ref="righeTableRef"
        :reso-id="props.resoId"
        :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
        :ddt-origine-id="detail?.ddt_origine_id ?? null"
        :is-modificabile="canEditRighe && !isReadonly"
        :readonly="isReadonlyPuro"
        @changed="loadDetail()"
        @form-aperto="onFormAperto" />

      <!-- Rientri (3-bis R-1b): dove rientra la merce. Compare solo se il reso
           fa rientrare merce; si scrivono solo in bozza (decide il DB). -->
      <ResoRientriSection
        ref="rientriRef"
        :reso-id="props.resoId"
        :modificabile="canEditRighe && !isReadonly"
        @changed="loadDetail()" />

    </template>
  </AppDrawer>

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
