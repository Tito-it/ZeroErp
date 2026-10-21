<script setup>
// Scopo: Dialog "Genera reso" del DDT (solo stato CONSEGNATO — non si rende
// cio' che non e' stato consegnato). E' il percorso UNICO per portare un DDT a
// RESO: il flip di stato e' automatico lato DB (fn_conferma_reso, solo a reso
// TOTALE confermato), mai un'azione manuale.
// Aperta dal pulsante «Genera reso» nella barra azioni del drawer DDT
// (2026-07-25, decisione Tid): l'attivita' e' un processo a se' — modale
// dedicata invece di un pannello sempre montato in coda al drawer, che
// allungava il contenuto e faceva fetch anche a chi non stava rendendo nulla.
// Le righe si caricano all'APERTURA (lazy), non al mount del drawer.
// Macchina selezione/quantità via BB `useRigheSelezioneQta` (regola del 2 —
// condivisa con evasione ordini e ri-spedizione reso); qui in piu': tipo reso +
// motivo per riga (mappe extra seedate in onLoaded) e `preselezione: 'nessuna'`
// (niente righe spuntate ne' quantita' precompilate: cosa e quanto rientra e'
// un dato di fatto che dichiara l'operatore, non un default plausibile —
// proporre "tutto reso" invita a confermare per inerzia un reso TOTALE, che
// flippa il DDT a RESO).
// Quantità in unità OPERATIVA; payload sempre ESPLICITO (mai null: la
// creazione parziale è la norma).
// Il reso nasce DRAFT: nessun router-push, si rifinisce/conferma dal tab Resi.
// L'over-return resta rifiutato dal guard DB (E_RESO_QTA_SUPERA_CONSEGNATO).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import AppDialog from '../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { formatNumber } from '../../../core/utils/format'
import { useRigheSelezioneQta } from '../../_shared/righe/useRigheSelezioneQta'
import { getRigheDdtPerReso } from '../../resi/api/resiApi'
import { useResiStore } from '../../resi/stores/resi'
import { TIPO_RESO } from '../../resi/constants'
import { useLookupCodici } from '../../../core/composables/useLookupCodici'

const { t } = useI18n()
const resiStore = useResiStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, required: true },
  ddtId: { type: Number, required: true },
  // In readonly puro la dialog e' consuntiva (righe visibili, no azione).
  readonly: { type: Boolean, default: false },
})
// `reso-creato` notifica il drawer padre (aggiorna i residui rendibili).
const emit = defineEmits(['update:visible', 'reso-creato'])

// Input extra per riga (keyed per ddt_riga_id): tipo reso + motivo libero.
const tipoMap = ref({})
const motivoMap = ref({})

// Tipi reso dal lookup generico (cache modulo-level condivisa, stessa chiave
// del LookupSelect rel="config.tipi_reso": transform envelope di default).
const { items: tipiReso, load: loadTipiReso } = useLookupCodici('config.tipi_reso')
// Default: A_CREDITO se presente, altrimenti il primo tipo attivo del lookup
// (fail-soft: un rename del codice_interno non deve lasciare le righe senza
// tipo e far fallire la creazione in modo muto).
const tipoDefaultId = computed(
  () => tipiReso.value.find(x => x.codice_interno === TIPO_RESO.A_CREDITO)?.id
    ?? tipiReso.value[0]?.id
    ?? null,
)

// Scopo: residuo rendibile OPERATIVO della riga DDT (0 se esaurito).
function residuoDi(r) {
  return Number(r.qta_resa_residua_operativa) || 0
}

// Macchina selezione/quantità (BB). Le due fetch (lookup tipi + righe) sono
// indipendenti: in parallelo (latenza = max, non somma).
const {
  righe, loadingRighe, selected, qtaMap, righeSelezionabili,
  loadRighe, buildPayloadRighe,
  isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected,
  chiudiConConferma,
} = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.ddtId) return []
    const [, res] = await Promise.all([
      loadTipiReso(),
      getRigheDdtPerReso(props.ddtId),
    ])
    return res.data.data || []
  },
  residuoDi,
  rowKey: 'ddt_riga_id',
  readonly: () => props.readonly,
  // La fotografia (D-14) e' del BB, fissata a ogni caricamento delle righe.
  visibile: () => props.visible,
  statoExtra: () => ({ tipo: tipoMap.value, motivo: motivoMap.value }),
  // Niente righe spuntate ne' quantita' precompilate: sceglie l'operatore.
  preselezione: 'nessuna',
  onLoaded: (rows) => {
    const tipo = {}
    const motivo = {}
    for (const r of rows) {
      tipo[r.ddt_riga_id] = tipoDefaultId.value
      motivo[r.ddt_riga_id] = ''
    }
    tipoMap.value = tipo
    motivoMap.value = motivo
  },
})

// Fetch lazy: all'apertura (e a ogni riapertura, cosi' i residui restano
// freschi dopo un reso appena creato). Non al mount: la dialog vive montata
// nel drawer, ma chi non genera resi non deve pagarne le query.
watch(
  () => [props.visible, props.ddtId],
  ([visible]) => { if (visible && props.ddtId) loadRighe() },
  { immediate: true },
)

// Footer di sola chiusura quando non c'e' nulla da fare: readonly puro
// (consuntivo) o nessuna riga con residuo rendibile.
const soloChiusura = computed(
  () => props.readonly || righeSelezionabili.value.length === 0,
)

