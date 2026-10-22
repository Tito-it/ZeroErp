<script setup>
// Scopo: Building block riusabile per il pannello componenti BoM di una
//        riga padre composita (modello unificato 2026-05-13).
//        Estratto da `PreventiviRigaComponentiPanel.vue` (Fase H
//        2026-05-14) per supportare le 4 sorgenti documento (preventivi,
//        contratti, ordini, ddt) senza duplicazione.
//
//        Usato in tre modalita':
//        - Fetch-driven readonly (expander DataTable): chiama apiList per
//          le righe persistite (es. AGGIUNTA bundle salvata).
//        - Fetch-driven editabile (drawer riga, readonly=false): apiList
//          + apiUpdate per editing prezzo inline.
//        - Data-driven readonly (initialData != null): salta la fetch e
//          rende direttamente l'array passato. Usato per anteprime con
//          shape JSONB aggregato in DB (es. fn_contratto_righe_preview),
//          dove i componenti vivono solo in `listini_righe_componenti`
//          senza istanza in `*_righe_componenti`.
//
//        La variabilita' tra sorgenti vive nelle 3 prop API
//        (apiList/apiUpdate/apiDelete) e nella `tabEntity` per emit
//        cross-tab; tutto il resto (UX, severity, validazione, badge,
//        layout) e' identico per design del modello unificato.
//
//        Auto-hide colonne metadata (origine, approvazione, IVA, esposto):
//        ogni colonna scompare quando nessuna riga visibile ha il campo
//        valorizzato (modalita' preview espone solo i dati base, quelle
//        avanzate solo per righe persistite).
//
//        i18n: chiavi sotto `vendite.componenti.panel.*` (default).
//        Caller puo' override `i18nPrefix` per varianti contestuali
//        (es. preventivi mantiene le chiavi legacy `vendite.preventivi.componenti_*`
//        per non rompere consumer terzi; `localizedKey` fa fallback
//        automatico al namespace base).
//
// Riferimenti: frontend-standards.md §Pattern lista, §Multilingua,
// §Stili CSS (no scoped per layout, usare classi app-*).

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEsposizioniComponente, severitaEsposizione } from '../../../catalogo/composables/useEsposizioniComponente'

import { useNotify } from '../../../core/composables/useNotify'
import { useRigaComponenti } from '../../../core/composables/useRigaComponenti'
import { extractApiError } from '../../../core/utils/apiError'
import { coerceJsonbToArray } from '../../../core/utils/meta'
import { MANAGE_ICONS, STATUS_ICONS } from '../../../core/constants'
import {
  pricingOrigineLabelKey,
  pricingOrigineSeverity,
} from '../../../core/utils/severity'
import { formatCurrency, formatNumber, PRICE_EPSILON } from '../../../core/utils/format'
import { useAuthStore } from '../../../stores/auth'
import {
  PRICING_ACTIONS,
  STATO_APPROVAZIONE,
} from '../../constants'

// DataTable grezza: sono i componenti BoM della riga padre (sotto-righe del
// documento, o `initialData` di anteprima), con prezzo editabile sulla cella.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'

const { t, te } = useI18n()
// Il modo di esposizione in fattura per esteso, con l'etichetta dal DB.
const { etichetta: etichettaEsposizione } = useEsposizioniComponente()
const notify = useNotify()
const auth = useAuthStore()

