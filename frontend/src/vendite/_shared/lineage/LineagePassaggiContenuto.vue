<script setup>
// Scopo: Corpo "Passaggi" (genealogia/lineage) di un documento vendite — resa
// PURA del payload GET {base}/{id}/passaggi/: pratica collegata, frontiera
// (documento piu' prossimo in esecuzione) e la catena reale dei transiti in
// ENTRAMBE le direzioni (Origine = indietro, Destinazioni = avanti) come
// timeline indentata per livello. L'arco R (is_ramo_inverso, DDT->Reso) e'
// reso come "ramo di ritorno"; il ruolo ROOT/COLLEGATO (commesse_sorgenti) e'
// mostrato in entrambe le direzioni.
//
// Estratto 2026-07-25 da LineagePassaggiPanel (che era Panel + fetch + resa in
// un solo file): serve identico in due contenitori diversi — la dialog aperta
// dai chip di `DocumentoCollegamentiBar` nei drawer documento, e INLINE nei
// drawer commessa, dove la genealogia e' il contenuto principale e una modale
// sarebbe un click di troppo su un drawer che esiste solo per quello.
//
// Il componente NON fetcha e NON apre drawer: riceve `data` (dal composable
// useDocumentoPassaggi) ed emette `apri-pratica` / `apri-documento`. Cosi' il
// contenitore possiede UNA sola istanza di PraticaDrawer/DocumentoDrawerHost,
// condivisa con i chip della barra (che aprono gli stessi bersagli).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { isTappaApribile } from '../../../core/drawerEntita'
import { lineageDocumentoLabel } from './lineageLabels'
import { faseDocumentoSeverity } from '../../../core/utils/severity'
import { MANAGE_ICONS } from '../../../core/constants'

const props = defineProps({
  // Payload passaggi (null finche' non caricato).
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  loaded: { type: Boolean, default: false },
})

const emit = defineEmits(['apri-pratica', 'apri-documento'])

const { t, te } = useI18n()

const pratica = computed(() => props.data?.pratica ?? null)
const frontiera = computed(() => props.data?.frontiera ?? null)

// Scopo: Normalizza un arco del traversal nella tappa da mostrare: in avanti
// il nodo TO (destinazione), in indietro il nodo FROM (origine).
function passaggioToRow(p, lato) {
  const from = lato === 'from'
  return {
    key: `${lato}-${p.ordine}`,
    livello: p.livello,
    tipoCodice: from ? p.from_tipo_codice_interno : p.to_tipo_codice_interno,
    // La natura del documento fiscale: e' cio' che distingue una nota di
    // credito da una fattura, che condividono il tipo sorgente.
    naturaCodice: from ? p.from_natura_doc_codice_interno : p.to_natura_doc_codice_interno,
    codice: from ? p.from_codice : p.to_codice,
    docId: from ? p.from_doc_id : p.to_doc_id,
    stato: from ? p.from_stato_codice_interno : p.to_stato_codice_interno,
    fase: from ? p.from_fase : p.to_fase,
    ramoInverso: p.is_ramo_inverso,
    // Il LEGAME, non il documento (brief-db-annullo-a-valle-riapre-a-monte §11):
    // la commessa puo' essere viva e il contributo di questo documento ritirato.
    // `=== true`: NULL e' «arco non censito», e non si dice niente.
    legameRitirato: p.is_legame_ritirato === true,
    ruolo: p.ruolo,
  }
}

// Le due sezioni della timeline, stessa resa (simmetria: ruolo ROOT/COLLEGATO
// e "ramo di ritorno" compaiono in entrambe le direzioni — gli archi B/E/F
// portano il ruolo anche in avanti, l'arco R e' inverso anche risalendo).
const sezioni = computed(() => [
  {
    key: 'origine',
    titolo: t('vendite.lineage.origine'),
    vuoto: t('vendite.lineage.nessuna_origine'),
    icona: MANAGE_ICONS.DOC_ORIGINE,
    rows: (props.data?.indietro ?? []).map((p) => passaggioToRow(p, 'from')),
  },
  {
    key: 'destinazioni',
    titolo: t('vendite.lineage.destinazioni'),
    vuoto: t('vendite.lineage.nessun_transito'),
    icona: MANAGE_ICONS.DOC_DESTINAZIONE,
    rows: (props.data?.avanti ?? []).map((p) => passaggioToRow(p, 'to')),
  },
])

// ⚠️ Due argomenti espliciti e non la riga intera: FRONTIERA e tappe hanno
// forme diverse (`tipo_codice_interno` vs `tipoCodice`). La natura serve a ENTRAMBE:
// la frontiera puo' essere una nota di credito — l'arco G dalla commessa non
// e' un ramo di ritorno, e al 2026-08-21 la NC e' gia' la frontiera
// dell'ordine 240 (misurato). «Una NC non e' mai frontiera» e' l'invariante
// falsa che il pgTAP del DB ha corretto (§44.5 del brief).
function tipoLabel(tipoCodice, naturaCodice = null) {
  return lineageDocumentoLabel(t, te, tipoCodice, naturaCodice)
}

// Scopo: l'etichetta della tappa quando il documento NON HA ANCORA UN NUMERO.
// ⚠️ Un documento puo' esistere ed essere gia' EMESSO senza codice: la fattura
// prende numero solo con «Rendi definitive», quindi fra emissione e
// numerazione la tappa ha tipo e stato ma `codice` NULL. Prima quel caso
// rendeva un link con etichetta VUOTA (o un trattino), e chi guardava leggeva
// «manca il collegamento» invece di «manca il numero» — due cose diverse, e la
// prima manda a cercare un guasto che non c'e' (rilievo in-app 2026-08-20).
function etichettaCodice(row) {
  return row.codice || t('vendite.lineage.non_numerato')
}

