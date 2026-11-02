<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il drawer AUTONOMO di una versione di template documentale
//        (2026-10-03, chiude il debito di brief-db-liste-datatable-grezze §4
//        riga 6 e la regola dei drawer autonomi). Fino a quel giorno la
//        versione era un form inline sotto la lista, dentro il drawer del
//        template: col footer del padre spento e l'HTML del template in una
//        textarea di centinaia di righe, il Salva finiva fuori vista — il
//        difetto che il footer fisso di `AppDrawer` (D-2) esiste per evitare.
//
//        - Nuova versione: `versioneId` null. Formato, pagina, orientamento e
//          margini partono VUOTI e, se restano vuoti, non si mandano: vale il
//          default della colonna a DB. Prima erano scritti qui (margini 15 mm
//          contro i 10 della colonna): due default per la stessa cosa.
//        - Versione BOZZA: modifica.
//        - PUBBLICATA / OBSOLETA: consultazione in sola lettura (prima non si
//          apriva affatto). Si cambia clonandola.
//
//        La forma dei dati (`versione_contesto`) si precompila con quella del
//        builder di oggi (`versioneContestoBuilder`): la si mostra, non si
//        confronta — pubblicazione e stampa le giudica il database.
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateVersioniStore } from '../stores/templateVersioni'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { DRAWER_WIDTH } from '../../core/constants'
import { parseIsoDate } from '../../core/utils/date'
import { payloadVersione } from '../utils/templateVersionePayload'
import { useLookupEtichettato } from '../../core/composables/useLookupEtichettato'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import TemplateAssetRiferimenti from './TemplateAssetRiferimenti.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const props = defineProps({
  visible: { type: Boolean, default: false },
  templateId: { type: Number, required: true },
  // `null` = nuova versione.
  versioneId: { type: [Number, null], default: null },
  emittenteFiscaleId: { type: [Number, null], default: null },
  versioneContestoBuilder: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved'])

const { t } = useI18n()
const store = useTemplateVersioniStore()
const { execute, loading, campiErrati } = useApiHandler()

// Formato del sorgente, formato e orientamento della pagina: i tre
// vocabolari a DB (brief-db-vocabolari-versione-template), con l'etichetta
// che il DB dichiara riga per riga. Il valore e' il `codice_interno`, la
// chiave che la FK della versione valida.
// ⛔ Fino al 2026-10-04 erano tre array copiati dai CHECK, e la copia era
//    gia' divergente (offriva `MARKDOWN` e `A5`, che il DB rifiutava).
const { opzioni: formatoTemplateOptions } = useLookupEtichettato(
  { rel: 'documenti.formati_template' }, { campoCodice: 'codice_interno' },
)
const { opzioni: formatOptions } = useLookupEtichettato(
  { rel: 'documenti.formati_pagina' }, { campoCodice: 'codice_interno' },
)
const { opzioni: orientationOptions } = useLookupEtichettato(
  { rel: 'documenti.orientamenti_pagina' }, { campoCodice: 'codice_interno' },
)

// Lo stato della versione letta: solo una BOZZA si modifica.
const stato = ref(null)
const isNew = computed(() => props.versioneId === null)
// ⛔ Una versione esistente NON ancora letta (`stato` null) e' in sola lettura:
//    il Salva non deve poter mandare il form vuoto, o quello della versione
//    aperta prima, sopra questa.
const isReadOnlyEffective = computed(() =>
  props.readonly || (!isNew.value && stato.value !== 'BOZZA'),
)

