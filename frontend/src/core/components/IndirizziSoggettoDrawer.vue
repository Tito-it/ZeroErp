<script setup>
// Scopo: Drawer dedicato per gestione indirizzi di un soggetto.
// Riutilizzabile da: SoggettoDrawer (edit), futuro ClienteDrawer, FornitoreDrawer.
// Mostra lista indirizzi esistenti con "Cambia" + form per aggiungere nuovi.

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../composables/useApiHandler'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import {
  listSoggettoIndirizzi, createSoggettoIndirizzo, replaceSoggettoIndirizzo
} from '../../anagrafiche/api/anagrafiche'
import { lookupMatriceIndirizzi } from '../apiCore'
import { DRAWER_WIDTH } from '../constants'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import DrawerTitle from './DrawerTitle.vue'
import DrawerFooter from './DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const indirizzo = useIndirizzoSoggettoForm()

const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: String, default: null },
  tipoSoggettoDettaglioId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

// Lista indirizzi esistenti
const indirizziList = ref([])
const listLoading = ref(false)
const matriceCompleta = ref([])

// Modalita' form: null = lista, 'new' = aggiungi, 'replace' = cambia
const formMode = ref(null)
// ID dell'indirizzo soggetto da sostituire (in mode 'replace')
const replaceId = ref(null)
const replaceLabel = ref('')

async function loadIndirizzi() {
  if (!props.soggettoId) return
  listLoading.value = true
  try {
    const res = await listSoggettoIndirizzi(props.soggettoId)
    indirizziList.value = res.data.data.results || res.data.data
  } catch {
    indirizziList.value = []
  } finally {
    listLoading.value = false
  }
}

async function loadMatrice() {
  if (!props.tipoSoggettoDettaglioId) return
  try {
    const res = await lookupMatriceIndirizzi(props.tipoSoggettoDettaglioId)
    matriceCompleta.value = res.data.data.results
  } catch {
    matriceCompleta.value = []
  }
}

// Tipi gia' associati (per filtrare in aggiungi)
const tipiEsistenti = computed(() =>
  new Set(indirizziList.value.map(i => i.tipo_indirizzo_codice))
)

// Matrice filtrata: solo tipi non ancora associati (per aggiungi)
const matriceDisponibile = computed(() =>
  matriceCompleta.value.filter(m => !tipiEsistenti.value.has(m.codice))
)

// Tipi obbligatori mancanti
const tipiMancanti = computed(() =>
  matriceCompleta.value.filter(m => m.obbligatorio && !tipiEsistenti.value.has(m.codice))
)

// Carica dati quando drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  formMode.value = null
  replaceId.value = null
  indirizzo.reset()
  await Promise.all([loadIndirizzi(), loadMatrice()])
})

// === Azioni ===

function onStartNew() {
  formMode.value = 'new'
  indirizzo.reset()
  indirizzo.setMatrice(matriceDisponibile.value)
}

function onStartReplace(ind) {
  formMode.value = 'replace'
  replaceId.value = ind.id
  replaceLabel.value = ind.tipo_indirizzo_descrizione
  indirizzo.reset()
  // La matrice per il replace ha solo il tipo da sostituire
  indirizzo.setMatrice([{
    codice: ind.tipo_indirizzo_codice,
    descrizione: ind.tipo_indirizzo_descrizione,
    obbligatorio: true,
  }])
}

function onCancelForm() {
  formMode.value = null
  replaceId.value = null
  indirizzo.reset()
}

