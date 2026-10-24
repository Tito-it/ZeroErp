<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la finestra con cui si LIBERA un blocco manuale (Lotto 3 R-5, M-3:
//        «si libera esplicitamente, non si consuma da se'»; piano-be-fe-
//        magazzino-lotto-3 C1). Una nota facoltativa: chi e quando li scrive
//        il verbo (`magazzino.fn_libera_blocco`), il perche' lo dice chi libera.
// ⚠️ Solo i blocchi MANUALI (senza sorgente): gli attesi di un documento si
//    chiudono col loro documento. Il chiamante offre il gesto solo su quelli.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'

import AppDialog from '../../core/components/AppDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'
import { formatQuantita } from '../../core/utils/format'
import { liberaBlocco } from '../api/magazzino'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Il blocco del popover: id, qta (negativa: un'uscita), soggetto, nota.
  blocco: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'liberato'])
const { t } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const nota = ref('')
watch(() => props.visible, (aperto) => { if (aperto) nota.value = '' })

async function onSave() {
  const esito = await execute(
    () => liberaBlocco(props.blocco.id, nota.value.trim() || null),
    { successMessage: t('magazzino.blocchi.liberato') },
  )
  if (esito === null) return
  emit('liberato', props.blocco.id)
  emit('update:visible', false)
}

// D-14: uscire con una nota scritta chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ nota: nota.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('magazzino.blocchi.titolo_libera')"
    width="sm"
    :loading="loading"
    :save-label="t('magazzino.blocchi.libera_conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
    @cancel="emit('update:visible', false)"
  >
    <div class="form-grid">
      <p v-if="blocco" style="margin: 0;">
        {{ t('magazzino.blocchi.libera_domanda', { qta: formatQuantita(Math.abs(Number(blocco.qta))) }) }}
        <span v-if="blocco.soggetto_ragione_sociale || blocco.nota" class="app-text-muted">
          — {{ blocco.soggetto_ragione_sociale || blocco.nota }}
        </span>
      </p>
      <div class="form-field">
        <label>{{ t('magazzino.blocchi.campo_nota_liberazione') }}</label>
        <InputText v-model="nota" maxlength="500" :invalid="campiErrati.includes('nota')" />
      </div>
    </div>
  </AppDialog>
</template>
