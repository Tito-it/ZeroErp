<script setup>
// Scopo: Badge di stato della configurazione di una lista personalizzabile.
//        Mostra il Tag "Configurazione temporanea" (warn) SOLO quando ci sono
//        modifiche di personalizzazione colonne NON salvate (dirty). Nessun badge
//        nello stato di riposo: il precedente Tag "Configurazione salvata"
//        (success) era permanente e non azionabile (rumore) ed e' stato rimosso.
//        Centralizza il blocco prima duplicato in 7 SearchTable.
import Tag from 'primevue/tag'
import { useI18n } from 'vue-i18n'

defineProps({
  dirty: { type: Boolean, default: false },
})

const { t } = useI18n()
</script>

<template>
  <Tag
    v-if="dirty"
    :value="t('lista_config.stato_temporanea')"
    severity="warn"
    v-tooltip.bottom="t('lista_config.stato_temporanea_tooltip')"
  />
</template>
