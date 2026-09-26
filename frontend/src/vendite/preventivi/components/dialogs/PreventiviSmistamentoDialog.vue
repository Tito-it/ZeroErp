<script setup>
// Scopo: Dialog Smistamento del preventivo — vista unica riga-per-riga dei
// due rami di smistamento (merce → ordine, servizi → fatturazione via
// commessa) con selezione multipla e azione unica "Smista selezionate": il
// routing per destinazione e' deciso dalla natura di riga (D3, nessuna scelta
// operatore). Mostra il progress verso EVASO (X/Y smistate). Sostituisce
// PreventiviIntegrazione + GeneraOrdineDialog (2026-06-12,
// brief-db-smistamento-preventivi.md §6). Fonte dati: GET /smistamento/
// (vw_preventivi_smistamento + _righe, stato autorevole). La sezione
// "Pratiche collegate" e' stata rimossa 2026-07-15: la pratica vive nei
// collegamenti del documento (chip «Pratica» di DocumentoCollegamentiBar, che
// apre il PraticaDrawer).
//
// Aperta dal pulsante «Smistamento» nella barra azioni del drawer preventivo
// (2026-07-25, decisione Tid): le azioni stanno in alto, non in coda al
// contenuto. Era un pannello sempre montato che allungava il drawer e faceva
// la fetch dello smistamento anche a chi non stava smistando nulla; ora le
// righe si caricano all'APERTURA (lazy) e a ogni riapertura (freschezza).
// Stesso pattern di DdtResoDialog.
//
// `consuntivo`: dialog in sola lettura — niente selezione ne' azioni. Usato in
// readonly puro (permesso LETTURA / revisione superseded). NB: sul percorso
// pratica il dialog resta INTERATTIVO (lo smistamento e' l'attivita' dello
// step), come nello standalone.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../../core/composables/useConfirmAction'
import { useNotify } from '../../../../core/composables/useNotify'
import { usePreventiviStore } from '../../stores/preventivi'
import { DESTINAZIONE_SMISTAMENTO, STATO_SMISTAMENTO } from '../../../constants'
import { formatNumber } from '../../../../core/utils/format'
import { useSelezioneToggle } from '../../../../core/composables/useSelezioneToggle'
import AppDialog from '../../../../core/components/AppDialog.vue'
import Tag from 'primevue/tag'
import Checkbox from 'primevue/checkbox'
// DataTable grezza: sono le RIGHE del preventivo col loro stato di smistamento
// (/smistamento/ → .righe), nel dialog d'azione — dettaglio del documento.
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, required: true },
  preventivoId: { type: Number, required: true },
  consuntivo: { type: Boolean, default: false },
})
// `smistato` notifica il drawer padre che almeno un ramo e' andato a buon fine
// e che testata + capabilities vanno ricaricate (transizione automatica
// ACCETTATO -> EVASO BE-driven, gate bi-ramo). Le altre tab (ordini,
// preventivi) le avvisa lo store, nel verbo che scrive.
const emit = defineEmits(['update:visible', 'smistato'])

const smistamento = ref(null)
const loadingSmistamento = ref(false)
const selected = ref([])

const righe = computed(() => smistamento.value?.righe ?? [])
// NB: aggregato e' null per preventivo senza righe attive (la vista aggregata
// GROUP BY non produce la riga; il BE non fabbrica un fallback).
const aggregato = computed(() => smistamento.value?.aggregato ?? null)
const righeResidue = computed(
  () => righe.value.filter(r => r.stato_smistamento === STATO_SMISTAMENTO.RESIDUA),
)
const righeSmistate = computed(() => {
  const a = aggregato.value
  if (!a) return 0
  return (a.righe_totali ?? 0) - (a.righe_residue ?? 0)
})
const tutteSmistate = computed(() => {
  const a = aggregato.value
  return (a?.righe_totali ?? 0) > 0 && (a?.righe_residue ?? 0) === 0
})

// Selezione vincolata alle sole righe RESIDUA via BB useSelezioneToggle
// (2026-07-15, sostituisce il setter-filtro che faceva "rimbalzare" la
// checkbox): il template usa la Column checkbox custom con :disabled per le
// righe già smistate, il guard di toggleRow tiene comunque fuori dalla
// selezione tutto ciò che non è RESIDUA. Il BE/DB farebbe skip silenzioso
// (D5), ma il conteggio del confirm deve riflettere lo smistato reale.
const { isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected } =
  useSelezioneToggle({
    selected,
    selezionabili: righeResidue,
    rowKey: 'riga_id',
  })

// Etichetta azione: "Smista tutto" quando le righe residue hanno un'unica
// destinazione e sono tutte selezionate (`allSelected` del BB — caso comune,
// es. preventivo tutto-merce: niente scelta da fare); altrimenti "Smista
// selezionate". Le righe sono comunque preselezionate (smista-tutto default).
const smistaLabel = computed(() => {
  const dest = new Set(righeResidue.value.map(r => r.destinazione_tipo))
  return dest.size === 1 && allSelected.value
    ? t('vendite.preventivi.smista_tutto')
    : t('vendite.preventivi.smista_selezionate')
})

