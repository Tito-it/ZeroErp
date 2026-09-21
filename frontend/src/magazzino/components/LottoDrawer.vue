<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
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

// Contenuto deferito a fine animazione (`feedback_content_ready_after_show`).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const isEdit = computed(() => props.lottoId != null)

function formVuoto() {
  return { codice: '', data_arrivo: null, data_scadenza: null, attivo: true }
}
const form = ref(formVuoto())
const originale = ref(formVuoto())

async function loadDetail() {
  const data = await loadDetailOrClose(() => store.fetchDetail(props.lottoId))
  if (data == null) return
  form.value = {
    codice: data.codice || '',
    data_arrivo: parseIsoDate(data.data_arrivo),
    data_scadenza: parseIsoDate(data.data_scadenza),
    attivo: data.attivo ?? true,
  }
  originale.value = { ...form.value }
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
      originale.value = formVuoto()
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
  const o = originale.value
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
  <Drawer
    :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('magazzino.lotti.titolo_singolare')"
        :icon="MANAGE_ICONS.LOTTO_MAGAZZINO" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
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

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>
