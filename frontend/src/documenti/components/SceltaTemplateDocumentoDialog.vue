<script setup>
// Scopo: Dialog di scelta template applicabile per la generazione di
//        un documento (Tranche M). Si apre solo quando esistono >1
//        template applicabili per la coppia (sorgente_tipo, emittente);
//        il caller (GeneraPdfButton) gestisce i casi 0 e 1 senza dialog.
//        Il default `is_default=true` viene preselezionato all'apertura.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../core/components/AppDialog.vue'
import Listbox from 'primevue/listbox'
import Tag from 'primevue/tag'

const props = defineProps({
  visible: { type: Boolean, default: false },
  templates: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'select', 'cancel'])

const { t } = useI18n()
const selectedId = ref(null)

// Pre-seleziono il template `is_default` all'apertura. Se nessuno e'
// default, lascio il primo della lista per ridurre il click.
watch(
  [() => props.visible, () => props.templates],
  ([visible, templates]) => {
    if (!visible) return
    const def = templates.find(t => t.is_default)
    selectedId.value = def?.id ?? templates[0]?.id ?? null
  },
)

const canConfirm = computed(() => selectedId.value != null && !props.loading)

function confirm() {
  if (!canConfirm.value) return
  emit('select', selectedId.value)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    @cancel="emit('cancel')"
    :header="t('documenti.scelta_template.title')"
    width="md"
    :loading="loading"
    :save-disabled="!canConfirm"
    :save-label="t('documenti.scelta_template.confirm')"
    @save="confirm"
  >
    <p class="app-text-muted">
      {{ t('documenti.scelta_template.subtitle') }}
    </p>
    <Listbox
      v-model="selectedId"
      :options="templates"
      option-label="descrizione"
      option-value="id"
      :listStyle="'max-height: 320px'"
    >
      <template #option="{ option }">
        <div class="app-lookup-option">
          <div class="app-lookup-option__primary">
            {{ option.descrizione }}
            <Tag
              v-if="option.is_default"
              :value="t('common.default')"
              severity="info"
            />
          </div>
          <div class="app-lookup-option__secondary">{{ option.codice }}</div>
          <div class="app-lookup-option__meta">
            <span v-if="option.tipo_documento_output_descrizione">
              {{ option.tipo_documento_output_descrizione }}
            </span>
            <span v-if="option.context_builder_code">{{ option.context_builder_code }}</span>
          </div>
        </div>
      </template>
    </Listbox>
  </AppDialog>
</template>
