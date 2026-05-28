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
//        Qui passa `defaultExpanded=true`: in modalita' dialog dedicato
//        ha senso mostrare subito principale + allegati senza dover
//        espandere riga per riga (UX picker).
import { useI18n } from 'vue-i18n'
import AppDialog from '../../core/components/AppDialog.vue'
import DocumentiGeneratiSorgenteList from './DocumentiGeneratiSorgenteList.vue'

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
  <AppDialog
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    :header="title || t('documenti.lista.title')"
    width="xl"
    close-only
    dismissable-mask
  >
    <DocumentiGeneratiSorgenteList
      v-if="visible && sorgenteId != null"
      :sorgente-code="sorgenteCode"
      :sorgente-id="sorgenteId"
      :allow-allegati="allowAllegati"
      default-expanded
    />
  </AppDialog>
</template>
