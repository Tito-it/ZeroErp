<script setup>
// Scopo: Thin wrapper ordini su `ComponentiPanel.vue` (BB Fase H 2026-05-14).
//        Chiude le API specifiche ordini + emit `TAB_ENTITIES.ORDINE`. Il
//        namespace i18n e' quello shared `vendite.componenti.panel.*` (single
//        source of truth del building block, coerente con `ComponentiDialog`).
//        In EDIT (readonly=false) consente l'edit inline del prezzo per
//        componente (PATCH) — unico punto di pricing dei compositi sull'ordine,
//        dato che il create BE non accetta override pre-save.

import ComponentiPanel from '../../_shared/componenti/ComponentiPanel.vue'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
} from '../api/ordiniApi'

const props = defineProps({
  ordineId: { type: Number, required: true },
  rigaId: { type: Number, required: true },
  readonly: { type: Boolean, default: true },
})

defineEmits(['changed'])
</script>

<template>
  <ComponentiPanel
    :documento-id="props.ordineId"
    :riga-id="props.rigaId"
    :readonly="props.readonly"
    :api-list="listRigaComponenti"
    :api-update="updateRigaComponente"
    :api-delete="deleteRigaComponente"
    :tab-entity="TAB_ENTITIES.ORDINE"
    @changed="$emit('changed')"
  />
</template>
