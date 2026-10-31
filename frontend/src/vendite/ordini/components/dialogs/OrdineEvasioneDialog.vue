<script setup>
// Scopo: Dialog "Genera DDT" (evasione) del drawer ORDINE. Macchina
// selezione/quantità via BB `useRigheSelezioneQta` (estratto 2026-07-14,
// regola del 2 alla 3ª copia, ok Tid — condiviso con crea-reso DDT e
// ri-spedizione reso). Tabella righe ordine con residuo per riga
// (`qta_residua_operativa` dal fulfillment multi-DDT aggregato, unità
// OPERATIVE), selezione multipla + quantità da evadere (default = RESIDUO) e
// azione unica "Genera DDT". Selezione completa e intatta ⇒ righe null (il BE
// evade il residuo effettivo: race-proof su evasioni concorrenti).
// L'over-shipping resta rifiutato dal guard DB (E_QTA_SUPERA_RESIDUO).
// Nessun router-push: il DDT nasce DRAFT e si apre dal suo tab.
//
// Aperta dal pulsante «Genera DDT» nella barra azioni del drawer ordine
// (2026-07-25, decisione Tid): le azioni di processo stanno in alto, non in
// coda al contenuto. Era un pannello sempre montato che allungava il drawer e
// caricava le righe anche a chi non stava evadendo nulla; ora la fetch e'
// all'APERTURA (lazy) e a ogni riapertura (residui freschi dopo un'evasione).
// Stesso pattern di DdtResoDialog.
import { watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../../core/composables/useConfirmAction'
import { useNotify } from '../../../../core/composables/useNotify'
import { useRigheSelezioneQta } from '../../../_shared/righe/useRigheSelezioneQta'
import { useOrdiniStore } from '../../stores/ordini'
import { formatNumber } from '../../../../core/utils/format'
import Column from 'primevue/column'
import TabellaSelezioneRighe from '../../../_shared/righe/TabellaSelezioneRighe.vue'

const { t } = useI18n()
const store = useOrdiniStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, required: true },
  ordineId: { type: Number, required: true },
  // In readonly puro (LETTURA/split/forzato) la dialog e' consuntiva: mostra
  // le righe ma niente selezione/azione.
  readonly: { type: Boolean, default: false },
})
// `evaso` notifica il drawer padre che un DDT e' stato generato: ricarica il
// detail (lo stato ordine e' proiettato dal BE) e propaga il DDT id.
const emit = defineEmits(['update:visible', 'evaso'])

// Scopo: residuo operativo della riga (0 se campo assente/riga gia' evasa).
function residuoDi(r) {
  return Number(r.qta_residua_operativa) || 0
}

// Macchina selezione/quantità (BB): le righe gia' completamente evase restano
// visibili come consuntivo (ordinata/evasa), le evadibili sono preselezionate
// con qta = residuo.
const selezione = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.ordineId) return []
    return (await store.loadRighe(props.ordineId)) || []
  },
  residuoDi,
  readonly: () => props.readonly,
  // La fotografia (D-14) e' del BB, fissata a ogni caricamento delle righe.
  visibile: () => props.visible,
})
const {
  selected,
  righeSelezionabili: righeEvadibili,
  coversAllResiduo: evadeTuttoResiduo,
  loadRighe,
  buildPayloadRighe,
  chiudiConConferma,
} = selezione

// Fetch lazy: all'apertura (e a ogni riapertura, cosi' i residui restano
// freschi dopo un DDT appena generato). Non al mount: la dialog vive montata
// nel drawer, ma chi non evade non deve pagarne le query.
watch(
  () => [props.visible, props.ordineId],
  ([visible]) => { if (visible && props.ordineId) loadRighe() },
  { immediate: true },
)

// Etichetta azione: "tutto il residuo" quando la selezione e' completa e
// intatta; altrimenti "selezione".
const generaLabel = computed(() =>
  evadeTuttoResiduo.value
    ? t('vendite.ordini.evasione_genera_tutto')
    : t('vendite.ordini.evasione_genera_selezione'),
)

