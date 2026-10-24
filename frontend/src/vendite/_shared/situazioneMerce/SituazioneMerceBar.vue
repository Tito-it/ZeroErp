<script setup>
// Scopo: Riga «situazione merce» nei drawer ordine e DDT — il RIASSUNTO IN
// TESTATA deciso al §5.2 del brief pannello: una riga sola che dice SE c'e'
// qualcosa di aperto, e da cui si apre il dettaglio.
//
// Sta sotto `DocumentoCollegamentiBar`, e le due si completano: quella dice
// COSA c'e' collegato («Ordine · 2 DDT · Reso»), questa dice COM'E' ANDATA
// («8 da accreditare · 3 da riconsegnare»). Erano il rilievo in-app di Tid del
// 2026-08-17: *«se si vuole avere la situazione di un ordine non si capisce
// nulla di quello che e' successo»* — cinque schermate per ricostruire una
// storia, e la riga che la riassume non esisteva.
//
// ⭐ PERCHE' IN TESTATA E NON UNA TABELLA SEMPRE VISIBILE (§5.2): su un ordine
// SANO non occupa spazio e non aggiunge rumore; su uno con pendenze si nota
// subito, che e' l'unico momento in cui serve. Sette colonne accanto alle righe
// d'ordine sarebbero una seconda tabella da leggere, e la si smette di guardare.
//
// ⚠️ REGOLA DI SVUOTAMENTO — ed e' l'opposto di quella dei collegamenti. La riga
// NON sparisce quando non c'e' nulla di aperto: mostra «tutto regolare». Il
// §5.2 lo chiede espressamente — «tutto regolare deve essere VISIBILMENTE
// diverso da non ancora calcolato» — e una riga assente e' ambigua fra le due.
// Sparisce solo quando non c'e' NIENTE da raccontare: documento senza merce
// (un DDT in bozza non ha ancora partite, soglia EMESSO) o dati non arrivati.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Tag from 'primevue/tag'
import SituazioneMerceDialog from './SituazioneMerceDialog.vue'
import { compitiSituazioneMerce, sintesiSituazioneMerce } from './situazioneMerceSintesi'
import { useSituazioneMerce } from './useSituazioneMerce'
import { ROUTE_RESI, TAB_RESI } from '../../resi/constants'
import { STATUS_ICONS } from '../../../core/constants'

// Da quale documento si arriva → su quale filtro si apre la coda accrediti.
// I due filtri sono ALTERNATIVI (il backend rifiuta la coppia).
const FILTRO_CODA_PER_BASE_PATH = Object.freeze({
  '/vendite/ddt': 'ddt_id',
  '/vendite/ordini': 'ordine_id',
})

const props = defineProps({
  // Path lista API del dominio ('/vendite/ordini' | '/vendite/ddt').
  basePath: { type: String, required: true },
  // Pk di dominio (null in CREATE: nessuna fetch, nessuna riga).
  docId: { type: Number, default: null },
  // ⭐ Il dettaglio che il drawer ospite ha appena letto (l'oggetto intero):
  // ogni sua rilettura rilegge anche qui (useLetturaDocumento). OBBLIGATORIA
  // di proposito — dimenticarla e' il difetto che l'ha fatta nascere (barra
  // stantia dopo l'annullo di una commessa, 2026-10-13): senza, Vue avvisa.
  // `null` finche' il dettaglio non e' arrivato e' ammesso (niente `type`).
  versione: { required: true },
  // Readonly PURO del chiamante (permessi area / split), NON il lock-di-stato
  // del documento: la dialog e' consultiva e deve aprirsi anche su un
  // documento post-DRAFT, che e' il caso normale qui — la merce si muove dopo
  // l'emissione. Stessa ragione di DdtResoDialog.
  readonly: { type: Boolean, default: false },
})

const { t } = useI18n()
const router = useRouter()

// Fetch unica condivisa con la dialog (che non fetcha: si apre istantanea).
// Si rilegge da se' a ogni rilettura del drawer ospite (`versione`): evasione,
// reso, annullo, emissione passano tutti da un `loadDetail`, e nessun drawer
// deve piu' ricordarsi di chiamare `reload` (2026-10-13).
const { sezioni, loaded, loading } = useSituazioneMerce(
  () => props.basePath,
  () => props.docId,
  () => props.versione,
)

const s = computed(() => sintesiSituazioneMerce(sezioni.value))

