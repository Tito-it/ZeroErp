<script setup>
// Scopo: drawer creazione/modifica indirizzo dettaglio.
// Modo CREA: comune → via (autocomplete o nuova) → civico.
// Modo EDIT: localizzazione read-only, solo civico editabile.
// Usa useIndirizzoBase per logica condivisa (CAP, duplicato, via nuova).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useIndirizziStore } from '../stores/indirizzi'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useIndirizzoBase, buildCivicoPart } from '../composables/useIndirizzoBase'
import { getIndirizzo } from '../api/anagrafiche'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import CivicoDettaglioCampi from './CivicoDettaglioCampi.vue'
import StradarioAutocomplete from './StradarioAutocomplete.vue'
import StradarioGeneraleAutocomplete from './StradarioGeneraleAutocomplete.vue'
import InputText from 'primevue/inputtext'
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
const { execute, loading, campiErrati } = useApiHandler()
const addr = useIndirizzoBase()

// Edit: dettaglio read-only + attivo
const editDetail = ref(null)
const attivo = ref(true)

// Modifiche non salvate (BB useDrawerFormPreserve): il form salvato e' il form
// indirizzo del composable piu' il toggle `attivo`, visti come un oggetto solo.
const formSalvato = computed(() => ({ ...addr.form, attivo: attivo.value }))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

const isCreate = computed(() => props.mode === 'create')
const canSave = computed(() => {
  if (isCreate.value) return addr.validate().length === 0
  return true
})

// Blocca save se indirizzo da stradario non trovato (centralizzato in useIndirizzoBase).
// Aggiunge condizione locale: solo in modalita' create.
const addressNotFound = computed(() =>
  isCreate.value && addr.addressNotFound.value
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
        return
      }
    }
    fissa()
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
    payload = { ...buildCivicoPart(addr.form), attivo: attivo.value }
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
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('indirizzi.indirizzo')"
    :icon="NAV_ICONS.INDIRIZZO"
    :action="isCreate ? t('common.new') : t('common.edit')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave || addressNotFound"
    @update:visible="(v) => emit('update:visible', v)"
    @save="handleSave"
  >
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
    <div class="form-grid mt-1">
      <CivicoDettaglioCampi :form="addr.form" :campi-errati="campiErrati" />

      <div v-if="!isCreate" class="form-field">
        <label>{{ t('indirizzi.campo_attivo') }}</label>
        <ToggleSwitch v-model="attivo" />
      </div>
    </div>

    <Message v-for="(msg, i) in addr.indirizzoWarnings.value" :key="i" severity="info" size="small" class="mt-1">
      {{ msg }}
    </Message>

    <Message v-if="addressNotFound" severity="warn" size="small" class="mt-1">
      {{ t('anagrafiche.indirizzo_soggetto.replace_non_trovato') }}
    </Message>
  </AppDrawer>
</template>
