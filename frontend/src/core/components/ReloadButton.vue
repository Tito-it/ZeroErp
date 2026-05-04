<script setup>
// Scopo: pulsante refresh standard per tutte le toolbar lista.
// Stessa estetica di NewButton (classe app-page-action).
// Auto-hide: si nasconde solo quando l'elenco e' BLOCCATO a livello oggetto;
// resta visibile in LETTURA (serve per consultare dati aggiornati).
import { useInjectBlocked } from '../composables/useReadonlyMode'
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../constants'
import Button from 'primevue/button'

defineEmits(['click'])
const { t } = useI18n()
const isBlocked = useInjectBlocked()
</script>

<template>
  <Button
    v-if="!isBlocked"
    :icon="MANAGE_ICONS.RELOAD"
    text
    class="app-reload-btn"
    v-tooltip.bottom="t('common.reload_list')"
    @click="$emit('click')"
  />
</template>
