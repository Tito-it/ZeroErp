<script setup>
// Scopo: tab permessi dentro il drawer modifica utente.
// Sezioni: override aree, override azioni, emittenti scope.
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtentiStore } from '../stores/utenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { listAreeFunzionali, listAzioniProcesso, listEmittentiFiscali } from '../api/amministrazione'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import MultiSelect from 'primevue/multiselect'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useUtentiStore()
const { execute } = useApiHandler()

// Lookup via useLookup (non piu' dallo store)
const areeFunzionali = useLookup(listAreeFunzionali, { immediate: true })
const azioniProcesso = useLookup(listAzioniProcesso, { immediate: true })
const emittentiFiscali = useLookup(listEmittentiFiscali, { immediate: true })

const props = defineProps({
  authUserId: { type: Number, required: true }
})

const livelloOptions = [
  { label: 'TUTTO', value: 'TUTTO' },
  { label: 'LETTURA', value: 'LETTURA' },
  { label: 'BLOCCATO', value: 'BLOCCATO' }
]

const isAdmin = computed(() => store.currentUtente?.ruolo_sistema === 'ADMIN')

// Aree override locali (editabili)
const localAree = ref([])
const localAzioni = ref([])
const localEmittentiIds = ref([])

onMounted(async () => {
  await Promise.all([
    store.fetchOverrideAree(props.authUserId),
    store.fetchOverrideAzioni(props.authUserId),
    store.fetchEmittentiScope(props.authUserId)
  ])
  syncLocal()
})

function syncLocal() {
  localAree.value = store.overrideAree.map(a => ({ ...a }))
  localAzioni.value = store.overrideAzioni.map(a => ({ ...a }))
  localEmittentiIds.value = store.emittentiScope.map(e => e.emittente_fiscale_id)
}

async function saveAree() {
  const items = localAree.value.map(a => ({
    area_id: a.area_id,
    livello: a.livello,
    motivo: a.motivo || null,
    valido_dal: a.valido_dal || null,
    valido_al: a.valido_al || null
  }))
  await execute(
    () => store.saveOverrideAree(props.authUserId, items),
    { successMessage: t('notifications.save_success') }
  )
}

async function saveAzioni() {
  const items = localAzioni.value.map(a => ({
    azione_id: a.azione_id,
    abilitata: a.abilitata,
    motivo: a.motivo || null,
    valido_dal: a.valido_dal || null,
    valido_al: a.valido_al || null
  }))
  await execute(
    () => store.saveOverrideAzioni(props.authUserId, items),
    { successMessage: t('notifications.save_success') }
  )
}

async function saveEmittenti() {
  await execute(
    () => store.saveEmittentiScope(props.authUserId, localEmittentiIds.value),
    { successMessage: t('notifications.save_success') }
  )
}

function addAreaOverride() {
  localAree.value.push({
    area_id: null, livello: 'BLOCCATO', motivo: '', valido_dal: null, valido_al: null
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
</script>

<template>
  <div class="permessi-tab">
    <Message v-if="isAdmin" severity="info" :closable="false" class="mb-3">
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

    <!-- Emittenti Scope -->
    <h4>{{ t('amm.emittenti_scope_title') }}</h4>
    <p class="text-sm text-color-secondary mb-2">{{ t('amm.emittenti_scope_hint') }}</p>
    <MultiSelect
      v-model="localEmittentiIds"
      :options="emittentiFiscali.items.value"
      option-label="descrizione"
      option-value="id"
      :placeholder="t('amm.select_emittenti')"
      class="w-full mb-2"
      display="chip"
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
