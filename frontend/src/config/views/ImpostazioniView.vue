<script setup>
// Scopo: Vista principale gestione impostazioni parametri.
import { ref } from 'vue'
import { registraDrawerChiudibile } from '../../core/composables/useDrawerChiusuraGlobale'
import { useI18n } from 'vue-i18n'
import { useImpostazioniStore } from '../stores/impostazioni'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { PARAMETER_SCOPE } from '../../core/composables/useParameterSettings'
import ImpostazioniSearchTable from '../components/ImpostazioniSearchTable.vue'
import ImpostazioniOverrideDrawer from '../components/ImpostazioniOverrideDrawer.vue'

const { t } = useI18n()
const store = useImpostazioniStore()
const { execute } = useApiHandler()
useReadonlyMode(READONLY_DOMAINS.CONFIG)

const drawerVisible = ref(false)
// Le sole due liste che tengono a mano lo stato del drawer invece di passare da
// `useDrawerState`: si registrano da se' nella chiusura globale, o resterebbero
// gli unici due pannelli a sopravvivere a un cambio di pagina.
registraDrawerChiudibile(() => { drawerVisible.value = false })

const selectedParameter = ref(null)

function onEditOverride(parameter) {
  selectedParameter.value = parameter
  drawerVisible.value = true
}

async function onRemoveOverride(parameter) {
  if (!parameter.user_override_id) return
  const result = await execute(
    () => store.removeOverride(parameter.user_override_id, parameter.code, PARAMETER_SCOPE.USER),
    { successMessage: t('config.impostazioni.override_removed') }
  )
  if (result !== null) await store.fetchList()
}

async function onRemoveEmittenteOverride(parameter) {
  if (!parameter.emittente_override_id) return
  const result = await execute(
    () => store.removeOverride(parameter.emittente_override_id, parameter.code, PARAMETER_SCOPE.EMITTENTE),
    { successMessage: t('config.impostazioni.override_removed') }
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
