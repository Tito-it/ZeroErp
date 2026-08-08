<script setup>
// Scopo: Form riga reso (create/edit) dentro ResoRigheTable. In CREATE si
// sceglie la riga del DDT sorgente con residuo rendibile (Select alimentato
// da /vendite/ddt/<id>/righe-per-reso/): articolo/UoM sono SNAPSHOT copiati
// dal BE, qui viaggiano solo ddt_riga_id + tipo_reso_id + qta_operativa +
// motivo. Il guard over-return resta a DB (E_RESO_QTA_SUPERA_CONSEGNATO);
// la UI limita l'input al residuo mostrato (best-effort UX).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import LookupSelect from '../../../core/components/LookupSelect.vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { formatNumber } from '../../../core/utils/format'
import { getRigheDdtPerReso } from '../api/resiApi'
import { useResiStore } from '../stores/resi'

const { t } = useI18n()
const store = useResiStore()
const { execute, loading, campiErrati } = useApiHandler()

const props = defineProps({
  resoId: { type: Number, required: true },
  ddtOrigineId: { type: [Number, null], default: null },
  // null = nuova riga; oggetto = edit.
  riga: { type: Object, default: null },
})
const emit = defineEmits(['saved', 'cancel'])

const isEdit = computed(() => props.riga?.id != null)

const form = ref({
  ddt_riga_id: null,
  tipo_reso_id: null,
  qta_operativa: null,
  motivo: '',
})

// Righe del DDT sorgente con residuo rendibile (solo CREATE).
const righeDdt = ref([])
const righeDdtLoading = ref(false)

const righeDdtOptions = computed(() => righeDdt.value
  .filter(r => Number(r.qta_resa_residua) > 0)
  .map(r => ({
    value: r.ddt_riga_id,
    label: `${r.articolo_codice || ''} — ${r.descrizione}`
      + ` (${t('vendite.resi.crea_col_residuo').toLowerCase()}: `
      + `${formatNumber(r.qta_resa_residua_operativa)} ${r.uom_codice || ''})`,
  })))

const rigaDdtSelezionata = computed(
  () => righeDdt.value.find(r => r.ddt_riga_id === form.value.ddt_riga_id) || null,
)
const residuoOperativo = computed(
  () => Number(rigaDdtSelezionata.value?.qta_resa_residua_operativa) || 0,
)

// Scopo: carica le righe rendibili del DDT sorgente (solo CREATE).
async function loadRigheDdt() {
  if (isEdit.value || !props.ddtOrigineId) return
  righeDdtLoading.value = true
  try {
    const res = await getRigheDdtPerReso(props.ddtOrigineId)
    righeDdt.value = res.data.data || []
  } finally {
    righeDdtLoading.value = false
  }
}

// Default qta = residuo alla selezione della riga DDT.
watch(() => form.value.ddt_riga_id, () => {
  if (!isEdit.value && residuoOperativo.value > 0) {
    form.value.qta_operativa = residuoOperativo.value
  }
})

watch(() => props.riga, (r) => {
  form.value = {
    ddt_riga_id: r?.ddt_riga_id ?? null,
    tipo_reso_id: r?.tipo_reso_id ?? null,
    qta_operativa: r?.qta_operativa != null ? Number(r.qta_operativa) : null,
    motivo: r?.motivo ?? '',
  }
  loadRigheDdt()
}, { immediate: true })

const canSave = computed(() =>
  form.value.tipo_reso_id != null
  && Number(form.value.qta_operativa) > 0
  && (isEdit.value || form.value.ddt_riga_id != null))

// Scopo: salva la riga (create/update). In UPDATE la riga DDT/articolo sono
// immutabili (snapshot): viaggiano solo tipo/qta/motivo.
async function handleSave() {
  if (!canSave.value) return
  const payload = {
    tipo_reso_id: form.value.tipo_reso_id,
    qta_operativa: String(form.value.qta_operativa),
    motivo: form.value.motivo || null,
  }
  let result
  if (isEdit.value) {
    result = await execute(
      () => store.aggiornaRiga(props.resoId, props.riga.id, payload),
      { successMessage: t('vendite.resi.riga_salvata') },
    )
  } else {
    payload.ddt_riga_id = form.value.ddt_riga_id
    result = await execute(
      () => store.addRiga(props.resoId, payload),
      { successMessage: t('vendite.resi.riga_salvata') },
    )
  }
  if (result !== null) emit('saved')
}
</script>

<template>
  <div class="form-grid">
    <!-- CREATE: scelta della riga DDT da rendere (residuo > 0). -->
    <div v-if="!isEdit" class="form-field">
      <label>{{ t('vendite.resi.riga_ddt_riga') }} *</label>
      <Select v-model="form.ddt_riga_id" :options="righeDdtOptions"
        option-label="label" option-value="value"
        :loading="righeDdtLoading"
        :placeholder="t('vendite.resi.riga_ddt_riga_placeholder')" />
      <small v-if="rigaDdtSelezionata" style="color: var(--text-color-secondary);">
        {{ t('vendite.resi.riga_residuo_hint', {
          residuo: formatNumber(residuoOperativo),
          uom: rigaDdtSelezionata.uom_codice || '',
        }) }}
      </small>
    </div>
    <!-- EDIT: articolo snapshot immutabile, solo display. -->
    <div v-else class="form-field">
      <label>{{ t('vendite.resi.riga_articolo') }}</label>
      <InputText :model-value="`${riga.articolo_codice || ''} — ${riga.descrizione}`" disabled />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.resi.riga_tipo') }} *</label>
        <LookupSelect v-model="form.tipo_reso_id" rel="config.tipi_reso"
          :placeholder="t('vendite.resi.riga_tipo')" :filter="false" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.riga_quantita') }} *</label>
        <InputNumber v-model="form.qta_operativa" :min="0"
          :max="!isEdit && residuoOperativo > 0 ? residuoOperativo : undefined"
          :min-fraction-digits="0" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.riga_motivo') }}</label>
        <InputText v-model="form.motivo"
          :invalid="campiErrati.includes('motivo')"
        />
      </div>
    </div>

    <div class="app-drawer-footer">
      <Button :label="t('common.cancel')" text severity="secondary"
        icon="pi pi-arrow-left" @click="emit('cancel')" />
      <Button :label="t('common.save')" icon="pi pi-check"
        :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>
