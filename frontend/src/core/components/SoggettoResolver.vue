<script setup>
// Scopo: Sotto-drawer universale "Cerca o Crea Soggetto".
// Data-driven: chiama config-resolver per tipo ruolo, adatta ricerca.
// Creazione soggetto delegata a SoggettoDrawer (zero duplicazione).
// Riusabile per operatori, clienti, fornitori, qualsiasi ruolo.
import { ref, watch, computed, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { DRAWER_WIDTH } from '../constants'
import { listSoggetti, getConfigResolver, listSoggettoContatti } from '../../anagrafiche/api/anagrafiche'
import SoggettoDrawer from '../../anagrafiche/components/SoggettoDrawer.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import AutoComplete from 'primevue/autocomplete'
import SoggettoMessageBanner from './SoggettoMessageBanner.vue'
import Button from 'primevue/button'

const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  tipoRuoloCodice: { type: String, default: '' }
})

const emit = defineEmits(['update:visible', 'soggetto-selezionato', 'soggetto-creato', 'annullato'])

const selectedSoggetto = ref(null)
const configResolver = ref(null)
const configLoading = ref(false)

// Sotto-drawer creazione soggetto (delega a SoggettoDrawer)
const creaDrawerVisible = ref(false)

// Ricerca soggetti — implementazione diretta per compatibilita' PrimeVue AutoComplete
const searchQuery = ref('')
const suggestions = ref([])
const searchLoading = ref(false)
let debounceTimer = null

