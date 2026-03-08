<script setup>
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import Button from 'primevue/button'

const { t } = useI18n()
const route = useRoute()

const breadcrumb = computed(() => {
  const meta = route.meta
  const items = []

  if (meta.domain) {
    items.push(t(`nav.${meta.domain}`))
  }
  if (meta.section) {
    items.push(meta.section)
  }

  return items
})

const showNewButton = computed(() => !!route.meta.allowNew)
</script>

<template>
  <header class="app-topbar">
    <div class="topbar-breadcrumb">
      <span v-for="(item, index) in breadcrumb" :key="index">
        <span v-if="index > 0" class="breadcrumb-separator">/</span>
        <span :class="{ 'breadcrumb-last': index === breadcrumb.length - 1 }">{{ item }}</span>
      </span>
    </div>

    <div class="topbar-actions">
      <Button
        v-if="showNewButton"
        :label="t('common.new')"
        icon="pi pi-plus"
        size="small"
      />
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--app-topbar-height);
  min-height: var(--app-topbar-height);
  padding: 0 var(--app-content-padding);
  background: var(--app-topbar-bg);
  border-bottom: 1px solid var(--app-topbar-border);
}

.topbar-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--app-font-size-base);
  color: var(--app-topbar-breadcrumb-color);
}

.breadcrumb-separator {
  color: var(--app-topbar-breadcrumb-color);
}

.breadcrumb-last {
  color: var(--app-topbar-breadcrumb-active-color);
  font-weight: 500;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
