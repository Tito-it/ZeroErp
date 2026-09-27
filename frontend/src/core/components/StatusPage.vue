<script setup>
// Scopo: componente riutilizzabile per pagine di stato — errori (404, 403),
// placeholder WIP, o qualsiasi pagina informativa centrata con icona + testo.
import Button from 'primevue/button'
import { STATUS_ICONS } from '../constants'

defineProps({
  icon: { type: String, default: STATUS_ICONS.INFO },
  title: { type: String, required: true },
  message: { type: String, default: '' },
  features: { type: Array, default: () => [] },
  featuresLabel: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
  actionIcon: { type: String, default: '' },
  showCard: { type: Boolean, default: false }
})

const emit = defineEmits(['action'])
</script>

<template>
  <div class="status-page">
    <div class="status-content" :class="{ 'status-card': showCard }">
      <i :class="icon" class="status-icon"></i>
      <h2>{{ title }}</h2>
      <p v-if="message">{{ message }}</p>

      <div v-if="features.length > 0" class="status-features">
        <h3 v-if="featuresLabel">{{ featuresLabel }}:</h3>
        <ul>
          <li v-for="(feature, idx) in features" :key="idx">{{ feature }}</li>
        </ul>
      </div>

      <slot />

      <Button
        v-if="actionLabel"
        :label="actionLabel"
        :icon="actionIcon"
        @click="emit('action')"
      />
    </div>
  </div>
</template>

<style scoped>
.status-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.status-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  max-width: 420px;
  text-align: center;
}

.status-card {
  padding: 2.5rem 3rem;
  border-radius: var(--app-card-radius);
  background: var(--app-card-bg);
  border: 1px solid var(--app-card-border);
}

.status-icon {
  font-size: 2.5rem;
  color: var(--app-text-muted);
}

.status-content h2 {
  margin: 0;
  color: var(--app-text-color);
  font-size: 1.2rem;
}

.status-content p {
  margin: 0;
  color: var(--app-text-muted);
  font-size: var(--app-font-size-base);
}

.status-features {
  text-align: left;
  width: 100%;
  margin-top: 0.5rem;
}

.status-features h3 {
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
  margin: 0 0 0.4rem 0;
}

.status-features ul {
  margin: 0;
  padding-left: 1.25rem;
}

.status-features li {
  font-size: var(--app-font-size-sm);
  color: var(--app-text-color);
  padding: 0.15rem 0;
}
</style>
