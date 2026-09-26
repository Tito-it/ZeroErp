<script setup>
// Scopo: Componente generico che visualizza la catena di fallback di un parametro.
// Mostra il valore risolto e da quale livello proviene (cascata BE post brief
// 2026-05-19: user > categoria_cliente > group > emittente > default).
// Il livello categoria_cliente compare nella catena solo se la chiamata
// /settings/ ha passato `categoria_cliente_id` (o `billing_account_id`).
// Riutilizzabile ovunque serva mostrare la provenienza di un valore parametro.
//
// Props:
//   parameter - Oggetto parametro da fn_list_parameters_for_user (con tutti i livelli)
//   compact   - Se true, mostra solo il valore risolto con badge livello (default: false)
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { resolveParameterLevel, parameterLevelSeverity } from '../utils/parameterLevel'

const { t } = useI18n()

const props = defineProps({
  parameter: { type: Object, required: true },
  compact: { type: Boolean, default: false }
})

const resolvedLevel = computed(() => resolveParameterLevel(props.parameter))
const levelLabel = computed(() => t(`config.impostazioni.level_${resolvedLevel.value}`))
const levelSeverity = computed(() => parameterLevelSeverity(resolvedLevel.value))

// Scopo: Costruisce la catena di valori per visualizzazione completa.
//        Il livello `categoria_cliente` si inserisce fra `group` e `user`
//        (cascata BE: user > categoria_cliente > group > emittente > default).
//        Lo mostriamo SOLO se il BE ha valorizzato categoria_cliente_value:
//        per le chiamate /settings/ senza categoria, la colonna resta NULL
//        e la riga sparisce dal display (evita rumore visivo).
const levels = computed(() => {
  const p = props.parameter
  const rows = [
    { key: 'default', value: p.default_value, label: t('config.impostazioni.level_default') },
    { key: 'emittente', value: p.emittente_value, label: t('config.impostazioni.level_emittente') },
    { key: 'group', value: p.group_value, label: t('config.impostazioni.level_group') },
  ]
  if (p.categoria_cliente_value != null || p.categoria_cliente_override_id != null) {
    rows.push({
      key: 'categoria_cliente',
      value: p.categoria_cliente_value,
      label: t('config.impostazioni.level_categoria_cliente'),
    })
  }
  rows.push({ key: 'user', value: p.user_value, label: t('config.impostazioni.level_user') })
  return rows
})
</script>

<template>
  <span v-if="compact" class="parameter-fallback-compact">
    <span>{{ parameter.resolved_value ?? '—' }}</span>
    <Tag :value="levelLabel" :severity="levelSeverity" class="parameter-level-badge" />
  </span>
  <div v-else class="parameter-fallback-chain">
    <div
      v-for="level in levels"
      :key="level.key"
      class="parameter-level-row"
      :class="{ 'parameter-level-active': resolvedLevel === level.key }"
    >
      <span class="parameter-level-label">{{ level.label }}</span>
      <span class="app-mono" :class="{ 'parameter-level-empty': level.value == null }">
        {{ level.value ?? '—' }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.parameter-fallback-compact {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.parameter-level-badge {
  font-size: 0.7rem;
}
.parameter-fallback-chain {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.parameter-level-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}
.parameter-level-active {
  background: var(--app-highlight-bg);
  font-weight: 600;
}
.parameter-level-label {
  min-width: 80px;
  color: var(--app-text-muted);
  font-size: 0.8rem;
}
.parameter-level-empty {
  color: var(--app-text-muted);
  font-style: italic;
}
</style>
