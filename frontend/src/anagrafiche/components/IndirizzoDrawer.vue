<script setup>
// Scopo: drawer creazione/modifica indirizzo dettaglio.
// Modo CREA: comune → via (autocomplete o nuova) → civico.
// Modo EDIT: localizzazione read-only, solo civico editabile.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizziStore } from '../stores/indirizzi'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { listToponomastica, lookupCodiciPostaliByComune, getIndirizzo } from '../api/anagrafiche'
import { DRAWER_WIDTH } from '../../core/constants'
import { useIndirizzoDuplicato } from '../../core/composables/useIndirizzoDuplicato'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import ComuneAutocomplete from '../../core/components/ComuneAutocomplete.vue'
import StradarioAutocomplete from '../../core/components/StradarioAutocomplete.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  itemId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useIndirizziStore()
const { execute, loading } = useApiHandler()

// Lookup toponomastica per "via nuova"
const toponomasticaLookup = useLookup(
  () => listToponomastica({ limit: 200 })
)

// CAP per comune selezionato
const capOptions = ref([])
const loadingCap = ref(false)

// Form state
const comuneId = ref(null)
const stradarioObj = ref(null)
const viaNuova = ref(false)
const toponomasticaId = ref(null)
const nomeVia = ref('')
const codicePostaleId = ref(null)
const civico = ref(null)
const estensioneCivico = ref('')
const palazzina = ref('')
const scala = ref('')
const piano = ref('')
const interno = ref('')
const attivo = ref(true)

// Dettaglio edit (read-only)
const editDetail = ref(null)

// Check duplicato indirizzo (generico)
const { indirizzoWarnings, checkDuplicato, resetWarnings } = useIndirizzoDuplicato()

const isCreate = computed(() => props.mode === 'create')
const canSave = computed(() => {
  if (isCreate.value) {
    const hasVia = viaNuova.value
      ? (toponomasticaId.value && nomeVia.value.trim() && codicePostaleId.value)
      : stradarioObj.value
    return comuneId.value && hasVia
  }
  return true
})

// Reset form
function resetForm() {
  comuneId.value = null
  stradarioObj.value = null
  viaNuova.value = false
  toponomasticaId.value = null
  nomeVia.value = ''
  codicePostaleId.value = null
  civico.value = null
  estensioneCivico.value = ''
  palazzina.value = ''
  scala.value = ''
  piano.value = ''
  interno.value = ''
  attivo.value = true
  editDetail.value = null
  capOptions.value = []
  resetWarnings()
}

// Check duplicato quando cambia stradario o civico (solo in create)
watch([stradarioObj, civico], () => {
  if (!isCreate.value || !stradarioObj.value?.id) { resetWarnings(); return }
  checkDuplicato(stradarioObj.value.id, civico.value)
})

// Carica toponomastica solo quando serve (via nuova attivata)
watch(viaNuova, (val) => {
  if (val && !toponomasticaLookup.loaded.value) {
    toponomasticaLookup.load()
  }
})

// Carica CAP quando cambia il comune
watch(comuneId, async (id) => {
  capOptions.value = []
  codicePostaleId.value = null
  if (id) {
    loadingCap.value = true
    try {
      const res = await lookupCodiciPostaliByComune(id)
      capOptions.value = res.data.data.results
      if (capOptions.value.length === 1) {
        codicePostaleId.value = capOptions.value[0].id
      }
    } finally {
      loadingCap.value = false
    }
  }
})

// Carica dettaglio in edit
watch(() => props.visible, async (val) => {
  if (val) {
    resetForm()
    if (props.mode === 'edit' && props.itemId) {
      try {
        const res = await getIndirizzo(props.itemId)
        const d = res.data.data
        editDetail.value = d
        civico.value = d.civico
        estensioneCivico.value = d.estensione_civico || ''
        palazzina.value = d.palazzina || ''
        scala.value = d.scala || ''
        piano.value = d.piano || ''
        interno.value = d.interno || ''
        attivo.value = d.attivo ?? true
      } catch {
        emit('update:visible', false)
      }
    }
  }
})

