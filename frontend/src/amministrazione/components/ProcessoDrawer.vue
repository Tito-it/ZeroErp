<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: drawer di CONSULTAZIONE di un processo automatico: chi è, dove scrive,
//        con quale identità lavora e quando è girato l'ultima volta.
//        Più l'unico verbo della schermata: creare l'utente tecnico di
//        un'azienda che il processo non serve ancora.
//
// ⭐ Sola lettura per costruzione: il registro dei processi è CATALOGO — nasce
//    da un seed, non da questa schermata. `footer="chiudi"` di AppDrawer: non c'è
//    niente da salvare, e un pulsante «Salva» che non salva niente è peggio di
//    nessun pulsante.
// ⚠️ Le quattro schede sono `Tabs` PrimeVue 4 e NON `useDrawerTabLista`:
//    quello serve a una lista PAGINATA con endpoint proprio e filtri. Qui
//    bersagli, identità e sveglie sono elenchi CHIUSI dal modello (un pugno di
//    righe, consegnate col dettaglio in un round-trip) e le corse sono le
//    ultime N. Montarci un paginator sarebbe cerimoniale.
// ⭐ Dal 2026-09-15 il drawer ha anche un VERBO sulle sveglie: «Esegui ora»
//    (piano-be-fe-avvio-manuale-di-un-processo.md §2.6). Il web NON esegue
//    niente: accoda un lavoro con l'identità di chi preme e il drenatore lancia
//    il comando alla corsa successiva. Il gesto è asincrono per costruzione, la
//    UI lo dice, e NON c'è polling: la corsa si vedrà fra le «Ultime corse»
//    alla riapertura, con `origine = COMMAND` e lo username — la colonna c'è già.
// ⭐ Dal 2026-10-16 il drawer dice anche se il processo è ACCESO su questa
//    installazione, e da dove viene lo stato (default per ambiente o scelta a
//    mano), con l'interruttore e il motivo obbligatorio
//    (brief-db-processi-accensione-per-ambiente §6.0 punto 5). È un fatto del
//    PROCESSO, non della sveglia: sta in testa, una volta, e le sveglie non
//    portano più la colonna «Abilitata» del deploy (`abilita` è ritirato).
// ⛔ La lista delle CORSE è l'unica che potrebbe crescere: è limitata a 50 dal
//    backend e lo dice a video. Se un giorno servisse scorrerla tutta, allora sì
//    diventa una lista vera con `useDrawerTabLista` — non prima.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { intlLocale } from '../../core/i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Button from 'primevue/button'
import AppDrawer from '../../core/components/AppDrawer.vue'
import MotivoDialog from '../../core/components/MotivoDialog.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import {
  getProcesso,
  listProcessoRun,
  creaUtenteTecnico,
  riattivaUtenteTecnico,
  eseguiOraProcesso,
  impostaAccensioneProcesso,
} from '../api/amministrazione'
import { displayTimestamp } from '../../core/utils/date'
import { descriviDovuto as descriviDovutoSveglia } from '../dovutoSveglia'



const props = defineProps({
  visible: { type: Boolean, default: false },
  codice: { type: String, default: null },
})

const emit = defineEmits(['update:visible', 'identita-creata'])

// ⛔ Quante corse si mostrano. Sede UNICA: prima il numero stava nella
//    chiamata E nella frase i18n, e due numeri per lo stesso fatto
//    divergono al primo che si tocca.
const CORSE_MOSTRATE = 50

const { t, te, locale } = useI18n()

// Scopo: la cadenza del lavoro di una sveglia calendariale, in parole (T-9).
function descriviDovuto(dovuto) {
  return descriviDovutoSveglia(dovuto, t, intlLocale(locale.value))
}
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const dettaglio = ref(null)
const corse = ref([])
const caricamento = ref(false)
const tabAttiva = ref('bersagli')
const emittenteScelto = ref(null)
const creazioneInCorso = ref(false)
// La unit il cui «Esegui ora» è in volo: mostra la rotellina su QUELLA riga e
// spegne il pulsante su TUTTE finché la risposta non torna — il dettaglio si
// ricarica subito dopo, e un secondo click nel frattempo partirebbe da
// capability già vecchie.
const eseguiInCorso = ref(null)

