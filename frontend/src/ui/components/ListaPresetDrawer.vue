<script setup>
// Scopo: Drawer crea/modifica testata preset (`ui.lista_preset`).
//        Pattern standard:
//          - DrawerTitle (auto-include ReadonlyBadge se readonly)
//          - app-readonly su contenuto se isReadonly OR props.readonly
//          - FormFooter standard (Salva nascosto in readonly)
//          - Refs profilo/emittente condizionali ad ambito
//        Lookup profili_accesso e emittenti_fiscali via LookupSelect /
//        endpoint dedicato (admin only). Per tenere il componente minimale
//        e Fase 1 minimal, qui uso 2 InputNumber (id) — il super-admin
//        sa gli id; in Fase 2 si possono sostituire con autocomplete
//        ricchi senza cambiare il contratto del drawer.
//        Su un preset nato dal seed di primo impianto i campi del software
//        sono spenti col motivo e restano fuori dal PATCH (R-UI-sup di
//        brief-db-seed-primo-impianto-non-si-riscrive §16.15).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { DRAWER_WIDTH } from '../../core/constants'
import { USO_MISURA, misuraDefault, misureOpzioni } from '../../core/misurePagina'
import { NAV_ICONS } from '../../core/navigation'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useUiPresetAdminStore } from '../stores/uiPresetAdmin'
import { campoDelSoftware } from '../../core/utils/campoDelSoftware'
import MotivoDelProgramma from '../../core/components/MotivoDelProgramma.vue'
import { senzaCampiFermi } from '../../core/utils/senzaCampiFermi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordId: { type: Number, default: null },
  recordData: { type: Object, default: null },
  listaId: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const presetStore = useUiPresetAdminStore()
const { execute, loading, campiErrati } = useApiHandler()

const injectedReadonly = useInjectReadonly()
const isReadonlyEffective = computed(
  () => props.readonly || injectedReadonly.value,
)
const isEdit = computed(() => props.mode === 'edit')

// Scopo: il campo lo stabilisce il programma su questo preset (riga di
// seed)? L'elenco viaggia con la riga della lista (`campi_del_software`).
const delProgramma = (campo) => isEdit.value && campoDelSoftware(props.recordData, campo)

const ambitiOptions = computed(() => [
  { label: t('ui.admin.preset_ambito_sistema'), value: 'sistema' },
  { label: t('ui.admin.preset_ambito_emittente_fiscale'), value: 'emittente_fiscale' },
  { label: t('ui.admin.preset_ambito_ruolo'), value: 'ruolo' },
])

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    ambito: 'sistema',
    profilo_accesso_id: null,
    emittente_fiscale_id: null,
    pagina_dimensione: null,
    // ⭐ La bozza nasce spenta (Q26 di brief-db-revisione-ui): si compone e
    // poi si accende. Un posto ha al piu' un preset acceso (BE23).
    attivo: false,
  }
}

const form = ref(defaultForm())
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Prima del watch immediate (TDZ).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Watch su props.recordData per pre-popolare il form in edit. Usa la
// risposta admin che include gia' tutti i campi.
watch(
  () => [props.visible, props.recordData],
  ([visible, data]) => {
    if (!visible) return
    if (isEdit.value && data) {
      form.value = {
        codice: data.codice ?? '',
        descrizione: data.descrizione ?? '',
        ambito: data.ambito ?? 'sistema',
        profilo_accesso_id: data.profilo_accesso_id ?? null,
        emittente_fiscale_id: data.emittente_fiscale_id ?? null,
        pagina_dimensione: data.pagina_dimensione ?? null,
        attivo: !!data.attivo,
      }
    } else {
      form.value = defaultForm()
    }
    fissa()
  },
  { immediate: true },
)

// Reset refs quando cambia ambito (UX coerenza con CHECK ambito_refs DB).
watch(() => form.value.ambito, (nuovo) => {
  if (nuovo === 'sistema') {
    form.value.profilo_accesso_id = null
    form.value.emittente_fiscale_id = null
  } else if (nuovo === 'ruolo') {
    form.value.emittente_fiscale_id = null
  } else if (nuovo === 'emittente_fiscale') {
    form.value.profilo_accesso_id = null
  }
})

const canSave = computed(() => {
  if (!form.value.codice?.trim()) return false
  if (!form.value.descrizione?.trim()) return false
  if (!form.value.ambito) return false
  if (form.value.ambito === 'ruolo' && !form.value.profilo_accesso_id) return false
  if (form.value.ambito === 'emittente_fiscale' && !form.value.emittente_fiscale_id) return false
  return true
})

