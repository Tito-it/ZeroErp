<script setup>
// Scopo: Dialog «Situazione merce» — wrapper AppDialog attorno a
// SituazioneMerceContenuto, aperta dai chip di `SituazioneMerceBar`.
// Gemella di `LineagePassaggiDialog`, stessa forma e stesse ragioni.
//
// Il payload arriva dalla barra (fetch unica di `useSituazioneMerce`): la
// dialog NON fetcha e si apre istantanea — ed e' anche cio' che garantisce che
// il numero del chip e le righe del dettaglio non possano divergere.
//
// Consultiva: footer di sola chiusura. Nessun verbo, per decisione §6 del brief
// pannello — «i verbi vivono dove gia' stanno» (code resi, dashboard). Questa
// e' una LETTURA, e mescolarci un'azione la trasformerebbe in una terza sede
// del processo.
//
// `readonly` = quello PURO del chiamante, per la stessa ragione di
// DdtResoDialog: la dialog e' lanciata da un drawer post-DRAFT che vive in
// `app-readonly`, e senza l'override erediterebbe readonly=true.
import AppDialog from '../../../core/components/AppDialog.vue'
import SituazioneMerceContenuto from './SituazioneMerceContenuto.vue'

defineProps({
  visible: { type: Boolean, required: true },
  sezioni: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})

// `apri-coda-accrediti`: il pannello non naviga da se'. La dialog va CHIUSA
// prima di cambiare rotta, o si resta con un overlay sopra la coda — e chi sa
// chiuderla e' chi l'ha aperta (la barra).
const emit = defineEmits(['update:visible', 'apri-coda-accrediti'])
</script>

<template>
  <AppDialog
    :visible="visible"
    width="xl"
    :header="$t('vendite.situazione_merce.titolo')"
    :readonly="readonly"
    close-only
    @update:visible="emit('update:visible', $event)"
    @cancel="emit('update:visible', false)"
  >
    <SituazioneMerceContenuto
      :sezioni="sezioni"
      :loading="loading"
      :loaded="loaded"
      @apri-coda-accrediti="emit('apri-coda-accrediti')"
    />
  </AppDialog>
</template>
