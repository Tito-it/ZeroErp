<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer autonomo di UN registro di numerazione — creazione e modifica.
//        Richiamabile dal tab dell'emittente e, un domani, da qualunque altra
//        superficie (`feedback_drawer_autonomi`).
//
// ⭐ IL PEZZO CHE VALE LA MASCHERA È LA FORMA DEL NUMERO. `prefisso`,
//    `suffisso` e `lunghezza_numero` sono l'unico posto in cui si può cambiare
//    come si chiamano i documenti: prima vivevano in `config.sistema_codici`,
//    che un pannello ce l'ha; dal 2026-08-31 vivono sul registro, che non ce
//    l'aveva. È la domanda che ha aperto tutto il cantiere del prefisso — «ho
//    visto ORD0000001, dov'è fisso ORD?» — e fino a oggi la risposta era un
//    campo che nessuno poteva leggere né correggere da nessuna schermata.
//
// ⛔ LA SOLA-LETTURA DELLA FORMA È PER RIGA, NON CATEGORICA. La decide
//    `forma_blocco_reason`, che arriva da `script.fn_check_registro_forma_
//    modificabile` — la STESSA funzione che il guard DB chiama per rifiutare.
//    Un registro che non ha mai consegnato un numero si modifica; uno che l'ha
//    fatto no, e il motivo si LEGGE: un campo grigio senza spiegazione è la
//    stessa promessa mancata del cestino spento senza tooltip.
//
// ⚠️ I TRE CAMPI FISCALI SOLO DOVE LA FAMIGLIA LI AMMETTE, e non basta
//    nasconderli: vanno anche non spediti. Il `CHECK` chk_registri_
//    fatturazione_famiglia_regole_fattura li rifiuta altrove, e un
//    `defaultForm()` che li tiene in memoria li porta comunque.
//
// ⭐ E «dove li ammette» NON è più un nome cablato (§11.10 FE-F2, 2026-09-02).
//    Fino a ieri qui c'era `REGISTRO_FAMIGLIA_FISCALE = 'FATTURA'`, gemello di
//    un letterale identico nel backend: due copie della stessa affermazione, in
//    due linguaggi, che nessun presidio teneva allineate. Ora la risposta la dà
//    il catalogo — `famiglie_documento.presidia_data_documento` — e arriva col
//    lookup delle famiglie, insieme ai default della forma.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
// ⛔ Mai formattare una data inline: la sede è unica
//    (`feedback_locale_formatters_centralizzato`).
import { displayDate, oggiAziendale } from '../../core/utils/date'
import { useLookup } from '../../core/composables/useLookup'
import { DRAWER_WIDTH, FIELD_LENGTH, MANAGE_ICONS } from '../../core/constants'
import {
  REGISTRO_CIFRE_MAX,
  REGISTRO_CIFRE_MIN,
  REGISTRO_POLITICA_DATA,
  REGISTRO_POLITICA_DATA_NEUTRA,
  REGISTRO_RESET_POLICY,
  REGISTRO_RESET_POLICY_DEFAULT,
} from '../constants'
import { useRegistriNumerazioneStore } from '../stores/registriNumerazione'
import { getRegistro, listRegistri } from '../api/registriNumerazione'
import { lookupFamiglie } from '../api/famiglieDocumento'
import AppDrawer from '../../core/components/AppDrawer.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Message from 'primevue/message'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'

const { t, te } = useI18n()
const notify = useNotify()
const store = useRegistriNumerazioneStore()
const isReadonly = useInjectReadonly()
// `campiErrati`: i campi che il backend nomina nel rifiuto (`error.fields`).
const { execute, campiErrati } = useApiHandler()

const props = defineProps({
  visible: Boolean,
  // `null` = creazione. Il drawer non ha una prop `mode`: la modalità è un
  // fatto dell'id, e due sorgenti di verità divergono.
  registroId: { type: Number, default: null },
  emittenteRagioneSociale: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'saved'])

const form = ref(defaultForm())
// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const dettaglio = ref(null)
const salvando = ref(false)

