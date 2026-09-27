<script setup>
// Scopo: Home operatore pratiche (launcher, V11): due gesti affiancati.
// - "Comincia": tile data-driven da pratiche.tipi_prestazione raggruppate per
//   categoria → deep-link alla dashboard col filtro tipo attivo.
// - "Continua": coda lavoro riusata (PraticheCodaLavoro, BB presentazionale)
//   → deep-link alla dashboard con pratica selezionata + flusso evidenziato.
// La home e' un launcher puro: nessuna azione di business qui (unica eccezione
// "prendi in carico", azione della coda condivisa via usePrendiInCarico). Il
// lavoro vero vive nella dashboard, unico wiring di percorso/drawer.
// Contratto deep-link (query param, consumati da PraticheDashboard in
// onActivated — KeepAlive-aware): tipo_prestazione_id (0 = azzera la lente),
// pratica_id, flusso_id. Meccanismo UNICO per tile, coda e "Tutte le pratiche".
// Brief: docs/it/dev/work-in-progress/brief-fe-home-operatore-launcher.md
import { computed, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useLookupCodici } from '../../core/composables/useLookupCodici'
import { MANAGE_ICONS, READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useAuthStore } from '../../stores/auth'
import { usePraticheStore } from '../stores/pratiche'
import { usePrendiInCarico } from '../composables/usePrendiInCarico'
import PraticheCodaLavoro from '../components/PraticheCodaLavoro.vue'

const { t } = useI18n()
const router = useRouter()
const store = usePraticheStore()
const auth = useAuthStore()
const { isReadonly, isBlocked } = useReadonlyMode(READONLY_DOMAINS.PRATICHE)

// Solo l'operatore con emittente 1-a-1 ha una coda lavoro: admin
// globale/portali → niente colonna Continua.
const isOperatore = computed(() => !!auth.emittenteCorrente?.id)

// Colonne visibili: Comincia richiede il permesso di creare (non readonly),
// Continua richiede una coda (operatore). Se entrambe mancano, la home mostra
// un empty-state esplicito — mai una pagina bianca; il link "Tutte le
// pratiche" sta nella testata, sempre raggiungibile.
const showComincia = computed(() => !isReadonly.value)
const showContinua = computed(() => isOperatore.value)
const soloConsultazione = computed(() => !showComincia.value && !showContinua.value)

// Tile "Comincia": tipi prestazione attivi non obsoleti (selezione per il
// nuovo). STESSA entry di cache della LookupSelect del PraticaDrawer, per
// costruzione (`useLookupCodici`, stesso `rel` + stesso insieme): tra home e
// drawer non si paga alcun round-trip aggiuntivo.
const { items: tipiItems, loading: tipiLoading } = useLookupCodici(
  'pratiche.tipi_prestazione',
  { includiObsoleti: false, immediate: true },
)

// Icona per categoria: mapping FE (decisione brief §2.5 — l'icona e'
// presentazione, non dato), valori dalle costanti centralizzate (NAV_ICONS, MANAGE_ICONS)
// (mai literal 'pi pi-*': il retheming resta un cambio in un punto solo).
const CATEGORIA_ICONS = {
  COMMERCIALE: MANAGE_ICONS.COMMERCIALE,
  VENDITE: NAV_ICONS.VENDITE,
}
function tileIcon(categoria) {
  return CATEGORIA_ICONS[categoria] || NAV_ICONS.GESTIONE_PRATICHE
}

// Raggruppamento per categoria (anti "muro di bottoni"): categorie con nome in
// ordine alfabetico, i tipi senza categoria accodati sotto "Altre". Le voci
// arrivano gia' ordinate per descrizione dal lookup.
const gruppi = computed(() => {
  const perCategoria = new Map()
  for (const tipo of tipiItems.value) {
    const categoria = tipo.categoria || ''
    if (!perCategoria.has(categoria)) perCategoria.set(categoria, [])
    perCategoria.get(categoria).push(tipo)
  }
  const senzaCategoria = perCategoria.get('')
  perCategoria.delete('')
  const out = [...perCategoria.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([categoria, tipi]) => ({ key: categoria, label: categoria, tipi }))
  if (senzaCategoria) {
    out.push({ key: 'altre', label: t('pratiche.home_categoria_altre'), tipi: senzaCategoria })
  }
  return out
})

// Tile = contesto, non verbo (brief §2.3): apre la dashboard filtrata sul
// tipo; e' il "Nuova pratica" della dashboard a partire gia' su quel tipo.
function onTileClick(tipo) {
  router.push({ name: 'pratiche-gestione', query: { tipo_prestazione_id: tipo.id } })
}

// "Tutte le pratiche": stesso meccanismo deep-link delle tile, col valore
// sentinella 0 = azzera la lente tipo (gli altri filtri restano come
// l'operatore li ha lasciati). Niente mutazioni dirette dello store da qui.
function goTutteLePratiche() {
  router.push({ name: 'pratiche-gestione', query: { tipo_prestazione_id: 0 } })
}

