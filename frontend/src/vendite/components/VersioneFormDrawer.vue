<script setup>
// Scopo: Drawer compatto per creare una nuova versione di un listino.
// Apertura: dal pulsante "+ Nuova versione" nell'expansion riga listino.
// Campi: codice_versione (obbl.), valido_dal (obbl.), valido_al.
// Lo stato iniziale e' BOZZA (gestito dal backend).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useListiniStore } from '../stores/listini'
import { createVersione } from '../api/listini'
import { getVersioneNewDefaults } from '../api/formDefaults'
import { toDateString, addDaysToToday } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'



const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()
const listiniStore = useListiniStore()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listino: { type: Object, default: null }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'saved'])

const form = ref({})
// existing_drafts arriva dal BE (Fase 2.B5a): single source of truth.
// Mantiene anche compat con lo store locale come fallback se l'endpoint
// fallisce (resilienza al primo open offline).
const beExistingDrafts = ref(null)

function emptyForm() {
  // Form iniziale prima della risposta BE: vuoto + valido_dal = oggi.
  // Sovrascritto dalla risposta di getVersioneNewDefaults sotto.
  return {
    codice_versione: '',
    valido_dal: addDaysToToday(0),
    valido_al: null,
  }
}

async function loadDefaults() {
  if (!props.listino?.id) return
  const res = await execute(
    () => getVersioneNewDefaults(props.listino.id),
    { silent: true },
  )
  if (res === null) return
  // execute() ritorna body.data unwrappato.
  form.value = {
    codice_versione: res.default_codice_versione || '',
    valido_dal: res.default_valido_dal ? new Date(res.default_valido_dal + 'T00:00:00') : null,
    valido_al: res.default_valido_al ? new Date(res.default_valido_al + 'T00:00:00') : null,
  }
  beExistingDrafts.value = Array.isArray(res.existing_drafts) ? res.existing_drafts : []
}

watch(() => props.visible, async (v) => {
  if (!v) {
    beExistingDrafts.value = null
    return
  }
  form.value = emptyForm()
  await loadDefaults()
})

const canSave = computed(() =>
  !!form.value.codice_versione?.trim() &&
  !!form.value.valido_dal
)

const bozzeEsistenti = computed(() => {
  // Se l'endpoint BE ha risposto, usiamo quello (single source of truth).
  // Altrimenti fallback allo store locale (popolato dalla lista versioni).
  if (beExistingDrafts.value !== null) return beExistingDrafts.value
  if (!props.listino?.id) return []
  const versioni = listiniStore.versioniByListino[props.listino.id] || []
  return versioni.filter(v => v.stato === 'BOZZA')
})

async function handleSave() {
  if (!props.listino?.id) return
  const f = form.value
  const payload = {
    codice_versione: f.codice_versione.trim(),
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
  }
  // execute() restituisce gia' body.data unwrappato (vedi useApiHandler).
  const result = await execute(
    () => createVersione(props.listino.id, payload),
    { successMessage: t('vendite.listini.versione_creata') }
  )
  if (result !== null) {
    emit('saved', { listinoId: props.listino.id, versione: result })
    close()
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :action="t('common.new')" :title="t('vendite.listini.nuova_versione')" :icon="NAV_ICONS.HISTORY" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listino" class="app-drawer-section">
        <h4>{{ t('vendite.listini.listino') }}: {{ listino.codice }} — {{ listino.descrizione }}</h4>
      </div>

      <Message v-if="bozzeEsistenti.length > 0" severity="warn" :closable="false" class="mb-1">
        {{ t('vendite.listini.warning_bozza_esistente', { codice: bozzeEsistenti.map(b => b.codice_versione).join(', ') }) }}
      </Message>

      <div class="form-field">
        <label>{{ t('vendite.listini.field_codice_versione') }} *</label>
        <InputText v-model="form.codice_versione"
          :invalid="campiErrati.includes('codice_versione')"
        />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_dal') }} *</label>
          <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon
            :invalid="campiErrati.includes('valido_dal')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
            :invalid="campiErrati.includes('valido_al')"
          />
        </div>
      </div>

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
