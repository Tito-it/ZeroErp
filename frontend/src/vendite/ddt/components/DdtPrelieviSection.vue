<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la sezione «Prelievi» del drawer della bolla (Lotto 3 R-2b,
//        piano-be-fe-magazzino-lotto-3 B1): da dove esce la merce, voce per
//        voce (la riga, o i componenti gestiti del kit). Involucro del BB
//        `SezioneMerceDocumento`: qui la lettura della bolla, i testi e la voce
//        (`DdtPrelievoVoce`); le voci le decide il DB
//        (`vendite.fn_ddt_merce_da_movimentare`).
//
// ⭐ Sta nel drawer e non dentro la riga: il motivo dell'emissione
//    («prelievi incompleti») riguarda la bolla intera, e dopo l'emissione
//    l'ubicazione di arrivo si completa senza riaprire una riga.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SezioneMerceDocumento from '../../_shared/merce/SezioneMerceDocumento.vue'
import { getPrelievi } from '../api/ddtApi'
import DdtPrelievoVoce from './DdtPrelievoVoce.vue'

const props = defineProps({
  ddtId: { type: Number, required: true },
  modificabile: { type: Boolean, default: false },
  arrivoModificabile: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])
const { t } = useI18n()

const sezione = ref(null)
const chiaveVoce = (v) => `${v.ddt_riga_id}-${v.ddt_riga_componente_id ?? 'r'}`

defineExpose({ carica: () => sezione.value?.carica() })
</script>

<template>
  <SezioneMerceDocumento
    ref="sezione"
    :leggi="() => getPrelievi(props.ddtId)"
    :titolo="t('vendite.ddt.prelievi.titolo')"
    :intro="t('vendite.ddt.prelievi.intro')"
    :senza-magazzino-testo="t('vendite.ddt.prelievi.senza_magazzino')"
    :chiave-voce="chiaveVoce"
    :modificabile="modificabile">
    <template #voce="{ voce, situazione, modificabile: voceModificabile }">
      <DdtPrelievoVoce
        :ddt-id="ddtId"
        :voce="voce"
        :testata="situazione"
        :modificabile="voceModificabile"
        :arrivo-modificabile="arrivoModificabile"
        @changed="emit('changed')" />
    </template>
  </SezioneMerceDocumento>
</template>
