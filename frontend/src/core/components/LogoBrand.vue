<script setup>
// Scopo: componente logo ZeroERP riutilizzabile — usato in sidebar e login.
// Accetta prop size per varianti dimensionali.
defineProps({
  size: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'large'].includes(v)
  },
  showText: {
    type: Boolean,
    default: true
  }
})
</script>

<template>
  <div class="logo-brand" :class="[`logo-brand--${size}`]">
    <span class="logo-brand-icon">Z</span>
    <span v-if="showText" class="logo-brand-text">ZeroERP</span>
  </div>
</template>

<style scoped>
.logo-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--app-logo-size);
  height: var(--app-logo-size);
  min-width: var(--app-logo-size);
  border-radius: var(--app-logo-radius);
  background: var(--app-logo-bg);
  color: var(--app-logo-color);
  font-weight: 700;
  font-size: var(--app-font-size-lg);
}

.logo-brand-text {
  font-weight: 600;
  font-size: var(--app-font-size-lg);
  color: var(--p-text-color);
  white-space: nowrap;
}

/* Variante large per login */
.logo-brand--large .logo-brand-icon {
  width: 40px;
  height: 40px;
  min-width: 40px;
  font-size: 1.3rem;
}

.logo-brand--large .logo-brand-text {
  font-weight: 700;
  font-size: 1.5rem;
}
</style>
