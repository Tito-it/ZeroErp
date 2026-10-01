<script setup>
// Scopo: Titolo standard per drawer. Azione a sinistra (piccola verde),
// icona + entita' centrata (verde grande), badge "Sola lettura" a destra
// (auto-visibile quando il drawer e' in modalita' readonly via inject).
// Layout a 3 colonne: [azione] [icona + titolo centrato] [badge readonly].
// Usare nel #header slot di ogni Drawer.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ReadonlyBadge from './ReadonlyBadge.vue'

const props = defineProps({
  action: { type: String, default: '' },
  title: { type: String, required: true },
  icon: { type: String, default: '' },
  // Ci sono modifiche non salvate (`modificato` di useDrawerFormPreserve):
  // la scritta dell'azione («Modifica») diventa arancio, il colore
  // dell'attenzione, finche' c'e' qualcosa da salvare (Tid, 2026-09-26).
  // ⚠️ Un drawer senza `action` non avrebbe niente da colorare: al suo posto
  //    compare la scritta «Modifiche non salvate», o il segnale non si vede.
  modificato: { type: Boolean, default: false },
})

const { t } = useI18n()
const scritta = computed(() =>
  props.action || (props.modificato ? t('common.modifiche_non_salvate.indicatore') : ''),
)
</script>

<template>
  <div class="app-drawer-title">
    <span
      class="app-drawer-title-action"
      :class="{ 'app-drawer-title-action--modificato': modificato }"
      v-tooltip.bottom="modificato ? t('common.modifiche_non_salvate.indicatore') : null"
    >{{ scritta }}</span>
    <span class="app-drawer-title-entity">
      <i v-if="icon" :class="icon" class="app-drawer-title-icon" />
      {{ title }}
    </span>
    <span class="app-drawer-title-end">
      <ReadonlyBadge />
    </span>
  </div>
</template>

<style scoped>
.app-drawer-title {
  display: flex;
  align-items: baseline;
  flex: 1;
  gap: 0.5rem;
}
.app-drawer-title-action {
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--app-accent-color);
  white-space: nowrap;
  min-width: 4rem;
}
.app-drawer-title-action--modificato {
  color: var(--app-warning-color);
  font-weight: 700;
}
.app-drawer-title-entity {
  flex: 1;
  text-align: center;
  font-size: 1.35rem;
  font-weight: 600;
  color: var(--app-accent-color);
}
.app-drawer-title-icon {
  font-size: 1.1rem;
  margin-right: 0.4rem;
  vertical-align: baseline;
}
.app-drawer-title-end {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 4rem;
}
</style>
