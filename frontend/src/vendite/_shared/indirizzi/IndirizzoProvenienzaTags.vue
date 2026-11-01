<script setup>
// Scopo: Tag di provenienza di una riga indirizzo documento, condivisi tra
//        sezione inline e drawer di gestione (regola del 2 — erano copiati
//        1:1). Semantica (allineata al BE upsert_indirizzo_documento):
//        - origine_indirizzo_id valorizzato -> aggancio anagrafico: nessun
//          tag base; se il TIPO anagrafico differisce dallo slot, tag
//          "da <tipo>" (warn);
//        - solo origine_soggetto_ruolo_id -> "da soggetto" (layer soggetto,
//          nessuna riga agganciabile in anagrafiche.indirizzi);
//        - nessuna origine -> "una tantum" (digitato, warn).

import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

defineProps({
  // Riga di `indirizzi[]` del documento (shape mixin BE).
  row: { type: Object, required: true },
})

const { t } = useI18n()
</script>

<template>
  <Tag
    v-if="!row.origine_indirizzo_id && row.origine_soggetto_ruolo_id"
    v-tooltip.bottom="t('vendite.indirizzi.tt_da_soggetto')"
    :value="t('vendite.indirizzi.da_soggetto')"
    severity="secondary" />
  <Tag
    v-if="!row.origine_indirizzo_id && !row.origine_soggetto_ruolo_id"
    v-tooltip.bottom="t('vendite.indirizzi.tt_una_tantum')"
    :value="t('vendite.indirizzi.una_tantum')"
    severity="warn" />
  <Tag
    v-if="row.origine_tipo_indirizzo_codice_interno
      && row.origine_tipo_indirizzo_codice_interno !== row.tipo_indirizzo_codice_interno"
    v-tooltip.bottom="t('vendite.indirizzi.tt_da_tipo', { tipo: row.origine_tipo_indirizzo_descrizione })"
    :value="t('vendite.indirizzi.da_tipo', { tipo: row.origine_tipo_indirizzo_descrizione })"
    severity="warn" />
</template>
