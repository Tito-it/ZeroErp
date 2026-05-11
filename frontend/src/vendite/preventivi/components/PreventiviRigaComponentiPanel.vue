<script setup>
// Scopo: Pannello componenti BoM CASO A di una riga preventivo (refactor 2026-05-11).
//        Usato in due contesti:
//        - Expander DataTable in PreventiviRigheTable.vue (readonly=true).
//        - Sezione "Componenti esposti in fattura" in PreventiviRigaForm.vue
//          (readonly=false, prezzo inline editabile per componente).
//
//        Lazy load via usePreventivoRigaComponenti su mount + watch su rigaId
//        (per consentire al consumer di riusare l'istanza su righe diverse).
//
//        Badge origine prezzo: 5 valori (PROMO/CONTRATTO_OVERRIDE/
//        CONTRATTO_LISTINO/CATEGORIA/MANUALE) con severity centralizzata in
//        core/utils/severity.js. L1/L2/L3 (workflow approvazione prezzi) sono
//        ereditati dai componenti tramite stato_approvazione_prezzo come per
//        la riga padre. Pattern allineato a PreventiviRigheTable.

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventivoRigaComponenti } from '../../../core/composables/usePreventivoRigaComponenti'
import { useNotify } from '../../../core/composables/useNotify'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { extractApiError } from '../../../core/utils/apiError'
import { pricingOrigineSeverity, pricingOrigineLabelKey } from '../../../core/utils/severity'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import { MANAGE_ICONS } from '../../../core/constants'
import { STATO_APPROVAZIONE, PRICING_ACTIONS, ORIGINE_PREZZO } from '../../constants'
import { useAuthStore } from '../../../stores/auth'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'

const { t } = useI18n()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const auth = useAuthStore()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  rigaId: { type: Number, required: true },
  readonly: { type: Boolean, default: true },
})

const emit = defineEmits(['changed'])

const { componenti, loading, load, update, remove } =
  usePreventivoRigaComponenti(props.preventivoId)

// L1: l'edit prezzo richiede l'azione `prezzo_override_manuale`. Stessa logica
// gia' applicata in PreventiviRigaForm per la riga padre, qui replicata sui
// componenti (la decisione di dominio chiusa dice "L1/L2/L3 sui singoli
// componenti usano stessi parametri della riga padre", refactor-componenti.md §8).
const canOverride = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

// Stato locale: prezzo in edit per ogni componente (Map componente_id -> prezzo).
// Permette di modificare PIU' componenti prima di salvarli uno alla volta —
// e' una scelta di UX semplice: l'operatore vede subito cosa sta cambiando e
// solo lo specifico componente in edit fa il PATCH.
const prezzoEditato = ref({})

// Reload sul cambio riga + cleanup mappa edit. Watch unico: il cambio rigaId
// invalida sempre gli edit pendenti (il dato e' di un'altra riga) e ricarica.
// Catch esplicito: load propaga errori al consumer, qui notifichiamo soft.
async function onRigaIdChange(id) {
  prezzoEditato.value = {}
  if (id == null) return
  try {
    await load(id)
  } catch (err) {
    notify.error(extractApiError(err, t('preventivi.componenti_errore_caricamento')))
  }
}
watch(() => props.rigaId, onRigaIdChange, { immediate: true })

function origineLabel(code) {
  const key = pricingOrigineLabelKey(code)
  return key ? t(key) : (code || '')
}

// Pattern severity tag stato approvazione (allineato a PreventiviRigheTable).
function approvazioneSeverity(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return 'success'
  if (stato === STATO_APPROVAZIONE.REJECTED) return 'danger'
  return 'warn'  // PENDING
}

function approvazioneLabel(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return t('preventivi.badge_approvazione_approved')
  if (stato === STATO_APPROVAZIONE.REJECTED) return t('preventivi.badge_approvazione_rejected')
  return t('preventivi.badge_approvazione_pending')
}

// Dirty check: il prezzo editato e' diverso da quello del componente?
function isDirty(comp) {
  const editVal = prezzoEditato.value[comp.id]
  if (editVal == null) return false
  return Math.abs(Number(editVal) - Number(comp.prezzo_unitario)) > 1e-6
}

function getPrezzoVisualizzato(comp) {
  // In edit mode: usa la mappa locale se popolata, altrimenti il valore DB.
  if (props.readonly) return Number(comp.prezzo_unitario)
  const local = prezzoEditato.value[comp.id]
  return local != null ? Number(local) : Number(comp.prezzo_unitario)
}

function setPrezzoEditato(componenteId, val) {
  prezzoEditato.value = { ...prezzoEditato.value, [componenteId]: val }
}