// Vocabolario APERTO: le famiglie stanno in `vendite.famiglie_documento` e una
// nuova arriva dal suo CRUD, non da un rilascio del frontend.
// ⛔ E NON dal lookup generico, ed è la voce BE-F1 del brief (decisione di Tid,
//    2026-09-02: «lookup generico non adatto»). `fn_get_lookup_codici` torna
//    id/codice/descrizione/attivo e non può portare i default della forma né le
//    colonne di natura — non è un suo difetto, è generico e va lasciato
//    generico. Qui servono `prefisso_default`, `lunghezza_default`,
//    `gestisce_serie` e `presidia_data_documento`, che sono esattamente ciò che
//    questa maschera deve sapere.
const { items: famiglieRaw, load: caricaFamiglie } = useLookup(lookupFamiglie)

// ⚠️ Il valore da spedire e' `codice_interno`: e' quello che la FK
//    `fk_registri_fatturazione_famiglia` referenzia.
// ⛔ E LE FAMIGLIE GIÀ SERVITE NON SI OFFRONO (§FE-3, «Nuovo deve inciampare
//    prima»): `uq_registri_fatturazione_famiglia_emittente_utility` ne ammette
//    UNO solo e **non filtra su `attivo`** — un registro spento continua a
//    occupare lo slot. Offrire quella riga significa mandare l'operatore a
//    prendere un 409 su una scelta che si sapeva già impossibile.
const famiglie = computed(() => famiglieRaw.value.map((f) => {
  const occupata = slotOccupato(f.codice_interno)
  return {
    value: f.codice_interno,
    label: occupata
      ? `${f.descrizione} — ${t('amministrazione.registri_numerazione.slot_occupato')}`
      : f.descrizione,
    disabled: occupata,
  }
}))

// La famiglia scelta, per intero: da qui vengono i default della forma e le due
// domande di natura (presidia la data? gestisce le serie?).
const famigliaCorrente = computed(
  () => famiglieRaw.value.find((f) => f.codice_interno === form.value.famiglia_documento) || null,
)

// ⭐ I registri che l'emittente ha GIÀ, spenti compresi: servono a sapere quali
//    slot sono presi. Si leggono una volta all'apertura in creazione.
// ⚠️ `limit` alto e non la pagina corrente della lista: la lista è paginata a
//    25, e uno slot occupato da un registro in seconda pagina risulterebbe
//    libero — cioè il presidio tacerebbe proprio dove serve.
const registriEsistenti = ref([])

async function caricaRegistriEsistenti() {
  registriEsistenti.value = []
  if (isEdit.value || !store.emittenteSoggettoRuoloId) return
  const res = await listRegistri({
    emittente_soggetto_ruolo_id: store.emittenteSoggettoRuoloId,
    // ⛔ 200, il massimo della lista: dal 2026-10-21 oltre il massimo e' un 400
    //    (fino a quel giorno il `500` di qui veniva ridotto a 200 in silenzio).
    limit: 200,
    offset: 0,
  })
  registriEsistenti.value = res.data.data.results || []
}

// Scopo: «questo slot è già preso?» — lo slot è la terna (famiglia, emittente,
//        utility), e l'emittente lo dà il contesto.
function slotOccupato(codiceFamiglia) {
  if (isEdit.value) return false
  const utility = form.value.utility_id ?? null
  return registriEsistenti.value.some(
    (r) => r.famiglia_documento === codiceFamiglia && (r.utility_id ?? null) === utility,
  )
}

const opzioniPolitica = computed(() => REGISTRO_POLITICA_DATA.map((v) => ({
  value: v,
  label: t(`amministrazione.registri_numerazione.politica_${v.toLowerCase()}`),
})))

// ⭐ Stessa forma di `opzioniPolitica`: il letterale sta in `constants.js`,
//    l'etichetta nei locales. Le due voci sono quelle del `CHECK`, non di piu'.
const opzioniReset = computed(() => REGISTRO_RESET_POLICY.map((v) => ({
  value: v,
  label: t(`amministrazione.registri_numerazione.reset_${v.toLowerCase()}`),
})))