// Apribile = regola unica del registry (`isTappaApribile`): id di dominio
// risolto dal BE + tipo sorgente con drawer. Qui decide se il codice si rende
// come link; l'apertura vera la guarda di nuovo il composable del contenitore.
const isApribile = isTappaApribile
</script>

<template>
  <div>
    <ProgressBar v-if="loading" mode="indeterminate" style="height: 4px" />

    <template v-if="loaded && data">
      <!-- Pratica collegata (1:1 di design, conteggio difensivo n_pratiche).
           Senza pratica: messaggio testuale al posto del "—" (il documento
           puo' legittimamente nascere fuori dal percorso pratica). -->
      <div class="lineage-row">
        <span class="lineage-label">{{ t('vendite.lineage.pratica') }}</span>
        <template v-if="pratica">
          <Button
            link
            class="lineage-link"
            :label="pratica.pratica_numero"
            @click="emit('apri-pratica')" />
          <span v-if="pratica.n_pratiche > 1" class="lineage-muted">
            {{ t('vendite.lineage.altre_pratiche', { n: pratica.n_pratiche - 1 }) }}
          </span>
        </template>
        <span v-else class="lineage-muted">{{ t('vendite.lineage.nessuna_pratica') }}</span>
      </div>

      <!-- Frontiera: documento piu' prossimo in esecuzione (G-6/G-9/G-10) -->
      <div class="lineage-row">
        <span class="lineage-label">{{ t('vendite.lineage.frontiera') }}</span>
        <template v-if="frontiera">
          <Tag
            :value="tipoLabel(frontiera.tipo_codice_interno, frontiera.natura_doc_codice_interno)"
            severity="secondary" />
          <!-- Stessa fallback delle tappe: una frontiera EMESSA ma non ancora
               numerata ha `codice` NULL, e il vuoto si legge «manca il
               collegamento» invece di «manca il numero». -->
          <span class="lineage-codice">{{ frontiera.codice || t('vendite.lineage.non_numerato') }}</span>
          <Tag
            :value="frontiera.stato_codice_interno ?? frontiera.fase"
            :severity="faseDocumentoSeverity(frontiera.fase)" />
          <span v-if="frontiera.n_discendenti_attivi > 1" class="lineage-muted">
            {{ t('vendite.lineage.altre_attive', { n: frontiera.n_discendenti_attivi - 1 }) }}
          </span>
        </template>
        <span v-else class="lineage-muted">{{ t('vendite.lineage.nessun_transito') }}</span>
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
          <i :class="row.ramoInverso ? MANAGE_ICONS.CORREZIONE : sezione.icona" class="lineage-step-icon" />
          <Tag :value="tipoLabel(row.tipoCodice, row.naturaCodice)" severity="secondary" />
          <Button
            v-if="isApribile(row)"
            link
            class="lineage-link"
            :label="etichettaCodice(row)"
            v-tooltip.top="t('vendite.lineage.apri_documento')"
            @click="emit('apri-documento', row)" />
          <span v-else class="lineage-codice">{{ etichettaCodice(row) }}</span>
          <Tag
            v-if="row.stato || row.fase"
            :value="row.stato ?? row.fase"
            :severity="faseDocumentoSeverity(row.fase)" />
          <!-- Lo stato accanto e' quello del DOCUMENTO (la commessa e' viva);
               questo dice che il legame non porta piu' niente: senza, da un
               preventivo annullato si leggeva «sta in una commessa pronta da
               fatturare» (collaudo di Tid, 2026-10-13). -->
          <Tag
            v-if="row.legameRitirato"
            :value="t('vendite.lineage.legame_ritirato')"
            severity="warn"
            v-tooltip.top="t('vendite.lineage.legame_ritirato_tooltip')" />
          <span v-if="row.ruolo" class="lineage-muted">{{ row.ruolo }}</span>
          <span v-if="row.ramoInverso" class="lineage-muted">
            {{ t('vendite.lineage.ramo_inverso') }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
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

/* Icona di direzione/ramo: e' un GLIFO, non un controllo — nessuna hit-area,
   nessun hover, cursor default (vedi frontend-standards, "Glifo vs controllo").
   La distinzione dalle icone-azione (colore semantico saturo + chrome del
   controllo) si gioca sul CHROME; il muted la rifinisce facendola arretrare.
   Deciso con Tid 2026-07-09 dopo A/B sul campo: su un glifo da 0.8rem la
   differenza --app-text-color vs --app-text-muted e' impercettibile -> il
   colore non e' la leva, e muted e' gia' inequivocabilmente != verde/blu/rosso. */
.lineage-step-icon {
  font-size: 0.8rem;
  color: var(--app-text-muted);
}

/* Ramo di ritorno (arco R, DDT->Reso): NIENTE opacity sulla riga (Tid 2026-07-09).
   Smorzava dati veri (codice, Tag stato) per dire una cosa gia' detta due volte —
   dall'icona ↩ e dalla label "ramo di ritorno" — e si SOMMAVA all'opacity 0.85 di
   .app-readonly nei drawer post-DRAFT (0.85 x 0.75 ~ 0.64: area illeggibile, e
   "decorativo" indistinguibile da "disabilitato" per costruzione). */

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
