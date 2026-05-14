<script setup>
// Scopo: Building block riusabile per il pannello componenti BoM di una
//        riga padre composita (modello unificato 2026-05-13).
//        Estratto da `PreventiviRigaComponentiPanel.vue` (Fase H
//        2026-05-14) per supportare le 4 sorgenti documento (preventivi,
//        contratti, ordini, ddt) senza duplicazione.
//
//        Usato in due contesti:
//        - Expander DataTable (readonly=true): tabella read-only.
//        - Sezione "Componenti" nel drawer riga (readonly=false): prezzo
//          inline editabile + salvataggio per componente.
//
//        La variabilita' tra sorgenti vive nelle 3 prop API
//        (apiList/apiUpdate/apiDelete) e nella `tabEntity` per emit
//        cross-tab; tutto il resto (UX, severity, validazione, badge,
//        layout) e' identico per design del modello unificato.
//
//        i18n: chiavi sotto `vendite.componenti.panel.*` (default).
//        Caller puo' override `i18nPrefix` per varianti contestuali
//        (es. preventivi mantiene le chiavi legacy `preventivi.componenti_*`
//        per non rompere consumer terzi; `localizedKey` fa fallback
//        automatico al namespace base).
//
// Riferimenti: frontend-standards.md §Pattern lista, §Multilingua,
// §Stili CSS (no scoped per layout, usare classi app-*).

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useNotify } from '../../../core/composables/useNotify'
import { useRigaComponenti } from '../../../core/composables/useRigaComponenti'
import { extractApiError } from '../../../core/utils/apiError'
import {
  pricingOrigineLabelKey,
  pricingOrigineSeverity,
} from '../../../core/utils/severity'
import { formatCurrency, formatNumber, PRICE_EPSILON } from '../../../core/utils/format'
import { useAuthStore } from '../../../stores/auth'
import {
  ORIGINE_PREZZO,
  PRICING_ACTIONS,
  STATO_APPROVAZIONE,
} from '../../constants'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'

const { t, te } = useI18n()
const notify = useNotify()
const auth = useAuthStore()

const props = defineProps({
  // ID del documento padre (preventivo/contratto/ordine/ddt).
  documentoId: { type: Number, required: true },
  // ID della riga padre composita.
  rigaId: { type: Number, required: true },
  // Read-only consultazione (expander) vs editabile (form drawer).
  readonly: { type: Boolean, default: true },
  // Callback API sorgente-specific. Firme:
  //   apiList(documentoId, rigaId, { soloAttivi }) -> axios response
  //   apiUpdate(documentoId, rigaId, componenteId, payload) -> axios response
  //   apiDelete(documentoId, rigaId, componenteId) -> axios response
  // Per preventivi: passare listRigaComponenti / updateRigaComponente /
  //   deleteRigaComponente di `preventivi/api/preventiviApi.js`.
  // Per contratti/ordini/ddt: omologa di quella sorgente.
  apiList: { type: Function, required: true },
  apiUpdate: { type: Function, required: true },
  apiDelete: { type: Function, required: true },
  // Chiave TAB_ENTITIES per emit cross-tab post-write (refresh in altre
  // tab che guardano lo stesso documento). Es. TAB_ENTITIES.PREVENTIVO,
  // TAB_ENTITIES.CONTRATTO.
  tabEntity: { type: String, default: null },
  // Namespace i18n. Default `vendite.componenti.panel`. Override per
  // caller con chiavi proprie (es. `preventivi.componenti` per backcompat).
  // `localizedKey` fa fallback automatico al namespace base.
  i18nPrefix: { type: String, default: 'vendite.componenti.panel' },
})

const emit = defineEmits(['changed'])

// Helper risoluzione i18n con fallback al namespace base. Permette al
// caller di sovrascrivere solo le chiavi differenti.
function localizedKey(key) {
  const prefixed = `${props.i18nPrefix}.${key}`
  return te(prefixed) ? prefixed : `vendite.componenti.panel.${key}`
}

// `soloAttivi` istanza-bound al factory: in readonly l'expander vede solo
// componenti attivi (default); in EDIT panel mostra anche gli opzionali
// disattivati per permettere riattivazione via checkbox toggle.
//
// `documentoId` passato come getter `() => props.documentoId` per garantire
// la reattivita' su drawer PrimeVue riusato (le props cambiano senza
// rimount; scalar verrebbe catturato a setup).
const { componenti, loading, load, update } = useRigaComponenti(
  () => props.documentoId,
  {
    apiList: props.apiList,
    apiUpdate: props.apiUpdate,
    apiDelete: props.apiDelete,
    soloAttivi: props.readonly,
    tabEntity: props.tabEntity,
  },
)