// ⭐ L'etichetta della politica corrente, per la sola lettura in modifica.
//    ⛔ NON si ricostruisce la chiave i18n una seconda volta: il prefisso
//    `reset_` sarebbe un letterale in due sedi, e chi rinomina le chiavi ne
//    troverebbe una sola. Si cerca dentro le opzioni, che sono gia' l'elenco
//    di cosa quei valori si chiamano a video.
const resetLabel = computed(() => {
  const scelta = opzioniReset.value.find((o) => o.value === form.value.reset_policy)
  // Ripiego sul valore grezzo e non su una stringa vuota: se un giorno il
  // database ammettesse un terzo valore, a video si vedrebbe QUELLO invece di
  // un campo muto — che e' l'unico modo per accorgersene.
  return scelta?.label || form.value.reset_policy || '—'
})

const isEdit = computed(() => props.registroId != null)

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    // ⛔ Nessuna famiglia preselezionata: il default era `FATTURA`, cioè lo
    //    stesso letterale che questo cantiere ha tolto. La sceglie chi crea.
    famiglia_documento: null,
    utility_id: null,
    serie_default: null,
    prefisso: '',
    suffisso: '',
    lunghezza_numero: 7,
    politica_data_documento: REGISTRO_POLITICA_DATA_NEUTRA,
    limite_emissione_giorni: null,
    limite_emissione_giorno_mese: null,
    // ⭐ Lo stesso default della COLONNA, non una scelta della maschera: un
    //    registro creato senza toccare il campo deve nascere come nasceva
    //    prima che il campo esistesse.
    reset_policy: REGISTRO_RESET_POLICY_DEFAULT,
    // ⛔ NON si sceglie da qui: lo decide un risolutore a INSERT dal default
    //    della famiglia. In creazione vale il default della colonna (false), e
    //    dopo il salvataggio la rilettura porta il valore vero.
    anno_nel_numero: false,
  }
}

// ⭐ LA DOMANDA È DEL CATALOGO, NON DEL NOME. `ammette_regole_fiscali` dice se
//    questa famiglia ammette i tre campi condizionati; `gestisce_serie` se i
//    suoi documenti registrano la serie da qualche parte.
// ⛔ E NON è `presidia_data_documento`, che il 2026-09-02 aveva la stessa
//    risposta su tutte e cinque: quella dice se c'è un PAVIMENTO sulla data del
//    documento, questa cosa ammette il `CHECK` dei registri. Sono due domande
//    diverse con la stessa risposta di oggi — e la prima famiglia creata dal
//    CRUD le separa, perché nasce presidiata e non fiscale (§12.2).
const ammetteRegoleFiscali = computed(
  () => famigliaCorrente.value?.ammette_regole_fiscali === true,
)
const gestisceSerie = computed(
  () => famigliaCorrente.value?.gestisce_serie === true,
)

// ⭐ IL MOTIVO PER CUI LA FORMA NON SI TOCCA, letto e non dedotto.
const formaBloccata = computed(() => Boolean(dettaglio.value?.forma_blocco_reason))
const motivoForma = computed(() =>
  dettaglio.value ? motivoBloccoRiga(t, te, dettaglio.value, 'forma_blocco') : '',
)

// ⭐ L'ANTEPRIMA, e si compone QUI. Non è una regola: è la concatenazione di
//    ciò che l'operatore ha appena scritto, quindi chiederla al backend
//    significherebbe un giro di rete per una `padStart`. È l'unica forma in cui
//    si capisce cosa si sta cambiando senza doverlo dedurre.
const anteprima = computed(() => {
  const cifre = Math.max(
    REGISTRO_CIFRE_MIN,
    Math.min(Number(form.value.lunghezza_numero) || REGISTRO_CIFRE_MIN, REGISTRO_CIFRE_MAX),
  )
  // ⭐ IL SEGMENTO DELL'ANNO, e non e' cosmesi: su un registro con
  //    `anno_nel_numero` il database compone `prefisso || <anno>- || progressivo
  //    || suffisso` (`fn_assegna_numero_documento`, passo 5). Senza questo pezzo
  //    l'anteprima mostrerebbe una stringa che quel sezionale non produce —
  //    cioe' un campo plausibile e falso, che e' peggio di un campo assente.
  // ⚠️ L'anno e' quello CORRENTE perche' l'anteprima parla del prossimo numero;
  //    il numero vero prende l'anno del DOCUMENTO, che puo' differire su un
  //    documento retrodatato.
  const anno = form.value.anno_nel_numero ? `${oggiAziendale().getFullYear()}-` : ''
  return `${form.value.prefisso || ''}${anno}${'1'.padStart(cifre, '0')}${form.value.suffisso || ''}`
})

