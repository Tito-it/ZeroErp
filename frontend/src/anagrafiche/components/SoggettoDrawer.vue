<script setup>
// Scopo: Drawer creazione/modifica soggetto PF/PG/ENTE.
// Compone i building block: SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm.
// Il payload unificato va al backend che scompone e crea in transazione.
// I trigger DEFERRED verificano al COMMIT (contatti, indirizzi, dati societari).

import { ref, watch, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSoggettiStore } from '../stores/soggetti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useSoggettoForm } from '../../core/composables/useSoggettoForm'
import { useContattoForm } from '../../core/composables/useContattoForm'
import { useIndirizzoSoggettoForm } from '../../core/composables/useIndirizzoSoggettoForm'
import { useDatiSocietariForm } from '../../core/composables/useDatiSocietariForm'
import { useLookup } from '../../core/composables/useLookup'
import { lookupFormeGiuridiche, lookupTipiRuoliPerNatura } from '../../core/apiCore'
import { lookupProvince, assignSoggettoRuolo } from '../api/anagrafiche'
import { DRAWER_WIDTH } from '../../core/constants'
import SoggettoForm from '../../core/components/SoggettoForm.vue'
import ContattoForm from '../../core/components/ContattoForm.vue'
import IndirizzoSoggettoForm from '../../core/components/IndirizzoSoggettoForm.vue'
import DatiSocietariForm from '../../core/components/DatiSocietariForm.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = useSoggettiStore()
const { execute, loading } = useApiHandler()

// Building block composables
const soggetto = useSoggettoForm()
const contatto = useContattoForm()
const indirizzo = useIndirizzoSoggettoForm()

// Lookup forme giuridiche (ricaricato al cambio tipo) — passato a useDatiSocietariForm
const formeGiuridicheLookup = ref([])
const datiSocietari = useDatiSocietariForm({ formeGiuridiche: formeGiuridicheLookup })
const provinceLookup = useLookup(() => lookupProvince())

