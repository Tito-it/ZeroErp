<!--
  Scopo: Building block "contesto pratica" — header standard dei drawer di
         ESECUZIONE FLUSSI (FlussoDrawer e futuri drawer dedicati per flusso,
         es. RICHIESTA_CLIENTE della pratica PREVENTIVI).

         Mostra sempre lo stesso set minimo di informazioni, identico su ogni
         drawer di flusso (principio di omogeneita' UI):
           - numero pratica (Tag; fallback "#id" se il codice manca)
           - soggetto (ragione_sociale_completa)
           - data di apertura della pratica
           - id fiscale univoco (CF/P.IVA)

         Wrapper di DrawerContextHeader (regola del 2): i singoli drawer di
         flusso non ricostruiscono items/label/formatting, passano solo i
         campi del payload BE (flusso.pratica_* da get_flusso/list_flussi,
         oppure i campi del dettaglio pratica).

         Uso (da FlussoDrawer, payload flusso):
           <PraticaContextHeader
             :codice="flusso.pratica_codice"
             :pratica-id="flusso.pratica_id"
             :soggetto="flusso.pratica_soggetto_display"
             :data-apertura="flusso.pratica_data_apertura"
             :id-fiscale="flusso.pratica_soggetto_id_fiscale"
           >
             <template #status>
               <Tag :value="stato" :severity="statoFlussoSeverity(stato)" />
             </template>
           </PraticaContextHeader>

         Slot:
           - #status: zona destra della primary row (Tag stato flusso/pratica)

         Props: tutti display-only; null/'' rendono il fallback '—' del BB base.
-->
<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DrawerContextHeader from '../../core/components/DrawerContextHeader.vue'
import { displayDate } from '../../core/utils/date'

const { t } = useI18n()

const props = defineProps({
  codice: { type: String, default: null },
  praticaId: { type: [Number, String], default: null },
  soggetto: { type: String, default: null },
  dataApertura: { type: String, default: null },
  idFiscale: { type: String, default: null },
})

// Tag identificativo: codice pratica, fallback "#id" se non ancora codificata.
const tagValue = computed(
  () => props.codice || (props.praticaId != null ? `#${props.praticaId}` : null)
)

// items[0] = primary row (soggetto), items[1..] = secondary row 2 colonne.
const items = computed(() => [
  { label: t('pratiche.col_soggetto'), value: props.soggetto },
  {
    label: t('pratiche.col_data_apertura'),
    value: props.dataApertura ? displayDate(props.dataApertura) : null,
  },
  { label: t('common.id_fiscale'), value: props.idFiscale },
])
</script>

<template>
  <DrawerContextHeader :tag-value="tagValue" :items="items">
    <template v-if="$slots.status" #status>
      <slot name="status" />
    </template>
  </DrawerContextHeader>
</template>