async function carica() {
  dettaglio.value = null
  if (!isEdit.value) {
    form.value = defaultForm()
    // ⚠️ Anche la memoria di cosa ha messo la famiglia: senza, riaprendo il
    //    drawer il primo cambio di famiglia crederebbe «toccato dall'operatore»
    //    un valore che aveva scritto lui stesso al giro prima.
    defaultsApplicati.value = {
      prefisso: '',
      lunghezza: form.value.lunghezza_numero,
    }
    return
  }
  const res = await getRegistro(props.registroId)
  const dati = res.data.data
  dettaglio.value = dati
  form.value = {
    codice: dati.codice ?? '',
    descrizione: dati.descrizione ?? '',
    famiglia_documento: dati.famiglia_documento,
    utility_id: dati.utility_id,
    serie_default: dati.serie_default,
    prefisso: dati.prefisso ?? '',
    suffisso: dati.suffisso ?? '',
    lunghezza_numero: dati.lunghezza_numero ?? 7,
    politica_data_documento:
      dati.politica_data_documento ?? REGISTRO_POLITICA_DATA_NEUTRA,
    limite_emissione_giorni: dati.limite_emissione_giorni,
    limite_emissione_giorno_mese: dati.limite_emissione_giorno_mese,
    reset_policy: dati.reset_policy ?? REGISTRO_RESET_POLICY_DEFAULT,
    anno_nel_numero: dati.anno_nel_numero === true,
  }
}

watch(() => props.visible, async (aperto) => {
  if (!aperto) {
    return
  }
  campiErrati.value = []
  await Promise.all([caricaFamiglie(), carica(), caricaRegistriEsistenti()])
  // Fotografia DOPO i tre caricamenti: il form e' popolato dal codice.
  if (props.visible) fissa()
})

// ⭐ FE-F1: LA FORMA SI PRECOMPILA DALLA FAMIGLIA, e non è una comodità. Fino
//    al 2026-09-02 il form nasceva con `prefisso: ''` e `lunghezza_numero: 7`
//    cablati, quindi una COMMESSA creata a mano usciva a 7 cifre mentre quella
//    creata dal provisioning ne aveva 9: due documenti della stessa famiglia,
//    due forme diverse, e nessuno che se ne accorgesse prima di vedere un
//    numero storto.
// ⛔ Solo in CREAZIONE, e SOLO su ciò che ha messo la famiglia precedente —
//    mai su ciò che ha scritto l'operatore.
// ⚠️ La prima stesura trattava i due campi in modo diverso: il prefisso lo
//    rispettava («solo se vuoto»), le cifre le sovrascriveva sempre. Chi
//    scriveva 9 e poi cambiava famiglia si vedeva tornare 7 senza capire
//    perché, e chi scriveva un prefisso non vedeva mai quello della famiglia
//    nuova. Due regole diverse sullo stesso gesto sono un difetto, quale che
//    sia quella giusta.
// ⭐ La regola è una sola: un campo che porta ancora il default della famiglia
//    di prima è «non toccato» e si aggiorna; un campo che l'operatore ha
//    cambiato resta suo.
const defaultsApplicati = ref({
  prefisso: '',
  lunghezza: defaultForm().lunghezza_numero,
})

watch(() => form.value.famiglia_documento, (codice) => {
  if (isEdit.value || !codice) return
  const fam = famiglieRaw.value.find((f) => f.codice_interno === codice)
  if (!fam) return
  const prefissoNuovo = fam.prefisso_default || ''
  const cifreNuove = fam.lunghezza_default ?? form.value.lunghezza_numero
  if (!form.value.prefisso || form.value.prefisso === defaultsApplicati.value.prefisso) {
    form.value.prefisso = prefissoNuovo
  }
  if (form.value.lunghezza_numero == null
      || form.value.lunghezza_numero === defaultsApplicati.value.lunghezza) {
    form.value.lunghezza_numero = cifreNuove
  }
  defaultsApplicati.value = { prefisso: prefissoNuovo, lunghezza: cifreNuove }
})

