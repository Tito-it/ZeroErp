<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer crea/modifica MAGAZZINO (piano anagrafiche-fuori-dal-pannello-
//        config §4.2): codice (lockato in edit: lo dice il trigger a DB),
//        descrizione, emittente in sola lettura (dalla sessione in create,
//        dal record in edit), INDIRIZZO scelto fra gli indirizzi del soggetto
//        emittente (Q-2 a: `IndirizziSoggettoDrawer selectable`),
//        `usa_ubicazioni`, `predefinito`, `attivo` (solo edit). In edit la
//        sezione «Ubicazioni (N)» + «Gestisci ubicazioni» (stampo
//        `ArticoloDrawer` §UoM).
//
// ⛔ `emittente_fiscale_id` NON viaggia nel payload: lo mette il DB dalla GUC
//    della sessione (`trgfn_default_emittente_fiscale('SOLLEVA')`). L'admin
//    globale su «tutti» riceve `E_EMITTENTE_NON_RISOLTO` col campo: qui il
//    pulsante si spegne prima (`defaultEmittenteId == null`).
// ⚠️ Il PATCH manda SOLO il delta: il lock su `codice` scatta solo se il codice
//    viaggia, il guard su `usa_ubicazioni` (a registro vuoto,
//    `E_MAG_MAGAZZINO_CON_GIACENZA`) solo se lo si tocca.
// ⚠️ Un indirizzo LIBERO del soggetto non e' un `indirizzi_dettaglio`: si
//    vede nel drawer ma non si sceglie, col motivo a toast (Q-2).
// ⚠️ Un dettaglio che non risponde (404 no-leak: magazzino di un altro
//    emittente) chiude il drawer col toast (`useDrawerDetailLoad`), invece di
//    lasciarlo aperto e vuoto — e' il caso per cui il BE risponde 404.
// ⛔ Niente `<style scoped>`: l'indirizzo scelto e' un `InputText` in sola
//    lettura con il pulsante accanto (`app-input-with-action`, la forma di
//    `SoggettoForm`/`DistintaRigaForm`), e il riepilogo delle ubicazioni usa
//    `app-riepilogo-*` di `main.css` (lo stampo di `ArticoloDrawer`).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

import AppDrawer from '../../core/components/AppDrawer.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import IndirizziSoggettoDrawer from '../../anagrafiche/components/IndirizziSoggettoDrawer.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useMagazziniStore } from '../stores/magazzini'
import MagazzinoUbicazioniDrawer from './MagazzinoUbicazioniDrawer.vue'

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  magazzinoId: { type: Number, default: null },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const store = useMagazziniStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const notify = useNotify()
const { defaultEmittenteId, soggettoIdSessione, isAdminMode, loadOptions } = useEmittenteFiscaleField()
const close = useDrawerClose(emit, 'cancelled')
const { loadDetailOrClose } = useDrawerDetailLoad(close)

const isEdit = computed(() => props.mode === 'edit')
const detail = ref(null)
const indirizziDrawerVisible = ref(false)
const ubicazioniDrawerVisible = ref(false)

function formVuoto() {
  return {
    codice: '',
    descrizione: '',
    indirizzo_dettaglio_id: null,
    indirizzo_display: '',
    usa_ubicazioni: false,
    predefinito: false,
    attivo: true,
  }
}
const form = ref(formVuoto())
// La fotografia del form all'apertura (BB useDrawerFormPreserve): serve al
// DELTA dell'edit e alle modifiche non salvate — conferma alla chiusura,
// «Modifica» arancio. Prima il drawer ne teneva una copia propria (`originale`).
const {
  preserva, fissa, modificato, chiudiConConferma, fotografia,
} = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Scopo: il record come lo vuole `EmittenteFiscaleField` in edit (legge
//        `emittente_fiscale_codice`; la riga del BE porta `emittente_codice`,
//        il nome che le liste del dominio gia' usano).
const recordEmittente = computed(() => detail.value
  ? { ...detail.value, emittente_fiscale_codice: detail.value.emittente_codice }
  : null)

// Il soggetto di cui scegliere gli indirizzi: in edit quello dell'emittente
// del record (fail-visible: viene dal DB), in create quello della sessione.
const soggettoIndirizzi = computed(() => (
  isEdit.value ? detail.value?.emittente_soggetto_id ?? null : soggettoIdSessione.value
))

// ⚠️ Si ricarica anche alla chiusura del sotto-drawer delle ubicazioni: senza
//    `preserva`, la descrizione digitata e non salvata tornava com'era sul
//    server, in silenzio (difetto trovato il 2026-09-26).
async function loadDetail() {
  const applica = preserva()
  detail.value = null
  const data = await loadDetailOrClose(() => store.fetchDetail(props.magazzinoId))
  if (data == null) return
  detail.value = data
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    indirizzo_dettaglio_id: data.indirizzo_dettaglio_id ?? null,
    indirizzo_display: data.indirizzo_normalizzato || '',
    usa_ubicazioni: data.usa_ubicazioni ?? false,
    predefinito: data.predefinito ?? false,
    attivo: data.attivo ?? true,
  }
  applica()
}

