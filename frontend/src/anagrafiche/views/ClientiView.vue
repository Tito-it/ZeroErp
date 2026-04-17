<script setup>
// Scopo: vista principale Gestione Clienti.
// SearchTable + Drawer creazione/visualizzazione.
// Sotto-drawer indirizzi e conti bancari dalla lista (come SoggettiView).
import { ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useContextStore } from '../../stores/context'
import { useClientiStore } from '../stores/clienti'
import ClientiSearchTable from '../components/ClientiSearchTable.vue'
import ClienteDrawer from '../components/ClienteDrawer.vue'
import ContattiSoggettoDrawer from '../../core/components/ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from '../../core/components/IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from '../../core/components/ContiBancariDrawer.vue'
import ContrattiBillingAccountDrawer from '../../vendite/components/ContrattiBillingAccountDrawer.vue'
import { TIPO_RUOLO } from '../../core/constants'

const { t } = useI18n()
const drawer = useDrawerState()
const store = useClientiStore()
const ctx = useContextStore()
const route = useRoute()
useReadonlyMode('anagrafiche', 'cliente')

// Se la ricerca universale ha selezionato un cliente, apri il drawer in edit.
// Il filtro lista viene applicato automaticamente da useSearchTable (legge ctx.searchTerm).
watch(() => route.fullPath, () => {
  if (route.name === 'anagrafiche-clienti' && ctx.entitaId) {
    nextTick(() => drawer.editRow({ id: ctx.entitaId }, 'id'))
  }
}, { immediate: true })

// Sotto-drawer dalla lista
const contattiDrawer = ref({ visible: false, ruoloId: null, istanzaUtilityId: null })
const indirizziDrawer = ref({ visible: false, ruoloId: null, istanzaUtilityId: null })
const contiBancariDrawer = ref({ visible: false, ruoloId: null, ownerName: '', istanzaUtilityId: null })
const contrattiDrawer = ref({
  visible: false,
  billingAccountId: null,
  billingAccountLabel: '',
  billingAccountUtility: '',
  canCreate: true,
  disabledReason: '',
})

function onContatti(data) {
  contattiDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id, istanzaUtilityId: data.istanza_utility_id }
}

function onIndirizzi(data) {
  indirizziDrawer.value = { visible: true, ruoloId: data.soggetto_ruolo_id, istanzaUtilityId: data.istanza_utility_id }
}

function onContiBancari(data) {
  contiBancariDrawer.value = {
    visible: true,
    ruoloId: data.soggetto_ruolo_id,
    ownerName: data.ragione_sociale_completa || '',
    istanzaUtilityId: data.istanza_utility_id,
  }
}

// Scopo: Determina se il BA ammette la creazione di nuovi contratti.
// Regola attuale: blocca su stato CESSATO/CHIUSO (estendibile).
function resolveCanCreateContratto(cliente) {
  const stato = (cliente?.stato_codice || '').toUpperCase()
  if (stato === 'CESSATO' || stato === 'CHIUSO') {
    return { canCreate: false, reason: t('clienti.ba_chiuso_no_contratti') }
  }
  return { canCreate: true, reason: '' }
}

function onContratti(data) {
  const { canCreate, reason } = resolveCanCreateContratto(data)
  contrattiDrawer.value = {
    visible: true,
    billingAccountId: data.billing_account_id,
    billingAccountLabel: data.ragione_sociale_completa || data.ba_codice || '',
    billingAccountUtility: data.utility_descrizione || '',
    canCreate,
    disabledReason: reason,
  }
}

// Scopo: Dopo salvataggio, riapre in edit se era creazione (per gestire contatti/indirizzi/banca).
async function onDrawerSaved(result) {
  store.filters.offset = 0
  await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}
</script>

<template>
  <div class="app-page">
    <ClientiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @contatti="onContatti"
      @indirizzi="onIndirizzi"
      @conti-bancari="onContiBancari"
      @contratti="onContratti"
    />

    <ClienteDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :cliente-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <ContattiSoggettoDrawer
      :visible="contattiDrawer.visible"
      @update:visible="v => contattiDrawer.visible = v"
      :soggetto-id="contattiDrawer.ruoloId"
      :istanza-utility-id="contattiDrawer.istanzaUtilityId"
      context="ruolo"
    />

    <IndirizziSoggettoDrawer
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="indirizziDrawer.ruoloId"
      :istanza-utility-id="indirizziDrawer.istanzaUtilityId"
      :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
      context="ruolo"
    />

    <ContiBancariDrawer
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="contiBancariDrawer.ruoloId"
      :owner-name="contiBancariDrawer.ownerName"
      :istanza-utility-id="contiBancariDrawer.istanzaUtilityId"
      context="ruolo"
    />

    <ContrattiBillingAccountDrawer
      :visible="contrattiDrawer.visible"
      @update:visible="v => contrattiDrawer.visible = v"
      :billing-account-id="contrattiDrawer.billingAccountId"
      :billing-account-label="contrattiDrawer.billingAccountLabel"
      :billing-account-utility="contrattiDrawer.billingAccountUtility"
      :can-create="contrattiDrawer.canCreate"
      :disabled-create-reason="contrattiDrawer.disabledReason"
    />
  </div>
</template>
