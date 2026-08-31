<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista dei TITOLI IVA di un soggetto (I7 / D10), aperta dalla sezione
// «Titoli IVA» del `SoggettoDrawer`. Apre il drawer del singolo titolo.
//
// ⛔ NON adotta `useSoggettoRuoloCollection`, ed e' una non-adozione MOTIVATA
//   (stessa forma con cui quel composable dichiara di non coprire
//   `IndirizziSoggettoDrawer`): quel backbone possiede la macchina a stati di un
//   form INLINE a card. Un titolo ha figli — le righe di ambito, e col registro
//   dei movimenti ne avra' due — quindi vuole un drawer suo, e qui non resta
//   nessuno stato di form da condividere. Riusarlo vorrebbe dire tenere una
//   `formMode` che nessuno accende.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import {
  listSoggettoTitoliIva,
  deleteSoggettoTitoloIva,
} from '../api/anagrafiche'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import TitoloIvaDrawer from './TitoloIvaDrawer.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmDelete } = useConfirmAction()
// Guard di versione: stesso motivo del drawer del titolo — il soggetto puo'
// cambiare piu' in fretta di quanto torni la lista.
const fv = useFetchVersion()

const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: String, default: null },
  soggettoNome: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'saved'])

const titoli = ref([])
const titoloDrawerVisible = ref(false)
const titoloSelezionatoId = ref(null)

async function loadTitoli() {
  if (!props.soggettoId) return
  const v = fv.tag()
  const res = await execute(() => listSoggettoTitoliIva(props.soggettoId))
  if (!fv.isCurrent(v)) return
  titoli.value = res === null ? [] : (res.data.data?.results || [])
}

watch(() => props.visible, (val) => {
  if (!val) { fv.invalidate(); return }
  loadTitoli()
})

function apriTitolo(id) {
  titoloSelezionatoId.value = id
  titoloDrawerVisible.value = true
}

async function onTitoloSaved() {
  await loadTitoli()
  emit('saved')
}

// ⚠️ La cancellazione la rifiuta il BE se il titolo ha gia' consumato plafond
//   (Q6): un registro e' la traccia di cio' che e' stato consumato. Qui non si
//   ri-deriva la regola — si chiede conferma e si lascia parlare il backend, che
//   dice anche COSA FARE al posto («si disattiva»).
function onDelete(riga) {
  confirmDelete(descriviTitolo(riga), async () => {
    const res = await execute(
      () => deleteSoggettoTitoloIva(props.soggettoId, riga.id),
      { successMessage: t('anagrafiche.titoli_iva.titolo_eliminato') },
    )
    if (res !== null) await onTitoloSaved()
  })
}

function descriviTitolo(r) {
  return `${r.tipo_descrizione} — ${r.emittente_ragione_sociale}`
}

// Severity del residuo: sotto zero e' uno sfondamento, e si vede (Q4).
function residuoSeverity(r) {
  if (r.residuo == null) return 'secondary'
  return Number(r.residuo) < 0 ? 'danger' : 'success'
}

const pageActions = computed(() => {
  const azioni = [{
    key: 'reload', kind: 'utility', label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD, command: loadTitoli,
  }]
  if (!isReadonly.value) {
    azioni.push({
      key: 'new', kind: 'primary', label: t('common.new'),
      tooltip: t('anagrafiche.titoli_iva.aggiungi_titolo'),
      icon: MANAGE_ICONS.ADD, command: () => apriTitolo(null),
    })
  }
  return azioni
})

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="visible" @update:visible="emit('update:visible', $event)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }">
    <template #header>
      <DrawerTitle
        :action="soggettoNome"
        :title="t('anagrafiche.titoli_iva.titolo_lista')"
        :icon="MANAGE_ICONS.TITOLI_IVA" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <PageActionsBar :actions="pageActions" />

      <DataTable :value="titoli" :loading="loading" class="app-datatable"
        data-key="id" size="small" @row-click="apriTitolo($event.data.id)">
        <Column field="tipo_descrizione" :header="t('anagrafiche.titoli_iva.col_tipo')" />
        <Column field="emittente_ragione_sociale"
          :header="t('anagrafiche.titoli_iva.col_emittente')" />
        <Column field="iva_codice" :header="t('anagrafiche.titoli_iva.col_iva')" />
        <Column :header="t('anagrafiche.titoli_iva.col_validita')">
          <template #body="{ data }">
            {{ displayDate(data.valido_dal) }} —
            {{ data.valido_al ? displayDate(data.valido_al) : t('anagrafiche.titoli_iva.senza_scadenza') }}
          </template>
        </Column>
        <Column :header="t('anagrafiche.titoli_iva.col_residuo')">
          <template #body="{ data }">
            <!-- Il residuo esiste solo dove esiste un tetto: sui tipi senza
                 plafond non si mostra uno zero, che sembrerebbe «esaurito». -->
            <Tag v-if="data.residuo != null" :value="formatCurrency(data.residuo)"
              :severity="residuoSeverity(data)" />
            <span v-else class="text-color-secondary">—</span>
          </template>
        </Column>
        <Column :header="t('anagrafiche.titoli_iva.col_stato')">
          <template #body="{ data }">
            <Tag v-if="!data.attivo" :value="t('anagrafiche.titoli_iva.tag_non_attivo')" severity="secondary" />
            <!-- Q2: RISTRETTO senza righe non copre nessuna merce. Lo DICHIARA
                 il backend (`ambito_incompleto`): qui non si ri-deriva. -->
            <Tag v-else-if="data.ambito_incompleto"
              :value="t('anagrafiche.titoli_iva.tag_ambito_incompleto')" severity="warn" />
            <Tag v-else :value="t('common.attivo')" severity="success" />
          </template>
        </Column>
        <Column v-if="!isReadonly" style="width: 4rem">
          <template #body="{ data }">
            <Button :icon="MANAGE_ICONS.DELETE" text severity="danger"
              @click.stop="onDelete(data)" />
          </template>
        </Column>
        <template #empty>{{ t('anagrafiche.titoli_iva.lista_vuota') }}</template>
      </DataTable>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <TitoloIvaDrawer
      v-model:visible="titoloDrawerVisible"
      :soggetto-id="soggettoId"
      :titolo-id="titoloSelezionatoId"
      @saved="onTitoloSaved" />
  </Drawer>
</template>