// Footer di sola chiusura quando non c'e' nulla da fare: consuntivo (readonly
// puro) o nessuna riga residua da smistare.
const soloChiusura = computed(
  () => props.consuntivo || righeResidue.value.length === 0,
)

// Scopo: Carica lo smistamento (aggregato + righe) e preseleziona tutte le
// righe residue (D2 "preseleziona tutte": smista-tutto e' il default,
// l'operatore deseleziona per lo smistamento parziale). Richiamata anche
// dopo ogni smistamento (refresh dello stato autorevole).
async function loadSmistamento() {
  if (!props.preventivoId) return
  loadingSmistamento.value = true
  try {
    smistamento.value = await store.loadSmistamento(props.preventivoId)
    selected.value = props.consuntivo ? [] : [...righeResidue.value]
  } finally {
    loadingSmistamento.value = false
  }
}

// Fetch lazy: all'apertura (e a ogni riapertura, cosi' lo stato resta fresco
// dopo uno smistamento). Non al mount: il dialog vive montato nel drawer, ma
// chi non smista non deve pagarne la query.
watch(
  () => [props.visible, props.preventivoId],
  ([visible]) => { if (visible && props.preventivoId) loadSmistamento() },
  { immediate: true },
)

function close() {
  emit('update:visible', false)
}

// Scopo: severita' Tag per lo stato di smistamento riga.
function statoSmistamentoSeverity(stato) {
  if (stato === STATO_SMISTAMENTO.RESIDUA) return 'warn'
  if (stato === STATO_SMISTAMENTO.FATTURATA) return 'success'
  return 'info'
}

// Scopo: toast differenziato per `result.stato` dell'orchestrator push
// commessa (HTTP 200 risponde anche con esito PARZIALE/ERRORE per riga):
//   COMPLETATO  -> success con push_log_id
//   PARZIALE    -> warn con push_log_id
//   ERRORE      -> error con primo errore di handler
//   SKIPPED     -> warn ("push gia' in corso")
// Se il preventivo ha `fatturazione_immediata=TRUE` aggiunge un hint che
// l'emit verso AF avverra' al prossimo run pipeline lotto (PR2 implementera'
// il servizio "emissione immediata" — vedi WIP sviluppo-push-singolo-preventivo §9).
function notifyEsitoPush(result) {
  const stato = result?.stato
  const pushLogId = result?.push_log_id
  // Righe pushate effettive = somma `created` + `updated` di tutti gli
  // handler; fallback su righe_pushable diagnostico (count pre-push).
  const righePush = result?.handlers?.reduce(
    (acc, h) => acc + (h?.created ?? 0) + (h?.updated ?? 0),
    0,
  ) ?? result?.righe_pushable ?? 0

  if (stato === 'COMPLETATO') {
    notify.success(t('vendite.preventivi.push_commessa_ok_dettaglio', { righe: righePush, push_log_id: pushLogId }))
  } else if (stato === 'PARZIALE') {
    notify.warn(t('vendite.preventivi.push_commessa_parziale', { righe: righePush, push_log_id: pushLogId }))
  } else if (stato === 'ERRORE') {
    const firstError = result?.handlers?.[0]?.errors?.[0] || t('common.error_generic')
    notify.error(t('vendite.preventivi.push_commessa_errore', { primo_errore: firstError }))
  } else if (stato === 'SKIPPED') {
    notify.warn(t('vendite.preventivi.push_commessa_skipped'))
  } else {
    notify.success(t('vendite.preventivi.push_commessa_ok'))
  }
  if (result?.fatturazione_immediata) {
    // useNotify non espone severity 'info': warn come avviso non bloccante.
    notify.warn(t('vendite.preventivi.push_commessa_immediata_hint'))
  }
  return stato === 'COMPLETATO' || stato === 'PARZIALE'
}

// Scopo: Smista le righe selezionate instradandole per natura: merce
// (destinazione ORDINE) → POST /genera-ordine/ {righe_ids}; servizi
// (destinazione COMMESSA) → POST /push-commessa/ {righe_ids}. Sequenziale:
// prima la merce, poi i servizi; se il ramo merce fallisce ci si ferma
// (l'operatore vede l'errore e ritenta — l'idempotenza di riga rende il
// retry sicuro). A valle ricarica e notifica il padre.
function onSmista() {
  const sel = selected.value
  const merceIds = sel
    .filter(r => r.destinazione_tipo === DESTINAZIONE_SMISTAMENTO.ORDINE)
    .map(r => r.riga_id)
  const serviziIds = sel
    .filter(r => r.destinazione_tipo === DESTINAZIONE_SMISTAMENTO.COMMESSA)
    .map(r => r.riga_id)
  if (!merceIds.length && !serviziIds.length) return

  confirmAction({
    header: t('vendite.preventivi.section_smistamento'),
    message: t('vendite.preventivi.conferma_smistamento', {
      merce: merceIds.length, servizi: serviziIds.length,
    }),
    onAccept: async () => {
      let qualcosaSmistato = false

      if (merceIds.length) {
        const result = await execute(
          () => store.generaOrdine(props.preventivoId, merceIds),
        )
        if (result === null) return // errore gestito; niente ramo servizi
        qualcosaSmistato = true
        notify.success(t('vendite.preventivi.ordine_generato', { numero: result.numero }))
      }

      if (serviziIds.length) {
        const result = await execute(
          () => store.inviaACommessa(props.preventivoId, serviziIds),
        )
        if (result !== null) {
          qualcosaSmistato = notifyEsitoPush(result) || qualcosaSmistato
        }
      }

      // Reload dello stato autorevole post-smistamento (righe + aggregato):
      // se l'azione e' fallita del tutto il dialog resta aperto e aggiornato.
      await loadSmistamento()
      if (!qualcosaSmistato) return
      emit('smistato')
      // Azione conclusa -> chiusura (come il crea-reso DDT): il drawer
      // ricarica testata e capability. Uno smistamento parziale si riprende
      // riaprendo la dialog, che ricarica lo stato autorevole.
      close()
    },
  })
}
</script>