// L1: l'edit prezzo richiede l'azione `prezzo_override_manuale`. Stessa
// logica gia' applicata nella riga padre, qui replicata sui componenti
// (decisione di dominio: L1/L2/L3 sui componenti usano stessi parametri
// della riga padre).
const canOverride = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

// Stato locale: prezzo in edit per ogni componente.
// Permette di editare PIU' componenti prima di salvarli uno alla volta —
// scelta UX semplice: l'operatore vede subito cosa sta cambiando, solo
// lo specifico componente in edit fa il PATCH.
const prezzoEditato = ref({})

// Reload sul cambio riga + cleanup mappa edit. Cambio rigaId invalida
// sempre gli edit pendenti (dato di un'altra riga) e ricarica.
async function onRigaIdChange(id) {
  prezzoEditato.value = {}
  if (id == null) return
  try {
    await load(id)
  } catch (err) {
    notify.error(extractApiError(err, t(localizedKey('errore_caricamento'))))
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
  if (stato === STATO_APPROVAZIONE.APPROVED) return t(localizedKey('badge_approvazione_approved'))
  if (stato === STATO_APPROVAZIONE.REJECTED) return t(localizedKey('badge_approvazione_rejected'))
  return t(localizedKey('badge_approvazione_pending'))
}

// Modello unificato 2026-05-13: `obbligatorio` ed `esposto_in_fattura`
// arrivano dalla proiezione BE (JOIN articoli_componenti).
function isObbligatorio(comp) {
  return comp.obbligatorio === true
}
function isEsposto(comp) {
  return comp.esposto_in_fattura === true
}

// Dirty check: prezzo editato diverso da quello del componente (oltre
// PRICE_EPSILON centralizzato).
function isDirty(comp) {
  const editVal = prezzoEditato.value[comp.id]
  if (editVal == null) return false
  return Math.abs(Number(editVal) - Number(comp.prezzo_unitario)) >= PRICE_EPSILON
}

// Validazione FE pre-PATCH: blocca prezzo=0 su componente obbligatorio
// (defense-in-depth oltre al trigger DB
// `trgfn_componenti_check_prezzo_obbligatorio`).
function isPrezzoEditatoValido(comp) {
  const editVal = prezzoEditato.value[comp.id]
  if (editVal == null) return true
  if (isObbligatorio(comp) && Number(editVal) === 0) return false
  return true
}

function getPrezzoVisualizzato(comp) {
  if (props.readonly) return Number(comp.prezzo_unitario)
  const local = prezzoEditato.value[comp.id]
  return local != null ? Number(local) : Number(comp.prezzo_unitario)
}

function setPrezzoEditato(componenteId, val) {
  prezzoEditato.value = { ...prezzoEditato.value, [componenteId]: val }
}

// Scopo: PATCH del solo prezzo del componente con origine MANUALE. Il BE
// applica L1/L2/L3 (stessi parametri della riga padre).
async function onSalvaPrezzo(comp) {
  const nuovoPrezzo = prezzoEditato.value[comp.id]
  if (nuovoPrezzo == null) return
  if (!isPrezzoEditatoValido(comp)) {
    notify.warn(t(localizedKey('obbligatorio_zero'), {
      codice: comp.componente_codice || comp.componente_id,
    }))
    return
  }
  try {
    await update(props.rigaId, comp.id, {
      prezzo_unitario: nuovoPrezzo,
      origine_prezzo: ORIGINE_PREZZO.MANUALE,
    })
    notify.success(t(localizedKey('prezzo_aggiornato')))
    const next = { ...prezzoEditato.value }
    delete next[comp.id]
    prezzoEditato.value = next
    emit('changed')
  } catch (err) {
    notify.error(extractApiError(err, t(localizedKey('errore_aggiornamento'))))
  }
}
</script>

<template>
  <div>
    <div v-if="loading && componenti.length === 0" class="componenti-panel-loading">
      <i class="pi pi-spin pi-spinner" /> {{ t('common.loading') }}
    </div>
    <div v-else-if="componenti.length === 0" class="componenti-panel-empty">
      {{ t(localizedKey('vuoto')) }}
    </div>
    <DataTable v-else :value="componenti" size="small" class="app-datatable" data-key="id">
      <Column :header="t(localizedKey('col_codice'))" style="width: 130px;">
        <template #body="{ data }">
          <div class="componenti-panel-codice-cell">
            <span class="componenti-panel-codice-line">
              <span class="componenti-panel-tree-marker">└─</span>
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
      <Column field="componente_descrizione" :header="t(localizedKey('col_descrizione'))" style="min-width: 140px;" />
      <Column :header="t(localizedKey('col_qta'))" style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t(localizedKey('col_uom'))" style="width: 70px;" />
      <Column :header="t(localizedKey('col_prezzo'))" style="width: 180px; min-width: 180px;">
        <template #body="{ data }">
          <template v-if="readonly">
            <span>{{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 2, maximumFractionDigits: 6 }) }}</span>
          </template>
          <template v-else>
            <div class="componenti-panel-prezzo-cell">
              <InputNumber
                :model-value="getPrezzoVisualizzato(data)"
                mode="currency" currency="EUR" locale="it-IT"
                :min-fraction-digits="2" :max-fraction-digits="6"
                :disabled="!canOverride
                  || loading
                  || data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING"
                :class="{ 'p-invalid': isDirty(data) && !isPrezzoEditatoValido(data) }"
                @update:model-value="(v) => setPrezzoEditato(data.id, v)"
                :input-style="{ width: '100%' }"
                class="componenti-panel-input" />
              <Button
                v-if="isDirty(data)"
                icon="pi pi-check"
                text rounded size="small"
                severity="success"
                :disabled="!isPrezzoEditatoValido(data) || loading"
                :loading="loading"
                v-tooltip.top="isPrezzoEditatoValido(data)
                  ? t('common.save')
                  : t(localizedKey('obbligatorio_zero'), { codice: data.componente_codice })"
                @click="onSalvaPrezzo(data)" />
            </div>
          </template>
        </template>
      </Column>
      <Column :header="t(localizedKey('col_origine'))" style="width: 100px;">
        <template #body="{ data }">
          <div class="componenti-panel-tag-stack">
            <Tag
              v-if="data.origine_prezzo"
              :severity="pricingOrigineSeverity(data.origine_prezzo)"
              :value="origineLabel(data.origine_prezzo)"
              class="app-tag-xs"
              v-tooltip.top="t(localizedKey('badge_origine_tooltip'), { origine: data.origine_prezzo })" />
            <Tag
              v-if="data.stato_approvazione_prezzo"
              :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
              :value="approvazioneLabel(data.stato_approvazione_prezzo)"
              class="app-tag-xs" />
          </div>
        </template>
      </Column>
      <Column field="iva_codice" :header="t(localizedKey('col_iva'))" style="width: 50px;" />
      <Column :header="t('vendite.componenti.col_esposto')" style="width: 70px;">
        <template #body="{ data }">
          <Tag
            v-if="isEsposto(data)"
            severity="info"
            :value="t('common.yes')"
            class="app-tag-xs"
            v-tooltip.top="t('vendite.componenti.esposto_in_fattura_tooltip')" />
          <Tag
            v-else
            severity="secondary"
            :value="t('common.no')"
            class="app-tag-xs"
            v-tooltip.top="t('vendite.componenti.esposto_no_tooltip')" />
        </template>
      </Column>
    </DataTable>
    <small v-if="!readonly && componenti.length > 0" class="componenti-panel-hint">
      {{ t(localizedKey('section_hint')) }}
    </small>
    <small v-if="!readonly && !canOverride && componenti.length > 0" class="componenti-panel-hint componenti-panel-hint-lock">
      <i class="pi pi-lock" /> {{ t(localizedKey('l1_richiede_autorizzazione')) }}
    </small>
  </div>
</template>

<style scoped>
/* Mini-stili visivi del building block — niente layout pagina o form
   (quelli stanno in main.css come da frontend-standards). Solo decoratori
   inline-specific (tag xs, gerarchia tabella, hint).
*/
.app-tag-xs {
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
}
.componenti-panel-loading {
  padding: 0.5rem;
  color: var(--app-text-muted);
}
.componenti-panel-empty {
  padding: 0.75rem;
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
.componenti-panel-codice-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.componenti-panel-codice-line {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.componenti-panel-tree-marker {
  color: var(--app-text-muted);
}
.componenti-panel-prezzo-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.componenti-panel-input {
  width: 130px;
}
.componenti-panel-tag-stack {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  align-items: flex-start;
}
.componenti-panel-hint {
  display: block;
  color: var(--app-text-muted);
  margin-top: 0.5rem;
}
.componenti-panel-hint-lock {
  margin-top: 0.25rem;
}
</style>