async function onSaveForm() {
  const payloads = indirizzo.toPayloadArray()
  if (!payloads.length) return

  let success = true

  if (formMode.value === 'replace') {
    // Sostituisci: un solo payload, usa PUT
    const result = await execute(
      () => replaceSoggettoIndirizzo(props.soggettoId, replaceId.value, payloads[0]),
      { successMessage: t('indirizzi.indirizzo_salvato') }
    )
    if (result === null) success = false
  } else {
    // Aggiungi: uno o piu' payload (auto-clone)
    for (const p of payloads) {
      const result = await execute(
        () => createSoggettoIndirizzo(props.soggettoId, p),
        { successMessage: t('indirizzi.indirizzo_creato') }
      )
      if (result === null) { success = false; break }
    }
  }

  if (success) {
    formMode.value = null
    replaceId.value = null
    indirizzo.reset()
    await loadIndirizzi()
    emit('saved')
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('soggetti.section_indirizzo')" icon="pi pi-map-marker" />
    </template>

    <div class="app-drawer-content">
      <!-- Loading -->
      <div v-if="listLoading" style="text-align: center; padding: 1rem;">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <!-- Lista indirizzi esistenti (sempre visibile) -->
      <template v-if="!listLoading">
        <div v-if="indirizziList.length === 0 && !formMode" class="indirizzi-empty">
          <i class="pi pi-map-marker" style="font-size: 1.5rem; opacity: 0.3;" />
          <p>{{ t('indirizzo_soggetto.nessun_indirizzo') }}</p>
        </div>

        <div v-else-if="indirizziList.length > 0" class="indirizzi-list">
          <div v-for="ind in indirizziList" :key="ind.id" class="indirizzo-card">
            <div class="indirizzo-card-content">
              <Tag :value="ind.tipo_indirizzo_descrizione" severity="info" />
              <span class="indirizzo-card-text">{{ ind.indirizzo_display }}</span>
            </div>
            <Button
              v-if="!formMode"
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              class="app-action-btn"
              :title="t('indirizzo_soggetto.cambia_indirizzo')"
              @click="onStartReplace(ind)"
            />
          </div>
        </div>

        <!-- Warning tipi mancanti -->
        <div v-if="tipiMancanti.length > 0 && !formMode" class="indirizzi-warning">
          <i class="pi pi-exclamation-triangle" />
          {{ t('indirizzo_soggetto.tipi_mancanti', { tipi: tipiMancanti.map(t => t.descrizione).join(', ') }) }}
        </div>

        <!-- Pulsante aggiungi (solo se ci sono tipi disponibili) -->
        <div v-if="!formMode && matriceDisponibile.length > 0" style="margin-top: 0.5rem;">
          <Button
            :label="t('indirizzo_soggetto.aggiungi_indirizzo')"
            icon="pi pi-plus"
            text
            size="small"
            class="app-action-btn"
            @click="onStartNew"
          />
        </div>
      </template>

      <!-- Form (aggiungi o cambia) -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formMode === 'replace'
            ? t('indirizzo_soggetto.cambia_indirizzo') + ': ' + replaceLabel
            : t('indirizzo_soggetto.nuovo_indirizzo')
          }}</h4>
        </div>
        <IndirizzoSoggettoForm
          :form="indirizzo.form"
          :is-libera="indirizzo.isLibera.value"
          @update:is-libera="v => indirizzo.isLibera.value = v"
          :tipi-stato="indirizzo.tipiStato.value"
          :toponomastica-lookup="indirizzo.toponomasticaLookup"
          :stati-lookup="indirizzo.statiLookup"
          :cap-options="indirizzo.capOptions.value"
          :loading-cap="indirizzo.loadingCap.value"
          :auto-clone="indirizzo.autoClone.value"
          @update:auto-clone="v => indirizzo.autoClone.value = v"
          @switch-tipo="indirizzo.switchTipo"
          :indirizzo-warnings="indirizzo.indirizzoWarnings.value"
          :disabled="false"
        />

        <DrawerFooter
          :loading="loading"
          :disabled="!indirizzo.canSave.value"
          @save="onSaveForm"
          @cancel="onCancelForm"
        />
      </template>
    </div>
  </Drawer>
</template>

<style scoped>
.indirizzi-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.indirizzo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-sm, 4px);
  padding: 0.5rem 0.75rem;
}

.indirizzo-card-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.indirizzo-card-text {
  font-size: 0.85rem;
  color: var(--p-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.indirizzi-empty {
  text-align: center;
  padding: 1.5rem;
  color: var(--p-text-muted-color);
}

.indirizzi-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-top: 0.5rem;
  background: var(--p-yellow-50);
  border: 1px solid var(--p-yellow-200);
  border-radius: var(--p-border-radius-sm, 4px);
  font-size: 0.8rem;
  color: var(--p-yellow-700);
}

.app-drawer-section {
  margin-top: 1rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--app-border-color, #e0e0e0);
}
.app-drawer-section h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--app-text-secondary, #666);
}
</style>
