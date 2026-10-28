<script setup>
// Scopo: Drawer compatto per creare una nuova versione di un listino.
// Apertura: dal pulsante "+ Nuova versione" nell'expansion riga listino.
// Campi: codice_versione (obbl.), valido_dal (obbl.), valido_al.
// Lo stato iniziale e' BOZZA (gestito dal backend).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useListiniStore } from '../stores/listini'
import { createVersione } from '../api/listini'
import { getVersioneNewDefaults } from '../api/formDefaults'
import { STATO_VERSIONE_LISTINO } from '../constants'
import { toDateString, addDaysToToday, parseIsoDate } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import AppDrawer from '../../core/components/AppDrawer.vue'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const listiniStore = useListiniStore()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listino: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const form = ref({})
// Modifiche non salvate: fotografia dopo i default BE, chiudere con
// modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
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
    valido_dal: parseIsoDate(res.default_valido_dal),
    valido_al: parseIsoDate(res.default_valido_al),
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
  fissa()
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
  return versioni.filter(v => v.stato === STATO_VERSIONE_LISTINO.BOZZA)
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
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.listini.nuova_versione')"
    :icon="MANAGE_ICONS.VERSIONI"
    :action="t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="handleSave"
  >
    <div v-if="listino" class="app-drawer-section">
      <h4>{{ t('vendite.listini.listino') }}: {{ listino.codice }} — {{ listino.descrizione }}</h4>
    </div>

    <Message v-if="bozzeEsistenti.length > 0" severity="warn" :closable="false">
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
  </AppDrawer>
</template>