watch(
  [() => props.visible, () => props.mode, () => props.magazzinoId],
  ([visible]) => {
    if (!visible) return
    campiErrati.value = []
    if (isEdit.value) {
      loadDetail()
    } else {
      detail.value = null
      form.value = formVuoto()
      fissa()
      // Il super admin ha il nome (e il soggetto) del suo emittente solo dal
      // lookup: si carica qui, come fa `EmittenteFiscaleField` per l'etichetta.
      if (isAdminMode.value) loadOptions()
    }
  },
)

// Senza un emittente su cui scrivere il «Salva» e' spento PRIMA del DB.
const senzaEmittente = computed(() => !isEdit.value && defaultEmittenteId.value == null)

const canSave = computed(() => {
  if (isReadonly.value || senzaEmittente.value) return false
  return Boolean(
    form.value.codice?.trim()
    && form.value.descrizione?.trim()
    && form.value.indirizzo_dettaglio_id,
  )
})

// Scopo: la scelta di un indirizzo del soggetto emittente. ⚠️ Solo un
//        `indirizzi_dettaglio`: un indirizzo libero non si puo' referenziare.
function onIndirizzoScelto(ind) {
  if (!ind?.indirizzo_dettaglio_id) {
    notify.warn(t('magazzino.magazzini.indirizzo_libero_non_ammesso'))
    return
  }
  form.value.indirizzo_dettaglio_id = ind.indirizzo_dettaglio_id
  form.value.indirizzo_display = ind.indirizzo_display || ind.indirizzo_libero || ''
  indirizziDrawerVisible.value = false
}

// Scopo: il payload del PATCH: SOLO i campi cambiati (delta).
function deltaEdit() {
  const payload = {}
  const f = form.value
  const o = fotografia.value ?? formVuoto()
  if (f.descrizione.trim() !== o.descrizione) payload.descrizione = f.descrizione.trim()
  if (f.indirizzo_dettaglio_id !== o.indirizzo_dettaglio_id) payload.indirizzo_dettaglio_id = f.indirizzo_dettaglio_id
  for (const flag of ['usa_ubicazioni', 'predefinito', 'attivo']) {
    if (f[flag] !== o[flag]) payload[flag] = f[flag]
  }
  return payload
}