async function handleSave() {
  let payload
  let successMsg

  if (isCreate.value) {
    successMsg = t('indirizzi.indirizzo_creato')
    if (viaNuova.value) {
      payload = {
        toponomastica_id: toponomasticaId.value,
        descrizione_via: nomeVia.value.trim(),
        comune_id: comuneId.value,
        codice_postale_id: codicePostaleId.value,
        civico: civico.value,
        estensione_civico: estensioneCivico.value.trim() || null,
        palazzina: palazzina.value.trim() || null,
        scala: scala.value.trim() || null,
        piano: piano.value.trim() || null,
        interno: interno.value.trim() || null
      }
    } else {
      payload = {
        stradario_id: stradarioObj.value?.id,
        civico: civico.value,
        estensione_civico: estensioneCivico.value.trim() || null,
        palazzina: palazzina.value.trim() || null,
        scala: scala.value.trim() || null,
        piano: piano.value.trim() || null,
        interno: interno.value.trim() || null
      }
    }
    const result = await execute(() => store.create(payload), { successMessage: successMsg })
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
      store.fetchList()
    }
  } else {
    successMsg = t('indirizzi.indirizzo_salvato')
    payload = {
      civico: civico.value,
      estensione_civico: estensioneCivico.value.trim() || null,
      palazzina: palazzina.value.trim() || null,
      scala: scala.value.trim() || null,
      piano: piano.value.trim() || null,
      interno: interno.value.trim() || null,
      attivo: attivo.value
    }
    const result = await execute(
      () => store.update(props.itemId, payload),
      { successMessage: successMsg }
    )
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
      store.fetchList()
    }
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :action="isCreate ? t('common.new') : t('common.edit')" :title="t('indirizzi.indirizzo')" icon="pi pi-map-marker" />
    </template>
    <div class="app-drawer-content">
      <!-- Localizzazione -->
      <div class="form-grid">
        <template v-if="isCreate">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_comune') }} *</label>
            <ComuneAutocomplete v-model="comuneId" />
          </div>

          <template v-if="!viaNuova">
            <div class="form-field">
              <label>{{ t('indirizzi.campo_via') }} *</label>
              <StradarioAutocomplete
                v-model="stradarioObj"
                :comune-id="comuneId"
                :disabled="!comuneId"
              />
            </div>
          </template>

          <div class="form-field">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <Checkbox v-model="viaNuova" :binary="true" input-id="via-nuova" />
              <label for="via-nuova">{{ t('indirizzi.via_non_presente') }}</label>
            </div>
          </div>

          <template v-if="viaNuova">
            <div class="form-field">
              <label>{{ t('indirizzi.campo_toponomastica') }} *</label>
              <Select
                v-model="toponomasticaId"
                :options="toponomasticaLookup.items.value"
                option-label="descrizione"
                option-value="id"
                :placeholder="t('indirizzi.campo_toponomastica')"
                :loading="toponomasticaLookup.loading.value"
              />
            </div>
            <div class="form-field">
              <label>{{ t('indirizzi.campo_nome_via') }} *</label>
              <InputText v-model="nomeVia" />
            </div>
            <div class="form-field">
              <label>{{ t('indirizzi.campo_cap') }} *</label>
              <Select
                v-model="codicePostaleId"
                :options="capOptions"
                option-label="codice"
                option-value="id"
                :placeholder="t('indirizzi.campo_cap')"
                :loading="loadingCap"
                :disabled="!comuneId"
              />
            </div>
          </template>
        </template>

        <!-- Edit: localizzazione read-only -->
        <template v-else-if="editDetail">
          <div class="form-field">
            <label>{{ t('indirizzi.col_indirizzo') }}</label>
            <InputText :model-value="editDetail.indirizzo_normalizzato" disabled />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.col_comune') }}</label>
            <InputText :model-value="`${editDetail.descrizione_comune} (${editDetail.provincia})`" disabled />
          </div>
        </template>
      </div>

      <!-- Civico -->
      <div class="form-grid" style="margin-top: 1rem;">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_civico') }}</label>
            <InputNumber v-model="civico" :use-grouping="false" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_estensione') }}</label>
            <InputText v-model="estensioneCivico" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_palazzina') }}</label>
            <InputText v-model="palazzina" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_scala') }}</label>
            <InputText v-model="scala" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_piano') }}</label>
            <InputText v-model="piano" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_interno') }}</label>
            <InputText v-model="interno" />
          </div>
        </div>

        <div v-if="!isCreate" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="attivo" />
        </div>
      </div>

      <Message v-for="(msg, i) in indirizzoWarnings" :key="i" severity="warn" size="small" class="mt-1">
        {{ msg }}
      </Message>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="emit('update:visible', false)"
      />
    </div>
  </Drawer>
</template>
