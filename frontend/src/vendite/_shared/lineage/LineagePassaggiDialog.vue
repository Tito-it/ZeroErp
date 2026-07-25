<script setup>
// Scopo: Dialog "Passaggi" (genealogia/lineage) del documento — wrapper
// AppDialog attorno a LineagePassaggiContenuto, aperta dai chip di
// `DocumentoCollegamentiBar`.
//
// Sostituisce (2026-07-25, decisione Tid) il pannello sempre montato in coda a
// ogni drawer documento: la genealogia si consulta quando serve, e i chip della
// barra dicono gia' a colpo d'occhio SE e COSA c'e' da consultare. Il payload
// arriva dalla barra (fetch unica del composable useDocumentoPassaggi): la
// dialog non fetcha e si apre istantanea.
//
// Consultiva: footer di sola chiusura. `readonly` = quello PURO del chiamante,
// per lo stesso motivo di DdtResoDialog — vedi il commento sul provide in
// DocumentoCollegamentiBar.
import AppDialog from '../../../core/components/AppDialog.vue'
import LineagePassaggiContenuto from './LineagePassaggiContenuto.vue'

defineProps({
  visible: { type: Boolean, required: true },
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'apri-pratica', 'apri-documento'])
</script>

<template>
  <AppDialog
    :visible="visible"
    width="lg"
    :header="$t('vendite.lineage.titolo')"
    :readonly="readonly"
    close-only
    @update:visible="emit('update:visible', $event)"
    @cancel="emit('update:visible', false)"
  >
    <LineagePassaggiContenuto
      :data="data"
      :loading="loading"
      :loaded="loaded"
      @apri-pratica="emit('apri-pratica')"
      @apri-documento="(row) => emit('apri-documento', row)"
    />
  </AppDialog>
</template>
