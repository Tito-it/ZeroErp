<script setup>
// Scopo: Thin wrapper DDT su `ComponentiPanel.vue` (BB Fase H). Chiude le API
//        specifiche DDT + emit `TAB_ENTITIES.DDT`. Il namespace i18n e' quello
//        shared `vendite.componenti.panel.*` (single source of truth del building
//        block, coerente con `ComponentiDialog`). In EDIT (readonly=false)
//        consente l'edit inline del prezzo per componente (PATCH).

import ComponentiPanel from '../../_shared/componenti/ComponentiPanel.vue'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
} from '../api/ddtApi'

const props = defineProps({
  ddtId: { type: Number, required: true },
  rigaId: { type: Number, required: true },
  readonly: { type: Boolean, default: true },
})

defineEmits(['changed'])
</script>

<template>
  <ComponentiPanel
    :documento-id="props.ddtId"
    :riga-id="props.rigaId"
    :readonly="props.readonly"
    :api-list="listRigaComponenti"
    :api-update="updateRigaComponente"
    :api-delete="deleteRigaComponente"
    :tab-entity="TAB_ENTITIES.DDT"
    @changed="$emit('changed')"
  />
</template>
