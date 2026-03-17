<script setup>
// Scopo: drawer creazione/modifica indirizzo dettaglio.
// Modo CREA: comune → via (autocomplete o nuova) → civico.
// Modo EDIT: localizzazione read-only, solo civico editabile.
// Usa useIndirizzoBase per logica condivisa (CAP, duplicato, via nuova).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizziStore } from '../stores/indirizzi'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useIndirizzoBase } from '../../core/composables/useIndirizzoBase'
import { getIndirizzo } from '../api/anagrafiche'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import ComuneAutocomplete from '../../core/components/ComuneAutocomplete.vue'
import StradarioAutocomplete from '../../core/components/StradarioAutocomplete.vue'
import StradarioGeneraleAutocomplete from '../../core/components/StradarioGeneraleAutocomplete.vue'
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
const addr = useIndirizzoBase()

// Edit: dettaglio read-only + attivo
const editDetail = ref(null)
const attivo = ref(true)

const isCreate = computed(() => props.mode === 'create')
const canSave = computed(() => {
  if (isCreate.value) return addr.validate().length === 0
  return true
})

// Blocca save se: via da stradario (non via_nuova), civico inserito,
// ma l'indirizzo esatto non esiste in DB. Stessa logica di IndirizziSoggettoDrawer.
const addressNotFound = computed(() =>
  isCreate.value
  && !addr.form.via_nuova
  && addr.form.via_obj?.stradario_id
  && addr.form.civico
  && !addr.existingDettaglioId.value
)

function resetForm() {
  addr.reset()
  editDetail.value = null
  attivo.value = true
}

// Carica dettaglio in edit
watch(() => props.visible, async (val) => {
  if (val) {
    resetForm()
    if (props.mode === 'edit' && props.itemId) {
      try {
        const res = await getIndirizzo(props.itemId)
        const d = res.data.data
        editDetail.value = d
        addr.restore({
          civico: d.civico,
          estensione_civico: d.estensione_civico,
          palazzina: d.palazzina,
          scala: d.scala,
          piano: d.piano,
          interno: d.interno,
        })
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
    payload = addr.buildPayload()
    const result = await execute(() => store.create(payload), { successMessage: successMsg })
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
      store.fetchList()
    }
  } else {
    successMsg = t('indirizzi.indirizzo_salvato')
    payload = {
      civico: addr.form.civico,
      estensione_civico: (addr.form.estensione_civico || '').trim() || null,
      palazzina: (addr.form.palazzina || '').trim() || null,
      scala: (addr.form.scala || '').trim() || null,
      piano: (addr.form.piano || '').trim() || null,
      interno: (addr.form.interno || '').trim() || null,
      attivo: attivo.value,
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
            <ComuneAutocomplete v-model="addr.form.comune_id" />
          </div>

          <template v-if="!addr.form.via_nuova">
            <div class="form-field">
              <label>{{ t('indirizzi.campo_via') }} *</label>
              <StradarioAutocomplete
                v-model="addr.form.via_obj"
                :comune-id="addr.form.comune_id"
                :disabled="!addr.form.comune_id"
              />
            </div>
          </template>

          <div class="form-field">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <Checkbox v-model="addr.form.via_nuova" :binary="true" input-id="via-nuova" />
              <label for="via-nuova">{{ t('indirizzi.via_non_presente') }}</label>
            </div>
          </div>

          <template v-if="addr.form.via_nuova">
            <div class="form-field">
              <label>{{ t('indirizzi.campo_via') }} *</label>
              <StradarioGeneraleAutocomplete v-model="addr.form.via_obj" />
            </div>
          </template>

          <!-- CAP: sempre visibile (auto-set da stradario, fallback da comune) -->
          <div class="form-field">
            <label>{{ t('indirizzi.campo_cap') }} *</label>
            <Select
              v-model="addr.form.codice_postale_id"
              :options="addr.capOptions.value"
              option-label="codice"
              option-value="id"
              :placeholder="t('indirizzi.campo_cap')"
              :loading="addr.loadingCap.value"
              :disabled="!addr.form.comune_id"
            />
          </div>
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
            <InputNumber v-model="addr.form.civico" :use-grouping="false" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_estensione') }}</label>
            <InputText :model-value="addr.form.estensione_civico" @update:model-value="v => addr.form.estensione_civico = (v || '').toUpperCase()" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_palazzina') }}</label>
            <InputText v-model="addr.form.palazzina" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_scala') }}</label>
            <InputText v-model="addr.form.scala" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_piano') }}</label>
            <InputText v-model="addr.form.piano" />
          </div>
          <div class="form-field">
            <label>{{ t('indirizzi.campo_interno') }}</label>
            <InputText v-model="addr.form.interno" />
          </div>
        </div>

        <div v-if="!isCreate" class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="attivo" />
        </div>
      </div>

      <Message v-for="(msg, i) in addr.indirizzoWarnings.value" :key="i" severity="info" size="small" class="mt-1">
        {{ msg }}
      </Message>

      <Message v-if="addressNotFound" severity="warn" size="small" class="mt-1">
        {{ t('indirizzo_soggetto.replace_non_trovato') }}
      </Message>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave || addressNotFound"
        @save="handleSave"
        @cancel="emit('update:visible', false)"
      />
    </div>
  </Drawer>
</template>
