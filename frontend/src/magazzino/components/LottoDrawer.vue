<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer crea/modifica LOTTO di un articolo (piano anagrafiche-fuori-
//        dal-pannello-config §6): codice (univoco per articolo), data di
//        arrivo (obbligatoria: da li' si conta la rotazione), data di scadenza
//        (facoltativa, >= arrivo: lo dice il CHECK a DB e il BE lo traduce col
//        campo — qui non si ricontrolla), `attivo` (solo edit).
//
// ⛔ `articolo_id` non e' un campo: un lotto nasce del suo articolo (lo mette
//    lo store dal padre). Il PATCH manda SOLO il delta; `data_scadenza`
//    svuotata viaggia come `null` (la toglie).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

import AppDrawer from '../../core/components/AppDrawer.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DATE_FORMAT, DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { parseIsoDate, toDateStringOrNull } from '../../core/utils/date'
import { useLottiStore } from '../stores/lotti'

const props = defineProps({
  visible: Boolean,
  // `null` = crea.
  lottoId: { type: Number, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useLottiStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const close = useDrawerClose(emit)
// Un dettaglio che non risponde (404) chiude il drawer col toast, invece di
// lasciarlo aperto e vuoto.
const { loadDetailOrClose } = useDrawerDetailLoad(close)

const isEdit = computed(() => props.lottoId != null)

function formVuoto() {
  return { codice: '', data_arrivo: null, data_scadenza: null, attivo: true }
}
const form = ref(formVuoto())
// La fotografia del form all'apertura (BB useDrawerFormPreserve): serve al
// DELTA dell'edit e alle modifiche non salvate — conferma alla chiusura,
// «Modifica» arancio. Prima il drawer ne teneva una copia propria (`originale`).
const {
  fissa, modificato, chiudiConConferma, fotografia,
} = useDrawerFormPreserve(form, { visibile: () => props.visible })

async function loadDetail() {
  const data = await loadDetailOrClose(() => store.fetchDetail(props.lottoId))
  if (data == null) return
  form.value = {
    codice: data.codice || '',
    data_arrivo: parseIsoDate(data.data_arrivo),
    data_scadenza: parseIsoDate(data.data_scadenza),
    attivo: data.attivo ?? true,
  }
  fissa()
}

watch(
  [() => props.visible, () => props.lottoId],
  ([visible]) => {
    if (!visible) return
    campiErrati.value = []
    if (isEdit.value) {
      loadDetail()
    } else {
      form.value = formVuoto()
      fissa()
    }
  },
)

const canSave = computed(() => {
  if (isReadonly.value) return false
  return Boolean(form.value.codice?.trim() && form.value.data_arrivo)
})

// Scopo: il payload del PATCH: SOLO i campi cambiati (le date confrontate
//        normalizzate, non per identita' di oggetto).
function deltaEdit() {
  const payload = {}
  const f = form.value
  const o = fotografia.value ?? formVuoto()
  if (f.codice.trim() !== o.codice) payload.codice = f.codice.trim()
  for (const k of ['data_arrivo', 'data_scadenza']) {
    if (toDateStringOrNull(f[k]) !== toDateStringOrNull(o[k])) payload[k] = toDateStringOrNull(f[k])
  }
  if (f.attivo !== o.attivo) payload.attivo = f.attivo
  return payload
}

async function handleSave() {
  let result
  if (isEdit.value) {
    const payload = deltaEdit()
    if (Object.keys(payload).length === 0) {
      close()
      return
    }
    result = await execute(
      () => store.update(props.lottoId, payload),
      { successMessage: t('magazzino.lotti.salvato') },
    )
  } else {
    const payload = {
      codice: form.value.codice.trim(),
      data_arrivo: toDateStringOrNull(form.value.data_arrivo),
    }
    const scadenza = toDateStringOrNull(form.value.data_scadenza)
    if (scadenza) payload.data_scadenza = scadenza
    result = await execute(
      () => store.create(payload),
      { successMessage: t('magazzino.lotti.creato') },
    )
  }
  if (result !== null) {
    emit('saved', result)
    close()
  }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('magazzino.lotti.titolo_singolare')"
    :icon="MANAGE_ICONS.LOTTO_MAGAZZINO"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.SIMPLE"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('magazzino.lotti.field_codice') }} *</label>
        <InputText v-model="form.codice" :disabled="isReadonly" :invalid="campiErrati.includes('codice')" />
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.lotti.field_data_arrivo') }} *</label>
        <DatePicker
          v-model="form.data_arrivo"
          :date-format="DATE_FORMAT"
          show-icon
          :disabled="isReadonly"
          :invalid="campiErrati.includes('data_arrivo')"
        />
        <small class="app-text-muted">{{ t('magazzino.lotti.hint_data_arrivo') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.lotti.field_data_scadenza') }}</label>
        <DatePicker
          v-model="form.data_scadenza"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          :disabled="isReadonly"
          :invalid="campiErrati.includes('data_scadenza')"
        />
        <small class="app-text-muted">{{ t('magazzino.lotti.hint_data_scadenza') }}</small>
      </div>

      <div v-if="isEdit" class="form-field">
        <label>{{ t('magazzino.lotti.field_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadonly" :invalid="campiErrati.includes('attivo')" />
        <small class="app-text-muted">{{ t('magazzino.lotti.hint_attivo') }}</small>
      </div>
    </div>
  </AppDrawer>
</template>
