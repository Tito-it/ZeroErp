<script setup>
// Scopo: Dialog "DDT ri-spedizione" del drawer RESO (solo CONFERMATO), aperta
// dal pulsante in barra azioni (2026-07-25, decisione Tid — stessa forma di
// «Genera reso» del DDT e «Genera DDT» dell'ordine: le azioni di processo
// stanno in alto, non in coda al contenuto).
//
// Macchina selezione/quantità via BB `useRigheSelezioneQta` (regola del 2 —
// condivisa con evasione ordini e crea-reso DDT). Righe reso per RI-CONSEGNA
// con copertura pendente; quantità in unità BASE (contratto
// fn_genera_ddt_riconsegna: [{resi_riga_id, qta}]). Selezione completa e
// intatta ⇒ righe null (il BE ri-spedisce tutta la copertura residua,
// race-proof). L'over-ri-spedizione resta rifiutata dal guard DB del ponte
// (E_RESO_RICONSEGNA_SUPERA_RESO).
//
// PARZIALE = NORMA, NON ECCEZIONE: qui `preselezione` resta 'tutto' (a
// differenza del crea-reso). Ri-spedire tutto il residuo è l'esito atteso —
// la merce da ri-consegnare è già determinata dal reso, non è una scelta
// dell'operatore — e la selezione intatta abilita il payload `null`
// race-proof. Una quantità minore genera un DDT parziale e LASCIA il resto
// pendente: la riga resta in lista con `qta_residua` ridotta e si genera un
// altro DDT quando serve (fn_genera_ddt_riconsegna salta le righe a residuo
// esaurito ed è ri-eseguibile).
import { watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import TabellaSelezioneRighe from '../../../_shared/righe/TabellaSelezioneRighe.vue'

import AppDialog from '../../../../core/components/AppDialog.vue'
import RowActionsMenu from '../../../../core/components/RowActionsMenu.vue'
import { MANAGE_ICONS } from '../../../../core/constants'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../../core/composables/useConfirmAction'
import { useNotify } from '../../../../core/composables/useNotify'
import { formatNumber } from '../../../../core/utils/format'
import { useRigheSelezioneQta } from '../../../_shared/righe/useRigheSelezioneQta'
import { useResiStore } from '../../stores/resi'

const { t } = useI18n()
const store = useResiStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, required: true },
  resoId: { type: Number, required: true },
  // In readonly puro la dialog e' consuntiva: righe visibili, niente azione.
  readonly: { type: Boolean, default: false },
})
// `aggiornato` notifica il drawer padre che la copertura ri-consegna e'
// CAMBIATA — da una delle tre uscite (DDT generato, quota resa definitiva,
// rinuncia riaperta). Un solo evento perche' la reazione del padre e' la
// stessa (ricarica detail, righe e chip collegamenti); il nome non dice
// "generato" proprio perche' due casi su tre non generano nulla.
const emit = defineEmits(['update:visible', 'aggiornato'])

// Macchina selezione/quantità (BB): righe = solo RESO_PER_RICONSEGNA;
// residuo = copertura residua in unità BASE.
const selezione = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.resoId) return []
    const rows = await store.loadRighe(props.resoId)
    // Tutte le righe di tipo ri-consegna, comprese quelle a copertura chiusa:
    // le esaurite restano come CONSUNTIVO (ri-spedite o rinunciate) — servono
    // a leggere la storia e, per le rinunciate, ad ospitare la riapertura.
    return (rows || []).filter(r => r.riapre_residuo)
  },
  residuoDi: (r) => Number(r.qta_residua) || 0,
  readonly: () => props.readonly,
  // La fotografia (D-14) e' del BB, fissata a ogni caricamento delle righe.
  visibile: () => props.visible,
})
const {
  righe,
  selected,
  righeSelezionabili,
  coversAllResiduo,
  loadRighe,
  buildPayloadRighe,
  chiudiConConferma,
} = selezione

// Fetch lazy: all'apertura (e a ogni riapertura, cosi' la copertura residua
// resta fresca dopo una ri-spedizione parziale appena generata).
watch(
  () => [props.visible, props.resoId],
  ([visible]) => { if (visible && props.resoId) loadRighe() },
  { immediate: true },
)

// L'etichetta dice quale delle due semantiche parte: tutta la copertura
// residua (payload null, race-proof) o la sola selezione esplicita.
const generaLabel = computed(() =>
  coversAllResiduo.value
    ? t('vendite.resi.riconsegna_genera_tutto')
    : t('vendite.resi.riconsegna_genera_selezione'),
)

