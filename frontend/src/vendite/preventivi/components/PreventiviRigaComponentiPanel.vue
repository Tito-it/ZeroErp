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
import { extractApiError } from '../../../core/utils/apiError'
import { pricingOrigineSeverity, pricingOrigineLabelKey } from '../../../core/utils/severity'
import { formatCurrency, formatNumber, PRICE_EPSILON } from '../../../core/utils/format'
import { STATO_APPROVAZIONE, PRICING_ACTIONS, ORIGINE_PREZZO } from '../../constants'
import { useAuthStore } from '../../../stores/auth'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'

const { t } = useI18n()
const notify = useNotify()
const auth = useAuthStore()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  rigaId: { type: Number, required: true },
  readonly: { type: Boolean, default: true },
})

const emit = defineEmits(['changed'])

// `remove` non e' piu' usato: il delete diventa toggle attivo via
// `update(... { attivo: false })`. Il trigger DB applica la disattivazione
// se opzionale, raise `E_DOC_COMPONENTE_OBBLIGATORIO` se obbligatorio.
//
// `soloAttivi` istanza-bound al factory: in readonly l'expander vede solo
// componenti attivi (default); in EDIT panel mostra anche gli opzionali
// disattivati per permettere riattivazione via checkbox toggle.
const { componenti, loading, load, update } =
  usePreventivoRigaComponenti(props.preventivoId, { soloAttivi: props.readonly })

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
// La modalita' `soloAttivi` e' bound al factory del composable (sopra).
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

// Modello unificato 2026-05-13: `obbligatorio` ed `esposto_in_fattura`
// arrivano dalla proiezione BE (JOIN articoli_componenti). Comparazione
// `=== true` coerente col Dialog: null/undefined → opzionale/non esposto.
function isObbligatorio(comp) {
  return comp.obbligatorio === true
}
function isEsposto(comp) {
  return comp.esposto_in_fattura === true
}

// Dirty check: il prezzo editato e' diverso da quello del componente?
// PRICE_EPSILON centralizzato in core/utils/format.
function isDirty(comp) {
  const editVal = prezzoEditato.value[comp.id]
  if (editVal == null) return false
  return Math.abs(Number(editVal) - Number(comp.prezzo_unitario)) >= PRICE_EPSILON
}

// Validazione FE pre-PATCH: blocca prezzo=0 su componente obbligatorio
// (defense-in-depth oltre al trigger DB `trgfn_componenti_check_prezzo_obbligatorio`).
// Per opzionali ammettiamo qualsiasi numero (incluso 0).
function isPrezzoEditatoValido(comp) {
  const editVal = prezzoEditato.value[comp.id]
  if (editVal == null) return true  // niente edit, non bloccare
  if (isObbligatorio(comp) && Number(editVal) === 0) return false
  return true
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
//        applica L1/L2/L3 (stessi parametri della riga padre). Validazione
//        FE blocca prezzo=0 su obbligatori (defense-in-depth: il trigger
//        DB `trgfn_componenti_check_prezzo_obbligatorio` solleverebbe
//        E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO, ma FE early-return
//        evita il round-trip e da' feedback immediato).
async function onSalvaPrezzo(comp) {
  const nuovoPrezzo = prezzoEditato.value[comp.id]
  if (nuovoPrezzo == null) return
  if (!isPrezzoEditatoValido(comp)) {
    notify.warn(t('preventivi.componenti_obbligatorio_zero', {
      codice: comp.componente_codice || comp.componente_id,
    }))
    return
  }
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

// Toggle attivo/disattivo del componente. Il guard DB
// `script.trgfn_componenti_guard_obbligatorio` blocca il flip su
// obbligatori → l'errore arriva come `E_DOC_COMPONENTE_OBBLIGATORIO`.
// In FE il checkbox e' gia' disabled per obbligatori (defense-in-depth):
// il guard DB resta safety net.
async function onToggleAttivo(comp, nuovoAttivo) {
  try {
    await update(props.rigaId, comp.id, { attivo: !!nuovoAttivo })
    emit('changed')
  } catch (err) {
    notify.error(extractApiError(err, t('preventivi.componenti_errore_aggiornamento')))
  }
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
    <DataTable v-else :value="componenti" size="small" class="app-datatable" data-key="id"
      :row-class="(data) => !data.attivo ? 'app-row-muted' : null">
      <Column :header="t('preventivi.componenti_col_codice')" style="width: 160px;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.15rem;">
            <span style="display: inline-flex; align-items: center; gap: 0.25rem;">
              <span style="color: var(--app-text-muted);">└─</span>
              <strong>{{ data.componente_codice || '—' }}</strong>
            </span>
            <Tag
              v-if="isObbligatorio(data)"
              severity="danger"
              :value="t('vendite.componenti.col_obbligatorio_tag')"
              class="app-tag-xs" />
            <Tag
              v-else
              severity="secondary"
              :value="t('vendite.componenti.col_opzionale_tag')"
              class="app-tag-xs" />
          </div>
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
                :disabled="!canOverride
                  || loading
                  || data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING
                  || !data.attivo"
                :class="{ 'p-invalid': isDirty(data) && !isPrezzoEditatoValido(data) }"
                @update:model-value="(v) => setPrezzoEditato(data.id, v)"
                style="width: 130px;" />
              <Button
                v-if="isDirty(data)"
                icon="pi pi-check"
                text rounded size="small"
                severity="success"
                :disabled="!isPrezzoEditatoValido(data) || loading"
                :loading="loading"
                v-tooltip.top="isPrezzoEditatoValido(data)
                  ? t('common.save')
                  : t('preventivi.componenti_obbligatorio_zero', { codice: data.componente_codice })"
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
      <Column v-if="!readonly" :header="t('vendite.componenti.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Checkbox
            :model-value="data.attivo"
            binary
            :disabled="isObbligatorio(data)
              || loading
              || data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING"
            v-tooltip.top="isObbligatorio(data)
              ? t('vendite.componenti.attivo_disabilitato_tooltip')
              : null"
            @update:model-value="(v) => onToggleAttivo(data, v)" />
        </template>
      </Column>
      <Column :header="t('vendite.componenti.col_esposto')" style="width: 90px;">
        <template #body="{ data }">
          <i
            v-if="isEsposto(data)"
            class="pi pi-eye"
            style="color: var(--app-text-info, var(--primary-color));"
            v-tooltip.top="t('vendite.componenti.esposto_in_fattura_tooltip')" />
          <i
            v-else
            class="pi pi-eye-slash"
            style="color: var(--app-text-muted);"
            v-tooltip.top="t('vendite.componenti.esposto_no_tooltip')" />
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

<style scoped>
.app-tag-xs {
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
}
/* Righe componenti con `attivo=FALSE` (opzionali disattivati): mostrate
   in muted per distinguerle dagli attivi senza nasconderle. L'operatore
   puo' riattivarle via checkbox. */
.app-datatable :deep(tr.app-row-muted td) {
  opacity: 0.55;
  font-style: italic;
}
</style>