// ⭐ Le sveglie di deploy arrivano col dettaglio (piano §2.5): zero, una o
//    più righe per processo, ognuna con la propria terna `can_esegui_ora*`.
//    ⚠️ `?? []` copre il solo caso in cui il campo manchi: un processo senza
//    sveglie (pgAgent) riceve una LISTA VUOTA, non un'assenza.
const sveglie = computed(() => dettaglio.value?.sveglie ?? [])

// ⭐ L'accensione del processo su questa installazione, dal dettaglio: lo
//    stato effettivo (`acceso`, null = non decidibile), da dove viene
//    (`scelta_a_mano` o il default per `ambiente`), e la capability
//    `can_imposta_accensione`. ⛔ Lo stato non si ricalcola qui dai due
//    default: la regola è del database, e qui si MOSTRA.
const accensione = computed(() => dettaglio.value?.accensione ?? null)
// Il gesto in corso nel dialog del motivo: `true` accende, `false` spegne,
// `null` torna al default. `undefined` = dialog chiuso.
const gestoAccensione = ref(undefined)
const dialogAccensione = computed({
  get: () => gestoAccensione.value !== undefined,
  set: (aperto) => { if (!aperto) gestoAccensione.value = undefined },
})

// Scopo: «Accendi» è spento? Il motivo dal backend (la terna `can_accendere*`,
//        dal predicato del guard del DB: R-BE-5, in PRODUZIONE un processo non
//        accendibile si spegne e torna al default, ma non si accende a mano).
// ⛔ Non si guarda `ambiente` né il catalogo per deciderlo: la regola è del
//    database, e qui si MOSTRA.
function accendiBloccato(a) {
  return bloccoAttivo(a, 'can_accendere', 'can_accendere')
}

// Scopo: il tooltip di «Accendi»: il MOTIVO se spento, cosa fa se acceso.
function accendiTooltip(a) {
  return accendiBloccato(a)
    ? motivoBloccoRiga(t, te, a, 'can_accendere')
    : t('amministrazione.processi.accendi_spiegazione')
}

// Scopo: la chiave i18n del gesto in corso, per titolo e pulsante del dialog.
function chiaveGesto(gesto) {
  if (gesto === true) return 'accendi'
  if (gesto === false) return 'spegni'
  return 'torna_al_default'
}

// Scopo: il nome dell'ambiente nella lingua di chi guarda. Il vocabolario
//        (`SVILUPPO`, `PRODUZIONE`) è del database: un valore nuovo senza
//        traduzione si mostra com'è, invece di sparire.
function etichettaAmbiente(ambiente) {
  const chiave = `amministrazione.processi.ambiente_valore.${ambiente}`
  return te(chiave) ? t(chiave) : ambiente
}

// Scopo: da dove viene lo stato, in parole: non si spegne mai, scelta a mano
//        (motivo, quando, chi), default dell'ambiente, ambiente non dichiarato.
function provenienzaAccensione(a) {
  if (a.spegnibile === false) return t('amministrazione.processi.accensione_mai_spento')
  // ⭐ Una scelta «accendi» che il divieto di produzione non ammette resta
  //    scritta ma non vale (R-BE-5): lo dice il backend (`ammessa`), qui si
  //    mostra. Senza, «Spento» e «Scelta a mano» si contraddirebbero.
  if (a.scelta_a_mano && a.scelta_a_mano.ammessa === false) {
    return t('amministrazione.processi.accensione_a_mano_non_ammessa', {
      motivo: a.scelta_a_mano.motivo,
      quando: displayTimestamp(a.scelta_a_mano.data),
      chi: a.scelta_a_mano.utente || '—',
    })
  }
  if (a.scelta_a_mano) {
    return t('amministrazione.processi.accensione_a_mano', {
      motivo: a.scelta_a_mano.motivo,
      quando: displayTimestamp(a.scelta_a_mano.data),
      chi: a.scelta_a_mano.utente || '—',
    })
  }
  if (a.ambiente) return t('amministrazione.processi.accensione_default', { ambiente: etichettaAmbiente(a.ambiente) })
  return t('amministrazione.processi.ambiente_non_dichiarato')
}