function close() {
  emit('update:visible', false)
}

// Scopo: crea il reso in bozza con le righe selezionate. Il payload viaggia
// in unita' OPERATIVA (il trigger DB deriva la base). A valle: toast + emit
// al padre (che ricarica il detail) + chiusura della dialog.
function onCrea() {
  if (!selected.value.length) return
  const payloadRighe = buildPayloadRighe(
    (r, qta) => ({
      ddt_riga_id: r.ddt_riga_id,
      tipo_reso_id: tipoMap.value[r.ddt_riga_id],
      qta_operativa: String(qta),
      motivo: motivoMap.value[r.ddt_riga_id]?.trim() || null,
    }),
    { filterRow: (r) => tipoMap.value[r.ddt_riga_id] != null },
  )

  if (!payloadRighe.length) {
    notify.warn(t('vendite.resi.crea_qta_nulla'))
    return
  }

  confirmAction({
    header: t('vendite.resi.crea_titolo'),
    message: t('vendite.resi.crea_conferma', { righe: payloadRighe.length }),
    onAccept: async () => {
      const result = await execute(
        () => resiStore.create({ ddt_id: props.ddtId, righe: payloadRighe }),
      )
      if (result === null) return
      // Il reso nasce in DRAFT: numero assegnato solo alla conferma.
      notify.success(t('vendite.resi.reso_creato'))
      emit('reso-creato', { resoId: result?.id ?? null })
      close()
    },
  })
}

</script>

<template>
  <!-- `readonly` esplicito = quello PURO del chiamante: la dialog e' lanciata da
       un drawer locked-by-stato (DDT CONSEGNATO) e senza override il FormFooter
       erediterebbe readonly=true nascondendo il pulsante di creazione — pur
       essendo il reso un'azione legittima proprio in quello stato. Stessa
       ragione per cui il pannello, quando viveva nel drawer, stava in
       `app-escape`. -->
  <AppDialog
    :conferma-uscita="chiudiConConferma"
    :visible="visible"
    width="xl"
    :header="t('vendite.resi.crea_titolo')"
    :readonly="readonly"
    :loading="loading"
    :close-only="soloChiusura"
    :save-disabled="selected.length === 0"
    :save-label="t('vendite.resi.crea_bottone')"
    @update:visible="emit('update:visible', $event)"
    @save="onCrea"
    @cancel="close"
  >
    <div class="form-grid">
      <p style="margin: 0; font-size: 0.85rem; color: var(--app-text-muted);">
        {{ t('vendite.resi.crea_intro') }}
      </p>

      <DataTable v-if="righe.length" :value="righe"
        data-key="ddt_riga_id" striped-rows size="small" class="app-datatable"
        :loading="loadingRighe" scrollable scrollHeight="360px">
        <!-- Checkbox custom (no selectionMode: PrimeVue 4 renderebbe spuntabili
             anche le righe con residuo esaurito): disabled per riga da
             isSelectable, colonna nascosta quando non resta nulla da rendere. -->
        <Column v-if="!readonly && righeSelezionabili.length" headerStyle="width: 3rem">
          <template #header>
            <Checkbox :model-value="allSelected" binary
              :indeterminate="anySelected" @update:model-value="toggleAll" />
          </template>
          <template #body="{ data }">
            <Checkbox :model-value="isSelected(data)" binary
              :disabled="!isSelectable(data)" @update:model-value="toggleRow(data)" />
          </template>
        </Column>
        <Column :header="t('vendite.resi.riga_articolo')">
          <template #body="{ data }">
            {{ data.articolo_codice }} — {{ data.descrizione }}
          </template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_consegnata')" style="width: 110px;">
          <template #body="{ data }">
            {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
          </template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_gia_resa')" style="width: 100px;">
          <template #body="{ data }">{{ formatNumber(data.qta_gia_resa) }}</template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_residuo')" style="width: 100px;">
          <template #body="{ data }">{{ formatNumber(data.qta_resa_residua_operativa) }}</template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_qta')" style="width: 150px;">
          <template #body="{ data }">
            <InputNumber v-if="!readonly && residuoDi(data) > 0"
              v-model="qtaMap[data.ddt_riga_id]" :min="0" :max="residuoDi(data)"
              :min-fraction-digits="0" :max-fraction-digits="6"
              input-style="width: 6.5rem;" />
            <span v-else>{{ formatNumber(qtaMap[data.ddt_riga_id]) }}</span>
          </template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_tipo')" style="width: 190px;">
          <template #body="{ data }">
            <Select v-if="!readonly && residuoDi(data) > 0"
              v-model="tipoMap[data.ddt_riga_id]" :options="tipiReso"
              option-label="descrizione" option-value="id" size="small" />
          </template>
        </Column>
        <Column :header="t('vendite.resi.crea_col_motivo')" style="width: 180px;">
          <template #body="{ data }">
            <InputText v-if="!readonly && residuoDi(data) > 0"
              v-model="motivoMap[data.ddt_riga_id]" size="small" style="width: 100%;" />
          </template>
        </Column>
      </DataTable>
      <div v-else-if="!loadingRighe" style="color: var(--app-text-muted); font-style: italic;">
        {{ t('vendite.resi.crea_nessuna_riga') }}
      </div>
    </div>
  </AppDialog>
</template>
