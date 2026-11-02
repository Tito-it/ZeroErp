<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la sezione «Rientri» del drawer del reso (3-bis R-1b,
//        piano-be-fe-magazzino-lotto-3 B2): dove rientra la merce, voce per
//        voce (la riga, o i componenti del kit com'erano usciti). Involucro del
//        BB `SezioneMerceDocumento`: qui la lettura del reso, i testi e la voce
//        (`ResoRientroVoce`); le voci le decide il DB
//        (`vendite.fn_reso_merce_da_rientrare`).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SezioneMerceDocumento from '../../_shared/merce/SezioneMerceDocumento.vue'
import { getRientri } from '../api/resiApi'
import ResoRientroVoce from './ResoRientroVoce.vue'

const props = defineProps({
  resoId: { type: Number, required: true },
  modificabile: { type: Boolean, default: false },
})
const emit = defineEmits(['changed'])
const { t } = useI18n()

const sezione = ref(null)
const chiaveVoce = (v) => `${v.resi_riga_id}-${v.ddt_riga_componente_id ?? 'r'}`

defineExpose({ carica: () => sezione.value?.carica() })
</script>

<template>
  <SezioneMerceDocumento
    ref="sezione"
    :leggi="() => getRientri(props.resoId)"
    :titolo="t('vendite.resi.rientri.titolo')"
    :intro="t('vendite.resi.rientri.intro')"
    :senza-magazzino-testo="t('vendite.resi.rientri.senza_magazzino')"
    :chiave-voce="chiaveVoce"
    :modificabile="modificabile">
    <template #voce="{ voce, situazione, modificabile: voceModificabile }">
      <ResoRientroVoce
        :reso-id="resoId"
        :voce="voce"
        :testata="situazione"
        :modificabile="voceModificabile"
        @changed="emit('changed')" />
    </template>
  </SezioneMerceDocumento>
</template>
