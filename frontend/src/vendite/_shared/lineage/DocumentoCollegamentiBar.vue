<script setup>
// Scopo: Riga "collegamenti del documento" sotto la barra azioni dei drawer
// vendite (2026-07-25, decisione Tid). Chip tipizzati e cliccabili per la
// pratica collegata, l'ORIGINE e le DESTINAZIONI dirette: «Pratica PRT…» ·
// «Ordine» · «2 DDT» · «Reso». Sostituisce il pannello Passaggi sempre montato
// in coda a ogni drawer: la segnalazione sta in alto e a colpo d'occhio, il
// dettaglio (grafo completo) si apre da qui in dialog.
//
// PERCHE' chip tipizzati e non un badge numerico su un pulsante «Passaggi»:
// il badge dice QUANTI, non COSA — e le due segnalazioni servono a cose
// diverse (un DDT su un ordine avvisa che le righe non sono piu' tue; un reso
// su un DDT avvisa che le quantita' non significano piu' quello che leggi).
//
// REGOLA DI SVUOTAMENTO: la riga sparisce quando non c'e' NE' pratica NE'
// archi. Il test include la pratica di proposito: un documento nato in una
// pratica e non ancora sceso a valle non ha archi, e senza il chip pratica
// perderebbe l'unico accesso a quel link (che il pannello mostrava sempre).
//
// LIVELLO 1 SOLTANTO: su ordine→DDT→reso, l'ordine mostra «DDT», non anche
// «Reso» — il reso e' collegato al DDT, non all'ordine. La catena completa
// resta mestiere della dialog.
//
// Gli ANNULLATI non contano fra le destinazioni (`to_is_abortito`): «2 DDT»
// che ne include uno annullato e' un numero che non torna con quello che si
// vede aprendo i passaggi. A monte il filtro non si applica — un'origine
// annullata resta l'origine, ed e' giusto mostrarla.
import { computed, provide, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { NAV_ICONS } from '../../../core/navigation'
import PraticaDrawer from '../../../pratiche/components/PraticaDrawer.vue'
import DocumentoDrawerHost from '../documenti/DocumentoDrawerHost.vue'
import { useDocumentoDrawer } from '../documenti/useDocumentoDrawer'
import LineagePassaggiDialog from './LineagePassaggiDialog.vue'
import { lineageDocumentoLabel } from './lineageLabels'
import { useDocumentoPassaggi } from './useDocumentoPassaggi'

const props = defineProps({
  // Path lista API del dominio (es. '/vendite/ordini').
  basePath: { type: String, required: true },
  // Pk di dominio del documento (null in CREATE: nessuna fetch, nessuna riga).
  docId: { type: Number, default: null },
  // Readonly PURO del contesto che apre (permessi area / split / forzato) —
  // NON il lock-di-stato del documento padre. Vedi provide sotto.
  readonly: { type: Boolean, default: false },
})

// I drawer aperti da qui (documento della tappa, pratica) sono documenti
// DIVERSI dal drawer padre: il suo lock-di-stato (post-DRAFT → provide
// READONLY_KEY=true) non deve contagiarli — senza questo reset, un ordine
// aperto dai passaggi di un DDT CONSEGNATO perdeva TUTTE le azioni di stato
// (mapAvailableActionsToDrawerActions ritorna [] in readonly puro), incluso
// «Invia a commessa» legittimo. Si ri-fornisce quindi il readonly PURO del
// chiamante: i permessi area/split continuano a propagare, il lock no.
provide(READONLY_KEY, computed(() => props.readonly))

const { t, te } = useI18n()

// Fetch unica condivisa con la dialog (che non fetcha: si apre istantanea).
const { data, loaded, loading, reload } = useDocumentoPassaggi(
  () => props.basePath,
  () => props.docId,
)
// I drawer ricaricano i collegamenti dopo un'azione che li cambia (evasione,
// push, creazione reso): `reload` e' il loro aggancio.
defineExpose({ reload })

const pratica = computed(() => data.value?.pratica ?? null)

// Scopo: raggruppa gli archi di LIVELLO 1 di una direzione in chip per tipo
//        documento, contando le occorrenze. `lato` decide quale estremo
//        dell'arco e' la controparte (in avanti il TO, indietro il FROM).
//        `escludiAbortiti` vale solo in avanti — il payload porta
//        `to_is_abortito`, non il gemello a monte.
function chipsDaArchi(archi, lato, { escludiAbortiti = false } = {}) {
  const avanti = lato === 'to'
  const perTipo = new Map()
  for (const p of archi ?? []) {
    if (p.livello !== 1) continue
    if (escludiAbortiti && p.to_is_abortito) continue
    const tipoCodice = avanti ? p.to_tipo_codice : p.from_tipo_codice
    if (!tipoCodice) continue
    // ⭐ SI RAGGRUPPA PER TIPO **E NATURA**, non per tipo soltanto. Fattura e
    // nota di credito hanno lo stesso `codice_interno` sorgente: raggruppate
    // insieme diventerebbero «2 Fattura» su una fattura che ne ha una sola e
    // una nota di credito a valle — cioe' il chip nasconderebbe proprio la
    // cosa che segnala (2026-08-21, arco N).
    const naturaCodice = avanti ? p.to_natura_doc_codice : p.from_natura_doc_codice
    const chiave = `${tipoCodice}|${naturaCodice ?? ''}`
    const corrente = perTipo.get(chiave)
    if (corrente) {
      corrente.n += 1
      // I rami di ritorno (arco R DDT->Reso, arco N fattura->nota di credito)
      // marcano il chip appena ce n'e' uno.
      corrente.ramoInverso = corrente.ramoInverso || Boolean(p.is_ramo_inverso)
    } else {
      perTipo.set(chiave, {
        key: `${lato}-${chiave}`,
        tipoCodice,
        naturaCodice,
        n: 1,
        avanti,
        ramoInverso: Boolean(p.is_ramo_inverso),
      })
    }
  }
  return [...perTipo.values()]
}

// Origine (indietro) prima, destinazioni (avanti) poi: stesso ordine di
// lettura della timeline nella dialog.
const chips = computed(() => [
  ...chipsDaArchi(data.value?.indietro, 'from'),
  ...chipsDaArchi(data.value?.avanti, 'to', { escludiAbortiti: true }),
])

// Niente pratica e niente archi = documento isolato: nessuna riga, nessun
// pulsante. E' la "pulizia" del drawer, non un errore di caricamento —
// per questo il gate include `loaded` (su fetch fallita non si mostra nulla,
// ma nemmeno un falso "nessun collegamento").
const hasCollegamenti = computed(
  () => loaded.value && (pratica.value !== null || chips.value.length > 0),
)

// Scopo: etichetta del chip — il conteggio compare solo da 2 in su («Ordine»,
//        «2 DDT»): a 1 il numero e' rumore, il chip stesso dice che c'e'.
function chipLabel(chip) {
  const tipo = lineageDocumentoLabel(t, te, chip.tipoCodice, chip.naturaCodice)
  return chip.n > 1 ? `${chip.n} ${tipo}` : tipo
}

// Glifo di direzione, coerente con la timeline della dialog: ← origine,
// → destinazione, ↩ ramo di ritorno (DDT->Reso, fattura->nota di credito).
function chipIcon(chip) {
  if (chip.ramoInverso) return 'pi pi-replay'
  return chip.avanti ? 'pi pi-arrow-right' : 'pi pi-arrow-left'
}

const passaggiDialogVisible = ref(false)
const praticaDrawerVisible = ref(false)

// Host cross-dominio: apre il drawer di dettaglio del documento della tappa
// cliccata nella dialog (impilato, come il link pratica). Una sola istanza
// per il contenitore, condivisa fra chip e dialog.
// La guardia "tappa apribile" vive nel composable (`apri` e' no-op su chiave
// sconosciuta o id nullo): qui basta inoltrare.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumentoDrawer,
} = useDocumentoDrawer()

