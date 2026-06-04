<script setup>
// Scopo: building block standard per il Tag di stato "Attivo / Non attivo".
//        Estratto 2026-06-05 (regola del 2): il ternario
//          <Tag :value="x.attivo ? active : inactive"
//               :severity="x.attivo ? 'success' : 'warn'" />
//        era ripetuto ~24 volte in liste e drawer.
//
// Il componente riceve il BOOLEANO gia' risolto (`active`), NON il path del
// campo (varia: attivo / emittente_attivo / is_active / row.attivo) per non
// reintrodurre coupling. Le label di default sono common.active/common.inactive;
// chi usa una famiglia i18n diversa (common.yes/no, amm.email_attivo,
// indirizzi.attivo, config_panel.attivo, search.status_active, ...) passa
// `activeLabel`/`inactiveLabel` gia' tradotte. `inactiveSeverity` per i casi
// che divergono dal default 'warn' (es. 'danger', 'secondary').
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

const props = defineProps({
  active: { type: Boolean, default: false },
  activeLabel: { type: String, default: null },
  inactiveLabel: { type: String, default: null },
  inactiveSeverity: { type: String, default: 'warn' },
})

const { t } = useI18n()

const label = computed(() =>
  props.active
    ? (props.activeLabel ?? t('common.active'))
    : (props.inactiveLabel ?? t('common.inactive')),
)
const severity = computed(() => (props.active ? 'success' : props.inactiveSeverity))
</script>

<template>
  <Tag :value="label" :severity="severity" />
</template>