function emptyForm() {
  return {
    titolo: '',
    formato_template: null,
    html_template: '',
    css_template: '',
    markdown_template: '',
    render_engine_id: null,
    // Precompilata con la forma di oggi: una proposta a video, confermata
    // dal salvataggio (il backend non ha default).
    versione_contesto: props.versioneContestoBuilder,
    page_format: null,
    page_orientation: null,
    margin_top_mm: null,
    margin_right_mm: null,
    margin_bottom_mm: null,
    margin_left_mm: null,
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

const form = ref(emptyForm())
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(form, { visibile: () => props.visible })

// Scopo: carica la versione (o prepara la nuova) all'apertura. Il form si
//        svuota SUBITO: fino alla risposta non resta a video la versione
//        aperta prima. Una risposta arrivata dopo che si e' aperta un'altra
//        versione (o chiuso il drawer) si scarta.
let letturaCorrente = 0
async function carica() {
  const lettura = ++letturaCorrente
  stato.value = null
  form.value = emptyForm()
  if (isNew.value) {
    fissa()
    return
  }
  const data = await store.fetchDetail(props.templateId, props.versioneId)
  if (lettura !== letturaCorrente || !props.visible || !data) return
  stato.value = data.stato ?? null
  form.value = {
    titolo: data.titolo ?? '',
    formato_template: data.formato_template ?? null,
    html_template: data.html_template ?? '',
    css_template: data.css_template ?? '',
    markdown_template: data.markdown_template ?? '',
    render_engine_id: data.render_engine_id ?? null,
    versione_contesto: data.versione_contesto ?? null,
    page_format: data.page_format ?? null,
    page_orientation: data.page_orientation ?? null,
    margin_top_mm: data.margin_top_mm ?? null,
    margin_right_mm: data.margin_right_mm ?? null,
    margin_bottom_mm: data.margin_bottom_mm ?? null,
    margin_left_mm: data.margin_left_mm ?? null,
    // `parseIsoDate`: niente slittamento di fuso su una data senza ora.
    valido_dal: parseIsoDate(data.valido_dal),
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true,
  }
  fissa()
}

watch(
  [() => props.visible, () => props.versioneId],
  ([visible]) => { if (visible) carica() },
  { immediate: true },
)

// Le textarea in cui il pannello degli asset inserisce un riferimento.
const htmlTextarea = ref(null)
const cssTextarea = ref(null)
const TEXTAREA_PER_CAMPO = { html_template: htmlTextarea, css_template: cssTextarea }

// Scopo: Inserisce il riferimento di un asset nel campo scelto, al posto
//        della selezione (o al cursore), e rimette il cursore dopo il testo
//        inserito. Senza un cursore noto (campo mai toccato) va in coda.
async function inserisciRiferimento({ campo, testo }) {
  const el = TEXTAREA_PER_CAMPO[campo]?.value?.$el
  const valore = form.value[campo] ?? ''
  const inizio = el?.selectionStart ?? valore.length
  const fine = el?.selectionEnd ?? valore.length
  form.value[campo] = valore.slice(0, inizio) + testo + valore.slice(fine)
  await nextTick()
  if (el) {
    el.focus()
    el.setSelectionRange(inizio + testo.length, inizio + testo.length)
  }
}

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  const f = form.value
  // L'HTML e' obbligatorio come titolo, motore e forma: il backend lo pretende
  // in creazione e la colonna e' NOT NULL (prima il Salva era acceso senza, e
  // la risposta era un 400).
  return Boolean(
    f.titolo?.trim() && f.html_template?.trim() && f.render_engine_id && f.versione_contesto,
  )
})

async function salva() {
  const payload = payloadVersione(form.value, { nuova: isNew.value })
  const result = await execute(
    () => isNew.value
      ? store.create(props.templateId, payload)
      : store.update(props.templateId, props.versioneId, payload),
    { successMessage: t('config.modelli_documenti.versioni.saved') },
  )
  if (result !== null) {
    fissa()
    emit('saved', result)
    emit('update:visible', false)
  }
}

const azione = computed(() => {
  if (isNew.value) return t('common.new')
  return isReadOnlyEffective.value ? t('common.view') : t('common.edit')
})
</script>

