<script setup>
// Scopo: Drawer per creare/modificare un override su un parametro.
// Mostra la catena di fallback (default -> emittente -> gruppo -> utente)
// e consente all'operatore di impostare il valore. L'utente admin puo' scegliere
// se applicare l'override a livello personale o a livello emittente (default per
// tutti gli utenti dell'azienda).
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerFormPreserve, gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { PARAMETER_SCOPE } from '../../core/composables/useParameterSettings'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useAuthStore } from '../../stores/auth'
import { DRAWER_WIDTH } from '../../core/constants'
import ParameterFallback from '../../core/components/ParameterFallback.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

const { t } = useI18n()
const store = useImpostazioniStore()
const auth = useAuthStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  parameter: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const overrideValue = ref('')
// Scope override corrente. Default: admin → emittente, altrimenti → user.
const scope = ref(PARAMETER_SCOPE.USER)
// Id categoria cliente selezionata quando scope=CATEGORIA_CLIENTE (Phase B
// 2026-05-19). Resettato ad ogni cambio scope. Obbligatorio lato BE.
const categoriaClienteId = ref(null)

// Modifiche non salvate: il form e' spezzato su tre ref, si raccoglie cio'
// che il Salva manda.
const formDaSalvare = computed(() => ({
  scope: scope.value,
  categoria_cliente_id: categoriaClienteId.value,
  valore: overrideValue.value,
}))
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(formDaSalvare, { visibile: () => props.visible })

const isEmittenteScope = computed(() => scope.value === PARAMETER_SCOPE.EMITTENTE)
const isCategoriaScope = computed(() => scope.value === PARAMETER_SCOPE.CATEGORIA_CLIENTE)

// Solo l'admin puo' scegliere lo scope; gli utenti normali restano fissi su USER.
// Cascata visualizzata BE: user > categoria_cliente > group > emittente > default.
const scopeOptions = computed(() => [
  { value: PARAMETER_SCOPE.EMITTENTE, label: t('config.impostazioni.scope_emittente') },
  { value: PARAMETER_SCOPE.CATEGORIA_CLIENTE, label: t('config.impostazioni.scope_categoria_cliente') },
  { value: PARAMETER_SCOPE.USER, label: t('config.impostazioni.scope_user') }
])

// Edit attivo se per lo scope corrente esiste già un valore configurato.
// Per categoria controlliamo l'override_id specifico al BE (potrebbe esserci
// `categoria_cliente_value` di una categoria DIVERSA da quella selezionata
// nel drawer — l'override_id stesso e' specifico della tupla `(param, cat_id)`).
const isEdit = computed(() => {
  if (!props.parameter) return false
  if (isEmittenteScope.value) return props.parameter.emittente_value != null
  if (isCategoriaScope.value) return props.parameter.categoria_cliente_override_id != null
  return props.parameter.user_override_id != null
})

// Restituisce il valore preimpostato per il campo in base allo scope corrente:
// valore già configurato per quello scope, altrimenti il valore risolto come suggerimento.
function valueForCurrentScope() {
  const p = props.parameter
  if (!p) return ''
  let existing
  if (isEmittenteScope.value) existing = p.emittente_value
  else if (isCategoriaScope.value) existing = p.categoria_cliente_value
  else existing = p.user_value
  return existing ?? p.resolved_value ?? ''
}

watch(() => props.visible, async (v) => {
  if (!v || !props.parameter) return
  scope.value = auth.isSuperAdmin ? PARAMETER_SCOPE.EMITTENTE : PARAMETER_SCOPE.USER
  categoriaClienteId.value = null
  overrideValue.value = valueForCurrentScope()
  // Fotografia DOPO il watch su `scope`, che riscrive `overrideValue`.
  await nextTick()
  fissa()
})

watch(scope, () => {
  if (!props.visible) return
  // Reset categoria all'uscita dallo scope: evita di mandare al BE un id
  // che riferisce un altro scope ("orfano").
  if (!isCategoriaScope.value) categoriaClienteId.value = null
  overrideValue.value = valueForCurrentScope()
})

const canSave = computed(() => {
  if (overrideValue.value === '') return false
  // Scope categoria richiede id selezionato (BE rifiuta 400 se manca).
  if (isCategoriaScope.value && categoriaClienteId.value == null) return false
  return true
})

// Label dinamica del campo valore in base allo scope.
const overrideLabel = computed(() => {
  if (isEmittenteScope.value) return t('config.impostazioni.emittente_override')
  if (isCategoriaScope.value) return t('config.impostazioni.categoria_cliente_override')
  return t('config.impostazioni.your_override')
})

async function handleSave() {
  if (!props.parameter) return
  const options = isCategoriaScope.value
    ? { categoriaClienteId: categoriaClienteId.value }
    : {}
  const result = await execute(
    () => store.saveOverride(
      props.parameter.code, overrideValue.value, scope.value, options,
    ),
    { successMessage: t('config.impostazioni.override_saved') }
  )
  if (result !== null) {
    emit('saved', result)
    close()
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}

const chiudi = () => chiudiConConferma(close)
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer :visible="visible" @update:visible="suVisibile"
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('config.impostazioni.override_title')"
        :modificato="modificato"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }" v-if="parameter">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('config.impostazioni.col_code') }}</label>
          <InputText :model-value="parameter.code" disabled />
        </div>

        <div class="form-field" v-if="parameter.description">
          <label>{{ t('config.impostazioni.col_description') }}</label>
          <div class="parameter-description">{{ parameter.description }}</div>
        </div>

        <div class="form-field">
          <label>{{ t('config.impostazioni.fallback_chain') }}</label>
          <ParameterFallback :parameter="parameter" />
        </div>

        <div v-if="auth.isSuperAdmin" class="form-field">
          <label>{{ t('config.impostazioni.scope_label') }}</label>
          <Select v-model="scope" :options="scopeOptions"
            option-label="label" option-value="value"
            :disabled="isReadonly" />
        </div>

        <!-- Quando scope=CATEGORIA_CLIENTE: lookup categoria (admin-only,
             Phase B 2026-05-19). Il LookupSelect copre la tabella
             `anagrafiche.categorie_clienti` come whitelist core. Senza
             selezione, canSave=false. -->
        <div v-if="isCategoriaScope" class="form-field">
          <label>{{ t('config.impostazioni.field_categoria_cliente') }} *</label>
          <LookupSelect v-model="categoriaClienteId"
            rel="anagrafiche.categorie_clienti"
            :placeholder="t('config.impostazioni.select_categoria_cliente')"
            :disabled="isReadonly" show-code />
        </div>

        <div class="form-field">
          <label>{{ overrideLabel }}</label>
          <InputText v-model="overrideValue" :disabled="isReadonly"
            :placeholder="t('config.impostazioni.override_placeholder')" />
        </div>
      </div>

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="chiudi" />
    </div>
  </Drawer>
</template>

<style scoped>
.parameter-description {
  color: var(--app-text-muted);
  font-size: 0.85rem;
  padding: 0.25rem 0;
}
</style>
