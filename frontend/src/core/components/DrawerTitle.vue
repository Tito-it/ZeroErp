<script setup>
// Scopo: Titolo standard per drawer. Azione a sinistra (piccola verde),
// icona + entita' centrata (verde grande).
// Layout a 3 colonne: [azione] [icona + titolo centrato] [spacer bilanciamento].
// Usare nel #header slot di ogni Drawer.
defineProps({
  action: { type: String, default: '' },
  title: { type: String, required: true },
  icon: { type: String, default: '' }
})
</script>

<template>
  <div class="app-drawer-title">
    <span class="app-drawer-title-action">{{ action }}</span>
    <span class="app-drawer-title-entity">
      <i v-if="icon" :class="icon" class="app-drawer-title-icon" />
      {{ title }}
    </span>
    <span class="app-drawer-title-action" style="visibility: hidden;">{{ action }}</span>
  </div>
</template>

<style scoped>
.app-drawer-title {
  display: flex;
  align-items: baseline;
  flex: 1;
}
.app-drawer-title-action {
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-primary-color);
  white-space: nowrap;
}
.app-drawer-title-entity {
  flex: 1;
  text-align: center;
  font-size: 1.35rem;
  font-weight: 600;
  color: var(--p-primary-color);
}
.app-drawer-title-icon {
  font-size: 1.1rem;
  margin-right: 0.4rem;
  vertical-align: baseline;
}
</style>
