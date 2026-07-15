<script setup>
// Scopo: Pannello "Passaggi" (genealogia/lineage) del documento vendite —
// building block condiviso dai drawer documento (preventivi, offerte, ordini,
// contratti, ddt, resi + drawer leggero commessa). Rende, dal GET
// {base}/{id}/passaggi/: pratica collegata (numero cliccabile ->
// PraticaDrawer), frontiera (documento piu' prossimo in esecuzione) e la
// catena reale dei transiti in ENTRAMBE le direzioni (Origine = indietro,
// Destinazioni = avanti) come timeline indentata per livello. L'arco R
// (is_ramo_inverso, DDT->Reso) e' reso come "ramo di ritorno" attenuato; il
// ruolo ROOT/COLLEGATO (commesse_sorgenti) e' mostrato in entrambe le
// direzioni. Le tappe con drawer di dettaglio sono cliccabili e aprono il
// documento impilato (LineageDocumentoDrawerHost).
//
// Lazy per costruzione: PrimeVue Panel toggleable chiuso di default, fetch a
// OGNI expand (freshness: il pannello puo' restare montato tra aperture del
// drawer padre — mai catena stantia). `start-open` per il drawer commessa
// (la genealogia e' il contenuto principale, carica al mount).
// Root `app-escape`: nei drawer post-DRAFT il contenuto e' .app-readonly ma
// la consultazione/navigazione della genealogia e' legittima (memoria
// feedback_app_escape_pannelli_processo).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { getPassaggi } from './lineageApi'
import LineageDocumentoDrawerHost from './LineageDocumentoDrawerHost.vue'
import { LINEAGE_DRAWER_TIPI } from './lineageDrawers'
import { lineageTipoLabel } from './lineageLabels'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'
import { faseDocumentoSeverity } from '../../../core/utils/severity'
import PraticaDrawer from '../../../pratiche/components/PraticaDrawer.vue'

const props = defineProps({
  // Path lista API del dominio (es. '/vendite/ordini').
  basePath: { type: String, required: true },
  // Pk di dominio del documento (null in CREATE: i consumer non montano).
  docId: { type: Number, default: null },
  // Apre il pannello di default e carica al mount (drawer commessa Fase C:
  // la genealogia È il contenuto principale, non una sezione secondaria).
  startOpen: { type: Boolean, default: false },
})

// `loaded`: emette il payload passaggi appena caricato (nodo + pratica +
// frontiera + catene) — consumato dal drawer commessa per l'header di testata
// senza una seconda fetch.
const emit = defineEmits(['loaded'])

const { t, te } = useI18n()
const { execute, loading } = useApiHandler()
const { tag, isCurrent, invalidate } = useFetchVersion()

const collapsed = ref(!props.startOpen)
const loaded = ref(false)
const data = ref(null)

// Scopo: Carica i passaggi. useApiHandler gestisce errori/toast (standard
// componenti dominio); il token useFetchVersion scarta risposte stantie sui
// cambi rapidi di documento. Su errore `loaded` resta false: il corpo non
// mostra mai un "vuoto" positivo su dati mai arrivati.
async function load() {
  if (!props.docId) return
  const token = tag()
  const result = await execute(() => getPassaggi(props.basePath, props.docId))
  if (!isCurrent(token) || result === null) return
  data.value = result
  loaded.value = true
  emit('loaded', data.value)
}

// Cambio documento: invalida e ricarica solo se il pannello e' aperto
// (altrimenti la fetch riparte al prossimo expand).
watch(() => props.docId, (id) => {
  invalidate()
  data.value = null
  loaded.value = false
  if (!collapsed.value && id) load()
}, { immediate: true })

// Ogni expand -> fetch (non solo il primo): il pannello resta montato tra
// aperture del drawer padre e la catena puo' cambiare (evasione, push, reso).
watch(collapsed, (val) => {
  if (!val && !loading.value) load()
})

const pratica = computed(() => data.value?.pratica ?? null)
const frontiera = computed(() => data.value?.frontiera ?? null)

