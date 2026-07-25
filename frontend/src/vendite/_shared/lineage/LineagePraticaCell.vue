<script setup>
// Scopo: Cella "Pratica" delle liste documento (lineage Fase B) — numero
// pratica cliccabile che apre il PraticaDrawer impilato (coerente col
// pannello "Passaggi"). "—" se il documento non è collegato a una pratica;
// badge "+N" se il modello ne espone più di una (difensivo, Q5).
//
// `@click.stop`: la riga della lista ha @row-click (apre il drawer del
// documento) — il click sul numero pratica NON deve aprire il documento.
// PraticaDrawer montato solo su apertura (v-if): zero drawer per le righe
// non cliccate.
import { nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import PraticaDrawer from '../../../pratiche/components/PraticaDrawer.vue'

const props = defineProps({
  praticaId: { type: [Number, null], default: null },
  praticaNumero: { type: String, default: null },
  nPratiche: { type: Number, default: 0 },
})

const { t } = useI18n()
const drawerVisible = ref(false)
// Montato al primo click e MAI smontato alla chiusura (`v-if="everOpened"`):
// un v-if su drawerVisible smonterebbe il Drawer a metà animazione di slide-out.
const everOpened = ref(false)

function open() {
  if (!props.praticaId) return
  everOpened.value = true
  // Apertura al tick successivo (pattern DocumentoDrawerHost): il
  // drawer monta NASCOSTO e riceve visible false->true, così parte lo
  // slide-in PrimeVue (after-show -> contentReady). Il fetch e' comunque
  // garantito anche a mount gia'-visibile (watch immediate nel PraticaDrawer).
  nextTick(() => { drawerVisible.value = true })
}
</script>

<template>
  <span v-if="praticaNumero" class="lineage-cell-pratica">
    <Button
      link
      class="lineage-cell-link"
      :label="praticaNumero"
      @click.stop="open" />
    <span v-if="nPratiche > 1" class="lineage-cell-muted">
      {{ t('vendite.lineage.altre_pratiche', { n: nPratiche - 1 }) }}
    </span>
    <PraticaDrawer
      v-if="everOpened"
      v-model:visible="drawerVisible"
      mode="edit"
      :pratica-id="praticaId" />
  </span>
  <span v-else class="lineage-cell-muted">—</span>
</template>

<style scoped>
.lineage-cell-pratica {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.lineage-cell-link {
  padding: 0;
  font-weight: 600;
}
.lineage-cell-muted {
  color: var(--app-text-muted);
  font-size: 0.85rem;
}
</style>
