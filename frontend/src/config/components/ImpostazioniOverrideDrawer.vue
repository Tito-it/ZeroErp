<script setup>
// Scopo: Drawer per creare/modificare un override su un parametro.
// Mostra la catena di fallback (default -> emittente -> gruppo -> utente)
// e consente all'operatore di impostare il valore. L'utente admin puo' scegliere
// se applicare l'override a livello personale o a livello emittente (default per
// tutti gli utenti dell'azienda).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { PARAMETER_SCOPE } from '../../core/composables/useParameterSettings'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useAuthStore } from '../../stores/auth'
import { DRAWER_WIDTH } from '../../core/constants'
import ParameterFallback from '../../core/components/ParameterFallback.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
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

const isEmittenteScope = computed(() => scope.value === PARAMETER_SCOPE.EMITTENTE)

// Solo l'admin puo' scegliere lo scope; gli utenti normali restano fissi su USER.
const scopeOptions = computed(() => [
  { value: PARAMETER_SCOPE.EMITTENTE, label: t('impostazioni.scope_emittente') },
  { value: PARAMETER_SCOPE.USER, label: t('impostazioni.scope_user') }
])

// Edit attivo se per lo scope corrente esiste già un valore configurato.
const isEdit = computed(() => {
  if (!props.parameter) return false
  return isEmittenteScope.value
    ? props.parameter.emittente_value != null
    : props.parameter.user_override_id != null
})

// Restituisce il valore preimpostato per il campo in base allo scope corrente:
// valore già configurato per quello scope, altrimenti il valore risolto come suggerimento.
function valueForCurrentScope() {
  const p = props.parameter
  if (!p) return ''
  const existing = isEmittenteScope.value ? p.emittente_value : p.user_value
  return existing ?? p.resolved_value ?? ''
}

watch(() => props.visible, (v) => {
  if (!v || !props.parameter) return
  scope.value = auth.isAdmin ? PARAMETER_SCOPE.EMITTENTE : PARAMETER_SCOPE.USER
  overrideValue.value = valueForCurrentScope()
})

watch(scope, () => {
  if (props.visible) overrideValue.value = valueForCurrentScope()
})

const canSave = computed(() => overrideValue.value !== '')

async function handleSave() {
  if (!props.parameter) return
  const result = await execute(
    () => store.saveOverride(props.parameter.code, overrideValue.value, scope.value),
    { successMessage: t('impostazioni.override_saved') }
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
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('impostazioni.override_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }" v-if="parameter">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('impostazioni.col_code') }}</label>
          <InputText :model-value="parameter.code" disabled />
        </div>

        <div class="form-field" v-if="parameter.description">
          <label>{{ t('impostazioni.col_description') }}</label>
          <div class="parameter-description">{{ parameter.description }}</div>
        </div>

        <div class="form-field">
          <label>{{ t('impostazioni.fallback_chain') }}</label>
          <ParameterFallback :parameter="parameter" />
        </div>

        <div v-if="auth.isAdmin" class="form-field">
          <label>{{ t('impostazioni.scope_label') }}</label>
          <Select v-model="scope" :options="scopeOptions"
            option-label="label" option-value="value"
            :disabled="isReadonly" />
        </div>

        <div class="form-field">
          <label>{{ isEmittenteScope ? t('impostazioni.emittente_override') : t('impostazioni.your_override') }}</label>
          <InputText v-model="overrideValue" :disabled="isReadonly"
            :placeholder="t('impostazioni.override_placeholder')" />
        </div>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

<style scoped>
.parameter-description {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  padding: 0.25rem 0;
}
</style>