// Scopo: dal pannello alla CODA ACCREDITI, gia' filtrata su questo documento
//        (FE-2). Il predicato del filtro e' lo stesso che alimenta la sezione
//        «da accreditare» qui dentro — stessa vista, stessa restrizione —
//        quindi l'elenco che si apre e' esattamente quello che il pannello
//        conta: se divergessero, il pannello direbbe «8» e la coda ne
//        mostrerebbe 7, e nessuno se ne accorgerebbe.
// ⚠️ La dialog si CHIUDE prima di navigare, o si resta con un overlay sopra la
//    coda. E la chiude chi l'ha aperta: il pannello non conosce il router.
function apriCodaAccrediti() {
  dialogVisible.value = false
  // ⚠️ Mappa esplicita e non `endsWith('/ddt') ? … : 'ordine_id'`: con il
  // ternario un basePath nuovo (o scritto storto) finirebbe SILENZIOSAMENTE
  // nel ramo ordine, e la coda si aprirebbe filtrata sull'id sbagliato — cioe'
  // mostrerebbe le righe di un altro documento senza dire niente. Qui un
  // dominio non previsto non naviga, e lo dice in console.
  const chiave = FILTRO_CODA_PER_BASE_PATH[props.basePath]
  if (!chiave) {
    console.warn('situazione merce: nessun filtro coda per basePath', props.basePath)
    return
  }
  // La pila di drawer che ci ospita non si chiude qui: ci pensa la chiusura
  // globale su cambio rotta (`useDrawerChiusuraGlobale`, agganciata nel router).
  // Farlo anche qui sarebbe una seconda strada per la stessa cosa — e quella
  // locale chiuderebbe UN anello solo, lasciando aperti quelli sopra.
  router.push({
    name: ROUTE_RESI,
    query: { tab: TAB_RESI.DA_ACCREDITARE, [chiave]: props.docId },
  })
}

// I compiti in testata: la STESSA lista che il dettaglio mostra come riepilogo
// in fondo alla dialog (`compitiSituazioneMerce`). Scritta una volta sola, il
// chip e la voce del riepilogo non possono dire due numeri diversi.
const chips = computed(() => compitiSituazioneMerce(s.value, t))

// La riga si mostra solo con dati ARRIVATI e qualcosa da dire. `loaded` e' la
// difesa contro il vuoto positivo: su una fetch fallita non si afferma nulla.
const visibile = computed(() => loaded.value && (s.value.haPendenze || s.value.tuttoRegolare))

const dialogVisible = ref(false)
</script>

<template>
  <!-- `app-escape`: nei drawer ordine/DDT il contenuto e' .app-readonly appena
       il documento esce da DRAFT (`pointer-events: none`), e la merce nasce
       PROPRIO li' — un DDT ha partite solo da EMESSO in poi. Senza questa
       classe la barra si vede e i chip NON si cliccano: la dialog di dettaglio
       non si apre MAI in uso reale, e con lei se ne va il collegamento alla
       coda accrediti (F3). Stessa ragione, e stessa riga, di
       `DocumentoCollegamentiBar` qui sopra: aprire un dettaglio e' LEGGERE,
       e leggere non e' l'azione che il protect deve fermare. -->
  <div v-if="visibile" class="app-escape app-merce-bar">
    <span class="app-merce-label">{{ t('vendite.situazione_merce.etichetta') }}</span>

    <button
      v-if="s.tuttoRegolare"
      type="button"
      class="app-merce-chip"
      v-tooltip.bottom="t('vendite.situazione_merce.apri')"
      @click="dialogVisible = true"
    >
      <Tag severity="success" :icon="STATUS_ICONS.SI" :value="t('vendite.situazione_merce.tutto_regolare')" />
    </button>

    <button
      v-for="chip in chips"
      :key="chip.key"
      type="button"
      class="app-merce-chip"
      v-tooltip.bottom="t('vendite.situazione_merce.apri')"
      @click="dialogVisible = true"
    >
      <Tag :severity="chip.severity" :value="chip.label" />
    </button>
  </div>

  <SituazioneMerceDialog
    v-model:visible="dialogVisible"
    :sezioni="sezioni"
    :loading="loading"
    :loaded="loaded"
    :readonly="readonly"
    @apri-coda-accrediti="apriCodaAccrediti"
  />
</template>

<style scoped>
.app-merce-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

/* Glifo, non controllo: l'etichetta arretra (vedi frontend-standards
   §"Glifo vs controllo") — i controlli sono i chip. */
.app-merce-label {
  color: var(--app-text-muted);
  font-size: var(--app-font-size-sm);
}

/* Chip = controllo vero (button), non un Tag con @click: hit-area, focus da
   tastiera e ruolo semantico corretti. Identico ad app-collegamento-chip. */
.app-merce-chip {
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  line-height: 0;
  border-radius: var(--p-border-radius-sm, 4px);
}

.app-merce-chip:focus-visible {
  outline: 2px solid var(--app-icon-color);
  outline-offset: 2px;
}

.app-merce-chip:hover :deep(.p-tag) {
  filter: brightness(0.95);
}

/* Affordance «cliccabile» sempre visibile, non solo all'hover: il chip ha la
   forma di un Tag, che altrove e' un'etichetta inerte — senza un segno che sia
   un link non si capisce che apre il dettaglio (rilievo in-app di Tid,
   2026-10-11). Verde sottolineato come i link dei passaggi lineage (Button
   `link` di PrimeVue = colore primario). */
.app-merce-chip :deep(.p-tag-label) {
  color: var(--p-primary-color);
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