async function onSearch({ query }) {
  clearTimeout(debounceTimer)
  if (!query || query.length < 3) {
    suggestions.value = []
    return
  }
  searchLoading.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const res = await listSoggetti({ search: query, limit: 10 })
      const results = res.data?.data?.results || []
      const nature = configResolver.value?.nature_ammesse || []
      const ruoloCodice = props.tipoRuoloCodice
      // Normalizza ruoli (il DB ritorna JSONB che puo' arrivare come stringa)
      // Marca soggetti con natura bloccata o ruolo duplicato
      suggestions.value = results.map(s => {
        let ruoli = []
        if (Array.isArray(s.ruoli)) { ruoli = s.ruoli }
        else if (typeof s.ruoli === 'string') {
          try { ruoli = JSON.parse(s.ruoli) } catch { /* malformato, ignora */ }
        }
        const naturaOk = !nature.length || nature.includes(s.natura_soggetto)
        const ruoloTrovato = ruoli.find(r => r.codice === ruoloCodice)
        return { ...s, ruoli, _naturaBloccata: !naturaOk, _ruoloDuplicato: !!ruoloTrovato, _ruoloDescrizione: ruoloTrovato?.descrizione }
      })
    } catch {
      suggestions.value = []
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

onUnmounted(() => clearTimeout(debounceTimer))

// Tipi ammessi — usati per filtrare nel SoggettoDrawer
const tipiAmmessiIds = computed(() => {
  const dettagli = configResolver.value?.tipi_soggetto_dettaglio
  if (!dettagli || !dettagli.length) return null
  return dettagli.map(d => d.id)
})
// Default: primo tipo ammesso (pre-seleziona nel SoggettoDrawer)
const tipoDefaultId = computed(() => {
  const dettagli = configResolver.value?.tipi_soggetto_dettaglio
  if (!dettagli || !dettagli.length) return null
  const privato = dettagli.find(d => d.codice_interno === 'PR')
  return privato ? privato.id : dettagli[0].id
})

// Carica config resolver all'apertura
watch(() => props.visible, async (val) => {
  if (!val) return
  selectedSoggetto.value = null
  searchQuery.value = ''
  suggestions.value = []

  configLoading.value = true
  try {
    if (props.tipoRuoloCodice) {
      const res = await getConfigResolver(props.tipoRuoloCodice)
      configResolver.value = res.data.data
    } else {
      configResolver.value = null
    }
  } catch {
    configResolver.value = null
  } finally {
    configLoading.value = false
  }
})

function onSoggettoSelect(event) {
  const s = event.value
  if (!s || s._naturaBloccata) {
    selectedSoggetto.value = null
    return
  }
  // _ruoloDuplicato: avviso, non blocco — lo stesso soggetto puo' avere piu' istanze
  selectedSoggetto.value = s
}

async function confermaSelezionato() {
  if (!selectedSoggetto.value) return
  const s = selectedSoggetto.value
  // Cerca email dai contatti del soggetto (best-effort, non blocca)
  let email = null
  try {
    const res = await listSoggettoContatti(s.id)
    const contatti = res.data?.data?.results || []
    const conEmail = contatti.find(c => c.email)
    if (conEmail) email = conEmail.email
  } catch { /* ignora — email resta null */ }
  emit('soggetto-selezionato', {
    id: s.id,
    ragione_sociale: s.ragione_sociale_completa,
    cognome: s.cognome || null,
    nome: s.nome || null,
    cf: s.codice_fiscale,
    piva: s.partita_iva,
    email,
    ruoli: s.ruoli || [],
    tipo_soggetto_dettaglio_id: s.tipo_soggetto_dettaglio_id || null
  })
  emit('update:visible', false)
}

function passaACreazione() {
  creaDrawerVisible.value = true
}

// Callback da SoggettoDrawer: soggetto creato con successo
// nextTick per dare tempo a PrimeVue di chiudere il sotto-drawer prima del resolver
async function onSoggettoCreatoDaDrawer(data) {
  creaDrawerVisible.value = false
  await nextTick()
  emit('soggetto-creato', data)
  emit('update:visible', false)
}

function onClose() {
  emit('update:visible', false)
  emit('annullato')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="t('resolver.action_search')"
        :title="t('soggetti.soggetto')"
        icon="pi pi-search"
      />
    </template>

    <div class="app-drawer-content">
      <div class="form-field mb-3">
        <label>{{ t('resolver.search_label') }}</label>
        <AutoComplete
          v-model="searchQuery"
          :suggestions="suggestions"
          :loading="searchLoading || configLoading"
          :min-length="3"
          :placeholder="t('resolver.search_placeholder')"
          option-label="ragione_sociale_completa"
          :force-selection="false"
          append-to="self"
          :panel-style="{ width: '100%', minWidth: '400px' }"
          class="w-full"
          @complete="onSearch"
          @item-select="onSoggettoSelect"
        >
          <template #option="{ option }">
            <div class="resolver-suggestion" :class="{ 'resolver-blocked': option._naturaBloccata }">
              <div class="resolver-suggestion-name">
                <strong>{{ option.ragione_sociale_completa }}</strong>
                <span class="resolver-suggestion-tipo">{{ option.tipo_descrizione }}</span>
              </div>
              <div class="resolver-suggestion-detail">
                <span v-if="option.codice_fiscale">CF: {{ option.codice_fiscale }}</span>
                <span v-if="option.partita_iva" class="ml-2">P.IVA: {{ option.partita_iva }}</span>
              </div>
              <div v-if="option._ruoloDuplicato" class="resolver-warning">
                <i class="pi pi-exclamation-triangle" />
                {{ t('resolver.already_role', { ruolo: option._ruoloDescrizione || tipoRuoloCodice }) }}
              </div>
              <div v-else-if="option._naturaBloccata" class="resolver-warning">
                <i class="pi pi-ban" />
                {{ t('resolver.natura_blocked') }}
              </div>
            </div>
          </template>
        </AutoComplete>
      </div>

      <!-- Soggetto selezionato -->
      <div v-if="selectedSoggetto" class="resolver-selected mb-3">
        <SoggettoMessageBanner
          :ragione-sociale="selectedSoggetto.ragione_sociale_completa"
          :codice-fiscale="selectedSoggetto.codice_fiscale"
        />
        <div class="flex justify-end gap-2 mt-2">
          <Button :label="t('resolver.confirm_selection')" icon="pi pi-check"
            @click="confermaSelezionato" />
        </div>
      </div>

      <!-- Link per creazione nuovo -->
      <div class="resolver-create-link mt-4">
        <Button :label="t('resolver.create_new')" icon="pi pi-plus"
          text severity="primary" @click="passaACreazione" />
      </div>
    </div>

    <!-- Sotto-drawer: SoggettoDrawer standard (zero duplicazione) -->
    <SoggettoDrawer
      :visible="creaDrawerVisible"
      mode="create"
      :tipo-default-id="tipoDefaultId"
      :tipi-ammessi-ids="tipiAmmessiIds"
      @update:visible="v => creaDrawerVisible = v"
      @saved-with-data="onSoggettoCreatoDaDrawer"
    />
  </Drawer>
</template>

<style scoped>
/* Input ricerca: occupa tutta la larghezza disponibile */
:deep(.p-autocomplete-input) {
  width: 100%;
}

.resolver-suggestion {
  padding: 0.35rem 0;
}

.resolver-suggestion-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.resolver-suggestion-tipo {
  font-size: var(--app-font-size-sm);
  color: var(--p-text-muted-color);
}

.resolver-suggestion-detail {
  font-size: var(--app-font-size-sm);
  color: var(--p-text-muted-color);
  margin-top: 0.15rem;
}

.resolver-blocked {
  opacity: 0.5;
  cursor: not-allowed;
}

.resolver-warning {
  font-size: var(--app-font-size-sm);
  color: var(--p-orange-500);
  margin-top: 0.2rem;
}

.resolver-warning i {
  margin-right: 0.25rem;
}

.resolver-create-link {
  border-top: 1px solid var(--p-surface-200);
  padding-top: 1rem;
}
</style>
