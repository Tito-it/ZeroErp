<script setup>
// Scopo: Cella "Fase" delle liste documento (lineage Fase B) — Tag colorato
// dalla fase normalizzata proiettata (faseDocumentoSeverity), etichetta i18n
// riusata dai cruscotti (dashFaseLabel, vocabolario dash_comune.fase_*).
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { faseDocumentoSeverity } from '../../../core/utils/severity'
import { dashFaseLabel } from '../../dashboardAree'

defineProps({ fase: { type: String, default: null } })

const { t, te } = useI18n()
</script>

<template>
  <Tag
    v-if="fase"
    :value="dashFaseLabel(t, te, fase)"
    :severity="faseDocumentoSeverity(fase)" />
  <span v-else class="lineage-cell-muted">—</span>
</template>

<style scoped>
.lineage-cell-muted {
  color: var(--app-text-muted);
}
</style>
