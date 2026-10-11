<script setup>
// Scopo: righe DDT master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        lista, la macchina del form e le azioni vivono nel BB; qui restano la
//        cella «senza prezzo» e il form di riga.
//        ⭐ Le colonne vengono dal catalogo (`vendite.ddt_righe`, lista 99) dal
//        2026-09-28 (brief-db-liste-righe-documento).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { useDdtStore } from '../stores/ddt'
import { useDdtRigheStore } from '../stores/ddtRighe'
import { exportRigheLista } from '../api/ddtApi'
import CellaConfigurabile from '../../../core/components/CellaConfigurabile.vue'
import { unisciFotografie } from '../../../core/composables/useDrawerFormPreserve'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import DdtRigaForm from './DdtRigaForm.vue'

const { t } = useI18n()
const store = useDdtStore()
// La lista delle righe: uno store per istanza del drawer.
const righe = useDdtRigheStore()

// DEC-6: prezzo assente non e' prezzo zero, e dopo B4 l'importo arriva NULL
// quando manca il prezzo. Senza il Tag la cella resterebbe vuota (o peggio,
// 0,00) e l'operatore non saprebbe se il prezzo manca o se qualcuno ha deciso
// che vale zero. Una regola, due colonne: un solo template qui sotto.
const COLONNE_PREZZO = ['prezzo_unitario', 'importo_riga']

defineProps({
  ddtId: { type: Number, required: true },
  // L'emittente del DDT (PK): lasciapassare del cancello di perimetro della
  // lista, per chi vede piu' emittenti. Arriva col dettaglio.
  emittenteFiscaleId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true },
  // FE-A: la causale del documento vende? Serve al form e ai componenti per
  // decidere se il prezzo e' obbligatorio (default `true` = comportamento
  // storico, cosi' un chiamante che non la passa non cambia).
  causaleFatturabile: { type: Boolean, default: true },
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
</script>

<template>
  <RigheMasterDetailTable
    ref="tabella"
    codice="vendite.ddt_righe"
    :store="righe"
    :parent-id="ddtId"
    :emittente-fiscale-id="emittenteFiscaleId"
    :export-fn="exportRigheLista"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    title-key="vendite.ddt.section_righe"
    new-tooltip-key="vendite.ddt.aggiungi_riga"
    confirm-delete-key="vendite.ddt.conferma_elimina_riga"
    deleted-message-key="vendite.ddt.riga_eliminata"
    new-label-key="vendite.ddt.nuova_riga"
    edit-label-key="vendite.ddt.modifica_riga"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template v-for="codice in COLONNE_PREZZO" #[`cell-${codice}`]="{ data, col, value }" :key="codice">
      <Tag v-if="value == null" severity="secondary" :value="t('vendite.ddt.riga_senza_prezzo')" />
      <CellaConfigurabile v-else :col="col" :data="data" />
    </template>

    <template #form="{ riga, onSaved, onComponentiChanged, onCancel, registra }">
      <DdtRigaForm
        :ref="registra"
        :ddt-id="ddtId"
        :riga="riga"
        :causale-fatturabile="causaleFatturabile"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>