// Scopo: il payload da spedire — ⛔ i campi che il verbo non ammette NON ci
//        entrano, invece di essere spediti e lasciati rifiutare.
function payload() {
  const p = {
    codice: form.value.codice,
    descrizione: form.value.descrizione,
  }
  // ⛔ I TRE campi fiscali — i due limiti E la politica data — si spediscono
  //    SOLO su FATTURA: il `CHECK` li rifiuta sulle altre quattro famiglie.
  //    La politica era il caso peggiore dei tre: stava nel `defaultForm()`
  //    senza nessun campo a video, quindi partiva sempre col suo valore
  //    cablato — un dato spedito che l'operatore non poteva né vedere né
  //    scegliere. Ora ha il suo Select, e fuori da FATTURA non parte.
  if (ammetteRegoleFiscali.value) {
    p.politica_data_documento = form.value.politica_data_documento
    p.limite_emissione_giorni = form.value.limite_emissione_giorni
    p.limite_emissione_giorno_mese = form.value.limite_emissione_giorno_mese
  }
  // La forma si spedisce solo quando è davvero modificabile: in creazione
  // sempre, in modifica solo se la check non l'ha bloccata.
  if (!isEdit.value || !formaBloccata.value) {
    p.prefisso = form.value.prefisso
    p.suffisso = form.value.suffisso
    p.lunghezza_numero = form.value.lunghezza_numero
  }
  // ⛔ `reset_policy` sta QUI e non fra i campi di modifica: è un asse della
  //    chiave del contatore, e cambiarla su un registro che ha già consegnato
  //    numeri farebbe ripartire il progressivo da 1 su un secchio nuovo. In
  //    modifica il campo si legge e non si tocca, come `serie_default`.
  if (!isEdit.value) {
    p.famiglia_documento = form.value.famiglia_documento
    p.utility_id = form.value.utility_id
    p.serie_default = form.value.serie_default
    p.reset_policy = form.value.reset_policy
  }
  return p
}

// ⛔ Fino al 2026-10-23 l'errore finiva in un `catch` vuoto, «gestito
//    dall'interceptor axios globale»: l'interceptor di `core/api.js` non mostra
//    toast, quindi un rifiuto chiudeva il giro in silenzio e il `prefisso` che i
//    due `23505` nominano non si accendeva. Ora passa da `execute`.
async function salva() {
  salvando.value = true
  try {
    const dati = await execute(() => (isEdit.value
      ? store.aggiorna(props.registroId, payload())
      : store.crea(payload())))
    if (dati === null) return
    notify.success(t('amministrazione.registri_numerazione.salvato'))
    fissa()
    emit('saved', dati)
    chiudi()
  } finally {
    salvando.value = false
  }
}

// Uscita dopo il salvataggio, diretta. Quella per volonta' dell'utente passa
// dalla conferma di AppDrawer (`conferma-uscita`).
function chiudi() {
  emit('update:visible', false)
}

