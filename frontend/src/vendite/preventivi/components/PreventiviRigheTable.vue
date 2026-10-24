<script setup>
// Scopo: righe preventivo master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        lista, la macchina del form e le azioni vivono nel BB; qui restano le
//        celle che il catalogo non sa rendere (il prezzo col badge
//        dell'approvazione), il form di riga e il predicato "elimina bloccato su PENDING".
//        ⭐ Le colonne vengono dal catalogo (`vendite.preventivo_righe`, lista
//        97) dal 2026-09-28: quelle che non entrano si ritirano nella riga
//        espandibile (brief-db-liste-righe-documento).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { usePreventivoRigheStore } from '../stores/preventivoRighe'
import { exportRigheLista } from '../api/preventiviApi'
import CellaConfigurabile from '../../../core/components/CellaConfigurabile.vue'
import { coerceJsonbToObject } from '../../../core/utils/meta'
import { STATO_APPROVAZIONE } from '../../constants'
import { unisciFotografie } from '../../../core/composables/useDrawerFormPreserve'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import PreventiviRigaForm from './PreventiviRigaForm.vue'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = usePreventiviStore()
// La lista delle righe: uno store per istanza del drawer.
const righe = usePreventivoRigheStore()

defineProps({
  preventivoId: { type: Number, required: true },
  // L'emittente del preventivo (PK): lasciapassare del cancello di perimetro
  // della lista, per chi vede piu' emittenti. Arriva col dettaglio.
  emittenteFiscaleId: { type: Number, default: null },
  // Refactor cascata 2026-05-15: propaga al PreventiviRigaForm per la
  // cascata soglie L2 con livello categoria_cliente del BA.
  billingAccountId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true },
  // La data del preventivo: minimo del calendario delle date di consegna.
  dataDocumento: { type: String, default: null },
})
const emit = defineEmits(['changed', 'form-aperto'])

// Elimina bloccata su righe con approvazione prezzo PENDING (lo blocca anche il
// backend via guard, ma il FE evita il round-trip).
function deleteDisabled(riga) {
  return riga?.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING
}

// severity Tag per stato approvazione prezzo (workflow L3): PENDING=warn,
// APPROVED=success, REJECTED=danger.
function approvazioneSeverity(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return 'success'
  if (stato === STATO_APPROVAZIONE.REJECTED) return 'danger'
  return 'warn'
}

function approvazioneLabel(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return t('vendite.preventivi.badge_approvazione_approved')
  if (stato === STATO_APPROVAZIONE.REJECTED) return t('vendite.preventivi.badge_approvazione_rejected')
  return t('vendite.preventivi.badge_approvazione_pending')
}

// Tooltip contestuale: per REJECTED legge la motivazione denormalizzata in
// `meta.approvazione_rifiuto.motivazione`; per PENDING torna il riferimento
// pratica.
function approvazioneTooltip(data) {
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.REJECTED) {
    const meta = coerceJsonbToObject(data.meta)
    const rif = meta.approvazione_rifiuto || {}
    if (rif.motivazione) {
      return t('vendite.preventivi.badge_approvazione_rejected_tooltip', { motivazione: rif.motivazione })
    }
    return t('vendite.preventivi.badge_approvazione_rejected_no_motivo')
  }
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING && data.pratica_approvazione_prezzo_id) {
    return t('vendite.preventivi.badge_approvazione_pending_tooltip', {
      pratica_id: data.pratica_approvazione_prezzo_id,
    })
  }
  return ''
}

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
    codice="vendite.preventivo_righe"
    :store="righe"
    :parent-id="preventivoId"
    :emittente-fiscale-id="emittenteFiscaleId"
    :export-fn="exportRigheLista"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    :delete-disabled="deleteDisabled"
    title-key="vendite.preventivi.section_righe"
    new-tooltip-key="vendite.preventivi.aggiungi_riga"
    confirm-delete-key="vendite.preventivi.conferma_elimina_riga"
    deleted-message-key="vendite.preventivi.riga_eliminata"
    new-label-key="vendite.preventivi.nuova_riga"
    edit-label-key="vendite.preventivi.modifica_riga"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <!-- Il prezzo col badge dell'approvazione. Il valore lo rende la cella di
         catalogo (formato della colonna): lo slot aggiunge solo il badge. -->
    <template #cell-prezzo_unitario="{ data, col }">
      <div style="display: flex; flex-direction: column; gap: 0.15rem; align-items: flex-start;">
        <CellaConfigurabile :col="col" :data="data" />
        <Tag
          v-if="data.stato_approvazione_prezzo"
          :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
          :value="approvazioneLabel(data.stato_approvazione_prezzo)"
          v-tooltip.top="approvazioneTooltip(data)"
        />
      </div>
    </template>
    <template #form="{ riga, onSaved, onComponentiChanged, onCancel, registra }">
      <PreventiviRigaForm
        :ref="registra"
        :preventivo-id="preventivoId"
        :billing-account-id="billingAccountId"
        :riga="riga"
        :data-documento="dataDocumento"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>