const props = defineProps({
  // FE-D1/D2 (brief-ddt-righe-senza-prezzo): il documento pretende un prezzo
  // sui componenti? Il DDT in conto visione no — il kit viaggia senza prezzi.
  // ⭐ `default: true` NON e' pigrizia: preventivi, ordini, contratti e listino
  // bundle non passano la prop e restano identici bit per bit. E' la stessa
  // scelta fatta dal team DB sul trigger C3 — non si tocca il codice condiviso,
  // si cambia solo quando la regola si applica.
  prezzoRichiesto: { type: Boolean, default: true },
  // ID del documento padre (preventivo/contratto/ordine/ddt).
  // Non required: in modalita' data-driven non serve.
  documentoId: { type: Number, default: 0 },
  // ID della riga padre composita.
  // Non required: in modalita' data-driven non serve.
  rigaId: { type: Number, default: 0 },
  // Read-only consultazione (expander) vs editabile (form drawer).
  // Forzato readonly in modalita' data-driven (initialData != null).
  readonly: { type: Boolean, default: true },
  // Modalita' data-driven: se passato (Array o stringa JSON aggregata
  // da DB), salta la fetch e rende direttamente. Shape attesa allineata
  // al jsonb_agg standard delle fn preview: componente_id,
  // componente_codice, componente_descrizione, uom_id, uom_codice,
  // coeff_qta, prezzo, obbligatorio, esposizione_in_fattura.
  // Il normalizer mappa coeff_qta->quantita e prezzo->prezzo_unitario
  // per usare le stesse celle del rendering fetch-driven.
  initialData: { type: [Array, String], default: null },
  // Callback API sorgente-specific. Firme:
  //   apiList(documentoId, rigaId, { soloAttivi }) -> axios response
  //   apiUpdate(documentoId, rigaId, componenteId, payload) -> axios response
  //   apiDelete(documentoId, rigaId, componenteId) -> axios response
  // Per preventivi: passare listRigaComponenti / updateRigaComponente /
  //   deleteRigaComponente di `preventivi/api/preventiviApi.js`.
  // Per contratti/ordini/ddt: omologa di quella sorgente.
  // Non required in modalita' data-driven (saltate completamente).
  apiList: { type: Function, default: null },
  apiUpdate: { type: Function, default: null },
  apiDelete: { type: Function, default: null },
  // Chiave TAB_ENTITIES per emit cross-tab post-write (refresh in altre
  // tab che guardano lo stesso documento). Es. TAB_ENTITIES.PREVENTIVO,
  // TAB_ENTITIES.CONTRATTO.
  tabEntity: { type: String, default: null },
  // Namespace i18n. Default `vendite.componenti.panel`. Override per
  // caller con chiavi proprie (es. `vendite.preventivi.componenti` per backcompat).
  // `localizedKey` fa fallback automatico al namespace base.
  i18nPrefix: { type: String, default: 'vendite.componenti.panel' },
})

const emit = defineEmits(['changed'])

// Modalita' data-driven decisa al setup. La prop `initialData` non e'
// pensata per cambiare runtime (caso non realistico: una stessa istanza
// di pannello non oscilla tra anteprima e fetch).
const isDataDriven = computed(() => props.initialData != null)
const effectiveReadonly = computed(() => isDataDriven.value || props.readonly)

// Guard runtime: in modalita' fetch-driven le 3 api callback sono
// obbligatorie. In data-driven sono ignorate.
if (!isDataDriven.value) {
  if (typeof props.apiList !== 'function'
      || typeof props.apiUpdate !== 'function'
      || typeof props.apiDelete !== 'function') {
    throw new Error(
      'ComponentiPanel: in modalita\' fetch-driven '
      + 'apiList/apiUpdate/apiDelete sono obbligatorie. '
      + 'Per la modalita\' data-driven passare invece initialData.',
    )
  }
}

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
//
// In modalita' data-driven `useRigaComponenti` viene saltato (le api
// callback non sono obbligatorie e l'array arriva da `initialData`).
const fetcher = isDataDriven.value
  ? null
  : useRigaComponenti(
      () => props.documentoId,
      {
        apiList: props.apiList,
        apiUpdate: props.apiUpdate,
        apiDelete: props.apiDelete,
        soloAttivi: props.readonly,
        tabEntity: props.tabEntity,
      },
    )

// Normalizer shape preview JSONB -> shape pannello. Mappa i nomi diversi
// e fornisce un id stabile usabile come data-key DataTable anche quando
// la riga non e' persistita (preview Parte 1b da listini_righe_componenti).
//
// Marker `_qta_is_snapshot` distingue le due semantiche:
//   - true:  `quantita` reale (snapshot riga padre x coeff_qta), persistito
//   - false: solo `coeff_qta` (rapporto BoM), preview senza istanza
// Usato per scegliere la label di colonna "Q.tà" vs "Coeff." nella
// modalita' data-driven.
function normalizeRow(c) {
  const hasSnapshotQta = c.quantita != null
  const qtaValue = hasSnapshotQta
    ? c.quantita
    : (c.coeff_qta_snapshot ?? c.coeff_qta)
  return {
    id: c.id ?? `prv-${c.componente_id ?? ''}-${c.componente_codice ?? ''}`,
    componente_id: c.componente_id ?? null,
    componente_codice: c.componente_codice ?? null,
    componente_descrizione: c.componente_descrizione ?? null,
    quantita: qtaValue,
    _qta_is_snapshot: hasSnapshotQta,
    uom_codice: c.uom_codice ?? null,
    prezzo_unitario: c.prezzo_unitario ?? c.prezzo ?? null,
    origine_prezzo: c.origine_prezzo ?? null,
    stato_approvazione_prezzo: c.stato_approvazione_prezzo ?? null,
    iva_codice: c.iva_codice ?? null,
    obbligatorio: c.obbligatorio === true,
    esposizione_in_fattura: c.esposizione_in_fattura ?? null,
  }
}