// Scopo: accende, spegne o riporta al default col motivo, poi ricarica: le
//        capability di «Esegui ora» dipendono dallo stato appena cambiato.
// ⚠️ Il dialog si chiude solo sul successo: un rifiuto (motivo, non
//    spegnibile) lo lascia aperto col motivo scritto.
async function confermaAccensione(motivo) {
  const res = await execute(
    () => impostaAccensioneProcesso(props.codice, gestoAccensione.value, motivo),
    { successMessage: t('amministrazione.processi.accensione_ok') },
  )
  if (res !== null) {
    gestoAccensione.value = undefined
    await carica()
  }
}

// ⛔ Il vocabolario delle forme è del BACKEND (`sveglie.py`: FORMA_TIMER,
//    FORMA_SERVIZIO). Qui si nomina il solo valore su cui il template
//    RAMIFICA — «Esegui ora» compare sui timer e non sui servizi (è natura,
//    non stato: brief §8.5 punto 2) — e non si ridichiara l'enum.
const FORMA_TIMER = 'timer'
// ⭐ L'azienda per cui la fabbrica ha detto «c'è già, ed è spento». Si tiene il
//    CODICE e non un booleano: cambiando scelta nella tendina il pulsante di
//    riattivazione deve sparire, o resterebbe acceso su un'altra azienda.
// ⛔ Non si calcola qui se un utente tecnico spento esista: lo saprebbe solo
//    ricostruendo lo username deterministico `processo@azienda`, che è una
//    regola del DATABASE — scriverla anche qui la renderebbe due, e la seconda è
//    quella che diverge il giorno che il formato cambia.
const daRiattivare = ref(null)
const codiceRifiuto = 'E_UTENTE_TECNICO_DA_RIATTIVARE'

// ⭐ Le aziende che questo processo NON serve arrivano dal dettaglio: sono
//    l'elenco su cui il verbo agisce. Senza, il pannello mostrerebbe due
//    identità e non direbbe che la terza azienda è scoperta.
const emittentiScoperti = computed(
  () => (dettaglio.value?.emittenti_non_serviti || []).map((e) => ({
    label: e.emittente_codice, value: e.emittente_codice,
  })),
)

// ⛔ «Questo processo vuole un utente tecnico?» NON si calcola qui: arriva dal
//    dettaglio come `vuole_identita`, dalla stessa espressione che la lista
//    legge da sempre. Fino al 2026-09-15 il drawer rifaceva il conto da sé con
//    `classe === 'DOMINIO' && ['PGAGENT', 'COMMAND'].includes(canale)` — una
//    copia della regola del database senza nessun test che la guardasse — ed è
//    rimasta indietro quando il DB ha aggiunto il canale `CODA_AUTOMATICA`
//    (05-09): su `chiusura_scadenze_daily` diceva «non gli serve» mentre ne usa
//    uno per azienda, e nascondeva l'avviso delle aziende scoperte. Il difetto
//    non dava nessun errore. La regola ha una sede sola, e non è questa.

// Scopo: carica dettaglio + corse del processo aperto.
// ⚠️ Anche il guard su `visible`: le ricariche dopo un verbo (`eseguiOra`,
//    `creaIdentita`) arrivano al ritorno di una chiamata, e se nel frattempo
//    il drawer è stato chiuso ridisegnerebbero un dettaglio che il watch di
//    chiusura ha appena azzerato.
async function carica() {
  if (!props.visible || !props.codice) return
  caricamento.value = true
  try {
    const [det, run] = await Promise.all([
      execute(() => getProcesso(props.codice)),
      execute(() => listProcessoRun(props.codice, { limit: CORSE_MOSTRATE })),
    ])
    // ⚠️ `execute` restituisce GIA' il payload scartato dall'envelope
    //    (`{data, meta}` -> `data`): scartarlo una seconda volta darebbe
    //    `undefined`, e il drawer sarebbe vuoto SENZA nessun errore.
    dettaglio.value = det ?? null
    corse.value = run?.results ?? []
    emittenteScelto.value = null
    daRiattivare.value = null
  } finally {
    caricamento.value = false
  }
}

