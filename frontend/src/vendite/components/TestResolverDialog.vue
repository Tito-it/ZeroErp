<script setup>
// Scopo: Dialog diagnostico resolver pricing v5 (POST /vendite/pricing/resolve/).
//        Esegue risoluzione 3 stadi PROMO → CONTRATTO → CATEGORIA/LISTINO e
//        mostra il prezzo finale con l'origine del match.
//        Nessun side effect: pura lettura deterministica.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { extractApiError } from '../../core/utils/apiError'
import { resolvePrezzoV5 } from '../api/listini'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { DATE_FORMAT, DRAWER_WIDTH, TIPO_RUOLO } from '../../core/constants'
import { toDateString } from '../../core/utils/date'

const { t } = useI18n()
const { loading } = useApiHandler()

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['update:visible'])

const form = ref({
  articolo_obj: null,
  uom_id: null,
  data_riferimento: new Date(),
  ba_obj: null,
  utility_id: null,
  classe_utenza_id: null,
})
const result = ref(null)
const errorMsg = ref(null)

// UoM operative dell'articolo selezionato (pattern VersioneDrawer).
const uomOptions = ref([])
const uomLoading = ref(false)

function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}

async function loadUomPerArticolo(articoloId) {
  uomOptions.value = []
  if (!articoloId) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articoloId)
    const list = res.data.data?.results || res.data.data || []
    uomOptions.value = list
    if (!form.value.uom_id) {
      const base = list.find(u => u.is_base)
      form.value.uom_id = base ? base.uom_id : (list.length === 1 ? list[0].uom_id : null)
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
  }
}

watch(
  () => form.value.articolo_obj?.id,
  (newId, oldId) => {
    if (newId === oldId) return
    form.value.uom_id = null
    loadUomPerArticolo(newId)
  },
)

// Il BA determina univocamente la utility (FK unique su (istanza, utility)).
// Quando l'utente seleziona/cambia BA, allineiamo form.utility_id al valore
// del BA per evitare test incoerenti (BA di una utility + utility diversa
// passata al resolver). Se il BA viene svuotato, la utility resta libera
// (eventualmente selezionabile a mano).
watch(
  () => form.value.ba_obj,
  (newBa) => {
    if (newBa?.utility_id) {
      form.value.utility_id = newBa.utility_id
    }
  },
)

// Pulizia stato al close del dialog.
watch(
  () => props.visible,
  (v) => {
    if (!v) {
      result.value = null
      errorMsg.value = null
    }
  },
)

const canTest = computed(() => (
  !!form.value.articolo_obj?.id
  && !!form.value.uom_id
  && !!form.value.ba_obj?.id
  && !!form.value.utility_id
  && !!form.value.data_riferimento
))

// Mappa origine del match a severity per visualizzazione Tag.
const origineSeverity = {
  PROMO: 'warn',
  CONTRATTO: 'info',
  CATEGORIA: 'success',
}

async function doTest() {
  result.value = null
  errorMsg.value = null
  const payload = {
    articolo_id: form.value.articolo_obj.id,
    uom_id: form.value.uom_id,
    ba_id: form.value.ba_obj.id,
    utility_id: form.value.utility_id,
    data_riferimento: toDateString(form.value.data_riferimento),
  }
  if (form.value.classe_utenza_id) {
    payload.classe_utenza_id = form.value.classe_utenza_id
  }
  try {
    const apiRes = await resolvePrezzoV5(payload)
    result.value = apiRes.data.data
  } catch (err) {
    errorMsg.value = extractApiError(err) || t('listini.resolver_errore')
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog :visible="visible" @update:visible="v => emit('update:visible', v)"
    :header="t('listini.test_prezzo')" modal :style="{ width: DRAWER_WIDTH.STANDARD }">

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('listini.field_articolo') }} *</label>
        <ArticoloLookup v-model="form.articolo_obj" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_uom') }} *</label>
        <Select
          v-model="form.uom_id"
          :options="uomOptions"
          :option-label="uomLabel"
          option-value="uom_id"
          :loading="uomLoading"
          :placeholder="!form.articolo_obj?.id
            ? t('vendite.promo_articoli.field_uom_articolo_first')
            : t('catalogo.select_uom')"
          :disabled="!form.articolo_obj?.id"
        />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_ba') }} *</label>
        <BillingAccountLookup v-model="form.ba_obj" :placeholder="t('listini.select_ba')" />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_utility') }} *</label>
        <UtilityPerRuoloSelect
          v-model="form.utility_id"
          :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
          :placeholder="t('listini.filtro_utility')"
          :disabled="!!form.ba_obj?.id"
        />
        <small v-if="form.ba_obj?.id" class="text-color-secondary">
          {{ t('listini.field_utility_derived_from_ba') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_classe_utenza') }}</label>
        <LookupSelect
          v-model="form.classe_utenza_id"
          rel="config.classi_utenze"
          :placeholder="t('listini.field_classe_utenza_placeholder')"
          show-clear
        />
      </div>
      <div class="form-field">
        <label>{{ t('listini.field_data_riferimento') }} *</label>
        <DatePicker v-model="form.data_riferimento" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
      </div>
    </div>

    <div style="display: flex; justify-content: center; margin: 1rem 0;">
      <Button :label="t('listini.esegui_test')" icon="pi pi-search" @click="doTest"
        :loading="loading" :disabled="!canTest" />
    </div>

    <div v-if="result" style="padding: 0.75rem; border: 1px solid var(--app-card-border); border-radius: 6px;">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.resolver_prezzo_finale') }}</label>
          <strong style="font-size: 1.4rem;">{{ result.prezzo_finale }}</strong>
        </div>
        <div class="form-field">
          <label>{{ t('listini.resolver_origine') }}</label>
          <Tag :value="result.origine" :severity="origineSeverity[result.origine] || 'secondary'" />
        </div>
        <div class="form-field" v-if="result.prezzo_base_snapshot != null">
          <label>{{ t('listini.resolver_prezzo_base') }}</label>
          <span>{{ result.prezzo_base_snapshot }}</span>
        </div>
        <div class="form-field" v-if="result.tipo_variazione_applicata">
          <label>{{ t('listini.resolver_variazione') }}</label>
          <span>
            {{ result.tipo_variazione_applicata }}
            <strong v-if="result.valore_variazione_applicata != null">
              {{ result.valore_variazione_applicata }}
            </strong>
          </span>
        </div>
        <div class="form-field" v-if="result.listino_id">
          <label>{{ t('listini.resolver_listino') }}</label>
          <span>#{{ result.listino_id }} · v{{ result.listino_versione_id }}</span>
        </div>
        <div class="form-field" v-if="result.contratto_id">
          <label>{{ t('listini.resolver_contratto') }}</label>
          <span>#{{ result.contratto_id }}</span>
        </div>
        <div class="form-field" v-if="result.promo_id">
          <label>{{ t('listini.resolver_promo') }}</label>
          <span>#{{ result.promo_id }}</span>
        </div>
        <div class="form-field" v-if="result.categoria_cliente_id_snapshot">
          <label>{{ t('listini.resolver_categoria') }}</label>
          <span>#{{ result.categoria_cliente_id_snapshot }}</span>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="app-field-error" style="padding: 0.75rem; text-align: center;">
      {{ errorMsg }}
    </div>

    <template #footer>
      <Button :label="t('common.close')" severity="secondary" @click="close" />
    </template>
  </Dialog>
</template>