// Scopo: Normalizza un arco del traversal nella tappa da mostrare: in avanti
// il nodo TO (destinazione), in indietro il nodo FROM (origine).
function passaggioToRow(p, lato) {
  const from = lato === 'from'
  return {
    key: `${lato}-${p.ordine}`,
    livello: p.livello,
    tipoCodice: from ? p.from_tipo_codice : p.to_tipo_codice,
    codice: from ? p.from_codice : p.to_codice,
    docId: from ? p.from_doc_id : p.to_doc_id,
    stato: from ? p.from_stato_codice_interno : p.to_stato_codice_interno,
    fase: from ? p.from_fase : p.to_fase,
    ramoInverso: p.is_ramo_inverso,
    ruolo: p.ruolo,
  }
}

// Le due sezioni della timeline, stessa resa (simmetria: ruolo ROOT/COLLEGATO
// e "ramo di ritorno" compaiono in entrambe le direzioni — gli archi B/E/F
// portano il ruolo anche in avanti, l'arco R e' inverso anche risalendo).
const sezioni = computed(() => [
  {
    key: 'origine',
    titolo: t('lineage.origine'),
    vuoto: t('lineage.nessuna_origine'),
    icona: 'pi-arrow-left',
    rows: (data.value?.indietro ?? []).map((p) => passaggioToRow(p, 'from')),
  },
  {
    key: 'destinazioni',
    titolo: t('lineage.destinazioni'),
    vuoto: t('lineage.nessun_transito'),
    icona: 'pi-arrow-right',
    rows: (data.value?.avanti ?? []).map((p) => passaggioToRow(p, 'to')),
  },
])

function tipoLabel(codice) {
  return lineageTipoLabel(t, te, codice)
}

// Apribile = la tappa ha un drawer di dettaglio (documenti + commessa) e l'id
// numerico risolto dal BE (Fattura: nodo terminale senza drawer; id null =
// fuori scope RLS -> tappa consultiva, non apribile).
function isApribile(row) {
  return row.docId != null && LINEAGE_DRAWER_TIPI.includes(row.tipoCodice)
}

// Scopo: Apre il drawer di DETTAGLIO del documento della tappa (impilato,
// come il link pratica), via l'host cross-dominio. Uniforma il comportamento
// dei link documento a quello del link pratica (deciso con Tid 2026-07-15).
const docDrawerVisible = ref(false)
const docDrawerTipo = ref(null)
const docDrawerId = ref(null)
function apriDocumento(row) {
  if (!isApribile(row)) return
  docDrawerTipo.value = row.tipoCodice
  docDrawerId.value = row.docId
  docDrawerVisible.value = true
}

// Pratica collegata: apertura in drawer (riuso PraticaDrawer pratiche).
const praticaDrawerVisible = ref(false)
</script>

