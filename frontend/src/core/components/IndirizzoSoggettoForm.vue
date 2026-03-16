<script setup>
// Scopo: Building block form indirizzo per layer soggetto (identita').
// Supporta modalita' normalizzata (comune + via + civico)
// e modalita' libera (indirizzo testuale + stato) per indirizzi esteri.
// Il tipo indirizzo e' filtrato dalla matrice del tipo soggetto.

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import StradarioAutocomplete from './StradarioAutocomplete.vue'

const { t } = useI18n()

defineProps({
  form: { type: Object, required: true },
  isLibera: { type: Boolean, default: false },
  tipiIndirizzo: { type: Array, default: () => [] },
  toponomasticaLookup: { type: Object, required: true },
  statiLookup: { type: Object, default: null },
  capOptions: { type: Array, default: () => [] },
  loadingCap: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})

defineEmits(['update:isLibera'])
</script>

<template>
  <div class="form-grid">
    <!-- Tipo indirizzo (filtrato dalla matrice) -->
    <div class="form-field">
      <label>{{ t('indirizzo_soggetto.tipo_indirizzo') }} *</label>
      <Select
        v-model="form.tipo_indirizzo_codice"
        :options="tipiIndirizzo"
        option-label="descrizione"
        option-value="codice"
        :placeholder="t('indirizzo_soggetto.select_tipo_indirizzo')"
        :disabled="disabled"
        class="w-full"
      />
    </div>

    <!-- Switch modalita' libera -->
    <div class="form-field">
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <Checkbox
          :modelValue="isLibera"
          @update:modelValue="$emit('update:isLibera', $event)"
          :binary="true"
          input-id="indirizzo-libero"
          :disabled="disabled"
        />
        <label for="indirizzo-libero">{{ t('indirizzo_soggetto.modalita_libera') }}</label>
      </div>
    </div>

    <!-- === MODALITA' NORMALIZZATA === -->
    <template v-if="!isLibera">
      <div class="form-field">
        <label>{{ t('indirizzi.campo_comune') }} *</label>
        <ComuneAutocomplete v-model="form.comune_id" :disabled="disabled" />
      </div>

      <!-- Via esistente (stradario) -->
      <template v-if="!form.via_nuova">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_via') }} *</label>
          <StradarioAutocomplete
            v-model="form.stradario_obj"
            :comune-id="form.comune_id"
            :disabled="disabled || !form.comune_id"
          />
        </div>
      </template>

      <!-- Checkbox via non presente -->
      <div class="form-field">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <Checkbox v-model="form.via_nuova" :binary="true" input-id="via-nuova-sogg" :disabled="disabled" />
          <label for="via-nuova-sogg">{{ t('indirizzi.via_non_presente') }}</label>
        </div>
      </div>

      <!-- Via nuova -->
      <template v-if="form.via_nuova">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_toponomastica') }} *</label>
          <Select
            v-model="form.toponomastica_id"
            :options="toponomasticaLookup.items.value"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('indirizzi.campo_toponomastica')"
            :loading="toponomasticaLookup.loading.value"
            :disabled="disabled"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_nome_via') }} *</label>
          <InputText v-model="form.nome_via" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_cap') }} *</label>
          <Select
            v-model="form.codice_postale_id"
            :options="capOptions"
            option-label="codice"
            option-value="id"
            :placeholder="t('indirizzi.campo_cap')"
            :loading="loadingCap"
            :disabled="disabled || !form.comune_id"
            class="w-full"
          />
        </div>
      </template>

      <!-- Civico e dettagli -->
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_civico') }}</label>
          <InputNumber v-model="form.civico" :use-grouping="false" :disabled="disabled" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_estensione') }}</label>
          <InputText v-model="form.estensione_civico" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_palazzina') }}</label>
          <InputText v-model="form.palazzina" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_scala') }}</label>
          <InputText v-model="form.scala" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_piano') }}</label>
          <InputText v-model="form.piano" :disabled="disabled" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('indirizzi.campo_interno') }}</label>
          <InputText v-model="form.interno" :disabled="disabled" class="w-full" />
        </div>
      </div>
    </template>

    <!-- === MODALITA' LIBERA === -->
    <template v-else>
      <div class="form-field">
        <label>{{ t('indirizzo_soggetto.indirizzo_libero') }} *</label>
        <InputText v-model="form.indirizzo_libero" :disabled="disabled" class="w-full" />
      </div>
      <div class="form-field" v-if="statiLookup">
        <label>{{ t('indirizzo_soggetto.stato') }} *</label>
        <Select
          v-model="form.stato_id"
          :options="statiLookup.items.value"
          :loading="statiLookup.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('geo.select_stato')"
          :disabled="disabled"
          filter
          class="w-full"
        />
      </div>
      <div class="form-field">
        <label>{{ t('indirizzo_soggetto.locality') }}</label>
        <InputText v-model="form.locality" :disabled="disabled" class="w-full" />
      </div>
    </template>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
