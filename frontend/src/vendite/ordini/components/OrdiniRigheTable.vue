<script setup>
// Scopo: righe ordine master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        lista, la macchina del form e le azioni vivono nel BB; qui resta il
//        form di riga.
//        ⭐ Le colonne vengono dal catalogo (`vendite.ordine_righe`, lista 98)
//        dal 2026-09-28 (brief-db-liste-righe-documento): nessuna cella
//        speciale, i formati li dichiara il catalogo.
//        ⚠️ Le due date di consegna sono DUE colonne (la confermata e la
//        richiesta dal cliente, decisione di Tid): prima erano una cella sola
//        che mostrava la seconda quando mancava la prima.
//        ⭐ Azione di riga «data di consegna confermata» (2026-10-10,
//        brief-db-testata-dopo-emissione fase 1): la promessa si cambia anche
//        dopo la conferma, quando la riga non si modifica piu'. Accesa o spenta
//        col motivo dalla capability di documento
//        `can_edit_data_consegna_confermata` e, per riga, dal motivo della
//        riga (`data_consegna_confermata_blocco`): qui non si decide niente.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../../../core/constants'
import { labelOrCode } from '../../../core/utils/i18nLabel'
import { motivoDaCodiceBlocco } from '../../../core/utils/bloccoMotivo'
import { useOrdiniStore } from '../stores/ordini'
import { useOrdineRigheStore } from '../stores/ordineRighe'
import { exportRigheLista } from '../api/ordiniApi'
import { unisciFotografie } from '../../../core/composables/useDrawerFormPreserve'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import OrdiniRigaForm from './OrdiniRigaForm.vue'
import OrdineRigaDataConsegnaDialog from './dialogs/OrdineRigaDataConsegnaDialog.vue'

const { t, te } = useI18n()
const store = useOrdiniStore()
// La lista delle righe: uno store per istanza del drawer.
const righe = useOrdineRigheStore()

const props = defineProps({
  ordineId: { type: Number, required: true },
  // L'emittente dell'ordine (PK): lasciapassare del cancello di perimetro
  // della lista, per chi vede piu' emittenti. Arriva col dettaglio.
  emittenteFiscaleId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true },
  // Il blob `capabilities` del dettaglio ordine: la terna
  // `can_edit_data_consegna_confermata` e' di DOCUMENTO (dipende solo dallo
  // stato della testata), quindi vale per ogni riga.
  capabilities: { type: Object, default: () => ({}) },
  // Readonly PURO (permessi / split): nasconde l'azione. Lo stato non la
  // nasconde, la spegne col motivo.
  readonly: { type: Boolean, default: false },
  // La data dell'ordine: minimo del calendario delle date di consegna.
  dataDocumento: { type: String, default: null },
})
const emit = defineEmits(['changed', 'form-aperto'])

// ⭐ D-13 (2026-10-03, analisi-fe-chrome-drawer): la fotografia della riga
//    aperta, inoltrata al drawer per le sue uscite. La tiene il form di riga,
//    che si registra presso la tabella (`registra` dello slot).
const tabella = ref(null)
defineExpose({
  ...unisciFotografie(() => tabella.value),
  // Il drawer padre rilegge le righe dopo un gesto fatto altrove (un documento
  // collegato chiuso dalla barra collegamenti).
  loadRighe: () => tabella.value?.loadRighe(),
})

const dataConsegnaVisible = ref(false)
const dataConsegnaRiga = ref(null)

// Scopo: le azioni di dominio della riga. Permesso ⇒ nascondi, stato ⇒
//        spegni col motivo (chiave i18n dal DB, ripiego sul codice).
// ⭐ Due risposte, nell'ordine in cui le dice il DB: prima il DOCUMENTO (la
//    capability, dallo stato), poi la RIGA (`data_consegna_confermata_blocco`
//    della vista, il primo motivo di
//    `script.fn_check_ordine_riga_data_consegna_confermata`: oggi la riga gia'
//    spedita, D-7 di brief-db-date-consegna-righe-in-blocco).
function azioniRiga(riga) {
  if (props.readonly) return []
  const capabilities = props.capabilities || {}
  const ammessaDocumento = capabilities.can_edit_data_consegna_confermata === true
  const motivoRiga = motivoDaCodiceBlocco(
    t, te, riga?.data_consegna_confermata_blocco,
    'vendite.ordini.data_consegna_confermata_reason',
  )
  return [{
    key: 'data-consegna-confermata',
    label: t('vendite.ordini.azione_data_consegna_confermata'),
    icon: MANAGE_ICONS.PROMESSA_CONSEGNA,
    disabled: !ammessaDocumento || Boolean(motivoRiga),
    tooltip: !ammessaDocumento
      ? labelOrCode(
          t, te,
          capabilities.can_edit_data_consegna_confermata_reason_key,
          capabilities.can_edit_data_consegna_confermata_reason,
        )
      : (motivoRiga || undefined),
    command: () => {
      dataConsegnaRiga.value = riga
      dataConsegnaVisible.value = true
    },
  }]
}
</script>

<template>
  <RigheMasterDetailTable
    ref="tabella"
    codice="vendite.ordine_righe"
    :store="righe"
    :parent-id="ordineId"
    :emittente-fiscale-id="emittenteFiscaleId"
    :export-fn="exportRigheLista"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    :extra-row-actions="azioniRiga"
    title-key="vendite.ordini.section_righe"
    new-tooltip-key="vendite.ordini.aggiungi_riga"
    confirm-delete-key="vendite.ordini.conferma_elimina_riga"
    deleted-message-key="vendite.ordini.riga_eliminata"
    new-label-key="vendite.ordini.nuova_riga"
    edit-label-key="vendite.ordini.modifica_riga"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #form="{ riga, onSaved, onComponentiChanged, onCancel, registra }">
      <OrdiniRigaForm
        :ref="registra"
        :ordine-id="ordineId"
        :riga="riga"
        :data-documento="dataDocumento"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>

  <OrdineRigaDataConsegnaDialog
    v-model:visible="dataConsegnaVisible"
    :ordine-id="ordineId"
    :riga="dataConsegnaRiga"
    :data-documento="dataDocumento"
    :readonly="readonly"
    @salvata="tabella?.loadRighe(); emit('changed')"
  />
</template>
