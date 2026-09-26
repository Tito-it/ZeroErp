<script setup>
// Scopo: componente logo ZeroERP riutilizzabile — usato in sidebar e login.
// Usa il logo PNG centralizzato in assets/images/logo-zeroerp.png.
// Accetta prop size per varianti dimensionali.
import logoSrc from '@/assets/images/logo-zeroerp.png'

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
    <img :src="logoSrc" alt="ZeroERP" class="logo-brand-icon" />
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
  width: var(--app-logo-size);
  height: var(--app-logo-size);
  min-width: var(--app-logo-size);
  border-radius: var(--app-logo-radius);
  object-fit: cover;
}

.logo-brand-text {
  font-weight: 600;
  font-size: var(--app-font-size-lg);
  color: var(--app-text-color);
  white-space: nowrap;
}

/* Variante large per login */
.logo-brand--large .logo-brand-icon {
  width: 40px;
  height: 40px;
  min-width: 40px;
}

.logo-brand--large .logo-brand-text {
  font-weight: 700;
  font-size: 1.5rem;
}
</style>
