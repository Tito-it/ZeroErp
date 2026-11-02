<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form con cui si APRE un documento interno di magazzino — un
//        inventario o una rettifica, UN dialog con la famiglia in prop (Q-1).
//
// ⭐ La creazione passa da un DIALOG e non dall'auto-save bozza dei documenti
//    di vendita (Q-4, decisione di Tid 2026-09-18): la testata ha tre campi, e
//    nessuna riga si scrive senza un magazzino scelto. Il dialog da' il
//    magazzino, e con esso il drawer nasce gia' «evoluto». E' la strada del
//    18/09 delle distinte, la piu' recente.
//
// ⭐ IL MAGAZZINO SI SCEGLIE QUI E BASTA: e' l'ancora del documento (RLS,
//    ubicazioni delle righe, `qta_sistema` del piano) e il PATCH della testata
//    non lo accetta — a DB lo difende R-4. Il picker e' il lookup generico
//    (`magazzino.magazzini`): la RLS filtra i magazzini per emittente, come
//    per ogni lettura del dominio. ⚠️ Il flag `usa_ubicazioni` NON viaggia
//    qui: lo legge il drawer dal dettaglio del documento
//    (`magazzino_usa_ubicazioni`), che e' l'unica sede da cui il form di riga
//    lo prende — una colonna in piu' sul lookup sarebbe emessa e mai letta.
//
// ⚠️ La data nasce OGGI perche' e' il caso normale — si conta oggi — e resta
//    modificabile: decide `data_mov` al posting.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString, oggiAziendale } from '../../core/utils/date'
import { useDocumentiInterniStore } from '../stores/documentiInterni'
import { FAMIGLIE } from '../vocabolari'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

// ⚠️ Niente `class="w-full"` sui campi: `.form-field` e' gia' `flex-direction:
//    column`, quindi i figli si stirano da se'.

const props = defineProps({
  visible: { type: Boolean, default: false },
  famiglia: { type: String, required: true, validator: (v) => v in FAMIGLIE },
})
const emit = defineEmits(['update:visible', 'aperto'])

const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const f = FAMIGLIE[props.famiglia]
const store = useDocumentiInterniStore(f.codice)

const form = ref(defaultForm())

function defaultForm() {
  return {
    magazzino_id: null,
    data: oggiAziendale(),
    descrizione: '',
  }
}

const canSave = computed(
  () => form.value.magazzino_id != null && form.value.data != null,
)

// Scopo: riazzera il form a ogni apertura.
watch(() => props.visible, (aperto) => {
  if (aperto) form.value = defaultForm()
})

async function onSave() {
  const payload = {
    magazzino_id: form.value.magazzino_id,
    data: toDateString(form.value.data),
  }
  // ⛔ La descrizione viaggia SOLO sulla famiglia che ce l'ha: sulla rettifica
  //    il backend rifiuta la chiave (`validate_allowed_keys`).
  if (f.conDescrizione && form.value.descrizione?.trim()) {
    payload.descrizione = form.value.descrizione.trim()
  }

  // ⚠️ NIENTE `silent`: il magazzino fuori perimetro o spento risponde 400 col
  //    campo, e in `silent` la finestra resterebbe aperta senza dire perche'.
  const dettaglio = await execute(
    () => store.crea(payload),
    { successMessage: t(`${f.i18n}.aperto`) },
  )
  // ⛔ `!== null`: un `0` legittimo non deve leggersi come fallimento.
  if (dettaglio === null) return

  emit('aperto', dettaglio.id ?? null)
  emit('update:visible', false)
}

function onCancel() { emit('update:visible', false) }

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ ...form.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t(`${f.i18n}.nuovo`)"
    width="md"
    :loading="loading"
    :save-disabled="!canSave"
    :save-label="t('magazzino.documenti_interni.apri_conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
    @cancel="onCancel"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('magazzino.documenti_interni.campo_magazzino') }} *</label>
        <LookupSelect
          v-model="form.magazzino_id"
          rel="magazzino.magazzini"
          :placeholder="t('magazzino.documenti_interni.campo_magazzino_placeholder')"
          :invalid="campiErrati.includes('magazzino_id')"
          show-code
        />
        <!-- ⭐ Si dice PRIMA che non si cambia: un campo che sparisce dal form
             del drawer senza spiegazione si legge come un difetto. -->
        <small class="app-text-muted">
          {{ t('magazzino.documenti_interni.magazzino_aiuto') }}
        </small>
      </div>

      <div class="form-field">
        <label>{{ t('magazzino.documenti_interni.campo_data') }} *</label>
        <DatePicker
          v-model="form.data"
          :date-format="DATE_FORMAT"
          show-icon
          :invalid="campiErrati.includes('data')"
        />
        <small class="app-text-muted">
          {{ t('magazzino.documenti_interni.data_aiuto') }}
        </small>
      </div>

      <div v-if="f.conDescrizione" class="form-field">
        <label>{{ t('magazzino.documenti_interni.campo_descrizione') }}</label>
        <InputText
          v-model="form.descrizione"
          maxlength="500"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
    </div>
  </AppDialog>
</template>
