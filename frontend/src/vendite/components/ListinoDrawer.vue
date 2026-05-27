<script setup>
// Scopo: Drawer crea/modifica listino.
//        In edit: pulsanti per aprire drawer autonomi versioni (eventi al parent).
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useAuthStore } from '../../stores/auth'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import TipologiaListinoSelect from './TipologiaListinoSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useListiniStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const auth = useAuthStore()

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata, DB 2026-05-02). Il composable risolve a id locale
// via lookup utilities-per-emittente.
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  listinoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

// Deferimento contenuto (pattern feedback_content_ready_after_show
// centralizzato in useDrawerContentReady).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Flag di soppressione reset tipologia durante il caricamento iniziale in edit.
// Evita che il watch su form.value.utility_id azzeri la tipologia che loadDetail
// sta impostando contestualmente a utility_id.
const isLoadingDetail = ref(false)

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    utility_id: utilityDefaultId.value,
    tipologia_id: null,
    attivo: true,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.listinoId) return
  isLoadingDetail.value = true
  try {
    const data = await store.fetchDetail(props.listinoId)
    if (!data) return
    detail.value = data
    form.value = {
      codice: data.codice || '',
      descrizione: data.descrizione || '',
      utility_id: data.utility_id ?? null,
      tipologia_id: data.tipologia_id ?? null,
      attivo: data.attivo ?? true
    }
  } finally {
    // nextTick non serve: il watch e' flush:'post' di default e vedra'
    // entrambe le assegnazioni nello stesso batch con isLoadingDetail true.
    isLoadingDetail.value = false
  }
}

watch(() => props.visible, async (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  // Carica il default utility (parameter + lookup) prima di resetForm:
  // defaultForm() legge utilityDefaultId.value gia' risolto a id locale.
  await loadUtilityDefault()
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

// Scopo: Watch su utility_id — al cambio reale (non al caricamento iniziale),
// azzera la tipologia selezionata. La matrice `config.listini_tipologie_utilities`
// puo' cambiare le tipologie ammesse; un valore residuo porterebbe all'errore
// del trigger DB. La guard `isLoadingDetail` sopprime il reset durante la
// load di un listino esistente (dove utility_id e tipologia_id sono coerenti
// per costruzione).
watch(() => form.value.utility_id, (newVal, oldVal) => {
  if (isLoadingDetail.value) return
  if (newVal === oldVal) return
  form.value.tipologia_id = null
})

// Scopo: in create l'emittente fiscale e' quello dell'operatore corrente
// (refactor operatore-emittenti: relazione 1-a-1). Gli admin globali non hanno
// un emittente personale e quindi non possono creare listini da questa UI.
// Nota: per listini serve soggettoRuoloId (FK verso soggetti_ruoli),
// NON l'id emittente fiscale (FK diverso).
const canSave = computed(() => {
  const base = !!form.value.codice?.trim()
    && !!form.value.descrizione?.trim()
    && !!form.value.utility_id
    && !!form.value.tipologia_id
  if (!base) return false
  if (isEdit.value) return true
  return !!auth.emittenteCorrente?.soggettoRuoloId
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      utility_id: f.utility_id,
      tipologia_id: f.tipologia_id,
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(props.listinoId, payload),
      { successMessage: t('listini.listino_salvato') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    // emittente_soggetto_ruolo_id: pricing v5 §3.1 — dimensione NOT NULL del
    // listino. FK verso soggetti_ruoli (NON emittenti_fiscali): usare
    // soggettoRuoloId dal profilo operatore, non id.
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      utility_id: f.utility_id,
      tipologia_id: f.tipologia_id,
      emittente_soggetto_ruolo_id: auth.emittenteCorrente?.soggettoRuoloId ?? null,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('listini.listino_creato') }
    )
    if (result !== null) { emit('saved', result); close() }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }" :dismissable="true"
    @after-show="onAfterShow">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('listini.listino')"
        :icon="NAV_ICONS.LISTINI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">
        <!-- Banner refactor operatore-emittenti (solo creazione) -->
        <Message v-if="!isEdit && auth.isAdminGlobale" severity="warn" :closable="false" class="mb-05">
          {{ t('listini.banner_admin_globale_no_create') }}
        </Message>
        <Message v-else-if="!isEdit && auth.emittenteCorrente" severity="info" :closable="false" class="mb-05">
          {{ t('listini.banner_emittente_corrente', { nome: auth.emittenteCorrente.ragioneSociale }) }}
        </Message>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_codice') }} *</label>
            <InputText v-model="form.codice" :disabled="isEdit" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_utility') }} *</label>
            <UtilityPerRuoloSelect v-model="form.utility_id"
              :placeholder="t('listini.field_utility')" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('listini.field_tipologia') }} *</label>
            <TipologiaListinoSelect v-model="form.tipologia_id"
              :utility-id="form.utility_id" />
          </div>
          <div class="form-field">
            <label>{{ t('listini.field_descrizione') }} *</label>
            <InputText v-model="form.descrizione" />
          </div>
        </div>

        <div v-if="isEdit" class="form-grid">
          <div class="form-field">
            <label>{{ t('indirizzi.campo_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>

      </template>

      <div v-else class="app-loading">
        <i class="pi pi-spin pi-spinner"></i>
      </div>

      <FormFooter v-if="contentReady" :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
