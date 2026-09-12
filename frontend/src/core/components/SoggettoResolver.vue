<script setup>
// Scopo: Sotto-drawer universale "Cerca o Crea Soggetto".
// Data-driven: chiama config-resolver per tipo ruolo, adatta ricerca.
// Creazione soggetto delegata a SoggettoDrawer (zero duplicazione).
// Riusabile per operatori, clienti, fornitori, qualsiasi ruolo.
import { ref, watch, computed, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../constants'
import { listSoggetti, getConfigResolver, listSoggettoContatti } from '../../anagrafiche/api/anagrafiche'
import SoggettoDrawer from '../../anagrafiche/components/SoggettoDrawer.vue'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import SoggettoMessageBanner from './SoggettoMessageBanner.vue'
import Button from 'primevue/button'
import { useDrawerContentReady } from '../composables/useDrawerContentReady'



const { t } = useI18n()

const props = defineProps({
  visible: Boolean,
  tipoRuoloCodice: { type: String, default: '' }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'soggetto-selezionato', 'soggetto-creato', 'annullato'])

const selectedSoggetto = ref(null)
const configResolver = ref(null)
const configLoading = ref(false)

// Sotto-drawer creazione soggetto (delega a SoggettoDrawer)
const creaDrawerVisible = ref(false)

// Ricerca soggetti — risultati resi come lista INLINE nel drawer (no overlay):
// un AutoComplete flottante dentro un Drawer PrimeVue confligge col focus-trap
// e il pannello si chiude al primo movimento del mouse. La lista inline non si
// chiude mai e resta selezionabile.
const searchQuery = ref('')
const suggestions = ref([])
const searchLoading = ref(false)
const searched = ref(false)
let debounceTimer = null

// Scopo: lunghezza minima query (data-driven dal config-resolver, default 3).
const minSearchLength = computed(() => configResolver.value?.min_search_length ?? 3)

// Scopo: ricerca debounced su input testo; popola `suggestions` per la lista inline.
function onSearchInput() {
  clearTimeout(debounceTimer)
  const query = searchQuery.value
  if (!query || query.length < minSearchLength.value) {
    suggestions.value = []
    searched.value = false
    return
  }
  searchLoading.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const res = await listSoggetti({ search: query, limit: 10 })
      const results = res.data?.data?.results || []
      const nature = configResolver.value?.nature_ammesse || []
      const ruoloCodice = props.tipoRuoloCodice
      // Marca soggetti con natura bloccata o ruolo duplicato (decorazione UX)
      suggestions.value = results.map(s => {
        const ruoli = s.ruoli || []
        const naturaOk = !nature.length || nature.includes(s.natura_soggetto)
        const ruoloTrovato = ruoli.find(r => r.codice === ruoloCodice)
        return { ...s, _naturaBloccata: !naturaOk, _ruoloDuplicato: !!ruoloTrovato, _ruoloDescrizione: ruoloTrovato?.descrizione }
      })
    } catch {
      suggestions.value = []
    } finally {
      searchLoading.value = false
      searched.value = true
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
// Default tipo soggetto (pre-seleziona nel SoggettoDrawer):
// 1) backend risolve via config.parameters DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>
// 2) fallback: primo tipo ammesso (se backend ritorna null)
const tipoDefaultId = computed(() => {
  const dettagli = configResolver.value?.tipi_soggetto_dettaglio
  if (!dettagli || !dettagli.length) return null
  return configResolver.value?.default_tipo_soggetto_dettaglio_id ?? dettagli[0].id
})

// Carica config resolver all'apertura
watch(() => props.visible, async (val) => {
  if (!val) return
  selectedSoggetto.value = null
  searchQuery.value = ''
  suggestions.value = []
  searched.value = false

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

// Scopo: selezione di una riga della lista inline. Natura bloccata = non
// selezionabile; ruolo duplicato = solo avviso (lo stesso soggetto puo' avere
// piu' istanze dello stesso ruolo).
function onPick(s) {
  if (!s || s._naturaBloccata) return
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

</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="t('resolver.action_search')"
        :title="t('anagrafiche.soggetti.soggetto')"
        icon="pi pi-search"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content">
      <div class="form-field mb-3">
        <label>{{ t('resolver.search_label') }}</label>
        <span class="p-input-icon-right resolver-search">
          <InputText
            v-model="searchQuery"
            :placeholder="t('resolver.search_placeholder')"
            class="w-full"
            autofocus
            @input="onSearchInput"
          />
          <i v-if="searchLoading || configLoading" class="pi pi-spin pi-spinner resolver-search-icon" />
        </span>

        <!-- Risultati INLINE: nessun overlay, l'elenco resta aperto e selezionabile -->
        <ul v-if="suggestions.length" class="resolver-results" role="listbox">
          <li
            v-for="option in suggestions"
            :key="option.id"
            class="resolver-suggestion"
            :class="{
              'resolver-blocked': option._naturaBloccata,
              'resolver-picked': selectedSoggetto && selectedSoggetto.id === option.id
            }"
            role="option"
            :aria-selected="selectedSoggetto && selectedSoggetto.id === option.id"
            @click="onPick(option)"
          >
            <div class="resolver-suggestion-name">
              <strong>{{ option.ragione_sociale_completa }}</strong>
              <span class="resolver-suggestion-tipo">{{ option.tipo_descrizione }}</span>
            </div>
            <div class="resolver-suggestion-detail">
              <span v-if="option.codice_fiscale">CF: {{ option.codice_fiscale }}</span>
              <span v-if="option.partita_iva" class="ml-2">P.IVA: {{ option.partita_iva }}</span>
            </div>
            <div v-if="option._ruoloDuplicato" class="resolver-warning">
              <i :class="MANAGE_ICONS.ERRORE" />
              {{ t('resolver.already_role', { ruolo: option._ruoloDescrizione || tipoRuoloCodice }) }}
            </div>
            <div v-else-if="option._naturaBloccata" class="resolver-warning">
              <i class="pi pi-ban" />
              {{ t('resolver.natura_blocked') }}
            </div>
          </li>
        </ul>
        <small
          v-else-if="searched && !searchLoading && searchQuery.length >= minSearchLength"
          class="resolver-empty"
        >
          {{ t('resolver.no_results') }}
        </small>
      </div>

      <!-- Soggetto selezionato -->
      <div v-if="selectedSoggetto" class="resolver-selected mb-3">
        <SoggettoMessageBanner
          :ragione-sociale="selectedSoggetto.ragione_sociale_completa"
          :id-fiscale="selectedSoggetto.codice_fiscale || selectedSoggetto.partita_iva"
        />
        <div class="flex justify-end gap-2 mt-2">
          <Button :label="t('resolver.confirm_selection')" :icon="MANAGE_ICONS.CONFIRM"
            @click="confermaSelezionato" />
        </div>
      </div>

      <!-- Link per creazione nuovo -->
      <div class="resolver-create-link mt-4">
        <Button :label="t('resolver.create_new')" :icon="MANAGE_ICONS.ADD"
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
/* Campo ricerca: input full-width con spinner a destra */
.resolver-search {
  position: relative;
  display: block;
}
.resolver-search-icon {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--app-text-muted);
}

/* Lista risultati inline (sostituisce l'overlay AutoComplete) */
.resolver-results {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid var(--app-drawer-section-border);
  border-radius: 6px;
}

.resolver-suggestion {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid var(--app-drawer-section-border);
}
.resolver-suggestion:last-child {
  border-bottom: none;
}
.resolver-suggestion:hover {
  background: var(--app-card-hover-bg);
}
.resolver-picked {
  background: var(--app-card-hover-bg);
  box-shadow: inset 3px 0 0 0 var(--p-primary-color);
}
.resolver-empty {
  display: block;
  margin-top: 0.5rem;
  color: var(--app-text-muted);
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
.resolver-blocked:hover {
  background: transparent;
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
