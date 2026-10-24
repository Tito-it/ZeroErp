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
import Tag from 'primevue/tag'
import AppDrawer from '../../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import PraticaDrawer from '../../../pratiche/components/PraticaDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../../core/constants'
import { statoCommessaSeverity } from '../../../core/utils/severity'
import DocumentoDrawerHost from '../../../core/components/DocumentoDrawerHost.vue'
import { useDocumentoDrawer } from '../../../core/composables/useDocumentoDrawer'
import LineagePassaggiContenuto from './LineagePassaggiContenuto.vue'
import { useDocumentoPassaggi } from './useDocumentoPassaggi'

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
  reload,
} = useDocumentoPassaggi('/vendite/commesse', () => props.commessaId)

const nodo = computed(() => passaggi.value?.nodo ?? null)
const pratica = computed(() => passaggi.value?.pratica ?? null)

const praticaDrawerVisible = ref(false)

// Host cross-dominio: apre il drawer di dettaglio del documento della tappa.
// ⭐ Alla CHIUSURA si rilegge (`onClose`), come fa DocumentoCollegamentiBar:
// nel drawer impilato l'operatore puo' aver agito (annullare il DDT, il
// preventivo…), e qui gli stati della catena e la testata della commessa
// vengono dalla stessa lettura — senza, restavano quelli di prima (2026-10-13).
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumentoDrawer,
  onVisibleChange: onDocDrawerVisibleChange,
} = useDocumentoDrawer(() => reload())

function apriDocumento(row) {
  // Guardia "tappa apribile" nel composable (`apri` no-op su chiave ignota).
  apriDocumentoDrawer(row?.tipoCodice, row?.docId)
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.lineage.commessa_titolo')"
    :icon="MANAGE_ICONS.COMMESSA"
    :width="DRAWER_WIDTH.STANDARD"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
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
      :visible="docDrawerVisible"
      @update:visible="onDocDrawerVisibleChange"
      :tipo-codice="docDrawerTipo"
      :doc-id="docDrawerId" />
  </AppDrawer>
</template>
