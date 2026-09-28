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
import { useOrdiniStore } from '../stores/ordini'
import { useOrdineRigheStore } from '../stores/ordineRighe'
import { exportRigheLista } from '../api/ordiniApi'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import OrdiniRigaForm from './OrdiniRigaForm.vue'

const store = useOrdiniStore()
// La lista delle righe: uno store per istanza del drawer.
const righe = useOrdineRigheStore()

defineProps({
  ordineId: { type: Number, required: true },
  // L'emittente dell'ordine (PK): lasciapassare del cancello di perimetro
  // della lista, per chi vede piu' emittenti. Arriva col dettaglio.
  emittenteFiscaleId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true },
})
const emit = defineEmits(['changed', 'form-aperto'])
</script>

<template>
  <RigheMasterDetailTable
    codice="vendite.ordine_righe"
    :store="righe"
    :parent-id="ordineId"
    :emittente-fiscale-id="emittenteFiscaleId"
    :export-fn="exportRigheLista"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    title-key="vendite.ordini.section_righe"
    new-tooltip-key="vendite.ordini.aggiungi_riga"
    confirm-delete-key="vendite.ordini.conferma_elimina_riga"
    deleted-message-key="vendite.ordini.riga_eliminata"
    new-label-key="vendite.ordini.nuova_riga"
    edit-label-key="vendite.ordini.modifica_riga"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #form="{ riga, onSaved, onComponentiChanged, onCancel }">
      <OrdiniRigaForm
        :ordine-id="ordineId"
        :riga="riga"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>