// Sorgente dati unificata: array reactive normalizzato. Le due modalita'
// convergono qui per non frammentare il rendering.
const componenti = computed(() => {
  const raw = isDataDriven.value
    ? coerceJsonbToArray(props.initialData)
    : fetcher.componenti.value
  return raw.map(normalizeRow)
})

const loading = computed(() => (isDataDriven.value ? false : fetcher.loading.value))

// L1: l'edit prezzo richiede l'azione `prezzo_override_manuale`. Stessa
// logica gia' applicata nella riga padre, qui replicata sui componenti
// (decisione di dominio: L1/L2/L3 sui componenti usano stessi parametri
// della riga padre).
const canOverride = computed(() => auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE))

// Auto-hide colonne metadata: in modalita' preview lo shape JSONB porta
// solo i dati base. Mostrare le colonne origine/approvazione/IVA vuote
// confonderebbe l'utente; il pannello le rimuove se nessuna riga visibile
// le ha valorizzate.
const hasOrigineData = computed(
  () => componenti.value.some((c) => c.origine_prezzo != null),
)
const hasApprovazioneData = computed(
  () => componenti.value.some((c) => c.stato_approvazione_prezzo != null),
)
const hasIvaData = computed(
  () => componenti.value.some((c) => c.iva_codice != null),
)
const qtaIsSnapshot = computed(
  () => componenti.value.some((c) => c._qta_is_snapshot),
)
// Label colonna q.ta' dinamica: "Q.tà" per snapshot persistito,
// "Coeff." per preview da listino (rapporto BoM puro).
const qtaColumnLabel = computed(
  () => t(localizedKey(qtaIsSnapshot.value ? 'col_qta' : 'col_coeff_qta')),
)

// Stato locale: prezzo in edit per ogni componente.
// Permette di editare PIU' componenti prima di salvarli uno alla volta —
// scelta UX semplice: l'operatore vede subito cosa sta cambiando, solo
// lo specifico componente in edit fa il PATCH.
const prezzoEditato = ref({})

// Reload sul cambio riga + cleanup mappa edit. Cambio rigaId invalida
// sempre gli edit pendenti (dato di un'altra riga) e ricarica.
// Watcher attivo SOLO in modalita' fetch-driven: in data-driven la
// sorgente e' la prop `initialData`, il rigaId e' un placeholder.
async function onRigaIdChange(id) {
  prezzoEditato.value = {}
  if (id == null || !fetcher) return
  try {
    await fetcher.load(id)
  } catch (err) {
    notify.error(extractApiError(err, t(localizedKey('errore_caricamento'))))
  }
}
if (!isDataDriven.value) {
  watch(() => props.rigaId, onRigaIdChange, { immediate: true })
}

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

// Modello unificato 2026-05-13: `obbligatorio` ed `esposizione_in_fattura`
// arrivano dalla proiezione BE (JOIN articoli_componenti).
function isObbligatorio(comp) {
  return comp.obbligatorio === true
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
  // FE-D2: lo zero resta invalido sugli obbligatori solo dove il documento
  // vende. Dove non vende (conto visione) e' il prezzo stesso a non avere
  // significato, quindi non c'e' niente da validare.
  if (props.prezzoRichiesto && isObbligatorio(comp) && Number(editVal) === 0) return false
  return true
}

