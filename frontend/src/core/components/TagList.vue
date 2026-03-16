<script setup>
// Scopo: Componente generico per mostrare una lista di tag con overflow.
// Mostra i primi N tag, poi un "+X" con tooltip per i rimanenti.
// Riutilizzabile per: ruoli, utility, competenze, categorie, ecc.

import Tag from 'primevue/tag'

const props = defineProps({
  items: { type: Array, default: () => [] },
  labelField: { type: String, default: 'descrizione' },
  keyField: { type: String, default: 'codice' },
  maxVisible: { type: Number, default: 2 },
  severity: { type: String, default: 'info' },
  overflowSeverity: { type: String, default: 'secondary' },
})
</script>

<template>
  <div v-if="items.length" class="tag-list">
    <Tag
      v-for="item in items.slice(0, maxVisible)"
      :key="item[keyField]"
      :value="item[labelField]"
      :severity="severity"
    />
    <Tag
      v-if="items.length > maxVisible"
      :value="`+${items.length - maxVisible}`"
      :severity="overflowSeverity"
      v-tooltip.top="items.slice(maxVisible).map(i => i[labelField]).join(', ')"
    />
  </div>
</template>

<style scoped>
.tag-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
</style>
