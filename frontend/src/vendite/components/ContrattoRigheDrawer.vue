<script setup>
// Scopo: Sub-drawer delle righe di un contratto — involucro del BB
//        `RigheEccezioniDrawer` (lista configurabile `vendite.contratto_righe`,
//        103, coi verbi del DB, e form inline di OVERRIDE/AGGIUNTA).
//
// ⭐ DAL 2026-10-05 E' UN INVOLUCRO (regola del 2, ok Tid, brief-db-righe-
//    esclusione-solo-non-si-vende §8.1): il corpo — lista, menu di riga dai
//    verbi, form, componenti BoM, flusso L2 — e' il BB condiviso con l'offerta,
//    nato da questo file. Qui resta cio' che e' del CONTRATTO: lo store della
//    sua lista, le sue scritture e API dei componenti, l'intestazione e il
//    banner del contesto pricing (forma, listino e versione fissata, deriva,
//    variazione, categoria), che l'offerta non ha.
//
// La storia del corpo (lista configurabile dal 2026-10-04, verbi del DB,
// «Escludi» vuoto) sta nel BB e in brief-db-liste-righe-documento.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useContrattoRigheStore } from '../stores/contrattoRighe'
import { FORMA_CONTRATTO } from '../constants'
import { TAB_ENTITIES } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import {
  previewRigaComponenti,
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
  getContrattoContestoPricing,
  exportRigheLista,
  listRigaErogazioni,
} from '../api/contratti'
import DrawerContextHeader from '../../core/components/DrawerContextHeader.vue'
import RigheEccezioniDrawer from '../_shared/righe/RigheEccezioniDrawer.vue'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useContrattiStore()

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  // L'emittente del contratto (PK di `anagrafiche.emittenti_fiscali`): il
  // lasciapassare del cancello di perimetro della lista.
  emittenteFiscaleId: { type: Number, default: null },
  // La "forma" del contratto, derivata dal padre dai campi testata:
  // "con_listino" o "senza_listino". Default null: il drawer la legge dal
  // contesto pricing. ⚠️ Serve SOLO al banner: la lista non decide niente
  // per forma.
  contrattoForma: { type: String, default: null },
  // Contesto contratto (per intestazione riepilogativa)
  contrattoNumero: { type: String, default: '' },
  contrattoCliente: { type: String, default: '' },
  contrattoValidoDal: { type: String, default: '' },
  contrattoValidoAl: { type: String, default: null },
  contrattoStatoCodice: { type: String, default: '' },
  contrattoStatoDescrizione: { type: String, default: '' },
  // Le righe si scrivono: la capability `can_edit_righe` del DB, dal
  // dettaglio del contratto (`detail.capabilities`). Assente = falso.
  righeModificabili: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'changed'])

// Righe modificabili lo dice il DB: la capability `can_edit_righe` di
// `script.fn_available_actions_contratto` (la regola «solo in DRAFT», col
// guard `E_RIGA_DOC_NON_BOZZA`, anche sui componenti dal 2026-10-05), non lo
// stato riletto qui. ⭐ Lo applica l'involucro, chiunque lo monti: fino al
// 2026-10-05 il blocco arrivava solo dalla catena readonly di `ContrattoDrawer`,
// e la lista dei contratti e il drawer del cliente, che aprono le righe
// direttamente, le lasciavano modificabili su un contratto ATTIVO (verbi, form
// e componenti accesi, poi il rifiuto del DB). Capability assente = falso,
// come sull'offerta: senza il si' del DB i verbi non si propongono.
const bloccato = computed(() => !props.righeModificabili)

// Lo store della lista: una istanza per drawer, nata nello scope di questo
// componente (si dispone con lui).
const righeStore = useContrattoRigheStore()

// Le scritture delle righe, nella forma che il BB chiede.
const scritture = {
  crea: (id, payload) => store.addRiga(id, payload),
  aggiorna: (id, rigaId, payload) => store.updateRiga(id, rigaId, payload),
  elimina: (id, rigaId) => store.deleteRiga(id, rigaId),
}
const apiComponenti = {
  anteprima: previewRigaComponenti,
  elenco: listRigaComponenti,
  aggiorna: updateRigaComponente,
  elimina: deleteRigaComponente,
}

// === Contesto pricing contratto (FE 2.2) ===
// Forma, listino + versione fissata (post-attivazione) o corrente (DRAFT),
// variazione, categoria cliente: il banner sopra la lista. Si legge col padre
// della lista (`fetchExtra` del BB), e «Ricarica» riallinea entrambi: banner e
// righe dipendono dalla stessa versione del listino.
const contestoPricing = ref(null)

// Forma effettiva: priorita' al backend (contesto pricing), fallback alla prop.
const formaEffettiva = computed(() => contestoPricing.value?.forma || props.contrattoForma)
const isSenzaListino = computed(() => formaEffettiva.value === FORMA_CONTRATTO.SENZA_LISTINO)