// ⚠️ `immediate` non serve — il drawer nasce chiuso — ma il watch sì: il
//    componente resta montato e cambia solo la prop quando si apre un altro
//    processo dalla lista.
watch(() => [props.visible, props.codice], ([aperto]) => {
  if (aperto) carica()
  else dettaglio.value = null
})

// Scopo: crea l'utente tecnico per l'azienda scelta, poi ricarica.
// ⛔ Nessuna scorciatoia «crea tutti quelli che mancano»: sarebbe il sistema che
//    concede perimetri da solo, cioè quello che la decisione D-9 ha escluso.
//
// ⚠️ Il `catch` intercetta SOLO per leggere il codice, e poi rilancia: il toast e
//    il resto della gestione errori restano dove stanno (`execute`). Senza
//    questo, la frase del database — «va riattivato, non creato di nuovo» —
//    arriverebbe all'operatore senza il pulsante che la esegue.
async function creaIdentita() {
  if (!emittenteScelto.value) return
  const azienda = emittenteScelto.value
  creazioneInCorso.value = true
  daRiattivare.value = null
  try {
    const res = await execute(
      () => creaUtenteTecnico(props.codice, azienda).catch((err) => {
        if (err?.response?.data?.error?.code === codiceRifiuto) {
          daRiattivare.value = azienda
        }
        throw err
      }),
    )
    if (res !== null) {
      notify.success(t('amministrazione.processi.identita_creata'))
      emit('identita-creata')
      await carica()
    }
  } finally {
    creazioneInCorso.value = false
  }
}

// Scopo: riaccende l'utente tecnico spento dell'azienda scelta, poi ricarica.
// ⚠️ Riaccende TUTTA la terna (utente, identità, legame): la fabbrica non
//    ammette una riattivazione parziale, perché un anello spento fermerebbe il
//    processo lasciandolo con l'aria di essere a posto.
async function riattivaIdentita() {
  if (!daRiattivare.value) return
  creazioneInCorso.value = true
  try {
    const res = await execute(
      () => riattivaUtenteTecnico(props.codice, daRiattivare.value),
    )
    if (res !== null) {
      notify.success(t('amministrazione.processi.identita_riattivata'))
      daRiattivare.value = null
      emit('identita-creata')
      await carica()
    }
  } finally {
    creazioneInCorso.value = false
  }
}

// Scopo: «questa sveglia si può lanciare adesso?» — letto dalla capability
//        del backend, mai ricalcolato qui. La terna `can_esegui_ora` /
//        `_reason` / `_reason_key` / `_dettaglio` la produce lo STESSO
//        predicato con cui l'endpoint rifiuta (`motivi_esegui_ora`): così il
//        tooltip e il 4xx non possono dire due cose diverse (api.md
//        §Capability di riga, «il backend trasporta, non deduce»).
// ⛔ Non si guarda l'accensione né `avvio_manuale` per decidere: sono dati da
//    MOSTRARE, e la regola che li combina ha una sede sola, nel backend.
function eseguiOraBloccato(sveglia) {
  return bloccoAttivo(sveglia, 'can_esegui_ora', 'can_esegui_ora')
}

// Scopo: il testo del tooltip sul pulsante: il MOTIVO se spento, cosa fa se
//        acceso. Fail-visible: senza chiave si vede il codice macchina.
function eseguiOraTooltip(sveglia) {
  return eseguiOraBloccato(sveglia)
    ? motivoBloccoRiga(t, te, sveglia, 'can_esegui_ora')
    : t('amministrazione.processi.esegui_ora_tooltip')
}

// Scopo: conferma, poi accoda. L'azione è `pericolosa = true` a catalogo
//        (`config.azioni_processo`, brief D-D): la conferma è il minimo, e il
//        messaggio nomina unit E comando — chi preme deve leggere che cosa
//        sta lanciando, non solo su quale riga.
function chiediEseguiOra(sveglia) {
  confirmAction({
    header: t('amministrazione.processi.esegui_ora_conferma_titolo'),
    message: t('amministrazione.processi.esegui_ora_conferma', {
      unit: sveglia.unit,
      comando: sveglia.comando.join(' '),
    }),
    acceptLabel: t('amministrazione.processi.esegui_ora'),
    acceptIcon: MANAGE_ICONS.PLAY,
    onAccept: () => eseguiOra(sveglia),
  })
}

