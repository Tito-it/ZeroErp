<script setup>
import { useI18n } from 'vue-i18n'
import { DOMAINS } from '../navigation'

const { t } = useI18n()
</script>

<template>
  <div class="home-view">
    <h2>{{ t('home.welcome') }}</h2>

    <div class="domain-grid">
      <router-link
        v-for="domain in DOMAINS"
        :key="domain.key"
        :to="domain.to"
        class="domain-card"
      >
        <i :class="domain.icon"></i>
        <span>{{ t(`nav.${domain.key}`) }}</span>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  max-width: 900px;
}

.home-view h2 {
  margin-bottom: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.domain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.domain-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  border-radius: var(--app-card-radius);
  background: var(--app-card-bg);
  border: 1px solid var(--app-card-border);
  color: var(--p-text-color);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: border-color var(--app-transition-fast), background var(--app-transition-fast);
}

.domain-card:hover {
  border-color: var(--app-card-hover-border);
  background: var(--app-card-hover-bg);
}

.domain-card i {
  font-size: 1.75rem;
  color: var(--app-card-icon-color);
}
</style>
