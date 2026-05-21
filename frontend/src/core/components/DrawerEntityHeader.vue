<script setup>
// Scopo: header informativo dei drawer entita' (numero + data + badge contesto
//   + Tag stato a destra). Mirror strutturale dei pattern duplicati su
//   ContrattoDrawer/PreventiviDrawer (.x-drawer-header-row).
//
// Il BB e' puramente di layout: niente logica di stato, niente formatter.
// Il chiamante popola il default slot (info a sinistra) e lo slot #status
// (Tag stato a destra). La classe .app-drawer-header-muted resta esposta
// per riusare lo stile "data sottotono" inline (vedi main.css).
//
// Uso tipico:
//   <DrawerEntityHeader>
//     <Tag :value="detail.numero" severity="secondary" />
//     <span class="app-drawer-header-muted">{{ displayDate(detail.data) }}</span>
//     <Tag :value="t('contratti.forma_con_listino')" severity="info" />
//
//     <template #status>
//       <Tag :value="detail.stato_descrizione"
//            :severity="statoContrattoSeverity(detail.stato_codice)" />
//     </template>
//   </DrawerEntityHeader>
</script>

<template>
  <div class="app-drawer-header-row">
    <div class="app-drawer-header-info">
      <slot />
    </div>
    <div v-if="$slots.status" class="app-drawer-header-status">
      <slot name="status" />
    </div>
  </div>
</template>
