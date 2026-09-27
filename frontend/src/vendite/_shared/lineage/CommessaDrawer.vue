<script setup>
// Scopo: Drawer leggero SOLA LETTURA per la commessa (Fase C, genealogia
// inversa). La commessa non ha lista/CRUD propria: qui si consulta solo la
// sua genealogia — sorgenti che l'hanno generata (Origine) + fatture a valle
// (Destinazioni) — riusando il contenuto lineage INLINE. Aperto dalle tappe
// COMMESSA dei chip/dialog "Passaggi" dei documenti (via DocumentoDrawerHost).
// L'header (codice + stato) arriva dal nodo dello stesso payload passaggi:
// una fetch sola per header e genealogia.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import PraticaDrawer from '../../../pratiche/components/PraticaDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../../core/constants'
import { statoCommessaSeverity } from '../../../core/utils/severity'
import DocumentoDrawerHost from '../../../core/components/DocumentoDrawerHost.vue'
import { useDocumentoDrawer } from '../../../core/composables/useDocumentoDrawer'
import LineagePassaggiContenuto from './LineagePassaggiContenuto.vue'
import { useDocumentoPassaggi } from './useDocumentoPassaggi'
import { gestoreVisibile } from '../../../core/composables/useDrawerFormPreserve'

const props = defineProps({
  visible: { type: Boolean, default: false },
  commessaId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])
const { t } = useI18n()

const {
  data: passaggi,
  loaded,
  loading,
} = useDocumentoPassaggi('/vendite/commesse', () => props.commessaId)

const nodo = computed(() => passaggi.value?.nodo ?? null)
const pratica = computed(() => passaggi.value?.pratica ?? null)

const praticaDrawerVisible = ref(false)

// Host cross-dominio: apre il drawer di dettaglio del documento della tappa.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumentoDrawer,
} = useDocumentoDrawer()

function apriDocumento(row) {
  // Guardia "tappa apribile" nel composable (`apri` no-op su chiave ignota).
  apriDocumentoDrawer(row?.tipoCodice, row?.docId)
}

function onClose() {
  emit('update:visible', false)
}
const suVisibile = gestoreVisibile(emit, onClose)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true">
    <template #header>
      <DrawerTitle :title="t('vendite.lineage.commessa_titolo')" :icon="MANAGE_ICONS.COMMESSA" />
    </template>

    <div class="app-drawer-content">
      <DrawerEntityHeader v-if="nodo">
        <Tag :value="nodo.codice || '—'" severity="secondary" />
        <template #status>
          <Tag
            v-if="nodo.stato_descrizione"
            :value="nodo.stato_descrizione"
            :severity="statoCommessaSeverity(nodo.stato_codice_interno)" />
        </template>
      </DrawerEntityHeader>

      <!-- La genealogia È il contenuto principale del drawer: contenuto INLINE,
           non chip + dialog come nei drawer documento — qui una modale sarebbe
           un click di troppo su un drawer che esiste solo per mostrarla. -->
      <LineagePassaggiContenuto
        :data="passaggi"
        :loading="loading"
        :loaded="loaded"
        @apri-pratica="praticaDrawerVisible = true"
        @apri-documento="apriDocumento" />

      <PraticaDrawer
        v-if="pratica"
        v-model:visible="praticaDrawerVisible"
        mode="edit"
        :pratica-id="pratica.pratica_id" />

      <DocumentoDrawerHost
        v-model:visible="docDrawerVisible"
        :tipo-codice="docDrawerTipo"
        :doc-id="docDrawerId" />
    </div>
  </Drawer>
</template>