// --- Continua: coda lavoro (fetch dallo store, il BB e' presentazionale) ---
// onActivated e non onMounted: sotto KeepAlive (AppLayout) la home viene messa
// in cache — al rientro la coda va rinfrescata (scatta anche al primo mount).
onActivated(() => { store.loadCodaLavoro() })

function onCodaSelectFlusso(item) {
  router.push({
    name: 'pratiche-gestione',
    query: { pratica_id: item.pratica_id, flusso_id: item.flusso_id },
  })
}

const { prendiInCarico: onPrendiInCarico } = usePrendiInCarico()
</script>

<template>
  <div class="app-page pratiche-home">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Testata: il link alla dashboard-lista e' sempre raggiungibile,
           qualunque combinazione di gate nasconda le colonne. -->
      <header class="home-head">
        <h1 class="home-head-title">
          <i :class="NAV_ICONS.PRATICHE" />
          {{ t('pratiche.home_titolo') }}
        </h1>
        <Button
          :label="t('pratiche.home_tutte_le_pratiche')"
          :icon="NAV_ICONS.GESTIONE_PRATICHE"
          text
          @click="goTutteLePratiche"
        />
      </header>

      <!-- Nessun gesto disponibile (readonly + niente coda): empty-state
           esplicito, mai pagina bianca. -->
      <div v-if="soloConsultazione" class="home-empty home-empty-page">
        {{ t('pratiche.home_solo_consultazione') }}
      </div>

      <div v-else class="home-cols">
        <section v-if="showComincia" class="home-col">
          <header class="home-col-head">
            <i :class="MANAGE_ICONS.ADD" />
            <div>
              <h2>{{ t('pratiche.home_comincia_titolo') }}</h2>
              <p>{{ t('pratiche.home_comincia_sottotitolo') }}</p>
            </div>
          </header>

          <div v-if="tipiLoading" class="home-loading">
            <i :class="STATUS_ICONS.CARICAMENTO" />
          </div>
          <div v-else-if="!gruppi.length" class="home-empty">
            {{ t('pratiche.home_nessun_tipo') }}
          </div>
          <div v-else class="home-gruppi">
            <div v-for="gruppo in gruppi" :key="gruppo.key" class="home-gruppo">
              <div class="home-gruppo-label">{{ gruppo.label }}</div>
              <div class="home-tiles">
                <button
                  v-for="tipo in gruppo.tipi"
                  :key="tipo.id"
                  type="button"
                  class="home-tile"
                  @click="onTileClick(tipo)"
                >
                  <i :class="tileIcon(tipo.categoria)" />
                  <span>{{ tipo.descrizione }}</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-if="showContinua" class="home-col">
          <header class="home-col-head">
            <i :class="NAV_ICONS.PRATICHE" />
            <div>
              <h2>{{ t('pratiche.home_continua_titolo') }}</h2>
              <p>{{ t('pratiche.home_continua_sottotitolo') }}</p>
            </div>
          </header>

          <div class="home-coda">
            <PraticheCodaLavoro
              :items="store.codaLavoro"
              :loading="store.codaLoading"
              @select-flusso="onCodaSelectFlusso"
              @prendi-in-carico="onPrendiInCarico"
            />
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pratiche-home {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.home-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem 0;
  flex: 0 0 auto;
}

.home-head-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.15rem;
}
.home-head-title > i { color: var(--app-icon-color); }

.home-cols {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  gap: 1rem;
  padding: 1rem;
}

.home-col {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--app-border-color);
  border-radius: 8px;
  background: var(--app-card-bg);
  overflow: hidden;
}

.home-col-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  border-bottom: 1px solid var(--app-border-color);
  flex: 0 0 auto;
}
.home-col-head > i {
  font-size: 1.4rem;
  color: var(--app-icon-color);
}
.home-col-head h2 {
  margin: 0;
  font-size: 1.05rem;
}
.home-col-head p {
  margin: 0;
  font-size: 0.8rem;
  color: var(--app-text-muted);
}

.home-loading,
.home-empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--app-text-muted);
}

.home-empty-page {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.home-gruppi {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem;
}

.home-gruppo + .home-gruppo {
  margin-top: 1.25rem;
}

.home-gruppo-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--app-text-muted);
  margin-bottom: 0.5rem;
}

.home-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.6rem;
}

.home-tile {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid var(--app-border-color);
  border-radius: 8px;
  background: var(--app-content-bg);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.home-tile:hover {
  background: var(--app-hover-bg);
  border-color: var(--app-icon-color);
}
.home-tile > i {
  font-size: 1.15rem;
  color: var(--app-icon-color);
  flex: 0 0 auto;
}
.home-tile > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-coda {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 0.5rem;
}

/* Tablet/mobile: colonne impilate, scrolla la pagina */
@media (max-width: 1023.98px) {
  .pratiche-home {
    overflow-y: auto;
  }
  .home-cols {
    flex-direction: column;
  }
  .home-col {
    overflow: visible;
  }
  .home-gruppi,
  .home-coda {
    overflow-y: visible;
  }
}
</style>
