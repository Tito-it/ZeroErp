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
import { listAreeFunzionali, listAzioniProcesso, listEmittentiFiscali, getModelOverridesLookup } from '../api/amministrazione'
import { LIVELLO_ACCESSO, buildLivelloOptions } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useOperatoriStore()
const notify = useNotify()

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
const localEmittentiIds = ref([])

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
  localEmittentiIds.value = store.emittentiScope.map(e => e.emittente_fiscale_id)
}

// Pattern: store action gia' unwrappate → chiamata diretta + try/catch.
// useApiHandler.execute() e' SOLO per response axios (feedback_useapihandler_solo_axios).
async function saveAree() {
  const items = localAree.value.map(a => ({
    area_id: a.area_id,
    livello: a.livello,
    motivo: a.motivo || null,
    valido_dal: a.valido_dal || null,
    valido_al: a.valido_al || null
  }))
  try {
    await store.saveOverrideAree(props.authUserId, items)
    notify.success(t('notifications.save_success'))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

async function saveAzioni() {
  const items = localAzioni.value.map(a => ({
    azione_id: a.azione_id,
    abilitata: a.abilitata,
    motivo: a.motivo || null,
    valido_dal: a.valido_dal || null,
    valido_al: a.valido_al || null
  }))
  try {
    await store.saveOverrideAzioni(props.authUserId, items)
    notify.success(t('notifications.save_success'))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

async function saveEmittenti() {
  try {
    await store.saveEmittentiScope(props.authUserId, localEmittentiIds.value)
    notify.success(t('notifications.save_success'))
    nextTick(() => store.fetchList().catch(() => {}))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
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

async function saveOggetti() {
  const items = localOggetti.value.map(o => ({
    app_label: o.app_label,
    model_name: o.model_name,
    livello: o.livello,
    motivo: o.motivo || null,
    valido_dal: o.valido_dal || null,
    valido_al: o.valido_al || null
  }))
  try {
    await store.saveOverrideOggetti(props.authUserId, items)
    notify.success(t('notifications.save_success'))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

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
            option-label="descrizione" option-value="id" class="w-full" />
        </template>
      </Column>
      <Column :header="t('amm.col_livello')">
        <template #body="{ data }">
          <Select v-model="data.livello" :options="livelloOptions"
            option-label="label" option-value="value" class="w-full" />
        </template>
      </Column>
      <Column style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeAreaOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div class="flex justify-between mb-4">
      <Button :label="t('amm.add_override')" icon="pi pi-plus" text @click="addAreaOverride" />
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveAree" />
    </div>

    <!-- Override Azioni -->
    <h4>{{ t('amm.override_azioni_title') }}</h4>
    <DataTable :value="localAzioni" class="mb-2" size="small">
      <Column :header="t('amm.col_azione')">
        <template #body="{ data }">
          <Select v-model="data.azione_id" :options="azioniProcesso.items.value"
            option-label="descrizione" option-value="id" class="w-full" />
        </template>
      </Column>
      <Column :header="t('amm.col_abilitata')" style="width: 6rem">
        <template #body="{ data }">
          <ToggleSwitch v-model="data.abilitata" />
        </template>
      </Column>
      <Column style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeAzioneOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div class="flex justify-between mb-4">
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
            @update:modelValue="v => onModelSelect(v, data)"
          />
        </template>
      </Column>
      <Column :header="t('amm.col_livello')">
        <template #body="{ data }">
          <Select v-model="data.livello" :options="livelloOptions"
            option-label="label" option-value="value" class="w-full" />
        </template>
      </Column>
      <Column style="width: 3rem">
        <template #body="{ index }">
          <Button icon="pi pi-trash" severity="danger" text @click="removeOggettoOverride(index)" />
        </template>
      </Column>
    </DataTable>
    <div class="flex justify-between mb-4">
      <Button :label="t('amm.add_override')" icon="pi pi-plus" text @click="addOggettoOverride" />
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveOggetti" />
    </div>

    <!-- Emittenti Scope -->
    <h4>{{ t('amm.emittenti_scope_title') }}</h4>
    <p class="text-sm text-color-secondary mb-2">{{ t('amm.emittenti_scope_hint') }}</p>
    <Select
      :modelValue="localEmittentiIds.length ? localEmittentiIds[0] : null"
      :options="emittentiFiscali.items.value"
      option-label="ragione_sociale"
      option-value="id"
      :placeholder="t('amm.select_emittenti')"
      show-clear
      class="w-full mb-2"
      @update:modelValue="v => localEmittentiIds = v != null ? [v] : []"
    />
    <div class="flex justify-end">
      <Button :label="t('common.save')" icon="pi pi-check" size="small" @click="saveEmittenti" />
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
</style>