// Footer di sola chiusura quando non c'e' nulla da ri-spedire: readonly puro
// (consuntivo) o copertura gia' completa.
const soloChiusura = computed(
  () => props.readonly || righeSelezionabili.value.length === 0,
)

// Righe già dichiarate definitive: consuntivo + bersaglio della riapertura.
const righeRinunciate = computed(
  () => righe.value.filter(r => (Number(r.qta_rinunciata) || 0) > 0),
)

function close() {
  emit('update:visible', false)
}

// Scopo: esegue una delle due uscite sulla selezione corrente. Le accomuna
// tutto tranne la chiamata e i messaggi: stessa lista, stessa selezione,
// stesso payload (`null` = tutta la copertura residua, race-proof).
// `titolo` = il nome dell'azione premuta: la conferma lo ripete in testa.
async function eseguiSuSelezione({ titolo, conferma, azione, successo }) {
  if (!selected.value.length) return
  const usaTutto = coversAllResiduo.value
  const payloadRighe = usaTutto
    ? null
    : buildPayloadRighe((r, qta) => ({ resi_riga_id: r.id, qta: String(qta) }))

  if (!usaTutto && !payloadRighe.length) {
    notify.warn(t('vendite.resi.riconsegna_qta_nulla'))
    return
  }

  confirmAction({
    header: titolo,
    message: conferma(
      usaTutto ? righeSelezionabili.value.length : payloadRighe.length,
    ),
    onAccept: async () => {
      const result = await execute(() => azione(payloadRighe))
      if (result === null) return
      notify.success(successo)
      emit('aggiornato', result)
      close()
    },
  })
}

// Uscita 1 — RI-SPEDISCI: la merce torna al cliente. Il DDT nasce DRAFT e si
// rifinisce dal tab DDT.
function onGenera() {
  eseguiSuSelezione({
    titolo: t('vendite.resi.riconsegna_azione'),
    conferma: (n) => t('vendite.resi.riconsegna_conferma', { righe: n }),
    azione: (righeSel) => store.generaRiconsegna(props.resoId, { righe: righeSel }),
    successo: t('vendite.resi.riconsegna_generato'),
  })
}

// Uscita 2 — RENDI DEFINITIVO: la merce NON torna al cliente. Chiude il residuo
// ordine (→ EVASO) e fa passare l'accredito da facoltativo a dovuto, senza
// cambiarne l'importo. La conferma lo dice per esteso: e' l'unica azione della
// dialog che ha una conseguenza contabile, e non e' deducibile dall'etichetta.
function onRendiDefinitivo() {
  eseguiSuSelezione({
    titolo: t('vendite.resi.rinuncia_azione'),
    conferma: (n) => t('vendite.resi.rinuncia_conferma', { righe: n }),
    azione: (righeSel) => store.chiudiRiconsegna(props.resoId, { righe: righeSel }),
    successo: t('vendite.resi.rinuncia_chiusa'),
  })
}

// Rimedio a una chiusura errata: riapre la rinuncia della singola riga (la
// quota torna ri-spedibile, l'ordine torna PARZIALMENTE_EVASO). Non chiude la
// dialog: si resta nell'elenco per continuare a lavorarlo.
function onRiapri(riga) {
  confirmAction({
    header: t('vendite.resi.rinuncia_riapri'),
    message: t('vendite.resi.rinuncia_riapri_conferma', {
      qta: formatNumber(riga.qta_rinunciata),
    }),
    onAccept: async () => {
      const result = await execute(
        () => store.riapriRiconsegna(props.resoId, {
          righe: [{ resi_riga_id: riga.id, qta: String(riga.qta_rinunciata) }],
        }),
      )
      if (result === null) return
      notify.success(t('vendite.resi.rinuncia_riaperta'))
      emit('aggiornato', result)
      // La ricarica rifissa la fotografia da se' (BB): la selezione riscritta
      // e' la nuova base, non una modifica dell'operatore.
      await loadRighe()
    },
  })
}

</script>