// Scopo: accoda il lavoro e RICARICA il dettaglio, così la riga passa a «già
//        in coda» e il pulsante si spegne da sé — dalla capability, non da uno
//        stato locale che direbbe «in coda» anche dopo che il lavoro è finito.
// ⚠️ Nessun polling: il gesto è asincrono per costruzione e il toast lo dice.
//    La corsa comparirà fra le «Ultime corse» alla riapertura, con
//    `origine = COMMAND` e lo username di chi ha premuto.
// ⚠️ Il rifiuto (422/409/501) arriva dal toast di `execute`, con la frase a
//    catalogo: non c'è niente da tradurre qui. ⛔ Ma si RICARICA anche su
//    rifiuto: un 409 «già in coda» o un 501 «spenta» dicono che la schermata
//    era invecchiata, e lasciarla com'è terrebbe acceso un pulsante che il
//    backend ha appena rifiutato — l'operatore lo ripremerebbe per leggere lo
//    stesso toast.
async function eseguiOra(sveglia) {
  eseguiInCorso.value = sveglia.unit
  try {
    const res = await execute(() => eseguiOraProcesso(props.codice, sveglia.unit))
    if (res !== null) {
      notify.success(
        t('amministrazione.processi.esegui_ora_accodato', { job_id: res?.job_id ?? '?' }),
      )
    }
  } finally {
    eseguiInCorso.value = null
    await carica()
  }
}
</script>