function buildPayload() {
  const payload = {
    codice: form.value.codice.trim(),
    descrizione: form.value.descrizione.trim(),
    attivo: form.value.attivo,
  }
  // Sempre, anche NULL: in modifica e' il modo di tornare al default. Prima si
  // mandava solo se valorizzata, e una misura tolta a video restava a DB.
  payload.pagina_dimensione = form.value.pagina_dimensione ?? null
  if (!isEdit.value) {
    // Campi immutabili: solo in create.
    payload.ambito = form.value.ambito
    if (form.value.ambito === 'ruolo') {
      payload.profilo_accesso_id = form.value.profilo_accesso_id
    } else if (form.value.ambito === 'emittente_fiscale') {
      payload.emittente_fiscale_id = form.value.emittente_fiscale_id
    }
  }
  return payload
}

async function onSave() {
  if (!canSave.value) return
  // ⛔ Un campo del programma non entra nel PATCH: il guard del DB lo rifiuta.
  const payload = isEdit.value ? senzaCampiFermi(buildPayload(), delProgramma) : buildPayload()
  let result
  if (isEdit.value) {
    result = await execute(
      () => presetStore.update(props.recordId, payload),
      { successMessage: t('notifications.save_success') },
    )
  } else {
    result = await execute(
      () => presetStore.create(props.listaId, payload),
      { successMessage: t('notifications.save_success') },
    )
  }
  if (result !== null) {
    emit('saved', result)
  }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('ui.admin.preset')"
    :icon="NAV_ICONS.PERSONALIZZAZIONI_LISTE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :readonly="isReadonlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="isReadonlyEffective ? 'chiudi' : 'form'"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
    <div class="form-grid">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('ui.admin.preset_codice') }}</label>
          <InputText v-model="form.codice" maxlength="80"
            :disabled="delProgramma('codice')"
            :invalid="campiErrati.includes('codice')"
          />
          <MotivoDelProgramma campo="codice" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
        </div>
        <div class="form-field">
          <label>{{ t('ui.admin.preset_pagina_dimensione') }}</label>
          <!-- ⭐ Le misure del catalogo DB (`ui.misure_pagina`), non un numero
               libero: fino al 2026-09-30 era un InputNumber 1-500, che faceva
               scrivere misure che il paginatore non offre. Vuoto = «il
               default» (NULL a DB). -->
          <Select
            v-model="form.pagina_dimensione"
            :options="misureOpzioni()"
            :placeholder="t('ui.admin.preset_pagina_dimensione_default', { misura: misuraDefault(USO_MISURA.PAGINA) })"
            show-clear
            :disabled="delProgramma('pagina_dimensione')"
            :invalid="campiErrati.includes('pagina_dimensione')"
          />
          <MotivoDelProgramma campo="pagina_dimensione" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.preset_descrizione') }}</label>
        <InputText v-model="form.descrizione" maxlength="200"
          :disabled="delProgramma('descrizione')"
          :invalid="campiErrati.includes('descrizione')"
        />
        <MotivoDelProgramma campo="descrizione" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.preset_ambito') }}</label>
        <Select
          v-model="form.ambito"
          :options="ambitiOptions"
          option-label="label"
          option-value="value"
          :disabled="isEdit"
          :invalid="campiErrati.includes('ambito')"
        />
        <Message
          v-if="isEdit"
          severity="info"
          :closable="false"
          size="small"
          class="mt-025"
        >
          {{ t('ui.admin.preset_ambito_immutabile') }}
        </Message>
      </div>

      <div v-if="form.ambito === 'ruolo'" class="form-field">
        <label>{{ t('ui.admin.preset_profilo_accesso') }}</label>
        <LookupSelect
          v-if="!isEdit"
          v-model="form.profilo_accesso_id"
          rel="config.profili_accesso"
          show-code
          :placeholder="t('ui.admin.preset_seleziona_profilo')"
        />
        <InputText
          v-else
          :model-value="recordData?.profilo_accesso_codice ?? ''"
          readonly
        />
      </div>
      <div v-else-if="form.ambito === 'emittente_fiscale'" class="form-field">
        <label>{{ t('ui.admin.preset_emittente_fiscale') }}</label>
        <!-- emittenti_fiscali non e' nella whitelist lookup generico
             (campi non standard); manteniamo InputNumber per ora.
             Fase 2: switch a EmittenteFiscaleField (gia' building block). -->
        <InputNumber
          v-if="!isEdit"
          v-model="form.emittente_fiscale_id"
          :min="1"
          show-buttons
          :invalid="campiErrati.includes('emittente_fiscale_id')"
        />
        <InputText
          v-else
          :model-value="recordData?.emittente_fiscale_codice ?? ''"
          readonly
        />
      </div>

      <div class="form-grid-2col">
        <div class="form-field form-field-inline">
          <Checkbox v-model="form.attivo" binary input-id="ui-preset-attivo"
            :disabled="delProgramma('attivo')"
            :invalid="campiErrati.includes('attivo')"
          />
          <label for="ui-preset-attivo">{{ t('common.active') }}</label>
          <MotivoDelProgramma campo="attivo" :fermo="delProgramma" :testo="t('ui.admin.campo_del_programma')" />
        </div>
      </div>
    </div>
  </AppDrawer>
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
</style>
