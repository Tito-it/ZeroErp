<script setup>
// Scopo: Wrapper Dialog riusabile attorno a `DocumentiGeneratiSorgenteList`.
//        Mostra in popup la lista dei PDF generati per una sorgente +
//        sorgenteId, con azione di download per riga (la action e'
//        gia' interna alla lista). Usato dalla lista preventivi
//        (azione di riga "PDF") e da chi serva un picker rapido senza
//        aprire il drawer del preventivo.
//
//        Il building block sottostante e' `DocumentiGeneratiSorgenteList`,
//        che fa fetch automatico al cambio props (`autoFetch=true`).
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import DocumentiGeneratiSorgenteList from './DocumentiGeneratiSorgenteList.vue'
import { DRAWER_WIDTH } from '../../core/constants'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], required: true },
  // Titolo personalizzabile dal caller (default: "Documenti generati").
  // Tipico uso: "Preventivo P-0001 — Documenti".
  title: { type: String, default: '' },
  // Abilita l'azione di riga "Aggiungi allegati" sui documenti generati
  // (es. offerta in EMESSA). Default off: la lista resta sola lettura.
  allowAllegati: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible'])
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    modal
    :header="title || t('documenti.lista.title')"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :closable="true"
    dismissable-mask
  >
    <DocumentiGeneratiSorgenteList
      v-if="visible && sorgenteId != null"
      :sorgente-code="sorgenteCode"
      :sorgente-id="sorgenteId"
      :allow-allegati="allowAllegati"
    />
  </Dialog>
</template>