// Footer di sola chiusura quando non c'e' nulla da fare: readonly puro
// (consuntivo) o nessuna riga con residuo da evadere.
const soloChiusura = computed(
  () => props.readonly || righeEvadibili.value.length === 0,
)

function close() {
  emit('update:visible', false)
}

// Scopo: genera il DDT dalle righe selezionate. Se evade tutto il residuo invia
// null (il BE risolve il residuo dal fulfillment); altrimenti invia l'array
// esplicito {ordine_riga_id, qta_da_evadere}. A valle: toast + emit al padre +
// notifica il tab DDT (refresh) + chiusura della dialog.
function onGenera() {
  if (!selected.value.length) return
  const usaResiduo = evadeTuttoResiduo.value
  const payloadRighe = usaResiduo
    ? null
    : buildPayloadRighe((r, qta) => ({ ordine_riga_id: r.id, qta_da_evadere: qta }))

  if (!usaResiduo && !payloadRighe.length) {
    notify.warn(t('vendite.ordini.evasione_qta_nulla'))
    return
  }

  confirmAction({
    header: t('vendite.ordini.evasione_titolo'),
    message: t('vendite.ordini.evasione_conferma', {
      righe: usaResiduo ? righeEvadibili.value.length : payloadRighe.length,
    }),
    onAccept: async () => {
      const result = await execute(
        () => store.generaDdt(props.ordineId, payloadRighe),
      )
      if (result === null) return
      const ddtId = result?.ddt_id ?? null
      // Il DDT nasce in DRAFT: il numero e' assegnato solo all'emissione.
      notify.success(t('vendite.ordini.ddt_generato'))
      emit('evaso', { ddtId })
      // Chiusura come per il crea-reso: l'azione e' conclusa e il lavoro
      // prosegue sul DDT. Un'evasione parziale si riprende riaprendo la
      // dialog, che ricarica i residui aggiornati.
      close()
    },
  })
}

</script>

<template>
  <!-- `readonly` esplicito = quello PURO del chiamante: la dialog e' lanciata da
       un drawer locked-by-stato (ordine CONFERMATO) e senza override il
       FormFooter erediterebbe readonly=true nascondendo il pulsante di
       generazione — pur essendo l'evasione un'azione legittima proprio in
       quello stato. Stessa ragione per cui il pannello, quando viveva nel
       drawer, stava in `app-escape`. -->
  <AppDialog
    :conferma-uscita="chiudiConConferma"
    :visible="visible"
    width="xl"
    :header="t('vendite.ordini.evasione_titolo')"
    :readonly="readonly"
    :loading="loading"
    :close-only="soloChiusura"
    :save-disabled="selected.length === 0"
    :save-label="generaLabel"
    @update:visible="emit('update:visible', $event)"
    @save="onGenera"
    @cancel="close"
  >
    <div class="form-grid">
      <p style="margin: 0; font-size: 0.85rem; color: var(--app-text-muted);">
        {{ t('vendite.ordini.evasione_intro') }}
      </p>

      <TabellaSelezioneRighe :macchina="selezione"
        :etichetta-qta="t('vendite.ordini.evasione_col_qta_da_evadere')" larghezza-qta="160px"
        :testo-vuoto="t('vendite.ordini.evasione_nessuna_riga')">
        <template #colonne>
          <Column :header="t('vendite.ordini.evasione_col_qta_ordinata')" style="width: 120px;">
            <template #body="{ data }">
              {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
            </template>
          </Column>
          <Column :header="t('vendite.ordini.evasione_col_qta_evasa')" style="width: 110px;">
            <template #body="{ data }">
              {{ formatNumber(data.qta_evasa_operativa) }}
            </template>
          </Column>
          <Column :header="t('vendite.ordini.evasione_col_qta_residua')" style="width: 110px;">
            <template #body="{ data }">
              {{ formatNumber(data.qta_residua_operativa) }}
            </template>
          </Column>
        </template>
      </TabellaSelezioneRighe>
    </div>
  </AppDialog>
</template>
