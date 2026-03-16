<script setup>
// Scopo: Building block form indirizzo per layer soggetto (identita').
// Supporta multi-tipo con barra tag, auto-clone per obbligatori.
// Modalita' normalizzata (comune + via + civico) e libera (estero).

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import StradarioAutocomplete from './StradarioAutocomplete.vue'

const { t } = useI18n()

defineProps({
  form: { type: Object, required: true },
  isLibera: { type: Boolean, default: false },
  tipiStato: { type: Array, default: () => [] },
  toponomasticaLookup: { type: Object, required: true },
  statiLookup: { type: Object, default: null },
  capOptions: { type: Array, default: () => [] },
  loadingCap: { type: Boolean, default: false },
  autoClone: { type: Boolean, default: true },
  indirizzoWarnings: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false }
})

defineEmits(['update:isLibera', 'update:autoClone', 'switchTipo'])
</script>

<template>
  <div class="form-grid">
    <!-- Barra tag tipi indirizzo -->
    <div v-if="tipiStato.length > 0" class="indirizzo-tipi-bar">
      <div
        v-for="tipo in tipiStato"
        :key="tipo.codice"
        class="indirizzo-tipo-tag"
        :class="{
          'indirizzo-tipo-tag--attivo': tipo.attivo,
          'indirizzo-tipo-tag--compilato': tipo.compilato,
          'indirizzo-tipo-tag--obbligatorio': tipo.obbligatorio,
        }"
        @click="$emit('switchTipo', tipo.codice)"
        :title="tipo.obbligatorio ? t('indirizzo_soggetto.obbligatorio') : ''"
      >
        <i v-if="tipo.compilato" class="pi pi-check" style="font-size: 0.7rem;" />
        <span>{{ tipo.descrizione }}</span>
        <span v-if="tipo.obbligatorio" class="indirizzo-tipo-req">*</span>
      </div>
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

      <Message v-for="(msg, i) in indirizzoWarnings" :key="i" severity="warn" size="small" class="mt-1">
        {{ msg }}
      </Message>
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

    <!-- Auto-clone checkbox -->
    <div v-if="tipiStato.filter(t => t.obbligatorio).length > 1" class="form-field">
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <Checkbox
          :modelValue="autoClone"
          @update:modelValue="$emit('update:autoClone', $event)"
          :binary="true"
          input-id="auto-clone"
          :disabled="disabled"
        />
        <label for="auto-clone" class="app-text-secondary">
          {{ t('indirizzo_soggetto.auto_clone') }}
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.indirizzo-tipi-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}

.indirizzo-tipo-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.6rem;
  border-radius: var(--p-border-radius-sm, 4px);
  font-size: 0.8rem;
  cursor: pointer;
  border: 1px solid var(--p-surface-300);
  background: var(--p-surface-50);
  color: var(--p-text-muted-color);
  transition: all 0.15s;
}

.indirizzo-tipo-tag:hover {
  border-color: var(--p-primary-300);
  background: var(--p-primary-50);
}

.indirizzo-tipo-tag--attivo {
  border-color: var(--p-primary-500);
  background: var(--p-primary-50);
  color: var(--p-primary-700);
  font-weight: 600;
}

.indirizzo-tipo-tag--compilato {
  border-color: var(--p-green-300);
  color: var(--p-green-700);
}

.indirizzo-tipo-tag--compilato.indirizzo-tipo-tag--attivo {
  border-color: var(--p-primary-500);
  color: var(--p-primary-700);
}

.indirizzo-tipo-req {
  color: var(--p-red-500);
  font-weight: 700;
}

.app-text-secondary {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
</style>
