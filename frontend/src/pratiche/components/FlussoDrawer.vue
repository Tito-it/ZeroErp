<script setup>
// Scopo: Drawer esecuzione flusso — avvio, completamento con esito, sospensione.
// Riutilizzabile: riceve flusso via props, emette eventi per refresh.
// Il contenuto e' dinamico: mostra azioni in base allo stato corrente del flusso.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { cambiaStatoFlusso } from '../api/pratiche-api'
import { DRAWER_WIDTH, STATO_FLUSSO } from '../../core/constants'
import { statoFlussoSeverity, esitoFlussoSeverity } from '../../core/utils/severity'
import { displayTimestamp } from '../../core/utils/date'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  flusso: { type: Object, default: null },
  praticaId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

const esito = ref(null)
const noteEsito = ref('')

const esitiOptions = computed(() => [
  { value: 'POSITIVO', label: t('pratiche.esito_positivo') },
  { value: 'NEGATIVO', label: t('pratiche.esito_negativo') },
  { value: 'PARZIALE', label: t('pratiche.esito_parziale') },
  { value: 'NON_APPLICABILE', label: t('pratiche.esito_non_applicabile') },
])

const stato = computed(() => props.flusso?.stato_codice_interno || '')

watch(() => props.visible, (val) => {
  if (val) { esito.value = null; noteEsito.value = '' }
})

// Scopo: Avvia il flusso (DA_ESEGUIRE → IN_CORSO).
async function onAvvia() {
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, { nuovo_stato: 'IN_CORSO' }),
    { successMessage: t('pratiche.flusso_avviato') }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

// Scopo: Completa il flusso con esito obbligatorio.
async function onCompleta() {
  if (!esito.value) return
  const result = await execute(
    () => cambiaStatoFlusso(props.praticaId, props.flusso.id, {
      nuovo_stato: 'COMPLETATO',
      esito: esito.value,
      note_esito: noteEsito.value || null,
    }),
    { successMessage: t('pratiche.flusso_completato') }
  )
  if (result !== null) { emit('saved'); emit('update:visible', false) }
}

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="t('pratiche.flusso_esecuzione')"
        :title="flusso?.template_flusso_codice || t('pratiche.flusso_generico')"
        icon="pi pi-sitemap"
      />
    </template>

    <div v-if="flusso" class="app-drawer-content">
      <!-- Header flusso -->
      <div class="form-grid">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('pratiche.col_codice') }}</label>
            <span class="form-value">{{ flusso.pratica_codice || `#${flusso.pratica_id}` }}</span>
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.col_stato') }}</label>
            <Tag :value="stato" :severity="statoFlussoSeverity(stato)" />
          </div>
        </div>

        <div v-if="flusso.template_flusso_descrizione" class="form-field">
          <label>{{ t('pratiche.flusso_col_template') }}</label>
          <span class="form-value">{{ flusso.template_flusso_descrizione }}</span>
        </div>

        <div v-if="flusso.data_insert" class="form-field">
          <label>{{ t('pratiche.col_data_apertura') }}</label>
          <span class="form-value">{{ displayTimestamp(flusso.data_insert) }}</span>
        </div>
      </div>

      <!-- Azioni in base allo stato -->

      <!-- DA_ESEGUIRE: Bottone Avvia -->
      <div v-if="stato === STATO_FLUSSO.DA_ESEGUIRE" class="flusso-actions">
        <Button
          :label="t('pratiche.flusso_avvia')"
          icon="pi pi-play" severity="info"
          :loading="loading"
          @click="onAvvia"
        />
      </div>

      <!-- IN_CORSO: Form completamento con esito -->
      <div v-if="stato === STATO_FLUSSO.IN_CORSO" class="flusso-actions">
        <h4>{{ t('pratiche.flusso_completa_con_esito') }}</h4>
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('pratiche.flusso_esito') }} *</label>
            <Select
              v-model="esito"
              :options="esitiOptions"
              option-label="label" option-value="value"
              class="w-full"
              :placeholder="t('pratiche.flusso_esito')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.flusso_note_esito') }}</label>
            <Textarea v-model="noteEsito" class="w-full" rows="3" auto-resize />
          </div>
        </div>
        <div class="flex justify-end mt-3">
          <Button
            :label="t('pratiche.flusso_completa')"
            icon="pi pi-check" severity="success"
            :loading="loading"
            :disabled="!esito"
            @click="onCompleta"
          />
        </div>
      </div>

      <!-- COMPLETATO: Mostra esito (readonly) -->
      <div v-if="stato === STATO_FLUSSO.COMPLETATO" class="form-grid mt-3">
        <div class="form-field">
          <label>{{ t('pratiche.flusso_esito') }}</label>
          <Tag :value="flusso.esito" :severity="esitoFlussoSeverity(flusso.esito)" />
        </div>
        <div v-if="flusso.note_esito" class="form-field">
          <label>{{ t('pratiche.flusso_note_esito') }}</label>
          <span class="form-value">{{ flusso.note_esito }}</span>
        </div>
      </div>

      <!-- Footer con Chiudi -->
      <div class="flex justify-end mt-4">
        <Button :label="t('common.cancel')" text @click="onClose" />
      </div>
    </div>
  </Drawer>
</template>

<style scoped>
.flusso-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.form-value {
  font-size: 0.9rem;
  color: var(--text-color);
}
</style>
