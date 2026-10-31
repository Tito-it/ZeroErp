<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form di UNA nota (crea / modifica), montato da `NoteDrawer` nello
//        slot `#form` di `ListaConFormInline`. Estratto dal corpo di
//        `NoteDrawer` il 2026-10-31, quando la lista delle note e' passata al
//        BB (brief-db-liste-datatable-grezze-secondo-giro riga 3): il form e'
//        quello di prima, spostato.
// Default applicativi minimi: anchor_tipo e posizione li governa il BE (li
// deriva da target_riga_id: DOCUMENTO/HEADER vs RIGA/AFTER). La lingua di
// partenza e' il parametro NOTE_DEFAULT_LINGUA (pre-compilata in creazione).
// ⭐ Espone la sua fotografia (`modificato`, `chiudiConConferma`): il BB la
//    registra (D-13) e chiede prima di cambiare nota o chiudere il drawer.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import { fetchParameterDefaults, lookupCodici } from '../apiCore'
import { useApiHandler } from '../composables/useApiHandler'
import { useDrawerFormPreserve } from '../composables/useDrawerFormPreserve'
import FormFooter from './FormFooter.vue'
import LookupSelect from './LookupSelect.vue'

const props = defineProps({
  // La nota in modifica; `null` in creazione.
  riga: { type: Object, default: null },
  // Il CRUD delle note del padre (`makeNotesApi(...)`).
  apiClient: { type: Object, required: true },
  // Il select «Riga» (note di riga): visibile se ci sono opzioni.
  supportsRiga: { type: Boolean, default: false },
  righeOptions: { type: Array, default: () => [] },
})
const emit = defineEmits(['saved', 'cancel'])

const { t } = useI18n()
const { execute, loading: saveLoading, campiErrati } = useApiHandler()

const inModifica = computed(() => props.riga != null)
const canSelectRiga = computed(() => props.supportsRiga && props.righeOptions.length > 0)

function formDa(n) {
  return n
    ? {
        testo_md: n.testo_md || n.testo || '',
        id_stile: n.id_stile ?? null,
        id_lingua: n.id_lingua ?? null,
        target_riga_id: n.target_riga_id ?? null,
        visibile: n.visibile !== false,
        solo_stampa: n.solo_stampa === true,
      }
    : {
        testo_md: '', id_stile: null, id_lingua: null, target_riga_id: null,
        visibile: true, solo_stampa: false,
      }
}

const form = ref(formDa(props.riga))
// Il form vive solo aperto: la fotografia si fissa alla nascita.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => true })

// Cache del default `id_lingua` risolto da parametro sistema (per istanza del
// form, com'era nel drawer). Pattern 2 chiamate:
// parametro NOTE_DEFAULT_LINGUA (codice_iso) -> lookup config.lingue per l'id;
// lookupCodici sfrutta la cache globale del LookupSelect.
let _defaultLinguaIdCache = null

async function resolveDefaultLinguaId() {
  if (_defaultLinguaIdCache !== null) return _defaultLinguaIdCache
  try {
    const r = await fetchParameterDefaults(['NOTE_DEFAULT_LINGUA'])
    const codiceIso = r.data?.data?.NOTE_DEFAULT_LINGUA
    if (!codiceIso) return null
    const res = await lookupCodici('config.lingue', { search: codiceIso })
    const match = (res.data?.data?.results || []).find(
      l => l.codice === codiceIso || l.codice_interno === codiceIso,
    )
    _defaultLinguaIdCache = match?.id ?? null
    return _defaultLinguaIdCache
  } catch {
    return null
  }
}

onMounted(async () => {
  fissa()
  if (inModifica.value) return
  // Pre-fill lingua dal parametro (best-effort): il BE applica comunque il
  // fallback al salvataggio se id_lingua e' null.
  const linguaId = await resolveDefaultLinguaId()
  if (linguaId != null && !inModifica.value) {
    // Il default arriva dopo: rientra nella fotografia solo se l'utente non
    // ha ancora toccato niente (altrimenti fisseremmo anche le sue modifiche).
    const intatto = !modificato.value
    form.value.id_lingua = linguaId
    if (intatto) fissa()
  }
})

const canSave = computed(() =>
  (form.value.testo_md || '').trim().length > 0 && form.value.id_stile != null,
)

// Scopo: persistenza. PATCH in modifica, create in creazione.
async function onSave() {
  if (!canSave.value) return
  const payload = {
    testo_md: form.value.testo_md,
    id_stile: form.value.id_stile,
    visibile: form.value.visibile,
    solo_stampa: form.value.solo_stampa,
  }
  // id_lingua opzionale: NULL in create = fallback BE `NOTE_DEFAULT_LINGUA`.
  if (form.value.id_lingua != null) payload.id_lingua = form.value.id_lingua
  // target_riga_id solo in create (il BE lo rifiuta in PATCH).
  if (!inModifica.value && form.value.target_riga_id != null) {
    payload.target_riga_id = form.value.target_riga_id
  }
  const result = await execute(
    inModifica.value
      ? () => props.apiClient.updateNota(props.riga.id, payload)
      : () => props.apiClient.createNota(payload),
    { successMessage: t('note.saved') },
  )
  if (result === null) return
  fissa()
  emit('saved', result)
}

// Annulla: con modifiche chiede conferma.
const annulla = () => chiudiConConferma(() => emit('cancel'))

defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <div class="form-field" v-if="canSelectRiga">
        <label>{{ t('note.field_riga') }}</label>
        <Select
          v-model="form.target_riga_id"
          :options="righeOptions"
          option-label="label" option-value="value"
          :placeholder="t('note.placeholder_riga_doc')"
          :disabled="inModifica"
          show-clear
          :invalid="campiErrati.includes('target_riga_id')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('note.field_stile') }} *</label>
        <LookupSelect
          v-model="form.id_stile"
          rel="config.note_stili"
          :placeholder="t('note.placeholder_stile')"
        />
      </div>
    </div>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('note.field_lingua') }}</label>
        <LookupSelect
          v-model="form.id_lingua"
          rel="config.lingue"
          :placeholder="t('note.placeholder_lingua')"
          show-code
          show-clear
        />
      </div>
    </div>
    <div class="form-field">
      <label>{{ t('note.field_testo') }} *</label>
      <Textarea
        v-model="form.testo_md" rows="6" auto-resize
        :placeholder="t('note.placeholder_testo')"
        :invalid="campiErrati.includes('testo_md')"
      />
    </div>
    <div class="form-grid-2col">
      <div class="form-field form-field-inline">
        <label>{{ t('note.field_visibile') }}</label>
        <ToggleSwitch v-model="form.visibile" :invalid="campiErrati.includes('visibile')" />
      </div>
      <div class="form-field form-field-inline">
        <label>{{ t('note.field_solo_stampa') }}</label>
        <ToggleSwitch v-model="form.solo_stampa" :invalid="campiErrati.includes('solo_stampa')" />
      </div>
    </div>
  </div>

  <FormFooter :loading="saveLoading" :disabled="!canSave" @save="onSave" @cancel="annulla" />
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>
