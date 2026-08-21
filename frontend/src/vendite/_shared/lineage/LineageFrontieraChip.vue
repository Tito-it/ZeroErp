<script setup>
// Scopo: Cella "Transito" delle liste documento (lineage Fase B) — chip del
// documento più prossimo in esecuzione (frontiera): "→ <tipo> CODICE · fase".
// Segnale in sola lettura (il drill-down vive nel pannello "Passaggi" del
// drawer). Fan-out F/H: suffisso "+N attive" quando ci sono più discendenti
// attivi (G-9). "—" se il documento non ha ancora transitato.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { faseDocumentoSeverity } from '../../../core/utils/severity'
import { lineageTipoLabel } from './lineageLabels'

defineProps({
  isTransitato: { type: Boolean, default: false },
  tipoCodice: { type: String, default: null },
  codice: { type: String, default: null },
  stato: { type: String, default: null },
  fase: { type: String, default: null },
  nAttivi: { type: Number, default: 0 },
})

const { t, te } = useI18n()

// Etichetta i18n del tipo sorgente (helper condiviso lineage, fail-visible).
function tipoLabel(codice) {
  return lineageTipoLabel(t, te, codice)
}
</script>

<template>
  <!-- ⚠️ Il gate e' sul TIPO, non sul codice: una frontiera EMESSA ma non
       ancora numerata (fattura o nota di credito prima di «Rendi definitive»)
       ha `codice` NULL — col vecchio gate la cella mostrava «—», cioe' «non
       transitato», per un documento che in esecuzione c'e' eccome. Stessa
       fallback `non_numerato` delle tappe del pannello (2026-08-20/21). -->
  <span v-if="isTransitato && tipoCodice" class="lineage-cell-chip">
    <i class="pi pi-arrow-right lineage-cell-arrow" />
    <Tag :value="tipoLabel(tipoCodice)" severity="secondary" />
    <span class="lineage-cell-codice">{{ codice || t('vendite.lineage.non_numerato') }}</span>
    <Tag
      v-if="stato || fase"
      :value="stato ?? fase"
      :severity="faseDocumentoSeverity(fase)" />
    <span v-if="nAttivi > 1" class="lineage-cell-muted">
      {{ t('vendite.lineage.altre_attive', { n: nAttivi - 1 }) }}
    </span>
  </span>
  <span v-else class="lineage-cell-muted">—</span>
</template>

<style scoped>
.lineage-cell-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}
.lineage-cell-arrow {
  font-size: 0.75rem;
  color: var(--app-text-muted);
}
.lineage-cell-codice {
  font-weight: 600;
}
.lineage-cell-muted {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