<template>
  <!-- ⚠️ WIDE_PLUS e non COMPLEX (rilievo di Tid, 2026-09-15): a 800 px il tab
       «Sveglie» sforava — la tabella voleva 983 px su `run_fatturazione_batch`
       — e «Esegui ora», ultima colonna, finiva oltre la barra di scorrimento.
       La larghezza da sola non basta, perché unit e comando sono testo libero
       del deploy: le due colonne vanno anche a capo (`app-proc-wrap`), così il
       pulsante resta in vista qualunque riga dichiari domani `sveglie.json`. -->
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="codice || ''"
    :icon="NAV_ICONS.PROCESSI_AUTOMATICI"
    :action="t('amministrazione.processi.drawer_action')"
    :width="DRAWER_WIDTH.WIDE_PLUS"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <template v-if="dettaglio">
      <div class="app-proc-testa">
        <Tag :value="dettaglio.classe" severity="info" />
        <Tag :value="dettaglio.canale" severity="secondary" />
        <Tag
          v-if="!dettaglio.attivo"
          :value="t('amministrazione.stato_inattivo')"
          severity="danger"
        />
        <span class="app-proc-descrizione">{{ dettaglio.descrizione }}</span>
      </div>

      <!-- L'accensione su QUESTA installazione: stato, provenienza, ambiente
           e l'interruttore. Solo per chi ha una sveglia: un processo `CODA`
           lo avvia una persona, e non c'è niente da accendere. -->
      <div v-if="accensione" class="app-proc-accensione">
        <Tag
          :value="accensione.ambiente
            ? t('amministrazione.processi.ambiente', { ambiente: etichettaAmbiente(accensione.ambiente) })
            : t('amministrazione.processi.ambiente_non_dichiarato')"
          :severity="accensione.ambiente ? 'secondary' : 'warn'"
        />
        <template v-if="accensione.ha_sveglia">
          <Tag
            :value="accensione.acceso === true
              ? t('amministrazione.processi.acceso')
              : accensione.acceso === false
                ? t('amministrazione.processi.spento')
                : t('amministrazione.processi.accensione_non_decidibile')"
            :severity="accensione.acceso === true ? 'success'
              : accensione.acceso === false ? 'secondary' : 'warn'"
          />
          <small class="app-field-hint">{{ provenienzaAccensione(accensione) }}</small>
          <template v-if="accensione.can_imposta_accensione">
            <Button
              v-if="accensione.acceso !== false"
              :label="t('amministrazione.processi.spegni')"
              :icon="MANAGE_ICONS.DISATTIVA"
              size="small" outlined severity="danger"
              @click="gestoAccensione = false"
            />
            <!-- ⚠️ Il tooltip sta sull'INVOLUCRO: un `<button disabled>` non
                 emette eventi del mouse, e a pulsante spento è proprio quando
                 il motivo serve (come «Esegui ora»). -->
            <span
              v-if="accensione.acceso !== true"
              class="app-action-tooltip-wrap"
              v-tooltip.top="accendiTooltip(accensione)"
            >
              <Button
                :label="t('amministrazione.processi.accendi')"
                :icon="MANAGE_ICONS.RIATTIVA"
                size="small" outlined
                :disabled="accendiBloccato(accensione)"
                @click="gestoAccensione = true"
              />
            </span>
            <Button
              v-if="accensione.scelta_a_mano"
              :label="t('amministrazione.processi.torna_al_default')"
              :icon="MANAGE_ICONS.UNDO"
              size="small" text
              @click="gestoAccensione = null"
            />
          </template>
        </template>
      </div>

      <Tabs v-model:value="tabAttiva">
        <TabList>
          <Tab value="bersagli">
            {{ t('amministrazione.processi.tab_bersagli') }}
            ({{ dettaglio.bersagli.length }})
          </Tab>
          <Tab value="identita">
            {{ t('amministrazione.processi.tab_identita') }}
            ({{ dettaglio.identita.length }})
          </Tab>
          <Tab value="run">
            {{ t('amministrazione.processi.tab_run') }} ({{ corse.length }})
          </Tab>
          <Tab value="sveglie">
            {{ t('amministrazione.processi.tab_sveglie') }} ({{ sveglie.length }})
          </Tab>
        </TabList>

        <TabPanels>
          <TabPanel value="bersagli">
            <!-- ⚠️ È un elenco DICHIARATO: prova che qualcuno ha detto dove
                 il processo scrive, non che scriva solo lì. -->
            <p class="app-proc-help">
              {{ t('amministrazione.processi.bersagli_help') }}
            </p>
            <table class="app-proc-tabella">
              <thead>
                <tr>
                  <th>{{ t('amministrazione.processi.col_tabella') }}</th>
                  <th>{{ t('amministrazione.processi.col_percorso') }}</th>
                  <th>{{ t('amministrazione.processi.col_colonna') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in dettaglio.bersagli" :key="`${b.schema_tabella}.${b.nome_tabella}`">
                  <td>{{ b.schema_tabella }}.{{ b.nome_tabella }}</td>
                  <!-- ⛔ Percorso assente = il processo scrive dove non c'è
                       niente su cui filtrare: è il caso che il presidio
                       «dominio senza emittente» esiste per prendere. -->
                  <td>
                    <Tag
                      v-if="!b.emittente_via"
                      :value="t('amministrazione.processi.senza_percorso')"
                      severity="warn"
                    />
                    <span v-else>{{ b.emittente_via }}</span>
                  </td>
                  <td>{{ b.emittente_colonna || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </TabPanel>

          <TabPanel value="identita">
            <p class="app-proc-help">
              {{ dettaglio.vuole_identita
                ? t('amministrazione.processi.identita_help')
                : t('amministrazione.processi.identita_non_serve') }}
            </p>
            <table v-if="dettaglio.identita.length" class="app-proc-tabella">
              <thead>
                <tr>
                  <th>{{ t('amministrazione.processi.col_utente') }}</th>
                  <th>{{ t('amministrazione.processi.col_azienda') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="i in dettaglio.identita" :key="i.auth_user_id">
                  <td>{{ i.username }}</td>
                  <td>{{ i.emittente_codice }}</td>
                </tr>
              </tbody>
            </table>

            <!-- ⭐ Il numero che rompe il silenzio: senza questo blocco, «due
                 identità» si legge come «tutto a posto» anche quando la terza
                 azienda non viene servita e il suo lavoro non parte. -->
            <template v-if="dettaglio.vuole_identita && emittentiScoperti.length">
              <Message severity="warn" :closable="false">
                {{ t('amministrazione.processi.aziende_scoperte', { n: emittentiScoperti.length }) }}
              </Message>
              <div class="app-proc-crea">
                <Select
                  v-model="emittenteScelto"
                  :options="emittentiScoperti"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('amministrazione.processi.scegli_azienda')"
                  @change="daRiattivare = null"
                />
                <Button
                  :label="t('amministrazione.processi.crea_identita')"
                  :icon="MANAGE_ICONS.ADD"
                  :disabled="!emittenteScelto || creazioneInCorso"
                  :loading="creazioneInCorso"
                  @click="creaIdentita"
                />
                <!-- ⭐ Compare SOLO dopo che la fabbrica ha detto che c'è
                     qualcosa di spento: è il rifiuto parlante a portare qui,
                     non un'ipotesi del frontend. -->
                <Button
                  v-if="daRiattivare"
                  :label="t('amministrazione.processi.riattiva_identita')"
                  :icon="MANAGE_ICONS.RIATTIVA"
                  severity="warn"
                  :disabled="creazioneInCorso"
                  :loading="creazioneInCorso"
                  @click="riattivaIdentita"
                />
              </div>
            </template>
          </TabPanel>

          <TabPanel value="run">
            <p class="app-proc-help">
              {{ t('amministrazione.processi.run_help', { n: CORSE_MOSTRATE }) }}
            </p>
            <table v-if="corse.length" class="app-proc-tabella">
              <thead>
                <tr>
                  <th>{{ t('amministrazione.processi.col_quando') }}</th>
                  <th>{{ t('amministrazione.processi.col_jobname') }}</th>
                  <th>{{ t('amministrazione.processi.col_origine') }}</th>
                  <th>{{ t('amministrazione.processi.col_esito') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in corse" :key="r.id">
                  <td>{{ displayTimestamp(r.started_at) }}</td>
                  <td>{{ r.jobname }}</td>
                  <td>{{ r.origine }}</td>
                  <td>
                    <!-- ⚠️ `ok` è a tre stati, e `null` ha tre letture: corsa
                         SALTATA (lock occupato: chiusa e senza esito, la dice
                         `saltata`), corsa ancora APERTA (`ended_at` vuoto), o
                         chiusa senza che nessuno abbia scritto l'esito.
                         Appiattirlo a rosso, o tutto a «in corso», direbbe il falso. -->
                    <Tag
                      v-if="r.saltata"
                      v-tooltip.top="t('amministrazione.processi.esito_saltata_tooltip')"
                      :value="t('amministrazione.processi.esito_saltata')"
                      severity="secondary"
                    />
                    <Tag
                      v-else-if="r.ok === true"
                      :value="t('amministrazione.processi.esito_ok')"
                      severity="success"
                    />
                    <Tag
                      v-else-if="r.ok === false"
                      :value="r.error_code || t('amministrazione.processi.esito_ko')"
                      severity="danger"
                    />
                    <Tag
                      v-else-if="!r.ended_at"
                      :value="t('amministrazione.processi.esito_in_corso')"
                      severity="secondary"
                    />
                    <Tag
                      v-else
                      :value="t('amministrazione.processi.esito_non_scritto')"
                      severity="warn"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="app-proc-help">
              {{ t('amministrazione.processi.run_nessuno') }}
            </p>
          </TabPanel>

          <TabPanel value="sveglie">
            <!-- ⚠️ È il DICHIARATO di deploy (`sveglie.json`), non lo stato
                 di questo host: cosa sta girando davvero lo dicono le corse. -->
            <p class="app-proc-help">
              {{ t('amministrazione.processi.sveglie_help') }}
            </p>
            <table v-if="sveglie.length" class="app-proc-tabella">
              <thead>
                <tr>
                  <th>{{ t('amministrazione.processi.col_unit') }}</th>
                  <th>{{ t('amministrazione.processi.col_forma') }}</th>
                  <th>{{ t('amministrazione.processi.col_cadenza') }}</th>
                  <th>{{ t('amministrazione.processi.col_comando') }}</th>
                  <th>{{ t('common.col_azioni') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in sveglie" :key="s.unit">
                  <td class="app-proc-wrap">{{ s.unit }}</td>
                  <td>
                    <Tag
                      :value="s.forma === FORMA_TIMER
                        ? t('amministrazione.processi.forma_timer')
                        : t('amministrazione.processi.forma_servizio')"
                      :severity="s.forma === FORMA_TIMER ? 'info' : 'secondary'"
                    />
                  </td>
                  <td>
                    <!-- ⭐ Sulle sveglie calendariali `oncalendar` e' solo la
                         sveglia oraria: la cadenza del LAVORO e' `dovuto`, nel
                         fuso dell'azienda (brief un-solo-fuso-aziendale T-9). -->
                    <span v-if="s.dovuto">{{ descriviDovuto(s.dovuto) }}</span>
                    <code v-else-if="s.oncalendar" class="app-proc-mono">{{ s.oncalendar }}</code>
                    <span v-else>{{ t('amministrazione.processi.sveglia_sempre_accesa') }}</span>
                  </td>
                  <td class="app-proc-wrap"><code class="app-proc-mono">{{ s.comando.join(' ') }}</code></td>
                  <td>
                    <!-- ⭐ Solo sui TIMER: su un servizio sempre acceso non
                         c'è una corsa da lanciare — non è un candidato, non
                         è uno stato, quindi il pulsante NON compare (invece
                         di comparire spento). Sul timer dichiarato non
                         candidato compare spento COL MOTIVO.
                         ⚠️ Il tooltip sta sull'INVOLUCRO: un `<button
                         disabled>` non emette eventi del mouse, e a pulsante
                         spento è proprio quando il motivo serve. -->
                    <span
                      v-if="s.forma === FORMA_TIMER"
                      class="app-action-tooltip-wrap"
                      v-tooltip.left="eseguiOraTooltip(s)"
                    >
                      <Button
                        :label="t('amministrazione.processi.esegui_ora')"
                        :icon="MANAGE_ICONS.PLAY"
                        size="small"
                        outlined
                        :disabled="eseguiOraBloccato(s) || eseguiInCorso !== null"
                        :loading="eseguiInCorso === s.unit"
                        @click="chiediEseguiOra(s)"
                      />
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="app-proc-help">
              {{ t('amministrazione.processi.sveglie_nessuna') }}
            </p>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>

    <p v-else-if="caricamento" class="app-proc-help">{{ t('common.loading') }}</p>

    <MotivoDialog
      v-model:visible="dialogAccensione"
      :header="t(`amministrazione.processi.${chiaveGesto(gestoAccensione)}`)"
      :label="t('amministrazione.processi.accensione_motivo')"
      obbligatorio
      :loading="loading"
      :invalid="campiErrati.includes('motivo')"
      :save-label="t(`amministrazione.processi.${chiaveGesto(gestoAccensione)}`)"
      :save-severity="gestoAccensione === false ? 'danger' : null"
      @conferma="confermaAccensione"
    >
      <p>{{ t(`amministrazione.processi.${chiaveGesto(gestoAccensione)}_spiegazione`) }}</p>
    </MotivoDialog>
  </AppDrawer>
</template>

<style scoped>
.app-proc-testa { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.app-proc-descrizione { font-size: 0.9rem; opacity: 0.85; }
.app-proc-accensione { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0; }
.app-proc-help { font-size: 0.85rem; opacity: 0.8; margin: 0.5rem 0; }
/* Tabelle di consultazione, non liste: scorrono nel proprio contenitore. */
.app-proc-tabella { width: 100%; display: block; overflow-x: auto; font-size: 0.85rem; }
.app-proc-tabella th, .app-proc-tabella td {
  text-align: left; padding: 0.25rem 0.5rem; white-space: nowrap;
}
.app-proc-tabella th { opacity: 0.7; font-weight: 500; }
/* Le celle di TESTO LIBERO del deploy (unit, comando) vanno a capo: la loro
 * lunghezza non la decide questa schermata, e con `nowrap` spingerebbero
 * l'ultima colonna — il pulsante — oltre la barra di scorrimento. Le altre
 * restano `nowrap`: sono tag, date e codici corti. `anywhere` spezza dentro
 * un token solo se non c'è un punto di rottura naturale (spazio, trattino). */
.app-proc-tabella td.app-proc-wrap { white-space: normal; overflow-wrap: anywhere; }
.app-proc-crea { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.75rem; }
/* Cadenza e comando si LEGGONO come sono scritti nel deploy: il `<code>` dà
 * già il monospace, qui solo la taglia — senza sfondo (è un dato, non un
 * pulsante). */
.app-proc-mono { font-size: 0.8rem; }
</style>