const titolo = computed(() => {
  const base = isEdit.value
    ? t('amministrazione.registri_numerazione.drawer_title_edit')
    : t('amministrazione.registri_numerazione.drawer_title_new')
  return props.emittenteRagioneSociale ? `${base} — ${props.emittenteRagioneSociale}` : base
})
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="titolo"
    :icon="MANAGE_ICONS.NUMERAZIONE"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="salvando"
    @update:visible="(v) => emit('update:visible', v)"
    @save="salva"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_codice') }} *</label>
        <InputText
          v-model="form.codice"
          class="app-codice-input"
          :maxlength="FIELD_LENGTH.REGISTRO_CODICE_MAX"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('codice')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_descrizione') }} *</label>
        <InputText
          v-model="form.descrizione"
          :maxlength="FIELD_LENGTH.REGISTRO_DESCRIZIONE_MAX"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>

      <!-- ⛔ La famiglia si sceglie SOLO in creazione: cambiarla sposterebbe
           il registro di slot (famiglia/emittente/utility), che è una
           creazione, non una modifica. -->
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_famiglia_descrizione') }}</label>
        <Select
          v-if="!isEdit"
          v-model="form.famiglia_documento"
          :options="famiglie"
          option-label="label"
          option-value="value"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('famiglia_documento')"
        />
        <span v-else>{{ dettaglio?.famiglia_descrizione || form.famiglia_documento }}</span>
      </div>

      <!-- ⚠️ `serie_default` SI VEDE E NON SI TOCCA (decisione di Tid,
           2026-09-01). Il guard sulla forma non la copre — entra nella chiave
           del contatore, e il mirror CSV la riscrive a ogni migrate — quindi
           un campo editabile su di lei sarebbe l'unico senza presidio. Si
           mostra perché spiega da dove viene la serie dei numeri. -->
      <div v-if="isEdit || famigliaCorrente" class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_serie_default') }}</label>
        <span v-if="isEdit">{{ form.serie_default || '—' }}</span>
        <!-- ⭐ FE-F2: sulle famiglie che la serie non la registrano da nessuna
             parte, il campo dice PERCHÉ invece di mostrare un trattino muto.
             La frase è la stessa che il database manda quando rifiuta
             (`serie_blocco.non_gestita`): una voce sola per lo stesso fatto,
             detta prima invece che dopo il rifiuto. -->
        <small v-if="!gestisceSerie" class="app-field-hint">
          {{ t('amministrazione.registri_fatturazione.serie_blocco.non_gestita', {
            famiglia_documento: famigliaCorrente?.descrizione || form.famiglia_documento,
            serie: form.serie_default || '—',
          }) }}
        </small>
        <small v-else class="app-field-hint">
          {{ t('amministrazione.registri_numerazione.serie_hint') }}
        </small>
      </div>

      <!-- ⭐ IL RESET DEL CONTATORE, e sta accanto alla serie perché sono la
           stessa cosa: due assi della CHIAVE su cui il progressivo riparte.
           ⛔ Si sceglie SOLO in creazione — cambiarla su un registro che ha
           già numerato sposta il secchio sotto il contatore, il progressivo
           riparte da 1 e sbatte contro i numeri già scritti. In modifica si
           legge, come `serie_default`.
           ⚠️ E nessun trigger lo rifiuta: qui il campo assente È il presidio,
           non una scelta di maschera. -->
      <div class="form-field">
        <label>{{ t('amministrazione.registri_numerazione.reset_policy') }}</label>
        <Select
          v-if="!isEdit"
          v-model="form.reset_policy"
          :options="opzioniReset"
          option-label="label"
          option-value="value"
          :disabled="isReadonly"
          :invalid="campiErrati.includes('reset_policy')"
        />
        <span v-else>{{ resetLabel }}</span>
        <small class="app-field-hint">
          {{ t('amministrazione.registri_numerazione.reset_hint') }}
        </small>
      </div>
    </div>

    <!-- ── La forma del numero ───────────────────────────────────────── -->
    <h4>{{ t('amministrazione.registri_numerazione.sezione_forma') }}</h4>

    <Message v-if="formaBloccata" severity="warn" :closable="false">
      {{ motivoForma }}
    </Message>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_prefisso') }}</label>
        <!-- ⛔ `maxlength` NON è un vezzo: la colonna è `varchar(4)`, e un
             carattere in più non produce un 400 parlante ma un `DataError`,
             che non passa da `map_integrity_error`. -->
        <InputText
          v-model="form.prefisso"
          :maxlength="FIELD_LENGTH.REGISTRO_PREFISSO_MAX"
          :disabled="isReadonly || formaBloccata"
          :invalid="campiErrati.includes('prefisso')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_suffisso') }}</label>
        <InputText
          v-model="form.suffisso"
          :maxlength="FIELD_LENGTH.REGISTRO_SUFFISSO_MAX"
          :disabled="isReadonly || formaBloccata"
          :invalid="campiErrati.includes('suffisso')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.registri_numerazione.col_lunghezza_numero') }}</label>
        <InputNumber
          v-model="form.lunghezza_numero"
          :min="REGISTRO_CIFRE_MIN"
          :max="REGISTRO_CIFRE_MAX"
          :disabled="isReadonly || formaBloccata"
          :invalid="campiErrati.includes('lunghezza_numero')"
        />
      </div>
      <!-- ⭐ L'ANNO NELLA STRINGA — in SOLA LETTURA, sempre, anche in
           creazione: non è una scelta del sezionale ma una proprietà della
           sua famiglia, e a scriverla è un risolutore a INSERT
           (`trg_..._set_anno_nel_numero_ins`).
           ⚠️ Si mostra perché cambia il numero che una PERSONA legge: un
           registro che azzera ogni anno senza l'anno nella stringa consegna
           la stessa stringa in anni diversi, e il database non se ne accorge
           — la sua unicità porta l'anno in colonna. -->
      <div class="form-field">
        <label>{{ t('amministrazione.registri_numerazione.anno_nel_numero') }}</label>
        <span>{{ form.anno_nel_numero ? t('common.yes') : t('common.no') }}</span>
        <small class="app-field-hint">
          {{ t('amministrazione.registri_numerazione.anno_nel_numero_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.registri_numerazione.anteprima') }}</label>
        <strong>{{ anteprima }}</strong>
        <small class="app-field-hint">
          {{ t('amministrazione.registri_numerazione.anteprima_hint') }}
        </small>
      </div>
    </div>

    <!-- ── I campi che il CHECK ammette solo su FATTURA ───────────────── -->
    <template v-if="ammetteRegoleFiscali">
      <h4>{{ t('amministrazione.registri_numerazione.sezione_limiti') }}</h4>
      <div class="form-grid-2col">
        <!-- ⭐ La politica data è il terzo campo condizionato del §FE-4, e
             fino alla revisione critica non aveva un campo: viaggiava nel
             payload col valore di `defaultForm()`. -->
        <div class="form-field">
          <label>{{ t('amministrazione.registri_numerazione.politica_data') }}</label>
          <Select
            v-model="form.politica_data_documento"
            :options="opzioniPolitica"
            option-label="label"
            option-value="value"
            :disabled="isReadonly"
            :invalid="campiErrati.includes('politica_data_documento')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.registri_numerazione.limite_giorni') }}</label>
          <InputNumber
            v-model="form.limite_emissione_giorni"
            :disabled="isReadonly"
            :invalid="campiErrati.includes('limite_emissione_giorni')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.registri_numerazione.limite_giorno_mese') }}</label>
          <InputNumber
            v-model="form.limite_emissione_giorno_mese"
            :disabled="isReadonly"
            :invalid="campiErrati.includes('limite_emissione_giorno_mese')"
          />
        </div>
      </div>
    </template>

    <!-- ── I contatori, in SOLA LETTURA ───────────────────────────────── -->
    <!-- ⛔ Non esiste nessun endpoint che li scriva, e non ne deve nascere uno
         "per l'amministratore": cambiare `last_numero` a mano significa
         riassegnare un numero già uscito, cioè due documenti con lo stesso
         numero sullo stesso sezionale.
         ⚠️ Tabella HTML e non `DataTable`: sono poche righe di sola lettura
         dentro un drawer, e importare `primevue/datatable` qui farebbe salire
         il contatore della regola zero per una cosa che non è una lista. -->
    <template v-if="isEdit && dettaglio?.progressivi?.length">
      <h4>{{ t('amministrazione.registri_numerazione.sezione_contatori') }}</h4>
      <table class="app-mini-table">
        <thead>
          <tr>
            <th>{{ t('amministrazione.registri_numerazione.col_anno') }}</th>
            <th>{{ t('vendite.registri_numerazione.col_serie_default') }}</th>
            <th>{{ t('amministrazione.registri_numerazione.col_ultimo_numero') }}</th>
            <th>{{ t('amministrazione.registri_numerazione.col_ultima_data') }}</th>
          </tr>
        </thead>
        <tbody>
          <!-- La chiave del contatore e' (registro, anno, serie): `mese` non
               esiste piu' sul database, per quanto la doc auto-gen la elenchi. -->
          <tr v-for="p in dettaglio.progressivi" :key="`${p.anno}-${p.serie}`">
            <td>{{ p.anno }}</td>
            <td>{{ p.serie || '—' }}</td>
            <td>{{ p.last_numero }}</td>
            <td>{{ displayDate(p.ultima_data) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </AppDrawer>
</template>

<style scoped>
/* Tabella di sola lettura dei contatori: quattro colonne, poche righe.
   ⛔ Non è una lista e non deve sembrarlo — niente paginator, niente azioni. */
.app-mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.app-mini-table th,
.app-mini-table td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid var(--app-border-color);
  text-align: left;
}
.app-mini-table th {
  font-weight: 600;
}
</style>
