<script setup>
// Scopo: Vista principale gestione impostazioni parametri.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { PARAMETER_SCOPE } from '../../core/composables/useParameterSettings'
import ImpostazioniSearchTable from '../components/ImpostazioniSearchTable.vue'
import ImpostazioniOverrideDrawer from '../components/ImpostazioniOverrideDrawer.vue'

const { t } = useI18n()
const store = useImpostazioniStore()
const { execute } = useApiHandler()
useReadonlyMode('config')

const drawerVisible = ref(false)
const selectedParameter = ref(null)

function onEditOverride(parameter) {
  selectedParameter.value = parameter
  drawerVisible.value = true
}

async function onRemoveOverride(parameter) {
  if (!parameter.user_override_id) return
  const result = await execute(
    () => store.removeOverride(parameter.user_override_id),
    { successMessage: t('impostazioni.override_removed') }
  )
  if (result !== null) await store.fetchList()
}

async function onRemoveEmittenteOverride(parameter) {
  if (!parameter.emittente_override_id) return
  const result = await execute(
    () => store.removeOverride(parameter.emittente_override_id, PARAMETER_SCOPE.EMITTENTE),
    { successMessage: t('impostazioni.override_removed') }
  )
  if (result !== null) await store.fetchList()
}

async function onDrawerSaved() {
  drawerVisible.value = false
  await store.fetchList()
}
</script>

<template>
  <div class="app-page">
    <ImpostazioniSearchTable
      @edit-override="onEditOverride"
      @remove-override="onRemoveOverride"
      @remove-emittente-override="onRemoveEmittenteOverride"
    />

    <ImpostazioniOverrideDrawer
      :visible="drawerVisible"
      @update:visible="v => drawerVisible = v"
      :parameter="selectedParameter"
      @saved="onDrawerSaved"
      @cancelled="drawerVisible = false"
    />
  </div>
</template>
