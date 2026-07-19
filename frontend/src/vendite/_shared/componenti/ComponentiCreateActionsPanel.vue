<script setup>
// Scopo: Building block "azioni componenti BoM in CREATE" per i form riga
//        di preventivi/contratti/offerte (mirror dei pattern condivisi
//        `ComponentiDialog` / `ComponentiPanel`). Estratto applicando la
//        regola del 2 (memoria `feedback_regola_del_2_estrai_bb`): 3
//        occorrenze quasi identiche in `PreventiviRigaForm`,
//        `ContrattoRigheDrawer`, `OffertaEccezioniDrawer`.
//
//        Contenuto:
//         - header sezione "Componenti..." (i18n key parametrizzata via
//           `sectionTitleKey`: i 3 domini usano label diverse —
//           preventivi: `vendite.preventivi.componenti_section_title`;
//           contratti/offerte: `vendite.componenti.panel.section_title`);
//         - Message info con hint "Definisci i prezzi dei componenti...";
//         - Bottone outlined "Modifica componenti" con icona BoM;
//         - summary live "{n} componenti pronti..." quando l'utente ha
//           gia' confermato il Dialog almeno una volta.
//
//        Il caller resta responsabile di:
//         - calcolare `disabled` (le regole differiscono per dominio:
//           contratti hanno il check qta vs fonte FISSA, offerte non lo
//           hanno per via di CONSUMO/LETTURE, ecc.);
//         - gestire lo stato di `componentiDialogVisible` (riapre via
//           `@apri-dialog`).
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { MANAGE_ICONS } from '../../../core/constants'

const props = defineProps({
  // Disabilita il bottone "Modifica componenti": la logica e' del caller.
  disabled: { type: Boolean, default: false },
  // Payload restituito dal `ComponentiDialog` alla conferma — null se
  // l'operatore non ha ancora aperto il Dialog o ha annullato.
  componentiPayload: { type: Object, default: null },
  // i18n key del titolo sezione (i 3 domini hanno label diverse).
  sectionTitleKey: {
    type: String,
    default: 'vendite.componenti.panel.section_title',
  },
})

defineEmits(['apri-dialog'])

const { t } = useI18n()
</script>

<template>
  <div class="app-drawer-section">
    <h4>{{ t(sectionTitleKey) }}</h4>
  </div>
  <div class="componenti-create-actions">
    <Message severity="info" :closable="false" size="small">
      {{ t('vendite.componenti.panel.create_hint') }}
    </Message>
    <Button
      :label="t('vendite.componenti.panel.modifica_componenti')"
      :icon="MANAGE_ICONS.BOM"
      outlined
      :disabled="props.disabled"
      @click="$emit('apri-dialog')"
    />
    <small
      v-if="props.componentiPayload?.summary"
      class="componenti-create-actions__summary"
    >
      {{ t('vendite.componenti.panel.summary_create', {
        n: props.componentiPayload.summary.n,
      }) }}
    </small>
  </div>
</template>

<style scoped>
.componenti-create-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.componenti-create-actions__summary {
  color: var(--app-text-muted);
}
</style>