function apriDocumento(row) {
  apriDocumentoDrawer(row?.tipoCodice, row?.docId)
}
</script>

<template>
  <!-- `app-escape`: nei drawer post-DRAFT il contenuto e' .app-readonly, ma
       consultare la genealogia e' legittimo in qualunque stato (memoria
       feedback_app_escape_pannelli_processo). -->
  <div v-if="hasCollegamenti" class="app-escape app-collegamenti-bar">
    <!-- Pratica: apre direttamente il PraticaDrawer, non la dialog — e' un
         link diretto, non una tappa del grafo. -->
    <button
      v-if="pratica"
      type="button"
      class="app-collegamento-chip"
      v-tooltip.bottom="t('vendite.lineage.collegamenti_apri_pratica')"
      @click="praticaDrawerVisible = true"
    >
      <Tag
        severity="secondary"
        :icon="NAV_ICONS.PRATICHE"
        :value="`${t('vendite.lineage.pratica')} ${pratica.pratica_numero}`" />
    </button>

    <button
      v-for="chip in chips"
      :key="chip.key"
      type="button"
      class="app-collegamento-chip"
      v-tooltip.bottom="t('vendite.lineage.collegamenti_apri')"
      @click="passaggiDialogVisible = true"
    >
      <Tag severity="secondary" :icon="chipIcon(chip)" :value="chipLabel(chip)" />
    </button>
  </div>

  <LineagePassaggiDialog
    v-model:visible="passaggiDialogVisible"
    :data="data"
    :loading="loading"
    :loaded="loaded"
    :readonly="readonly"
    @apri-pratica="praticaDrawerVisible = true"
    @apri-documento="apriDocumento"
  />

  <PraticaDrawer
    v-if="pratica"
    v-model:visible="praticaDrawerVisible"
    mode="edit"
    :pratica-id="pratica.pratica_id" />

  <DocumentoDrawerHost
    v-model:visible="docDrawerVisible"
    :tipo-codice="docDrawerTipo"
    :doc-id="docDrawerId" />
</template>

<style scoped>
.app-collegamenti-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

/* Chip = controllo vero (button), non un Tag con @click: hit-area, focus da
   tastiera e ruolo semantico corretti. Il reset toglie il chrome del button
   e lascia parlare il Tag. */
.app-collegamento-chip {
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  line-height: 0;
  border-radius: var(--p-border-radius-sm, 4px);
}

.app-collegamento-chip:focus-visible {
  outline: 2px solid var(--app-icon-color);
  outline-offset: 2px;
}

.app-collegamento-chip:hover :deep(.p-tag) {
  filter: brightness(0.95);
}
</style>
