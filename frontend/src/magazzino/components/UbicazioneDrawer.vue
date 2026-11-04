<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer crea/modifica UBICAZIONE di un magazzino (piano anagrafiche-
//        fuori-dal-pannello-config §5): codice (univoco nel magazzino), tipo
//        (`config.tipi_ubicazione`), padre (un'ubicazione DELLO STESSO
//        magazzino, dal lookup filtrato sul padre — il DB lo rispecchia con
//        `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO` e rifiuta i cicli con
//        `E_MAG_UBICAZIONE_PADRE_CICLICO`), descrizione, la posizione fisica
//        (area/corsia/scaffale/piano/posizione), `attivo` (solo edit).
//
// ⚠️ Il picker del padre FILTRA per magazzino e toglie l'ubicazione stessa: e'
//    la comodita' dell'operatore, non la regola — quella e' del trigger a DB,
//    e un client qualunque la incontra li'. Il PATCH manda SOLO il delta.
//    ⛔ Fetcher e transform del picker sono PURI rispetto all'istanza (la
//    chiave di cache e' per magazzino, e `useGlobalLookup` tiene il PRIMO
//    fetcher/transform registrato): il magazzino e' catturato per VALORE nel
//    fetcher, e «senza me stessa» sta in `excludeValue`, a valle della cache
//    — nel transform avrebbe scritto nella cache condivisa l'esclusione della
//    prima ubicazione aperta, invisibile poi come padre di tutte le altre.
// ⚠️ Un dettaglio che non risponde (404 no-leak: ubicazione di un altro
//    magazzino, o magazzino fuori perimetro) chiude il drawer col toast
//    (`useDrawerDetailLoad`), invece di lasciarlo aperto e vuoto.
// ⛔ `magazzino_id` non e' un campo: un'ubicazione nasce nel suo magazzino
//    (lock a DB, `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { lookupUbicazioni } from '../api/magazzino'
import { useUbicazioniStore } from '../stores/ubicazioni'
import { chiaveLookupUbicazioni } from '../vocabolari'

const props = defineProps({
  visible: Boolean,
  magazzinoId: { type: Number, default: null },
  // `null` = crea.
  ubicazioneId: { type: Number, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useUbicazioniStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const close = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(close)

const isEdit = computed(() => props.ubicazioneId != null)

const CAMPI_POSIZIONE = ['area', 'corsia', 'scaffale', 'piano', 'posizione']

function formVuoto() {
  return {
    codice: '',
    descrizione: '',
    tipo_id: null,
    parent_id: null,
    area: '', corsia: '', scaffale: '', piano: '', posizione: '',
    attivo: true,
  }
}
const form = ref(formVuoto())
// La fotografia del form all'apertura (BB useDrawerFormPreserve): serve al
// DELTA dell'edit e alle modifiche non salvate — conferma alla chiusura,
// «Modifica» arancio. Prima il drawer ne teneva una copia propria (`originale`).
const {
  fissa, modificato, chiudiConConferma, fotografia,
} = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Scopo: le ubicazioni del magazzino come opzioni del padre: etichetta
//        «codice — descrizione». PURA (solo la risposta): finisce nella cache
//        condivisa per magazzino. L'ubicazione stessa la toglie `excludeValue`
//        (un ciclo di lunghezza uno lo rifiuterebbe comunque il DB, ma non si
//        propone).
function opzioniPadre(res) {
  return (res.data.data.results || [])
    .map((u) => ({ ...u, etichetta: u.descrizione ? `${u.codice} — ${u.descrizione}` : u.codice }))
}
// Il magazzino catturato per VALORE: la chiave di cache e' la sua, e il
// fetcher registrato per quella chiave deve leggere QUEL magazzino anche se
// questa istanza del drawer nel frattempo ne mostra un altro.
const fetchPadri = computed(() => {
  const magazzinoId = props.magazzinoId
  return () => lookupUbicazioni(magazzinoId)
})

async function loadDetail() {
  const data = await loadDetailOrClose(() => store.fetchDetail(props.ubicazioneId))
  if (data == null) return
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    tipo_id: data.tipo_id ?? null,
    parent_id: data.parent_id ?? null,
    area: data.area || '',
    corsia: data.corsia || '',
    scaffale: data.scaffale || '',
    piano: data.piano || '',
    posizione: data.posizione || '',
    attivo: data.attivo ?? true,
  }
  fissa()
}

watch(
  [() => props.visible, () => props.ubicazioneId],
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
  return Boolean(form.value.codice?.trim() && form.value.tipo_id)
})

// Un testo vuoto viaggia come `null` (`feedback_null_vs_empty`).
const testoONull = (v) => (v && v.trim() ? v.trim() : null)

// Scopo: il payload del PATCH: SOLO i campi cambiati.
function deltaEdit() {
  const payload = {}
  const f = form.value
  const o = fotografia.value ?? formVuoto()
  if (f.codice.trim() !== o.codice) payload.codice = f.codice.trim()
  if (f.tipo_id !== o.tipo_id) payload.tipo_id = f.tipo_id
  if (f.parent_id !== o.parent_id) payload.parent_id = f.parent_id
  if (f.attivo !== o.attivo) payload.attivo = f.attivo
  for (const k of ['descrizione', ...CAMPI_POSIZIONE]) {
    if (testoONull(f[k]) !== testoONull(o[k])) payload[k] = testoONull(f[k])
  }
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
      () => store.update(props.ubicazioneId, payload),
      { successMessage: t('magazzino.ubicazioni.salvata') },
    )
  } else {
    const payload = {
      codice: form.value.codice.trim(),
      tipo_id: form.value.tipo_id,
    }
    if (form.value.parent_id) payload.parent_id = form.value.parent_id
    for (const k of ['descrizione', ...CAMPI_POSIZIONE]) {
      const v = testoONull(form.value[k])
      if (v !== null) payload[k] = v
    }
    result = await execute(
      () => store.create(payload),
      { successMessage: t('magazzino.ubicazioni.creata') },
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
    :title="t('magazzino.ubicazioni.titolo_singolare')"
    :icon="MANAGE_ICONS.UBICAZIONI"
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
        <label>{{ t('magazzino.ubicazioni.field_codice') }} *</label>
        <InputText v-model="form.codice" class="app-codice-input" :disabled="isReadonly" :invalid="campiErrati.includes('codice')" />
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.ubicazioni.field_tipo') }} *</label>
        <LookupSelect
          v-model="form.tipo_id"
          rel="config.tipi_ubicazione"
          show-code
          :disabled="isReadonly"
          :invalid="campiErrati.includes('tipo_id')"
        />
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.ubicazioni.field_parent') }}</label>
        <!-- Le ubicazioni DI QUESTO magazzino, senza questa: la chiave di
             cache porta il magazzino, e la lista la invalida a ogni scrittura. -->
        <LookupSelect
          :key="`padre-${magazzinoId}-${ubicazioneId ?? 'new'}`"
          v-model="form.parent_id"
          :fetcher="fetchPadri"
          :lookup-key="chiaveLookupUbicazioni(magazzinoId)"
          :transform="opzioniPadre"
          :exclude-value="ubicazioneId"
          label-field="etichetta"
          show-clear
          :disabled="isReadonly"
          :invalid="campiErrati.includes('parent_id')"
        />
        <small class="app-text-muted">{{ t('magazzino.ubicazioni.hint_parent') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.ubicazioni.field_descrizione') }}</label>
        <InputText v-model="form.descrizione" :disabled="isReadonly" :invalid="campiErrati.includes('descrizione')" />
      </div>

      <div class="app-drawer-section"><h4>{{ t('magazzino.ubicazioni.sezione_posizione') }}</h4></div>
      <div v-for="k in CAMPI_POSIZIONE" :key="k" class="form-field">
        <label>{{ t(`magazzino.ubicazioni.field_${k}`) }}</label>
        <InputText v-model="form[k]" :disabled="isReadonly" :invalid="campiErrati.includes(k)" />
      </div>

      <div v-if="isEdit" class="form-field">
        <label>{{ t('magazzino.ubicazioni.field_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadonly" :invalid="campiErrati.includes('attivo')" />
        <small class="app-text-muted">{{ t('magazzino.ubicazioni.hint_attivo') }}</small>
      </div>
    </div>
  </AppDrawer>
</template>
