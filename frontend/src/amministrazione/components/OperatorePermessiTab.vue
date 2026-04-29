<script setup>
// Scopo: Componente permessi operatore riutilizzabile.
// Sezioni: override aree, override azioni, emittenti scope.
// Usato sia dentro il TabView di OperatoreDrawer sia dal
// drawer dedicato OperatorePermessiDrawer (azione rapida dalla lista).
// Reagisce automaticamente al cambio di authUserId.
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useNotify } from '../../core/composables/useNotify'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { listAreeFunzionali, listAzioniProcesso, listEmittentiFiscali, getModelOverridesLookup } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import RadioButton from 'primevue/radiobutton'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useOperatoriStore()
const notify = useNotify()
// Readonly inject: il tab puo' essere usato dentro OperatoreDrawer in modalita'
// readonly o dentro OperatorePermessiDrawer; in entrambi i casi i pulsanti
// add/save/trash e i Select/ToggleSwitch di riga vanno disattivati.
const isReadonly = useInjectReadonly()

// Lookup via useLookup (non piu' dallo store)
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })
const modelOverrides = useLookup(getModelOverridesLookup, { immediate: true })
const emittentiFiscali = useLookup(listEmittentiFiscali, { immediate: true })

const props = defineProps({
  authUserId: { type: Number, required: true }
})

const livelloOptions = buildLivelloOptions(t)

// Multi-face auth: flag SUPER_ADMIN dal detail dell'operatore gestito
// (non dal user corrente auth). Se il detail non e' ancora caricato,
// loadAll() lo fetcha. Banner "admin ha accesso totale" guidato da qui.
const isSuperAdmin = computed(() => store.currentOperatore?.is_super_admin === true)

// Stato locale editabile (mantenuto separato dallo store per permettere undo
// logico tra un save e l'altro e per non mutare direttamente lo store).
const localAree = ref([])
const localAzioni = ref([])
const localOggetti = ref([])

// Fase 2 multi-face: scope dichiarativo. `localScopeMode` e' la radio
// attualmente selezionata; `localEmittenteId` e' l'id selezionato quando
// scope_mode='SINGLE'. Salvataggio costruisce il payload
// `{scope_mode, emittenti_ids}` dal couple.
const localScopeMode = ref('GLOBAL')
const localEmittenteId = ref(null)

// Scopo: Carica tutto lo stato necessario per il componente.
//        Viene chiamato dal watch su authUserId (immediate) e garantisce
//        che currentOperatore, overrideAree/azioni, emittentiScope siano
//        coerenti con l'utente passato.
async function loadAll(userId) {
  if (!userId) return
  const needDetail = store.currentOperatore?.auth_user_id !== userId
  await Promise.all([
    needDetail ? store.fetchDetail(userId) : Promise.resolve(),
    store.fetchOverrideAree(userId),
    store.fetchOverrideAzioni(userId),
    store.fetchOverrideOggetti(userId),
    store.fetchEmittentiScope(userId)
  ])
  syncLocal()
}

watch(() => props.authUserId, loadAll, { immediate: true })

function syncLocal() {
  localAree.value = store.overrideAree.map(a => ({ ...a }))
  localAzioni.value = store.overrideAzioni.map(a => ({ ...a }))
  localOggetti.value = store.overrideOggetti.map(o => ({ ...o }))
  localScopeMode.value = store.emittentiScope.scope_mode || 'GLOBAL'
  localEmittenteId.value = (store.emittentiScope.emittenti_ids || [])[0] ?? null
}

// Capability esposte dal BE: render condizionale e disable/tooltip.
const allowedScopeModes = computed(() => store.emittentiScope.allowed_scope_modes || ['GLOBAL', 'SINGLE'])
const canChangeScope = computed(() => store.emittentiScope.can_change_scope !== false)
const changeScopeReason = computed(() => store.emittentiScope.change_scope_reason || null)
const scopeModeOptions = computed(() => [
  { value: 'GLOBAL', label: t('amm.scope_mode_global'), disabled: !allowedScopeModes.value.includes('GLOBAL') },
  { value: 'SINGLE', label: t('amm.scope_mode_single'), disabled: !allowedScopeModes.value.includes('SINGLE') },
])