<template>
  <AppDrawer
    :visible="visible"
    :title="t('config.modelli_documenti.versioni.drawer_title')"
    :action="azione"
    :width="DRAWER_WIDTH.COMPLEX"
    :readonly="isReadOnlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="isReadOnlyEffective ? 'chiudi' : 'form'"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @save="salva"
  >
    <div class="form-grid">
      <Message severity="info" :closable="false">
        {{ isNew
          ? t('config.modelli_documenti.versioni.creating_hint')
          : isReadOnlyEffective
            ? t('config.modelli_documenti.versioni.consulting_hint')
            : t('config.modelli_documenti.versioni.editing_hint') }}
      </Message>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_titolo') }} *</label>
        <InputText v-model="form.titolo" maxlength="255" fluid
          :invalid="campiErrati.includes('titolo')"
        />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_render_engine') }} *</label>
          <LookupSelect
            v-model="form.render_engine_id"
            rel="documenti.render_engine_documento"
            :placeholder="t('config.modelli_documenti.versioni.field_render_engine_placeholder')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_versione_contesto') }} *</label>
          <InputNumber v-model="form.versione_contesto"
            :min="1" :use-grouping="false" fluid
            :invalid="campiErrati.includes('versione_contesto')"
          />
          <small v-if="props.versioneContestoBuilder" class="app-text-muted">
            {{ t('config.modelli_documenti.versioni.versione_contesto_hint', {
              forma: props.versioneContestoBuilder,
            }) }}
          </small>
          <small v-else class="app-text-muted">
            {{ t('config.modelli_documenti.versioni.versione_contesto_builder_assente') }}
          </small>
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_formato') }}</label>
          <Select
            v-model="form.formato_template"
            :options="formatoTemplateOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :show-clear="isNew"
            fluid
            :invalid="campiErrati.includes('formato_template')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo"
            :invalid="campiErrati.includes('attivo')"
          />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_html') }} *</label>
        <Textarea ref="htmlTextarea" v-model="form.html_template" rows="10" auto-resize fluid
          :invalid="campiErrati.includes('html_template')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_css') }}</label>
        <Textarea ref="cssTextarea" v-model="form.css_template" rows="6" auto-resize fluid
          :invalid="campiErrati.includes('css_template')"
        />
      </div>
      <div class="form-field">
        <TemplateAssetRiferimenti
          :emittente-fiscale-id="props.emittenteFiscaleId"
          :readonly="isReadOnlyEffective"
          @inserisci="inserisciRiferimento"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_markdown') }}</label>
        <Textarea v-model="form.markdown_template" rows="6" auto-resize fluid
          :invalid="campiErrati.includes('markdown_template')"
        />
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_page_format') }}</label>
          <Select
            v-model="form.page_format"
            :options="formatOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :show-clear="isNew"
            fluid
            :invalid="campiErrati.includes('page_format')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_page_orientation') }}</label>
          <Select
            v-model="form.page_orientation"
            :options="orientationOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :show-clear="isNew"
            fluid
            :invalid="campiErrati.includes('page_orientation')"
          />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_margin_top') }}</label>
          <InputNumber v-model="form.margin_top_mm" :min="0" :max="100" fluid
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :invalid="campiErrati.includes('margin_top_mm')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_margin_right') }}</label>
          <InputNumber v-model="form.margin_right_mm" :min="0" :max="100" fluid
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :invalid="campiErrati.includes('margin_right_mm')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_margin_bottom') }}</label>
          <InputNumber v-model="form.margin_bottom_mm" :min="0" :max="100" fluid
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :invalid="campiErrati.includes('margin_bottom_mm')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_margin_left') }}</label>
          <InputNumber v-model="form.margin_left_mm" :min="0" :max="100" fluid
            :placeholder="t('config.modelli_documenti.versioni.default_sistema')"
            :invalid="campiErrati.includes('margin_left_mm')"
          />
        </div>
      </div>
    </div>
  </AppDrawer>
</template>