function getPrezzoVisualizzato(comp) {
  // ⛔ FE-D3: `Number(null)` e' `0`, e uno zero qui sarebbe una BUGIA — la
  // cella direbbe «vale zero» dove il prezzo non c'e'. Si ritorna `null` e la
  // colonna mostra il tag «senza prezzo» (DEC-6).
  const grezzo = effectiveReadonly.value
    ? comp.prezzo_unitario
    : (prezzoEditato.value[comp.id] ?? comp.prezzo_unitario)
  return grezzo == null ? null : Number(grezzo)
}

function setPrezzoEditato(componenteId, val) {
  prezzoEditato.value = { ...prezzoEditato.value, [componenteId]: val }
}

// Scopo: PATCH del solo prezzo del componente con origine MANUALE. Il BE
// applica L1/L2/L3 (stessi parametri della riga padre).
// Disponibile solo in modalita' fetch-driven (data-driven e' readonly).
async function onSalvaPrezzo(comp) {
  if (!fetcher) return
  const nuovoPrezzo = prezzoEditato.value[comp.id]
  if (nuovoPrezzo == null) return
  if (!isPrezzoEditatoValido(comp)) {
    notify.warn(t(localizedKey('obbligatorio_zero'), {
      codice: comp.componente_codice || comp.componente_id,
    }))
    return
  }
  try {
    // `origine_prezzo` NON si manda: un prezzo scritto dall'operatore e'
    // MANUALE per definizione, e lo scrive il backend (contratto PATCH dei
    // componenti, 2026-09-26). Mandarlo ora e' un 400.
    await fetcher.update(props.rigaId, comp.id, {
      prezzo_unitario: nuovoPrezzo,
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
      <i :class="STATUS_ICONS.CARICAMENTO" /> {{ t('common.loading') }}
    </div>
    <div v-else-if="componenti.length === 0" class="componenti-panel-empty">
      {{ t(localizedKey('vuoto')) }}
    </div>
    <DataTable v-else :value="componenti" size="small" class="app-datatable app-datatable--inner" data-key="id">
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
      <Column :header="qtaColumnLabel" style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t(localizedKey('col_uom'))" style="width: 70px;" />
      <!-- I 180px servono all'input col bottone salva; in sola lettura il
           prezzo e' un numero, e la colonna larga allargava la tabella
           interna (scrollbar nella riga espansa del kit). -->
      <Column :header="t(localizedKey('col_prezzo'))"
              :style="effectiveReadonly ? 'width: 110px;' : 'width: 180px; min-width: 180px;'">
        <template #body="{ data }">
          <template v-if="effectiveReadonly">
            <!-- DEC-6: prezzo assente non e' prezzo zero, e non e' nemmeno una
                 cella vuota — quella si legge come «non l'ho ancora guardato». -->
            <Tag v-if="data.prezzo_unitario == null"
                 severity="secondary" :value="t(localizedKey('senza_prezzo'))" />
            <span v-else>{{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 2, maximumFractionDigits: 6 }) }}</span>
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
                :icon="MANAGE_ICONS.CONFIRM"
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
      <Column
        v-if="hasOrigineData || hasApprovazioneData"
        :header="t(localizedKey('col_origine'))" style="width: 100px;">
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
      <Column
        v-if="hasIvaData"
        field="iva_codice" :header="t(localizedKey('col_iva'))" style="width: 50px;" />
      <Column :header="t('vendite.componenti.col_esposto')" style="width: 150px;">
        <!-- Il modo per esteso (NASCOSTO / DESCRITTIVO / VALORIZZATO), con
             l'etichetta che il DB dichiara: dal 2026-10-01 non e' piu' un si'/no. -->
        <template #body="{ data }">
          <Tag
            :severity="severitaEsposizione(data.esposizione_in_fattura)"
            :value="etichettaEsposizione(data.esposizione_in_fattura)"
            class="app-tag-xs"
          />
        </template>
      </Column>
    </DataTable>
    <small v-if="!effectiveReadonly && componenti.length > 0" class="componenti-panel-hint">
      {{ t(localizedKey('section_hint')) }}
    </small>
    <small v-if="!effectiveReadonly && !canOverride && componenti.length > 0" class="componenti-panel-hint componenti-panel-hint-lock">
      <i :class="STATUS_ICONS.BLOCCATO" /> {{ t(localizedKey('l1_richiede_autorizzazione')) }}
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
