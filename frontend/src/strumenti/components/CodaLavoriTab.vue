<script setup>
// Scopo: Tab «Coda lavori» della vista Strumenti (FE-4/FE-5): lista paginata
//        dei job di dbops.coda_lavori. Righe proprie = azionabili (annulla su
//        PENDING, requeue su IN_CORSO/ERRORE); righe altrui = sola lettura con
//        colonna proprietario. La vista «Tutti» è aperta a ogni operatore
//        (2026-07-23, decisione Tid): la coda è condivisa e chi aspetta deve
//        vedere il lavoro altrui che la impegna; azioni e DETTAGLIO restano
//        gated (proprie o code_manage). `is_mio` arriva dal BE (P-5: il FE non
//        confronta identità). Gate stato sui CODICI stabili (I-2), enforcement
//        vero nel BE (I-3: qui si nasconde, là si blinda).
//
//        Lista configurabile su config DB `dbops.coda_lavori`
//        (ui.lista_definizione id 34 — 7° lotto, 2026-08-03): personalizzazione
//        colonne + ordinamento server-side (whitelist BE ELENCA_SORT_SQL,
//        estesa a `stato`/`proprietario` il 2026-08-02) + preset
//        `started_at desc` che replica il default BE. Stato lista nello store
//        Pinia `useCodaLavoriStore` (stores/codeJobs.js).
//
// ⭐ Dal 2026-08-27 lo SCHELETRO (toolbar, stato worker, lista, refresh
//    periodico silenzioso, colonna stato con la rotellina, empty) vive in
//    `CodaTabBase`, condiviso con la coda stampa. Qui restano le colonne di
//    dominio e — ciò che la stampa non ha — le AZIONI di riga e il drawer di
//    dettaglio.
// ⚠️ Il reload dopo un'azione passa dal ref al base (`baseRef.load()`): la
//    fetch è sua, insieme al refresh dello stato worker.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { statoCodaLavoriSeverity, STATO_CODA_LAVORI_MAP } from '../../core/utils/severity'
import {
  annullaCodaLavoro,
  archiviaCodaLavoro,
  requeueCodaLavoro,
  ripristinaCodaLavoro,
} from '../../core/api/tracciamento'
import { MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useCodaArchiviazione } from '../composables/useCodaArchiviazione'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import { useSelezioneCoda } from '../composables/useSelezioneCoda'
import { useCodaLavoriStore } from '../stores/codeJobs'
import CodaTabBase from './CodaTabBase.vue'
import JobDettaglioDrawer from './JobDettaglioDrawer.vue'

