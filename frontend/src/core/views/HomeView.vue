<script setup>
// Scopo: dashboard home — benvenuto, sessioni attive, 4 card placeholder dashboard
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import SessioniAttivePanel from '../components/SessioniAttivePanel.vue'

const { t } = useI18n()
const auth = useAuthStore()

// 4 card placeholder per futura dashboard KPI
const dashCards = [
  { key: 'dash-1', labelKey: 'home.dash_1', icon: 'pi pi-wrench' },
  { key: 'dash-2', labelKey: 'home.dash_2', icon: 'pi pi-wrench' },
  { key: 'dash-3', labelKey: 'home.dash_3', icon: 'pi pi-wrench' },
  { key: 'dash-4', labelKey: 'home.dash_4', icon: 'pi pi-wrench' }
]
</script>

<template>
  <div class="home-view">
    <h2>{{ t('home.welcome_user', { name: auth.displayName || t('home.welcome_fallback') }) }}</h2>

    <SessioniAttivePanel />

    <div class="dashboard-grid">
      <div
        v-for="card in dashCards"
        :key="card.key"
        class="dash-card"
      >
        <i :class="card.icon"></i>
        <span>{{ t(card.labelKey) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  max-width: 900px;
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100%;
}

.home-view h2 {
  margin-bottom: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  width: 100%;
}

.dash-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  border-radius: var(--app-card-radius);
  background: var(--app-card-bg);
  border: 1px solid var(--app-card-border);
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  font-weight: 500;
}

.dash-card i {
  font-size: 1.75rem;
  color: var(--p-text-muted-color);
}

/* Tablet landscape */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }
}

/* Tablet portrait / mobile */
@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dash-card {
    padding: 1.25rem 0.75rem;
  }
}
</style>
