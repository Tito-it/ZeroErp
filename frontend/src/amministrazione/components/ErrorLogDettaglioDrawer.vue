<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer di dettaglio di una riga di `dbops.error_log` (pezzo E
//        dell'osservabilita'): testata (quando, area, funzione, codice e
//        classe), la frase, la causa e la soluzione A CATALOGO, e il `context`
//        — gli appunti del tecnico — reso com'e' dal BB `JsonBlocco`.
//        Sola lettura, nessuna fetch: la riga e' quella della pagina, la
//        passa il caller. Le azioni (giornale della transazione, copia del
//        tx_id) restano nel kebab della lista.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import FormFooter from '../../core/components/FormFooter.vue'
import JsonBlocco from '../../core/components/JsonBlocco.vue'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { displayTimestamp } from '../../core/utils/date'
import { classeErroreSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH } from '../../core/constants'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  riga: { type: Object, default: null },
})

// Contenuto deferito a fine animazione (`feedback_content_ready_after_show`).
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible'])
const onClose = useDrawerClose(emit)

const titolo = computed(() =>
  t('amministrazione.error_log.dettaglio_titolo', { codice: props.riga?.codice ?? '' }),
)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :header="titolo"
    @update:visible="(v) => emit('update:visible', v)"
    @after-show="onAfterShow"
  >
    <div v-if="contentReady && riga" class="app-drawer-content">
      <div class="app-error-log-testata">
        <span class="app-mono app-error-log-funzione">{{ riga.function_name }}</span>
        <Tag v-if="riga.classe" :value="riga.classe" :severity="classeErroreSeverity(riga.classe)" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.error_log.col_quando') }}</label>
          <span>{{ riga.occurred_at ? displayTimestamp(riga.occurred_at) : '—' }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.error_log.col_area') }}</label>
          <span>{{ riga.area }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.error_log.col_codice') }}</label>
          <span class="app-mono">{{ riga.codice }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.error_log.col_tx_id') }}</label>
          <span class="app-mono">{{ riga.tx_id ?? '—' }}</span>
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('amministrazione.error_log.col_messaggio') }}</label>
        <span>{{ riga.messaggio }}</span>
      </div>
      <div v-if="riga.causa" class="form-field">
        <label>{{ t('amministrazione.error_log.col_causa') }}</label>
        <span>{{ riga.causa }}</span>
      </div>
      <div v-if="riga.soluzione" class="form-field">
        <label>{{ t('amministrazione.error_log.col_soluzione') }}</label>
        <span>{{ riga.soluzione }}</span>
      </div>

      <!-- Gli appunti del tecnico, com'erano: niente pulizia, niente
           riscrittura (vincolo del Passo A). -->
      <div class="form-field">
        <label>{{ t('amministrazione.error_log.dettaglio_context') }}</label>
        <JsonBlocco v-if="riga.context" :value="riga.context" />
        <span v-else>{{ t('amministrazione.error_log.dettaglio_context_vuoto') }}</span>
      </div>

      <FormFooter close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>

<style scoped>
.app-error-log-testata {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.app-error-log-funzione {
  font-weight: 600;
}
</style>