<template>
  <div class="app-escape">
    <Panel v-model:collapsed="collapsed" toggleable class="lineage-panel">
      <template #header>
        <span class="lineage-panel-title">{{ t('lineage.titolo') }}</span>
      </template>

      <ProgressBar v-if="loading" mode="indeterminate" style="height: 4px" />

      <template v-if="loaded && data">
        <!-- Pratica collegata (1:1 di design, conteggio difensivo n_pratiche) -->
        <div class="lineage-row">
          <span class="lineage-label">{{ t('lineage.pratica') }}</span>
          <template v-if="pratica">
            <Button
              link
              class="lineage-link"
              :label="pratica.pratica_numero"
              @click="praticaDrawerVisible = true" />
            <span v-if="pratica.n_pratiche > 1" class="lineage-muted">
              {{ t('lineage.altre_pratiche', { n: pratica.n_pratiche - 1 }) }}
            </span>
          </template>
          <span v-else class="lineage-muted">—</span>
        </div>

        <!-- Frontiera: documento piu' prossimo in esecuzione (G-6/G-9/G-10) -->
        <div class="lineage-row">
          <span class="lineage-label">{{ t('lineage.frontiera') }}</span>
          <template v-if="frontiera">
            <Tag :value="tipoLabel(frontiera.tipo_codice)" severity="secondary" />
            <span class="lineage-codice">{{ frontiera.codice }}</span>
            <Tag
              :value="frontiera.stato_codice_interno ?? frontiera.fase"
              :severity="faseDocumentoSeverity(frontiera.fase)" />
            <span v-if="frontiera.n_discendenti_attivi > 1" class="lineage-muted">
              {{ t('lineage.altre_attive', { n: frontiera.n_discendenti_attivi - 1 }) }}
            </span>
          </template>
          <span v-else class="lineage-muted">{{ t('lineage.nessun_transito') }}</span>
        </div>

        <!-- Timeline nelle due direzioni (Origine = indietro, Destinazioni =
             avanti), stessa resa per tappa: icona (↩ per il ramo inverso),
             Tag tipo, codice cliccabile se apribile, Tag stato/fase, ruolo
             ROOT/COLLEGATO, etichetta ramo di ritorno. -->
        <div v-for="sezione in sezioni" :key="sezione.key" class="lineage-section">
          <span class="lineage-section-title">{{ sezione.titolo }}</span>
          <div v-if="!sezione.rows.length" class="lineage-muted">
            {{ sezione.vuoto }}
          </div>
          <div
            v-for="row in sezione.rows"
            :key="row.key"
            class="lineage-step"
            :class="{ 'lineage-step-inverso': row.ramoInverso }"
            :style="{ paddingLeft: `${(row.livello - 1) * 1.25}rem` }">
            <i :class="row.ramoInverso ? 'pi pi-replay' : `pi ${sezione.icona}`" class="lineage-step-icon" />
            <Tag :value="tipoLabel(row.tipoCodice)" severity="secondary" />
            <Button
              v-if="isApribile(row)"
              link
              class="lineage-link"
              :label="row.codice"
              v-tooltip.top="t('lineage.apri_documento')"
              @click="apriDocumento(row)" />
            <span v-else class="lineage-codice">{{ row.codice ?? '—' }}</span>
            <Tag
              v-if="row.stato || row.fase"
              :value="row.stato ?? row.fase"
              :severity="faseDocumentoSeverity(row.fase)" />
            <span v-if="row.ruolo" class="lineage-muted">{{ row.ruolo }}</span>
            <span v-if="row.ramoInverso" class="lineage-muted">
              {{ t('lineage.ramo_inverso') }}
            </span>
          </div>
        </div>
      </template>
    </Panel>

    <PraticaDrawer
      v-if="pratica"
      v-model:visible="praticaDrawerVisible"
      mode="edit"
      :pratica-id="pratica.pratica_id" />

    <!-- Host cross-dominio: apre il drawer di dettaglio del documento della
         tappa cliccata (impilato, come il link pratica). -->
    <LineageDocumentoDrawerHost
      v-model:visible="docDrawerVisible"
      :tipo-codice="docDrawerTipo"
      :doc-id="docDrawerId" />
  </div>
</template>

<style scoped>
.lineage-panel-title {
  font-weight: 600;
  color: var(--app-icon-color);
}

/* Freccia di espansione (toggle) verde come il titolo, coerente con i titoli
   di area dell'app (--app-icon-color = primario verde). */
.lineage-panel :deep(.p-panel-toggle-button) {
  color: var(--app-icon-color);
}

.lineage-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  flex-wrap: wrap;
}

.lineage-label {
  min-width: 7.5rem;
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.lineage-section {
  margin-top: 0.75rem;
}

.lineage-section-title {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--app-text-muted);
  margin-bottom: 0.25rem;
}

.lineage-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.15rem 0;
  flex-wrap: wrap;
}

.lineage-step-icon {
  font-size: 0.8rem;
  color: var(--app-text-muted);
}

.lineage-step-inverso {
  opacity: 0.75;
}

.lineage-codice {
  font-weight: 600;
}

.lineage-link {
  padding: 0;
  font-weight: 600;
}

.lineage-muted {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}
</style>