<template>
  <!-- `readonly` esplicito = quello PURO del chiamante: la dialog e' lanciata da
       un drawer locked-by-stato (reso CONFERMATO) e senza override il FormFooter
       erediterebbe readonly=true nascondendo il pulsante di generazione — pur
       essendo la ri-spedizione un'azione legittima proprio in quello stato. -->
  <AppDialog
    :conferma-uscita="chiudiConConferma"
    :visible="visible"
    width="xl"
    :header="t('vendite.resi.riconsegna_titolo')"
    :readonly="readonly"
    :loading="loading"
    :close-only="soloChiusura"
    @update:visible="emit('update:visible', $event)"
    @cancel="close"
  >
    <!-- Footer custom: la copertura ha DUE uscite e stanno nello stesso posto,
         sulla stessa lista e sulla stessa selezione. Una dialog gemella
         costringerebbe a rifare la selezione per cambiare esito. «Rendi
         definitivo» e' `warn` outlined: e' l'uscita con conseguenza contabile,
         non va data la stessa enfasi del percorso normale. -->
    <template v-if="!soloChiusura" #footer="{ chiudi }">
      <div class="app-rispedizione-footer">
        <Button
          text
          :label="t('common.close')"
          :icon="MANAGE_ICONS.CANCEL"
          :disabled="loading"
          @click="chiudi" />
        <Button
          severity="warn"
          outlined
          :label="t('vendite.resi.rinuncia_azione')"
          :icon="MANAGE_ICONS.RINUNCIA"
          :loading="loading"
          :disabled="selected.length === 0"
          @click="onRendiDefinitivo" />
        <Button
          :label="generaLabel"
          :icon="MANAGE_ICONS.GENERA_DOCUMENTO"
          :loading="loading"
          :disabled="selected.length === 0"
          @click="onGenera" />
      </div>
    </template>
    <div class="form-grid">
      <p class="app-dialog-intro">
        {{ t('vendite.resi.riconsegna_intro') }}
      </p>

      <TabellaSelezioneRighe :macchina="selezione"
        :etichetta-qta="t('vendite.resi.riconsegna_col_qta')" larghezza-qta="170px"
        :testo-vuoto="t('vendite.resi.riconsegna_nessuna_riga')">
        <template #colonne>
          <Column :header="t('vendite.resi.riconsegna_col_resa')" style="width: 100px;">
            <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
          </Column>
          <Column :header="t('vendite.resi.riconsegna_col_riconsegnata')" style="width: 120px;">
            <template #body="{ data }">{{ formatNumber(data.qta_riconsegnata) }}</template>
          </Column>
          <!-- Le due uscite affiancate: quanto e' tornato al cliente e quanto e'
               stato dichiarato definitivo. Il "—" a zero tiene la colonna
               leggibile quando non ci sono rinunce (il caso normale). -->
          <Column :header="t('vendite.resi.rinuncia_col_rinunciata')" style="width: 120px;">
            <template #body="{ data }">
              <span v-if="(Number(data.qta_rinunciata) || 0) > 0" class="app-rinuncia-qta">
                {{ formatNumber(data.qta_rinunciata) }}
              </span>
              <span v-else>—</span>
            </template>
          </Column>
          <Column :header="t('vendite.resi.riconsegna_col_residua')" style="width: 100px;">
            <template #body="{ data }">{{ formatNumber(data.qta_residua) }}</template>
          </Column>
        </template>
        <template #colonne-dopo>
          <!-- Riapertura: solo sulle righe con una rinuncia da annullare.
               Kebab per riga (MANAGE_ICONS.KEBAB), non un pulsante inline: e'
               un rimedio, non un'azione del flusso normale. -->
          <Column v-if="!readonly && righeRinunciate.length"
            class="app-col-actions" style="width: 4rem;">
            <template #body="{ data }">
              <RowActionsMenu
                v-if="(Number(data.qta_rinunciata) || 0) > 0"
                :row="data"
                :actions="[{
                  key: 'riapri',
                  label: t('vendite.resi.rinuncia_riapri'),
                  icon: MANAGE_ICONS.UNDO,
                  command: () => onRiapri(data),
                }]" />
            </template>
          </Column>
        </template>
      </TabellaSelezioneRighe>

      <!-- Nota esplicita sul parziale: una quantita' inferiore al residuo NON
           perde il resto — o lo ri-spedisci dopo, o lo dichiari definitivo.
           Senza dirlo, l'operatore non puo' sapere che fine fa la differenza. -->
      <p v-if="righeSelezionabili.length" class="app-riconsegna-nota">
        {{ t('vendite.resi.riconsegna_nota_parziale') }}
      </p>
    </div>
  </AppDialog>
</template>

<style scoped>
.app-riconsegna-nota {
  margin: 0;
  font-size: 0.8rem;
  color: var(--app-text-muted);
  font-style: italic;
}

/* Footer a due uscite: chiusura a sinistra, azioni a destra con la definitiva
   PRIMA della ri-spedizione — l'ultima posizione resta al percorso normale. */
.app-rispedizione-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.app-rispedizione-footer > :first-child {
  margin-right: auto;
}

/* La quota definitiva e' un fatto contabile: si legge, non si mimetizza.
   Colore dalla variabile centralizzata, mai un valore diretto. */
.app-rinuncia-qta {
  font-weight: 600;
  color: var(--app-warning-color);
}
</style>