// Pattern: store action gia' unwrappate → chiamata diretta + try/catch.
// useApiHandler.execute() e' SOLO per response axios (feedback_useapihandler_solo_axios).
//
// Helper consolidato per saveAree/Azioni/Oggetti/Emittenti: ogni save ha la
// stessa struttura (guard readonly + chiamata store + notify success +
// catch silente per delegare all'interceptor globale). Estraendo l'helper
// evitiamo la copia-incolla che renderebbe fragile un eventuale fix di pattern.
async function _saveOverride(action, items, afterSuccess) {
  if (isReadonly.value) return
  try {
    await action(props.authUserId, items)
    notify.success(t('notifications.save_success'))
    afterSuccess?.()
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

// Mapper per la riga area override -> payload BE.
const _toAreaItem = (a) => ({
  area_id: a.area_id,
  livello: a.livello,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toAzioneItem = (a) => ({
  azione_id: a.azione_id,
  abilitata: a.abilitata,
  motivo: a.motivo || null,
  valido_dal: a.valido_dal || null,
  valido_al: a.valido_al || null,
})

const _toOggettoItem = (o) => ({
  app_label: o.app_label,
  model_name: o.model_name,
  livello: o.livello,
  motivo: o.motivo || null,
  valido_dal: o.valido_dal || null,
  valido_al: o.valido_al || null,
})

const saveAree = () =>
  _saveOverride(store.saveOverrideAree, localAree.value.map(_toAreaItem))

const saveAzioni = () =>
  _saveOverride(store.saveOverrideAzioni, localAzioni.value.map(_toAzioneItem))

// Costruzione payload Fase 2: GLOBAL -> emittenti_ids: []; SINGLE -> [id].
// La validazione e' centralizzata sul BE (E_AMM_SCOPE_NON_AMMESSO se SINGLE
// senza emittente). Qui blocchiamo solo lato UX per evitare round-trip.
function _buildScopePayload() {
  if (localScopeMode.value === 'GLOBAL') {
    return { scope_mode: 'GLOBAL', emittenti_ids: [] }
  }
  return { scope_mode: 'SINGLE', emittenti_ids: localEmittenteId.value != null ? [localEmittenteId.value] : [] }
}

const canSaveEmittenti = computed(() => {
  if (!canChangeScope.value) return false
  // Defense-in-depth: la modalita' selezionata deve essere ammessa dal BE.
  // Se in futuro `allowed_scope_modes` venisse ridotto (es. lockdown sul
  // SUPER_ADMIN), evita un round-trip che ritorna E_AMM_SCOPE_NON_AMMESSO.
  if (!allowedScopeModes.value.includes(localScopeMode.value)) return false
  if (localScopeMode.value === 'SINGLE' && localEmittenteId.value == null) return false
  return true
})

const saveEmittenti = () => {
  if (!canSaveEmittenti.value) return
  return _saveOverride(
    store.saveEmittentiScope,
    _buildScopePayload(),
    // Refresh asincrono lista operatori (la `emittenti_descrizione` puo'
    // essere cambiata): dopo il prossimo render frame per non interrompere
    // l'animazione del toast.
    () => nextTick(() => store.fetchList().catch(() => {})),
  )
}

function addAreaOverride() {
  localAree.value.push({
    area_id: null, livello: LIVELLO_ACCESSO.BLOCCATO, motivo: '', valido_dal: null, valido_al: null
  })
}

function removeAreaOverride(index) {
  localAree.value.splice(index, 1)
}

function addAzioneOverride() {
  localAzioni.value.push({
    azione_id: null, abilitata: false, motivo: '', valido_dal: null, valido_al: null
  })
}

function removeAzioneOverride(index) {
  localAzioni.value.splice(index, 1)
}

// Scopo: Label per il dropdown model override (es. "anagrafiche.conto_bancario — Anagrafiche").
const modelOverrideOptions = computed(() =>
  modelOverrides.items.value.map(m => ({
    ...m,
    label: `${m.app_label}.${m.model_name} — ${m.area_descrizione}`
  }))
)

const saveOggetti = () =>
  _saveOverride(store.saveOverrideOggetti, localOggetti.value.map(_toOggettoItem))

function addOggettoOverride() {
  localOggetti.value.push({
    app_label: null, model_name: null, livello: LIVELLO_ACCESSO.BLOCCATO,
    motivo: '', valido_dal: null, valido_al: null
  })
}

function removeOggettoOverride(index) {
  localOggetti.value.splice(index, 1)
}

function onModelSelect(item, row) {
  if (item) {
    row.app_label = item.app_label
    row.model_name = item.model_name
  }
}
</script>

<template>
  <div class="permessi-tab">
    <Message v-if="isSuperAdmin" severity="info" :closable="false" class="mb-3">
      {{ t('amm.admin_full_access') }}
    </Message>

    <!-- Override Aree -->
    <h4>{{ t('amm.override_aree_title') }}</h4>
    <DataTable :value="localAree" class="mb-2" size="small">
      <Column :header="t('amm.col_area')">
        <template #body="{ data }">
          <Select v-model="data.area_id" :options="areeFunzionali.items.value"
            option-label="descrizione" option-value="id" class="w-full"
            :disabled="isReadonly" />
        </template>
      </Column>
      <Column :header="t('amm.col_livello')">
        <template #body="{ data }">
          <Select v-model="data.livello" :options="livelloOptions"
            option-label="label" option-value="value" class="w-full"
            :disabled="isReadonly" />
        </template>
      </Column>
      <Column v-if="!isReadonly" style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeAreaOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div v-if="!isReadonly" class="flex justify-between mb-4">
      <Button :label="t('amm.add_override')" icon="pi pi-plus" text @click="addAreaOverride" />
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveAree" />
    </div>

    <!-- Override Azioni -->
    <h4>{{ t('amm.override_azioni_title') }}</h4>
    <DataTable :value="localAzioni" class="mb-2" size="small">
      <Column :header="t('amm.col_azione')">
        <template #body="{ data }">
          <Select v-model="data.azione_id" :options="azioniProcesso.items.value"
            option-label="descrizione" option-value="id" class="w-full"
            :disabled="isReadonly" />
        </template>
      </Column>
      <Column :header="t('amm.col_abilitata')" style="width: 6rem">
        <template #body="{ data }">
          <ToggleSwitch v-model="data.abilitata" :disabled="isReadonly" />
        </template>
      </Column>
      <Column v-if="!isReadonly" style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeAzioneOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div v-if="!isReadonly" class="flex justify-between mb-4">
      <Button :label="t('amm.add_override')" icon="pi pi-plus" text @click="addAzioneOverride" />
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveAzioni" />
    </div>

    <!-- Override Oggetti (v2 permessi — livello model) -->
    <h4>{{ t('amm.override_oggetti_title') }}</h4>
    <DataTable :value="localOggetti" class="mb-2" size="small">
      <Column :header="t('amm.col_model')">
        <template #body="{ data }">
          <Select
            :modelValue="data.app_label && data.model_name ? modelOverrideOptions.find(m => m.app_label === data.app_label && m.model_name === data.model_name) : null"
            :options="modelOverrideOptions"
            option-label="label"
            :placeholder="t('amm.select_model')"
            class="w-full"
            :disabled="isReadonly"
            @update:modelValue="v => onModelSelect(v, data)"
          />
        </template>
      </Column>
      <Column :header="t('amm.col_livello')">
        <template #body="{ data }">
          <Select v-model="data.livello" :options="livelloOptions"
            option-label="label" option-value="value" class="w-full"
            :disabled="isReadonly" />
        </template>
      </Column>
      <Column v-if="!isReadonly" style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeOggettoOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div v-if="!isReadonly" class="flex justify-between mb-4">
      <Button :label="t('amm.add_override')" icon="pi pi-plus" text @click="addOggettoOverride" />
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveOggetti" />
    </div>

    <!-- Emittenti Scope (Fase 2 multi-face) -->
    <h4>{{ t('amm.emittenti_scope_title') }}</h4>
    <p class="text-sm text-color-secondary mb-2">{{ t('amm.emittenti_scope_hint') }}</p>

    <!-- Radio scope: GLOBAL/SINGLE. `MULTI` non e' incluso in
         allowed_scope_modes post Q2 (architetturalmente chiuso). -->
    <div
      class="scope-radio-group mb-2"
      v-tooltip.bottom="!canChangeScope ? changeScopeReason : null"
    >
      <div
        v-for="opt in scopeModeOptions"
        :key="opt.value"
        class="scope-radio-row"
      >
        <RadioButton
          v-model="localScopeMode"
          :value="opt.value"
          :input-id="'scope-mode-' + opt.value"
          :disabled="isReadonly || !canChangeScope || opt.disabled"
        />
        <label :for="'scope-mode-' + opt.value" class="scope-radio-label">{{ opt.label }}</label>
      </div>
    </div>

    <!-- Select emittente: visibile solo in SINGLE -->
    <Select
      v-if="localScopeMode === 'SINGLE'"
      v-model="localEmittenteId"
      :options="emittentiFiscali.items.value"
      option-label="ragione_sociale"
      option-value="id"
      :placeholder="t('amm.select_emittenti')"
      show-clear
      class="w-full mb-2"
      :disabled="isReadonly || !canChangeScope"
    />

    <div v-if="!isReadonly" class="flex justify-end">
      <Button
        :label="t('common.save')"
        icon="pi pi-check"
        size="small"
        :disabled="!canSaveEmittenti"
        @click="saveEmittenti"
      />
    </div>
  </div>
</template>

<style scoped>
.permessi-tab {
  padding: 0.5rem 0;
}
h4 {
  margin-bottom: 0.5rem;
  margin-top: 1rem;
}
h4:first-child {
  margin-top: 0;
}
.scope-radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.scope-radio-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.scope-radio-label {
  cursor: pointer;
}
</style>
