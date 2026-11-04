<script setup>
// Scopo: Building block form indirizzo per layer soggetto (identita').
// Supporta multi-tipo con barra tag, auto-clone per obbligatori.
// Modalita' normalizzata (comune + via + civico) e libera, in due forme decise
// dallo stato scelto (`indirizzoLibero.js`): comune e CAP dall'elenco per uno
// stato col catalogo dei comuni, la localita' per gli altri.

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import { STATUS_ICONS } from '../../core/constants'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import CivicoDettaglioCampi from './CivicoDettaglioCampi.vue'
import StradarioAutocomplete from './StradarioAutocomplete.vue'
import StradarioGeneraleAutocomplete from './StradarioGeneraleAutocomplete.vue'
import { isFormaCatalogo, statoDi } from '../composables/indirizzoLibero'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  isLibera: { type: Boolean, default: false },
  tipiStato: { type: Array, default: () => [] },
  statiLookup: { type: Object, default: null },
  capOptions: { type: Array, default: () => [] },
  loadingCap: { type: Boolean, default: false },
  autoClone: { type: Boolean, default: true },
  indirizzoWarnings: { type: Array, default: () => [] },
  addressNotFound: { type: Boolean, default: false },
  tipiEsistenti: { type: Array, default: () => [] },
  comuneInitialItem: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
  // I nomi dei campi che il backend chiede di correggere (`campiErrati` del
  // drawer padre): il guard del civico li manda per civico e dettagli.
  campiErrati: { type: Array, default: () => [] }
})

defineEmits(['update:isLibera', 'update:autoClone', 'switchTipo'])

const stradarioRef = ref(null)
const stradarioGenRef = ref(null)

// Arricchisce tipiStato con flag 'esistente' (gia' creato nel DB per questa istanza)
const tipiStatoArricchiti = computed(() =>
  props.tipiStato.map(t => ({
    ...t,
    esistente: props.tipiEsistenti.includes(t.codice_interno),
  }))
)

// Descrizione del tipo indirizzo attivo (per il titolo sopra il form)
const tipoAttivoDescrizione = computed(() => {
  const attivo = tipiStatoArricchiti.value.find(t => t.attivo)
  return attivo?.descrizione || null
})

// La forma dell'indirizzo libero, dal flag dello stato scelto.
const formaCatalogo = computed(() =>
  isFormaCatalogo(statoDi(props.statiLookup?.items.value, form.value.stato_id)))

// True se almeno un tab e' selezionato (non esistente)
const hasTabAttivo = computed(() => !!tipoAttivoDescrizione.value)

// Warning "via non trovata" — differenziato per stradario locale vs generale
const viaNoResultsLocale = computed(() =>
  !form.value.via_nuova && (stradarioRef.value?.noResults || false)
)
const viaNoResultsGenerale = computed(() =>
  form.value.via_nuova && (stradarioGenRef.value?.noResults || false)
)
</script>