// Listino associato ma senza versione operativa oggi: la lista ha le sole
// eccezioni, e l'operatore deve attivare una versione del listino.
// ⭐ Dal contesto pricing, che sceglie la versione con la regola del contratto.
const listinoSenzaVersione = computed(() => (
  contestoPricing.value?.forma === FORMA_CONTRATTO.CON_LISTINO
    && contestoPricing.value?.listino_versione_id == null
))

async function loadContestoPricing() {
  if (!props.contrattoId) {
    contestoPricing.value = null
    return
  }
  try {
    const res = await getContrattoContestoPricing(props.contrattoId)
    contestoPricing.value = res?.data?.data || null
  } catch (err) {
    contestoPricing.value = null
    console.warn('contratto contesto pricing fetch failed',
      err?.response?.data || err)
  }
}

watch(() => props.visible, (v) => {
  if (!v) contestoPricing.value = null
})
</script>

<template>
  <RigheEccezioniDrawer
    :visible="props.visible"
    :documento-id="props.contrattoId"
    :emittente-fiscale-id="props.emittenteFiscaleId"
    lista-codice="vendite.contratto_righe"
    documento="CONTRATTO"
    :righe-store="righeStore"
    :scritture="scritture"
    :esporta-righe="exportRigheLista"
    :api-componenti="apiComponenti"
    :erogazioni-articolo="listRigaErogazioni"
    :tab-entity="TAB_ENTITIES.CONTRATTO"
    i18n-documento="vendite.contratti"
    :bloccato="bloccato"
    :fetch-extra="loadContestoPricing"
    @update:visible="(v) => emit('update:visible', v)"
    @changed="emit('changed')"
  >
    <template #intestazione>
      <DrawerContextHeader
        :tag-value="contrattoNumero"
        :items="[
          { label: t('vendite.contratti.col_ba'), value: contrattoCliente },
          { label: t('vendite.contratti.col_valido_dal'), value: displayDate(contrattoValidoDal) },
          { label: t('vendite.contratti.col_valido_al'), value: contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' },
        ]">
        <template #status>
          <Tag v-if="contrattoStatoCodice"
            :value="contrattoStatoDescrizione"
            :severity="statoContrattoSeverity(contrattoStatoCodice)" />
        </template>
      </DrawerContextHeader>
    </template>

    <template #avvisi>
      <!-- Banner contesto pricing: forma derivata + listino + versione
           fissata (post-attivazione) o corrente (DRAFT) + categoria cliente. -->
      <Message v-if="contestoPricing"
        :severity="isSenzaListino ? 'warn' : 'info'"
        :closable="false" size="small">
        <div>
          <strong>{{ t(`vendite.contratti.forma_${formaEffettiva}_descrizione`) }}</strong>
        </div>
        <div v-if="contestoPricing.listino_codice">
          {{ t('vendite.contratti.contesto_listino', {
            codice: contestoPricing.listino_codice,
            versione: contestoPricing.listino_versione_codice || '—',
          }) }}
          <Tag v-if="contestoPricing.listino_versione_fissata"
               :value="t('vendite.contratti.contesto_versione_fissata')"
               severity="success" class="ml-05" />
          <!-- Deriva: il contratto e' fissato a una versione del listino
               diversa da quella oggi ATTIVA. Informativo: i prezzi restano
               calcolati sulla fissata per progetto. -->
          <Tag v-if="contestoPricing.drift_versione_listino"
               :value="t('vendite.contratti.contesto_drift_versione', {
                 versione_corrente: contestoPricing.listino_versione_corrente_codice,
               })"
               severity="warn" class="ml-05"
               v-tooltip.top="t('vendite.contratti.contesto_drift_versione_tooltip', {
                 versione_corrente: contestoPricing.listino_versione_corrente_codice,
                 versione_fissata: contestoPricing.listino_versione_codice,
               })" />
        </div>
        <div v-if="contestoPricing.tipo_variazione_globale">
          {{ t('vendite.contratti.contesto_variazione', {
            tipo: contestoPricing.tipo_variazione_globale,
            valore: contestoPricing.valore_variazione_globale,
          }) }}
        </div>
        <div v-if="contestoPricing.categoria_cliente_codice">
          {{ t('vendite.contratti.contesto_categoria', {
            codice: contestoPricing.categoria_cliente_codice,
          }) }}
        </div>
      </Message>

      <!-- Avviso "senza_listino": tutte le righe AGGIUNTA, prezzo obbligatorio. -->
      <Message v-if="isSenzaListino && !contestoPricing"
               severity="warn" :closable="false" size="small">
        {{ t('vendite.contratti.righe_senza_listino_warn') }}
      </Message>

      <!-- Listino associato ma senza versione operativa oggi: la lista ha le
           sole eccezioni, legittimamente. -->
      <Message v-if="listinoSenzaVersione"
        severity="warn" :closable="false" size="small">
        {{ t('vendite.contratti.preview_listino_senza_versione', {
          codice: contestoPricing.listino_codice || ''
        }) }}
      </Message>
    </template>
  </RigheEccezioniDrawer>
</template>
