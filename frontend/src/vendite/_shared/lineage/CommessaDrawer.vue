<script setup>
// Scopo: Drawer leggero SOLA LETTURA per la commessa (Fase C, genealogia
// inversa). La commessa non ha lista/CRUD propria: qui si consulta solo la
// sua genealogia — sorgenti che l'hanno generata (Origine) + fatture a valle
// (Destinazioni) — riusando LineagePassaggiPanel aperto di default. Aperto
// dalle tappe COMMESSA dei pannelli "Passaggi" dei documenti (via
// LineageDocumentoDrawerHost). L'header (codice + stato) arriva dal payload
// passaggi già caricato dal pannello (evento @loaded): niente seconda fetch.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../../core/components/DrawerEntityHeader.vue'
import { DRAWER_WIDTH } from '../../../core/constants'
import { statoCommessaSeverity } from '../../../core/utils/severity'
import LineagePassaggiPanel from './LineagePassaggiPanel.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  commessaId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])
const { t } = useI18n()

const nodo = ref(null)

function onLoaded(data) {
  nodo.value = data?.nodo ?? null
}

function onClose() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="(v) => { if (!v) onClose() }"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true">
    <template #header>
      <DrawerTitle :title="t('lineage.commessa_titolo')" icon="pi pi-sitemap" />
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

      <!-- La genealogia È il contenuto principale del drawer: pannello aperto
           di default (start-open). Mostra Origine (sorgenti) + Destinazioni. -->
      <LineagePassaggiPanel
        v-if="commessaId"
        base-path="/vendite/commesse"
        :doc-id="commessaId"
        start-open
        @loaded="onLoaded" />
    </div>
  </Drawer>
</template>