<template>
  <div class="form-grid">
    <!-- Barra tab tipi indirizzo -->
    <div v-if="tipiStatoArricchiti.length > 0" class="indirizzo-tipi-bar">
      <div
        v-for="tipo in tipiStatoArricchiti"
        :key="tipo.codice_interno"
        class="indirizzo-tipo-tab"
        :class="{
          'indirizzo-tipo-tab--attivo': tipo.attivo,
          'indirizzo-tipo-tab--compilato': tipo.compilato && !tipo.attivo,
          'indirizzo-tipo-tab--esistente': tipo.esistente,
        }"
        @click="!tipo.esistente && $emit('switchTipo', tipo.codice_interno)"
        :title="tipo.esistente ? t('anagrafiche.indirizzo_soggetto.tipo_gia_creato') : (tipo.obbligatorio ? t('anagrafiche.indirizzo_soggetto.obbligatorio') : '')"
      >
        <i v-if="tipo.compilato && !tipo.esistente" :class="STATUS_ICONS.SI" style="font-size: 0.7rem;" />
        <i v-else-if="tipo.esistente" :class="STATUS_ICONS.BLOCCATO" style="font-size: 0.65rem;" />
        <span>{{ tipo.descrizione }}</span>
        <span v-if="tipo.obbligatorio && !tipo.esistente" class="indirizzo-tipo-req">*</span>
      </div>
    </div>

    <!-- Titolo tipo attivo + opzioni (solo se un tab e' selezionato) -->
    <template v-if="hasTabAttivo">
    <div class="indirizzo-tipo-titolo">{{ tipoAttivoDescrizione }}</div>

    <!-- Checkbox: auto-clone + formato libero + via non presente (affiancati) -->
    <div class="form-row-inline" style="flex-wrap: wrap;">
      <div v-if="tipiStatoArricchiti.filter(t => t.obbligatorio && !t.esistente).length > 1" style="display: flex; align-items: center; gap: 0.5rem;">
        <Checkbox
          :modelValue="autoClone"
          @update:modelValue="$emit('update:autoClone', $event)"
          :binary="true"
          input-id="auto-clone"
          :disabled="disabled"
        />
        <label for="auto-clone" class="app-text-secondary">{{ t('anagrafiche.indirizzo_soggetto.auto_clone') }}</label>
      </div>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <Checkbox
          :modelValue="isLibera"
          @update:modelValue="$emit('update:isLibera', $event)"
          :binary="true"
          input-id="indirizzo-libero"
          :disabled="disabled"
        />
        <label for="indirizzo-libero">{{ t('anagrafiche.indirizzo_soggetto.modalita_libera') }}</label>
      </div>
      <div v-if="!isLibera" style="display: flex; align-items: center; gap: 0.5rem;">
        <Checkbox v-model="form.via_nuova" :binary="true" input-id="via-nuova-sogg" :disabled="disabled" />
        <label for="via-nuova-sogg">{{ t('indirizzi.via_non_presente') }}</label>
      </div>
    </div>

    <!-- === MODALITA' LIBERA: via scritta e stato === -->
    <template v-if="isLibera">
      <div class="form-field">
        <label>{{ t('anagrafiche.indirizzo_soggetto.indirizzo_libero') }} *</label>
        <InputText v-model="form.indirizzo_libero" :disabled="disabled" />
      </div>
      <div class="form-field" v-if="statiLookup">
        <label>{{ t('anagrafiche.indirizzo_soggetto.stato') }} *</label>
        <Select
          v-model="form.stato_id"
          :options="statiLookup.items.value"
          :loading="statiLookup.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('geo.select_stato')"
          :disabled="disabled"
          filter
        />
      </div>
    </template>

    <!-- Comune + CAP affiancati: dell'indirizzo normalizzato, e della forma
         libera «del catalogo» (stato col catalogo dei comuni). Un blocco solo. -->
    <template v-if="!isLibera || formaCatalogo">
      <div style="display: flex; gap: 0.5rem;">
        <div class="form-field" style="flex: 3;">
          <label>{{ t('indirizzi.campo_comune') }} *</label>
          <ComuneAutocomplete v-model="form.comune_id"
            :initial-item="form._comune_obj || comuneInitialItem"
            :disabled="disabled"
            @item-selected="obj => form._comune_obj = obj" />
        </div>
        <div class="form-field" style="flex: 1;">
          <label>{{ t('indirizzi.campo_cap') }} *</label>
          <Select
            v-model="form.codice_postale_id"
            :options="capOptions"
            option-label="codice"
            option-value="id"
            :placeholder="t('indirizzi.campo_cap')"
            :loading="loadingCap"
            :disabled="disabled || !form.comune_id"
          />
        </div>
      </div>

    </template>

    <!-- === MODALITA' NORMALIZZATA: via e civico === -->
    <template v-if="!isLibera">
      <!-- Via esistente (stradario locale) -->
      <template v-if="!form.via_nuova">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_via') }} *</label>
          <StradarioAutocomplete
            ref="stradarioRef"
            v-model="form.via_obj"
            :comune-id="form.comune_id"
            :disabled="disabled || !form.comune_id"
          />
        </div>
      </template>

      <!-- Via nuova: autocomplete su stradario_generale -->
      <template v-if="form.via_nuova">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_via') }} *</label>
          <StradarioGeneraleAutocomplete
            ref="stradarioGenRef"
            v-model="form.via_obj"
            :disabled="disabled"
          />
        </div>
      </template>

      <!-- Civico e dettagli -->
      <CivicoDettaglioCampi :form="form" :campi-errati="campiErrati" :disabled="disabled" />

      <Message v-if="viaNoResultsLocale" severity="warn" size="small" class="mt-1">
        {{ t('indirizzi.via_non_trovata_crea_nuovo') }}
      </Message>
      <Message v-if="viaNoResultsGenerale" severity="warn" size="small" class="mt-1">
        {{ t('indirizzi.via_non_trovata_stradario_generale') }}
      </Message>
      <Message v-for="(msg, i) in indirizzoWarnings" :key="i" v-show="form.via_nuova" severity="warn" size="small" class="mt-1">
        {{ msg }}
      </Message>
      <Message v-if="addressNotFound && form.via_nuova" severity="warn" size="small" class="mt-1">
        {{ t('indirizzi.indirizzo_non_trovato') }}
      </Message>
    </template>

    <!-- === MODALITA' LIBERA: i campi della forma estera === -->
    <template v-if="isLibera">
      <!-- Forma estera: la localita'; codice postale e regione facoltativi. -->
      <template v-if="!formaCatalogo && form.stato_id">
        <div class="form-field">
          <label>{{ t('anagrafiche.indirizzo_soggetto.locality') }} *</label>
          <InputText v-model="form.locality" :disabled="disabled" />
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.indirizzo_soggetto.postal_code') }}</label>
            <InputText v-model="form.postal_code" :disabled="disabled" />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.indirizzo_soggetto.administrative_area') }}</label>
            <InputText v-model="form.administrative_area" :disabled="disabled" />
          </div>
        </div>
      </template>
      <div v-if="form.stato_id" class="form-field">
        <label>{{ t('anagrafiche.indirizzo_soggetto.sublocality') }}</label>
        <InputText v-model="form.sublocality" :disabled="disabled" />
      </div>
    </template>

    </template><!-- /hasTabAttivo -->

  </div>
</template>

<style scoped>
.indirizzo-tipi-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: 0.5rem;
}

.indirizzo-tipo-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.5rem 0.85rem;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--app-text-muted);
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  user-select: none;
}

.indirizzo-tipo-tab:hover:not(.indirizzo-tipo-tab--esistente) {
  color: var(--p-primary-500);
  border-bottom-color: var(--p-primary-200);
}

.indirizzo-tipo-tab--attivo {
  color: var(--p-primary-700);
  border-bottom-color: var(--p-primary-500);
  font-weight: 600;
}

.indirizzo-tipo-tab--compilato {
  color: var(--p-green-700);
  border-bottom-color: var(--p-green-300);
}

.indirizzo-tipo-tab--esistente {
  color: var(--p-surface-400);
  cursor: not-allowed;
  opacity: 0.6;
}

.indirizzo-tipo-titolo {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--p-primary-700);
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--p-surface-200);
}

.indirizzo-tipo-req {
  color: var(--app-severity-danger);
  font-weight: 700;
}

.app-text-secondary {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