const { t } = useI18n()
const notify = useNotify()
const { execute, loading: azioneLoading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const store = useCodaLavoriStore()

// Solo il gate delle AZIONI: le opzioni dei filtri le prende il base.
const { canManage } = useCodaFiltri(STATO_CODA_LAVORI_MAP)

const baseRef = ref(null)
function ricarica() {
  baseRef.value?.load()
}

// Selezione multipla per l'archiviazione di massa. ⚠️ Abilitata solo con
// `code_manage` e fuori readonly: senza, niente caselle — il permesso nasconde.
const selezione = useSelezioneCoda({
  righeVisibili: computed(() => store.items),
  abilitata: computed(() => canManage.value && !isReadonly.value),
})

// Archivia / Ripristina: le voci di riga E il verbo di massa vivono nel
// composable condiviso con la coda stampa — stessa bandiera, stesso trigger,
// stesso codice errore.
const { azioniArchiviazione, archiviaRighe, loading: archiviazioneLoading } =
  useCodaArchiviazione({
    archivia: archiviaCodaLavoro,
    ripristina: ripristinaCodaLavoro,
    ricarica,
    etichettaRiga: (row) => `#${row.id} (${row.job_type})`,
    // Le righe archiviate escono dall'elenco: una selezione che le contasse
    // ancora mentirebbe al pulsante.
    // Le righe archiviate escono dall'elenco: una selezione che le contasse
    // ancora mentirebbe. ⭐ Si tengono spuntate le sole FALLITE — sono
    // esattamente quelle su cui l'operatore deve tornare.
    onArchiviato: (idsFalliti) => selezione.tieniSolo(idsFalliti),
  })

// Drawer dettaglio (FE-6).
const dettaglioVisible = ref(false)
const dettaglioJobId = ref(null)

function apriDettaglio(row) {
  dettaglioJobId.value = row.id
  dettaglioVisible.value = true
}

// Scopo: annulla un job PENDING proprio (conferma esplicita, poi reload).
function annullaJob(row) {
  confirmAction({
    header: t('strumenti.code.annulla_header'),
    message: t('strumenti.code.annulla_conferma', { id: row.id, tipo: row.job_type }),
    danger: true,
    onAccept: async () => {
      const res = await execute(() => annullaCodaLavoro(row.id))
      if (res !== null) {
        notify.success(t('strumenti.code.annulla_esito'))
        ricarica()
      }
    },
  })
}

// Scopo: requeue/sblocco di un job IN_CORSO o ERRORE (alza max_tentativi).
function requeueJob(row) {
  confirmAction({
    header: t('strumenti.code.requeue_header'),
    message: t('strumenti.code.requeue_conferma', { id: row.id, tipo: row.job_type }),
    onAccept: async () => {
      const res = await execute(() => requeueCodaLavoro(row.id))
      if (res !== null) {
        notify.success(t('strumenti.code.requeue_esito'))
        ricarica()
      }
    },
  })
}

// Scopo: azioni riga — annulla/requeue solo su righe azionabili (mie o
//        code_manage) fuori readonly, gate sui codici stato. Anche il
//        DETTAGLIO è gated (mie o code_manage): la lista «Tutti» è visibilità
//        della coda condivisa, ma payload/errori del job altrui possono
//        contenere dati della sua attività — il BE risponde comunque 404
//        fuori scope, qui si evita di offrire un'azione destinata a fallire.
function buildRowActions(row) {
  const azionabile = (row.is_mio === true || canManage.value) && !isReadonly.value
  return [
    {
      key: 'dettaglio',
      label: t('strumenti.code.azione_dettaglio'),
      icon: MANAGE_ICONS.INSPECT,
      visible: row.is_mio === true || canManage.value,
      command: () => apriDettaglio(row),
    },
    {
      key: 'annulla',
      label: t('strumenti.code.azione_annulla'),
      icon: MANAGE_ICONS.ANNULLA,
      severity: 'danger',
      visible: azionabile && row.stato === 'PENDING',
      command: () => annullaJob(row),
    },
    {
      key: 'requeue',
      label: t('strumenti.code.azione_requeue'),
      icon: MANAGE_ICONS.RIPROVA,
      severity: 'warn',
      visible: azionabile && (row.stato === 'IN_CORSO' || row.stato === 'ERRORE'),
      command: () => requeueJob(row),
    },
    // ⚠️ L'archiviazione NON passa da `azionabile`: quel predicato e'
    //    l'ownership di annulla/requeue («e' mio, oppure ho code_manage»), e
    //    qui non c'entra — il verbo ha effetto globale e vuole `code_manage`
    //    e basta. Il gate lo porta la voce stessa (`action`), il readonly lo
    //    guarda il composable.
    ...azioniArchiviazione(row),
  ]
}

// Click riga = dettaglio, stesso gate delle azioni.
function onRowClick(data) {
  if (data.is_mio === true || canManage.value) apriDettaglio(data)
}

// Prop del base: si passa la FUNZIONE, non il booleano — il base la invoca per
// riga. `computed` solo per il loading, che è reattivo.
const loadingAzione = computed(() => azioneLoading.value || archiviazioneLoading.value)
</script>

<template>
  <CodaTabBase
    ref="baseRef"
    :store="store"
    codice="dbops.coda_lavori"
    coda="coda_lavori"
    :stato-map="STATO_CODA_LAVORI_MAP"
    :stato-severity="statoCodaLavoriSeverity"
    empty-key="strumenti.code.nessuna_riga"
    :empty-icon="NAV_ICONS.CODE_LAVORO"
    :extra-loading="loadingAzione"
    :build-row-actions="buildRowActions"
    :on-row-click="onRowClick"
    :selezione="selezione"
    :on-archivia-selezione="archiviaRighe"
  >
    <template #cell-job_type="{ data }">
      <span class="app-mono">{{ data.job_type }}</span>
    </template>
    <template #cell-proprietario="{ data }">
      <span>
        {{ data.proprietario ?? '—' }}
        <Tag
          v-if="data.is_mio"
          :value="t('strumenti.code.mio_tag')"
          severity="info"
          class="app-code-mio-tag"
        />
      </span>
    </template>
    <!-- Colonna calcolata FE (seed: campo_sorgente NULL, ordinabile=f). -->
    <template #cell-tentativi="{ data }">
      {{ data.tentativi }}/{{ data.max_tentativi }}
    </template>
    <!-- started_at/ended_at non hanno slot: il seed dichiara `datetime_short`
         e il formatter di serie le rende gia' cosi'. -->

    <template #extra>
      <JobDettaglioDrawer
        v-model:visible="dettaglioVisible"
        :job-id="dettaglioJobId"
        @changed="ricarica"
      />
    </template>
  </CodaTabBase>
</template>