// Ruoli (edit mode)
const ruoliAssegnati = ref([])
const ruoliDisponibili = ref([])
const nuovoRuoloId = ref(null)
const ruoloLoading = ref(false)

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  itemId: { type: String, default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const isEdit = computed(() => props.mode === 'edit')
const title = computed(() =>
  isEdit.value ? t('soggetti.modifica_soggetto') : t('soggetti.nuovo_soggetto')
)

// Carica forme giuridiche filtrate al cambio tipo soggetto.
// Versione per evitare race condition: se il tipo cambia durante il fetch,
// la risposta della richiesta precedente viene scartata.
let fgVersion = 0
watch(() => soggetto.form.tipo_soggetto_dettaglio_id, async (tipoId) => {
  if (!tipoId || !soggetto.showDatiSocietari.value) {
    formeGiuridicheLookup.value = []
    return
  }
  const v = ++fgVersion
  try {
    const res = await lookupFormeGiuridiche(tipoId)
    if (v === fgVersion) formeGiuridicheLookup.value = res.data.data.results
  } catch {
    if (v === fgVersion) formeGiuridicheLookup.value = []
  }
})

// Carica province quando servono dati societari
watch(() => soggetto.showDatiSocietari.value, (show) => {
  if (show && !provinceLookup.loaded.value) {
    provinceLookup.load()
  }
})

// Popola il drawer con i dati del soggetto in edit mode.
function populateFromDetail(data) {
  soggetto.form.tipo_soggetto_dettaglio_id = data.tipo_soggetto_dettaglio_id
  soggetto.form.cognome = data.cognome || ''
  soggetto.form.nome = data.nome || ''
  soggetto.form.ragione_sociale = data.ragione_sociale || ''
  soggetto.form.codice_fiscale = data.codice_fiscale || ''
  soggetto.form.partita_iva = data.partita_iva || ''
  soggetto.form.sesso = data.sesso || 'M'
  soggetto.form.data_nascita = data.data_nascita || null
  soggetto.form.comune_nascita_id = data.comune_nascita_id || null
  if (data.contatti?.length > 0) {
    contatto.populate(data.contatti[0])
  }
  if (data.dati_societari) {
    datiSocietari.populate(data.dati_societari)
  }
  // Ruoli
  ruoliAssegnati.value = data.ruoli || []
}

// Scopo: Carica i ruoli disponibili filtrati per natura e aggiorna la lista.
async function loadRuoliDisponibili(natura) {
  try {
    const res = await lookupTipiRuoliPerNatura(natura)
    ruoliDisponibili.value = res.data.data.results
  } catch {
    ruoliDisponibili.value = []
  }
}

// Scopo: Assegna ruolo al soggetto corrente.
async function onAssignRuolo() {
  if (!nuovoRuoloId.value || !props.itemId) return
  const selected = ruoliDisponibili.value.find(r => r.id === nuovoRuoloId.value)
  if (!selected) return
  ruoloLoading.value = true
  try {
    await assignSoggettoRuolo(props.itemId, { codice_ruolo: selected.codice })
    ruoliAssegnati.value.push({
      tipo_ruolo_id: selected.id,
      ruolo_codice: selected.codice,
      ruolo_descrizione: selected.descrizione,
    })
    nuovoRuoloId.value = null
  } finally {
    ruoloLoading.value = false
  }
}

// Carica dati quando il drawer si apre.
// Quando si chiude, invalida versioni async per scartare risposte in volo.
watch(() => props.visible, async (val) => {
  if (!val) { fgVersion++; return }

  if (isEdit.value && props.itemId) {
    try {
      const data = await store.fetchDetail(props.itemId)
      populateFromDetail(data)
      // Carica ruoli disponibili per la natura del soggetto
      await loadRuoliDisponibili(data.natura_soggetto)
    } catch {
      emit('update:visible', false)
      return
    }
  } else {
    soggetto.reset()
    contatto.reset()
    indirizzo.reset()
    datiSocietari.reset()
    ruoliAssegnati.value = []
    ruoliDisponibili.value = []
    nuovoRuoloId.value = null
  }

  // Carica lookup contatto (lazy, non blocca)
  contatto.tipiContatto.load()
})

// Scopo: Validazione aggregata di tutti i building block.
const canSave = computed(() => {
  if (isEdit.value) return true
  const sogValid = soggetto.validate().length === 0
  const conValid = contatto.validate().length === 0
  return sogValid && conValid
})

// Scopo: Salvataggio — costruisce payload unificato per il backend.
async function handleSave() {
  if (isEdit.value) {
    const payload = {}
    const f = soggetto.form
    if (soggetto.isPF.value) {
      payload.cognome = f.cognome
      payload.nome = f.nome
      payload.sesso = f.sesso
      payload.data_nascita = f.data_nascita
      payload.comune_nascita_id = f.comune_nascita_id
    } else {
      payload.ragione_sociale = f.ragione_sociale
    }
    payload.codice_fiscale = f.codice_fiscale
    payload.partita_iva = f.partita_iva

    const result = await execute(
      () => store.update(props.itemId, payload),
      { successMessage: t('soggetti.soggetto_salvato') }
    )
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
    }
  } else {
    const payload = {
      tipo_soggetto_dettaglio_id: soggetto.form.tipo_soggetto_dettaglio_id,
      cognome: soggetto.form.cognome,
      nome: soggetto.form.nome,
      ragione_sociale: soggetto.form.ragione_sociale,
      codice_fiscale: soggetto.form.codice_fiscale,
      partita_iva: soggetto.form.partita_iva,
      sesso: soggetto.form.sesso,
      data_nascita: soggetto.form.data_nascita,
      contatto: { ...contatto.form },
    }

    // Indirizzi (array con tutti quelli compilati)
    if (indirizzo.canSave.value) {
      payload.indirizzi = [indirizzo.toPayload()]
    }

    // Dati societari (solo se visibili)
    if (soggetto.showDatiSocietari.value) {
      payload.dati_societari = { ...datiSocietari.form }
    }

    const result = await execute(
      () => store.create(payload),
      { successMessage: t('soggetti.soggetto_creato') }
    )
    if (result !== null) {
      emit('saved')
      emit('update:visible', false)
    }
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :header="title"
  >
    <div class="app-drawer-content">
      <!-- Sezione: Dati soggetto -->
      <SoggettoForm
        :form="soggetto.form"
        :tipi-soggetto="soggetto.tipiSoggetto"
        :is-p-f="soggetto.isPF.value"
        :show-partita-iva="soggetto.showPartitaIva.value"
        :disabled="false"
      />

      <!-- Separatore: Contatto -->
      <div class="app-drawer-section">
        <h4>{{ t('soggetti.section_contatto') }}</h4>
      </div>
      <ContattoForm
        :form="contatto.form"
        :tipi-contatto="contatto.tipiContatto"
        :unita-organizzative="contatto.unitaOrganizzative"
        :show-u-o="false"
        :disabled="false"
      />

      <!-- Separatore: Indirizzo (solo in create mode) -->
      <template v-if="!isEdit">
        <div class="app-drawer-section">
          <h4>{{ t('soggetti.section_indirizzo') }}</h4>
        </div>
        <IndirizzoSoggettoForm
          :form="indirizzo.form"
          :is-libera="indirizzo.isLibera.value"
          @update:is-libera="v => indirizzo.isLibera.value = v"
          :tipi-indirizzo="soggetto.matriceIndirizzi.value"
          :toponomastica-lookup="indirizzo.toponomasticaLookup"
          :stati-lookup="indirizzo.statiLookup"
          :cap-options="indirizzo.capOptions.value"
          :loading-cap="indirizzo.loadingCap.value"
          :disabled="false"
        />
      </template>

      <!-- Sezione: Dati societari (condizionale) -->
      <template v-if="soggetto.showDatiSocietari.value">
        <div class="app-drawer-section">
          <h4>{{ t('soggetti.section_dati_societari') }}</h4>
        </div>
        <DatiSocietariForm
          :form="datiSocietari.form"
          :forme-giuridiche="formeGiuridicheLookup"
          :province-lookup="provinceLookup"
          :show-rea="datiSocietari.showRea.value"
          :require-rea="datiSocietari.requireRea.value"
          :show-capitale-sociale="datiSocietari.showCapitaleSociale.value"
          :require-capitale-sociale="datiSocietari.requireCapitaleSociale.value"
          :required="soggetto.requireDatiSocietari.value"
          :disabled="false"
        />
      </template>

      <!-- Sezione: Ruoli (solo edit mode) -->
      <template v-if="isEdit">
        <div class="app-drawer-section">
          <h4>{{ t('soggetti.section_ruoli') }}</h4>
        </div>
        <div class="form-grid">
          <!-- Ruoli assegnati -->
          <div v-if="ruoliAssegnati.length > 0" class="ruoli-tags">
            <Tag v-for="r in ruoliAssegnati" :key="r.tipo_ruolo_id"
                 :value="r.ruolo_descrizione" severity="info" />
          </div>
          <div v-else style="color: var(--app-text-secondary, #888); font-size: 0.85rem;">
            {{ t('soggetti.nessun_ruolo') }}
          </div>

          <!-- Aggiungi ruolo -->
          <div class="form-grid-2col" style="align-items: flex-end;">
            <div class="form-field">
              <label>{{ t('soggetti.aggiungi_ruolo') }}</label>
              <Select
                v-model="nuovoRuoloId"
                :options="ruoliDisponibili"
                option-label="descrizione"
                option-value="id"
                :placeholder="t('soggetti.select_ruolo')"
                class="w-full"
              />
            </div>
            <Button
              :label="t('common.save')"
              icon="pi pi-plus"
              :loading="ruoloLoading"
              :disabled="!nuovoRuoloId"
              @click="onAssignRuolo"
              size="small"
            />
          </div>
        </div>
      </template>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="emit('update:visible', false)"
      />
    </div>
  </Drawer>
</template>

<style scoped>
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
.ruoli-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