async function handleSave() {
  if (isEdit.value) {
    const payload = deltaEdit()
    if (Object.keys(payload).length === 0) {
      close()
      return
    }
    const result = await execute(
      () => store.update(props.magazzinoId, payload),
      { successMessage: t('magazzino.magazzini.salvato') },
    )
    if (result !== null) { fissa(); emit('saved', result) }
  } else {
    const payload = {
      codice: form.value.codice.trim(),
      descrizione: form.value.descrizione.trim(),
      indirizzo_dettaglio_id: form.value.indirizzo_dettaglio_id,
      usa_ubicazioni: form.value.usa_ubicazioni,
      predefinito: form.value.predefinito,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('magazzino.magazzini.creato') },
    )
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

// Il riepilogo delle ubicazioni si rilegge dal dettaglio: il conteggio lo
// calcola il BE (`ubicazioni_count`).
function onUbicazioniChiuse() {
  if (isEdit.value) loadDetail()
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('magazzino.magazzini.titolo_singolare')"
    :icon="NAV_ICONS.MAGAZZINO"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_codice') }} *</label>
        <InputText
          v-model="form.codice"
          class="app-codice-input"
          :disabled="isEdit || isReadonly"
          :invalid="campiErrati.includes('codice')"
        />
        <small v-if="isEdit" class="app-text-muted">{{ t('magazzino.magazzini.hint_codice_lockato') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_descrizione') }} *</label>
        <InputText
          v-model="form.descrizione"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_emittente') }}</label>
        <EmittenteFiscaleField
          :model-value="isEdit ? (detail?.emittente_fiscale_id ?? null) : defaultEmittenteId"
          :record="recordEmittente"
          :is-edit="isEdit"
          :invalid="campiErrati.includes('emittente_fiscale_id')"
        />
        <small v-if="senzaEmittente" class="app-text-muted">{{ t('magazzino.magazzini.hint_senza_emittente') }}</small>
      </div>

      <!-- L'indirizzo: l'indirizzo scelto in sola lettura e «Scegli», che apre
           gli indirizzi del soggetto emittente in modalita' selezione. -->
      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_indirizzo') }} *</label>
        <div class="app-input-with-action">
          <InputText
            :model-value="form.indirizzo_display"
            readonly
            :placeholder="t('magazzino.magazzini.indirizzo_da_scegliere')"
            :invalid="campiErrati.includes('indirizzo_dettaglio_id')"
          />
          <Button
            v-if="!isReadonly"
            :label="t('magazzino.magazzini.scegli_indirizzo')"
            :icon="MANAGE_ICONS.INDIRIZZI"
            text size="small" class="app-action-btn app-escape"
            :disabled="!soggettoIndirizzi"
            @click="indirizziDrawerVisible = true" />
        </div>
        <small class="app-text-muted">{{ t('magazzino.magazzini.hint_indirizzo') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_usa_ubicazioni') }}</label>
        <ToggleSwitch v-model="form.usa_ubicazioni" :disabled="isReadonly" :invalid="campiErrati.includes('usa_ubicazioni')" />
        <small class="app-text-muted">{{ t('magazzino.magazzini.hint_usa_ubicazioni') }}</small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.magazzini.field_predefinito') }}</label>
        <ToggleSwitch v-model="form.predefinito" :disabled="isReadonly" :invalid="campiErrati.includes('predefinito')" />
      </div>

      <div v-if="isEdit" class="form-field">
        <label>{{ t('magazzino.magazzini.field_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadonly" :invalid="campiErrati.includes('attivo')" />
        <small class="app-text-muted">{{ t('magazzino.magazzini.hint_attivo') }}</small>
      </div>
    </div>

    <!-- Sezione: le ubicazioni (edit): il conteggio lo dice il BE, la
         gestione e' il drawer autonomo (`feedback_drawer_autonomi`). -->
    <template v-if="isEdit && detail">
      <div class="app-drawer-section"><h4>{{ t('magazzino.ubicazioni.titolo', { n: detail.ubicazioni_count }) }}</h4></div>
      <div class="app-riepilogo-section">
        <div v-if="!detail.usa_ubicazioni" class="app-riepilogo-empty">{{ t('magazzino.ubicazioni.magazzino_non_le_usa') }}</div>
        <Button
          :label="t('magazzino.ubicazioni.gestisci')" :icon="MANAGE_ICONS.UBICAZIONI"
          text size="small" class="app-action-btn app-escape mt-025"
          @click="ubicazioniDrawerVisible = true" />
      </div>
    </template>
  </AppDrawer>

  <!-- Gli indirizzi del soggetto emittente, in modalita' selezione (Q-2 a):
       sa anche aggiungerne uno; qui si accetta solo un `indirizzi_dettaglio`. -->
  <IndirizziSoggettoDrawer
    :visible="indirizziDrawerVisible"
    @update:visible="v => indirizziDrawerVisible = v"
    :soggetto-id="soggettoIndirizzi"
    selectable
    :select-tooltip="t('magazzino.magazzini.usa_indirizzo')"
    @select="onIndirizzoScelto"
  />

  <MagazzinoUbicazioniDrawer
    :visible="ubicazioniDrawerVisible"
    @update:visible="v => { ubicazioniDrawerVisible = v; if (!v) onUbicazioniChiuse() }"
    :magazzino-id="props.magazzinoId"
    :magazzino-codice="detail?.codice ?? ''"
    :usa-ubicazioni="detail?.usa_ubicazioni ?? true"
  />
</template>