<template>
  <!-- `readonly` esplicito = il consuntivo del chiamante: il dialog e' lanciato
       da un drawer locked-by-stato (preventivo ACCETTATO) e senza override il
       FormFooter erediterebbe readonly=true nascondendo il pulsante di
       smistamento — pur essendo lo smistamento un'azione legittima proprio in
       quello stato. Stessa ragione per cui il pannello, quando viveva nel
       drawer, stava in `app-escape`. -->
  <AppDialog
    :visible="visible"
    width="xl"
    :header="t('vendite.preventivi.section_smistamento')"
    :readonly="consuntivo"
    :loading="loading"
    :close-only="soloChiusura"
    :save-disabled="selected.length === 0"
    :save-label="smistaLabel"
    @update:visible="emit('update:visible', $event)"
    @save="onSmista"
    @cancel="close"
  >
    <div class="form-grid">
      <!-- Progress verso EVASO. A completamento il Tag diventa verde con la
           spunta cerchiata (il testo esteso resta nel tooltip). -->
      <div v-if="aggregato && aggregato.righe_totali > 0" class="smistamento-header">
        <Tag
          :severity="tutteSmistate ? 'success' : 'info'"
          :icon="tutteSmistate ? 'pi pi-check-circle' : undefined"
          v-tooltip.bottom="tutteSmistate ? t('vendite.preventivi.smistamento_completato') : ''"
          :value="t('vendite.preventivi.smistamento_progress', {
            smistate: righeSmistate, totali: aggregato.righe_totali,
          })" />
      </div>

      <DataTable v-if="righe.length" :value="righe"
        data-key="riga_id" striped-rows size="small" class="app-datatable"
        :loading="loadingSmistamento" scrollable scrollHeight="360px">
        <!-- Checkbox custom (no selectionMode: PrimeVue 4 renderebbe spuntabili
             anche le righe già smistate): disabled per riga da isSelectable,
             colonna nascosta quando non resta nulla da smistare (consuntivo). -->
        <Column v-if="!consuntivo && righeResidue.length" headerStyle="width: 3rem">
          <template #header>
            <Checkbox :model-value="allSelected" binary
              :indeterminate="anySelected" @update:model-value="toggleAll" />
          </template>
          <template #body="{ data }">
            <Checkbox :model-value="isSelected(data)" binary
              :disabled="!isSelectable(data)" @update:model-value="toggleRow(data)" />
          </template>
        </Column>
        <Column :header="t('vendite.preventivi.riga_articolo')">
          <template #body="{ data }">
            {{ data.articolo_codice }} — {{ data.riga_descrizione }}
          </template>
        </Column>
        <Column :header="t('vendite.preventivi.riga_quantita')" style="width: 110px;">
          <template #body="{ data }">
            {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
          </template>
        </Column>
        <Column :header="t('vendite.preventivi.smistamento_col_destinazione')" style="width: 150px;">
          <template #body="{ data }">
            <Tag severity="secondary"
              :value="data.destinazione_tipo === DESTINAZIONE_SMISTAMENTO.ORDINE
                ? t('vendite.preventivi.destinazione_ordine')
                : t('vendite.preventivi.destinazione_commessa')" />
          </template>
        </Column>
        <Column :header="t('vendite.preventivi.smistamento_col_stato')" style="width: 180px;">
          <template #body="{ data }">
            <Tag :severity="statoSmistamentoSeverity(data.stato_smistamento)"
              :value="t(`vendite.preventivi.stato_smistamento.${data.stato_smistamento.toLowerCase()}`)" />
            <span v-if="data.ordine_numero" class="smistamento-doc-rif">
              {{ data.ordine_numero }}
            </span>
          </template>
        </Column>
      </DataTable>
      <div v-else-if="!loadingSmistamento" style="color: var(--app-text-muted); font-style: italic;">
        {{ t('vendite.preventivi.smistamento_non_disponibile') }}
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.smistamento-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.smistamento-doc-rif {
  margin-left: 0.4rem;
  font-size: 0.85rem;
  color: var(--app-text-muted);
}
</style>
