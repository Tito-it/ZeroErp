<script setup>
// Scopo: Banner riusabile per mostrare soggetto selezionato/associato.
// Usato in: ClienteDrawer, FornitoreDrawer, EmittenteFiscaleDrawer,
// PraticaDrawer (sempre via SoggettoResolver o detail store).
//
// Etichetta unificata "Id. fiscale" (i18n common.id_fiscale): l'identificativo
// fiscale puo' essere CF o P.IVA a seconda del soggetto, quindi una label
// neutra coerente con quella delle liste (col_id_fiscale). Il caller passa
// gia' il valore corretto (CF || P.IVA), il banner non interpreta.
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'

defineProps({
  ragioneSociale: { type: String, default: '' },
  idFiscale: { type: String, default: null }
})

const { t } = useI18n()
</script>

<template>
  <Message severity="success" :closable="false">
    <div>
      <i class="pi pi-user" />
      <strong>{{ ragioneSociale }}</strong>&nbsp;
      <span v-if="idFiscale" class="app-text-muted ml-05">
        {{ t('common.id_fiscale') }}: {{ idFiscale }}
      </span>
    </div>
  </Message>
</template>
