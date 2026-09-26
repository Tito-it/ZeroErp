<!--
  Scopo: Building block per l'intestazione "contesto padre" dei drawer di
         RIGA / FIGLIO (es. ContrattoRigheDrawer, OffertaEccezioniDrawer).
         Centralizza il pattern duplicato 2026-05-29 (regola del 2).

         Layout (refactor 2026-05-29 bis):
           ┌─────────────────────────────────────────────────────────┐
           │ [Tag]  Cliente: NomeCliente              [Tag stato]    │  ← primary row
           │        Valido dal: 01/01/2026  Valido al: 31/12/2026    │  ← secondary row
           └─────────────────────────────────────────────────────────┘
         - Primary row: Tag identificativo + items[0] (cliente) + slot status a destra
         - Secondary row: items[1..N] in griglia 2 colonne (es. valido_dal | valido_al)

         Uso:
           <DrawerContextHeader
             :tag-value="contrattoNumero"
             :items="[
               { label: t('vendite.contratti.col_ba'),         value: contrattoCliente },
               { label: t('vendite.contratti.col_valido_dal'), value: displayDate(contrattoValidoDal) },
               { label: t('vendite.contratti.col_valido_al'),  value: contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' },
             ]">
             <template #status>
               <Tag v-if="contrattoStatoCodice"
                 :value="contrattoStatoDescrizione"
                 :severity="statoContrattoSeverity(contrattoStatoCodice)" />
             </template>
           </DrawerContextHeader>

         Slot:
           - default (opzionale): tag identificativo principale custom (override del Tag generato)
           - #status: zona destra della primary row per Tag stato

         Props:
           - tagValue: string -- testo del Tag numero/codice principale (con contorno)
           - tagSeverity: string -- severity PrimeVue del Tag (default 'secondary')
           - items: Array<{ label: string, value: string|number|null, fallback?: string }>
                    -- items[0] sta sulla primary row col Tag, items[1..] sulla secondary row.
                    Se value è null/undefined/'', mostra fallback (default '—').
-->
<script setup>
import { computed } from 'vue'
import Tag from 'primevue/tag'

const props = defineProps({
  tagValue: { type: String, default: null },
  tagSeverity: { type: String, default: 'secondary' },
  items: { type: Array, default: () => [] },
})

const primaryItem = computed(() => props.items[0] || null)
const secondaryItems = computed(() => props.items.slice(1))

// Scopo: risolve il valore visualizzato per un item, applicando il fallback
//        quando value è null/undefined o stringa vuota. Default '—'.
function displayValue(item) {
  if (item.value != null && item.value !== '') return item.value
  return item.fallback || '—'
}
</script>

<template>
  <div class="drawer-context-header">
    <div class="drawer-context-header-primary">
      <slot>
        <Tag v-if="tagValue" :value="tagValue" :severity="tagSeverity" />
      </slot>
      <div v-if="primaryItem" class="drawer-context-header-item">
        <span class="drawer-context-header-label">{{ primaryItem.label }}</span>
        <span class="font-bold">{{ displayValue(primaryItem) }}</span>
      </div>
      <div v-if="$slots.status" class="drawer-context-header-status">
        <slot name="status" />
      </div>
    </div>
    <div
      v-if="secondaryItems.length"
      class="drawer-context-header-secondary"
    >
      <div
        v-for="(item, idx) in secondaryItems"
        :key="idx"
        class="drawer-context-header-item"
      >
        <span class="drawer-context-header-label">{{ item.label }}</span>
        <span class="font-bold">{{ displayValue(item) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawer-context-header {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.5rem;
}

.drawer-context-header-primary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex-wrap: wrap;
}

.drawer-context-header-secondary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.35rem 1rem;
  min-width: 0;
}

.drawer-context-header-item {
  display: inline-flex;
  align-items: baseline;
  gap: 0.4rem;
  min-width: 0;
  font-size: 0.9rem;
}

.drawer-context-header-label {
  color: var(--app-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}

.drawer-context-header-item > span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-context-header-status {
  margin-left: auto;
  flex: 0 0 auto;
}

@media (max-width: 767.98px) {
  .drawer-context-header-primary {
    flex-direction: column;
    align-items: flex-start;
  }

  .drawer-context-header-status {
    margin-left: 0;
  }

  .drawer-context-header-secondary {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
