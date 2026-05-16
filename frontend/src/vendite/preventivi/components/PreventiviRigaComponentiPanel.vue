<script setup>
// Scopo: Thin wrapper preventivi su `ComponentiPanel.vue` (BB Fase H
//        2026-05-14). Chiude le API specifiche preventivi + emit
//        `TAB_ENTITIES.PREVENTIVO`. Il namespace i18n e' quello shared
//        `vendite.componenti.panel.*` (single source of truth dopo
//        l'estrazione del building block, coerente con `ComponentiDialog`
//        in `vendite/_shared/componenti/`).
//
//        Per nuovi consumer (contratti/ordini/ddt) usare direttamente
//        `ComponentiPanel` passando le proprie callback API.

import ComponentiPanel from '../../_shared/componenti/ComponentiPanel.vue'
import { TAB_ENTITIES } from '../../../core/constants'
import {
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
} from '../api/preventiviApi'

const props = defineProps({
  preventivoId: { type: Number, required: true },
  rigaId: { type: Number, required: true },
  readonly: { type: Boolean, default: true },
})

defineEmits(['changed'])
</script>

<template>
  <ComponentiPanel
    :documento-id="props.preventivoId"
    :riga-id="props.rigaId"
    :readonly="props.readonly"
    :api-list="listRigaComponenti"
    :api-update="updateRigaComponente"
    :api-delete="deleteRigaComponente"
    :tab-entity="TAB_ENTITIES.PREVENTIVO"
    @changed="$emit('changed')"
  />
</template>