// Scopo: PATCH del solo prezzo del componente con override MANUALE. Il BE
//        applica L1/L2/L3 (stessi parametri della riga padre). In caso di
//        violazione L2 il PATCH solleva: l'errore arriva via useApiHandler
//        con toast — il workflow "richiedi approvazione" sui componenti
//        non e' esposto in questa Fase 5, va aggiunto se richiesto post-smoke.
// useApiHandler.execute() richiede response axios; il composable ritorna gia'
// unwrappato (vedi feedback_useapihandler_solo_axios in memoria). Quindi
// chiamata diretta con try/catch e notify manuale.
async function onSalvaPrezzo(comp) {
  const nuovoPrezzo = prezzoEditato.value[comp.id]
  if (nuovoPrezzo == null) return
  try {
    await update(props.rigaId, comp.id, {
      prezzo_unitario: nuovoPrezzo,
      origine_prezzo: ORIGINE_PREZZO.MANUALE,
    })
    notify.success(t('preventivi.componenti_prezzo_aggiornato'))
    // Pulisce la mappa di edit per il componente salvato (il reload nel
    // composable riporta il valore aggiornato in `componenti`).
    const next = { ...prezzoEditato.value }
    delete next[comp.id]
    prezzoEditato.value = next
    emit('changed')
  } catch (err) {
    notify.error(extractApiError(err, t('preventivi.componenti_errore_aggiornamento')))
  }
}

function onElimina(comp) {
  confirmAction({
    message: t('preventivi.componenti_conferma_elimina'),
    onAccept: async () => {
      try {
        await remove(props.rigaId, comp.id)
        notify.success(t('preventivi.componenti_componente_eliminato'))
        emit('changed')
      } catch (err) {
        notify.error(extractApiError(err, t('preventivi.componenti_errore_aggiornamento')))
      }
    },
  })
}

</script>

<template>
  <div>
    <div v-if="loading && componenti.length === 0" style="padding: 0.5rem; color: var(--app-text-muted);">
      <i class="pi pi-spin pi-spinner" /> {{ t('common.loading') }}
    </div>
    <div v-else-if="componenti.length === 0" style="padding: 0.75rem; color: var(--app-text-muted); font-size: 0.85rem;">
      {{ t('preventivi.componenti_non_caso_a') }}
    </div>
    <DataTable v-else :value="componenti" size="small" class="app-datatable" data-key="id">
      <Column :header="t('preventivi.componenti_col_codice')" style="width: 160px;">
        <template #body="{ data }">
          <span style="display: inline-flex; align-items: center; gap: 0.25rem;">
            <span style="color: var(--app-text-muted);">└─</span>
            <span>{{ data.componente_codice || '—' }}</span>
          </span>
        </template>
      </Column>
      <Column field="componente_descrizione" :header="t('preventivi.componenti_col_descrizione')" style="min-width: 180px;" />
      <Column :header="t('preventivi.componenti_col_qta')" style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('preventivi.componenti_col_uom')" style="width: 70px;" />
      <Column :header="t('preventivi.componenti_col_prezzo')" style="width: 200px;">
        <template #body="{ data }">
          <template v-if="readonly">
            <span>{{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}</span>
          </template>
          <template v-else>
            <div style="display: flex; align-items: center; gap: 0.25rem;">
              <InputNumber
                :model-value="getPrezzoVisualizzato(data)"
                mode="currency" currency="EUR" locale="it-IT"
                :min-fraction-digits="6" :max-fraction-digits="6"
                :disabled="!canOverride || data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING"
                @update:model-value="(v) => setPrezzoEditato(data.id, v)"
                style="width: 130px;" />
              <Button
                v-if="isDirty(data)"
                icon="pi pi-check"
                text rounded size="small"
                severity="success"
                v-tooltip.top="t('common.save')"
                @click="onSalvaPrezzo(data)" />
            </div>
          </template>
        </template>
      </Column>
      <Column :header="t('preventivi.componenti_col_origine')" style="width: 160px;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.15rem; align-items: flex-start;">
            <Tag
              v-if="data.origine_prezzo"
              :severity="pricingOrigineSeverity(data.origine_prezzo)"
              :value="origineLabel(data.origine_prezzo)"
              v-tooltip.top="t('preventivi.badge_origine_tooltip', { origine: data.origine_prezzo })" />
            <Tag
              v-if="data.stato_approvazione_prezzo"
              :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
              :value="approvazioneLabel(data.stato_approvazione_prezzo)" />
          </div>
        </template>
      </Column>
      <Column field="iva_codice" :header="t('preventivi.componenti_col_iva')" style="width: 70px;" />
      <Column v-if="!readonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <Button :icon="MANAGE_ICONS.DELETE" text rounded size="small" class="app-delete-btn"
            v-tooltip.top="t('common.delete')"
            :disabled="data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING"
            @click="onElimina(data)" />
        </template>
      </Column>
    </DataTable>
    <small v-if="!readonly && componenti.length > 0" style="display: block; color: var(--app-text-muted); margin-top: 0.5rem;">
      {{ t('preventivi.componenti_section_hint') }}
    </small>
    <small v-if="!readonly && !canOverride && componenti.length > 0" style="display: block; color: var(--app-text-muted); margin-top: 0.25rem;">
      <i class="pi pi-lock" /> {{ t('preventivi.componenti_l1_richiede_autorizzazione') }}
    </small>
  </div>
</template>
