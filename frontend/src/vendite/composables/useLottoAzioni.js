// Scopo: le azioni di governo del lotto di fatturazione in UNA sola sede —
//   conferme, chiamate, toast, motivi. Consumate dal drawer diagnostico
//   (LottoDrawer) e dal kebab della lista lotti (LottiListView).
//
// Estratto il 2026-08-04 alla seconda occorrenza (regola del 2, ok Tid): senza,
// le stesse cinque conferme e i loro testi — che spiegano cosa viene DEMOLITO —
// sarebbero finiti copiati in due file, con la garanzia che prima o poi uno dei
// due sarebbe rimasto indietro.
//
// ── CHI DECIDE COSA ──────────────────────────────────────────────────────────
//   Il DB dice SE un verbo è possibile su quel lotto
//   (`script.fn_available_actions_lotto` → `enabled` + `reasons`); qui si sa
//   solo COSA chiamare e come chiederne conferma. Nessuna precondizione fiscale
//   è riscritta in JavaScript: era così fino al 2026-08-03 (cinque `computed`
//   nel drawer) e aveva già prodotto un pulsante-vicolo-cieco trovato in-app.
//
//   Due eccezioni dichiarate, `avanza_step` e `rilancia_step`: il DB non le
//   espone di proposito, perché il loro verdetto (step successivo + criticità +
//   distinzione avanza/rilancio, D-Q p.1) vive per intero nel runner Python.
//   Finché sta lì restano gate del frontend — vedi `risposta-db-azioni-lista-lotto.md` §5.
import { ref, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { useAuthStore } from '../../stores/auth'
import { estraiBersagli } from '../../core/bersagli'
import { azioniDaBersagli } from '../../core/bersaglioGesto'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useNotify } from '../../core/composables/useNotify'
import { testoMotivi } from '../../core/composables/useDrawerActions'
import {
  getLotto,
  numeraLotto,
  riportaLottoADraft,
  ristampaLotto,
  resetLottoDraft,
  runLottoPipeline,
} from '../api/lotti'
import { MANAGE_ICONS } from '../../core/constants'
import { aspettoAzione } from '../../core/aspettoAzioni'

// Permesso di processo dei SOLI verbi di pipeline, che il DB non espone (vedi
// testata). ⛔ Numera, riporta in bozza e annulla non stanno qui (ritirati il
// 2026-10-27, brief-modello-documento-vendita §15.8 punto 5): il loro permesso
// lo dice la riga del passaggio della matrice, e la capability del lotto
// NASCONDE il verbo a chi non ce l'ha. Una copia qui era una seconda sede del
// permesso, e prima della ritirata di `reset_lotto_draft` diceva gia' altro.
// La ristampa non ha permesso — stampare è leggere (I-4).
export const LOTTO_AZIONE_PERMESSO = {
  avanza_step: 'genera_fatture_lotti',
  // Stessa chiamata e stesso potere di `avanza_step`: cambia solo COME si
  // chiama davanti all'operatore (vedi `verbiPipeline`). Un permesso proprio
  // direbbe che e' un'altra facolta', e non lo e'.
  rigenera_bozza: 'genera_fatture_lotti',
  rilancia_step: 'genera_fatture_lotti',
}

// Presentazione dei due verbi che il DB non espone (vedi testata): il resto
// delle azioni prende label/icona/severity dal `meta` di catalogo.
export const LOTTO_AZIONE_PIPELINE_UI = {
  avanza_step: { label_key: 'vendite.lotti.avanza', icon: MANAGE_ICONS.AVANZA, severity: undefined },
  // ⚠️ Icona DIVERSA da `avanza_step` di proposito: la freccia in avanti su un
  // gesto che non avanza e' la stessa bugia dell'etichetta.
  rigenera_bozza: { label_key: 'vendite.lotti.rigenera', icon: MANAGE_ICONS.RIGENERA, severity: undefined },
  rilancia_step: { label_key: 'vendite.lotti.rerun', icon: MANAGE_ICONS.RIPROVA, severity: 'warn' },
}

// Le tre CHIAVI dei due verbi che il DB non espone (`rigenera_bozza` è la
// seconda presentazione di `avanza_step`: stessa API, stesso permesso), in UNA
// sede sola — sono le chiavi dell'oggetto qui sopra, non una lista riscritta.
// `esegui` e `eseguiVerificato` le trattano diversamente dagli altri verbi, e
// prima l'elenco stava per esteso dentro un `if`: una presentazione aggiunta
// sopra e dimenticata nell'`if` sarebbe passata dal percorso sbagliato.
const VERBI_PIPELINE = Object.keys(LOTTO_AZIONE_PIPELINE_UI)

// ⭐ Icona e colore dei verbi di stato NON stanno qui: li dà il verbo, dalla
// stessa mappa della barra del drawer (`core/aspettoAzioni.js`,
// brief-db-icone-azioni-per-significato). Le copie a mano dei valori del DB
// (`LOTTO_AZIONE_ICONA`, `LOTTO_AZIONE_SEVERITY`) sono ritirate il 2026-09-27:
// la riga di lista il blob non ce l'ha, e la copia doveva inseguire il seed.

// Scopo: un lotto si può numerare? ⚠️ È lo stato del DOCUMENTO, non del lavoro:
//   `stato_lotto` (bozza/in esecuzione/completato) è un altro asse.
//
// ⛔ ESPORTATO, e in una sede SOLA. Lo leggono due cose che devono dire lo
//   stesso: il kebab della riga — che propone «Rendi definitive» — e la casella
//   di selezione della lista Lotti, che decide se quella riga si può spuntare.
//   Con due copie il kebab potrebbe offrire il verbo su una riga la cui casella
//   è spenta, o il contrario: nessun errore, solo un'interfaccia che si
//   contraddice da sola. È esattamente ciò che il commento di `verbiPlausibili`
//   chiedeva — «tenerla qui, in una sede sola, è ciò che impedisce che
//   ricompaia sparsa nei template» — e che una seconda scrittura ha disatteso.
//
// ⚠️ Non è il VERDETTO e non deve diventarlo: dice cosa ha senso proporre,
//   mentre se l'atto si possa fare davvero lo stabilisce il DB. Il backend
//   applica comunque lo stato al perimetro: un lotto non emesso che arrivasse
//   all'API non verrebbe numerato lo stesso.
export function lottoNumerabile(row) {
  return row?.stato_doc_fiscale_codice === 'EMESSA'
}

export function useLottoAzioni({ onDone } = {}) {
  const { t, te } = useI18n()
  const { execute, loading } = useApiHandler()
  // Serve al degrado del bersaglio (area BLOCCATA → nessun pulsante).
  const auth = useAuthStore()
  const notify = useNotify()
  const { confirmAction } = useConfirmAction()
  // ⭐ La key del GESTO (`useChiaveGesto`): numerare, annullare, riportare in
  //    bozza non si rifanno due volte perche' un clic e' andato in timeout. Il
  //    reinvio dello stesso verbo sullo stesso lotto con gli stessi dati
  //    rimanda la stessa key, e il backend risponde con l'esito del primo.
  // ⚠️ UNA per composable, non una per verbo: il verbo sta nel payload, quindi
  //    due verbi hanno due key; e il successo di QUALUNQUE verbo la azzera —
  //    dopo «Riporta in lavorazione» riuscito, una «Rendi definitive» rimasta
  //    in sospeso non deve diventare il replay di una numerazione vecchia.
  // ⭐ La numerazione passa dal dialog della data, che resta aperto fino
  //    all'esito: il reinvio avviene dentro, aprirlo azzera la key. I verbi a
  //    conferma secca si fanno una volta sola (annulla, riporta in bozza): un
  //    reinvio identico e' lo stesso gesto, e li' il limite resta la durata.
  const gesto = useChiaveGesto()

  // Un verbo = chiamata + testi di conferma + esito. `danger` porta con sé la
  // conferma forte (rosso + label esplicita) sui due distruttivi.
  const VERBI = {
    avanza_step: {
      api: (id, _opzioni, config) => runLottoPipeline(id, {}, config),
      title: 'vendite.lotti.avanza_header',
      message: 'vendite.lotti.avanza_conferma',
      esito: () => t('vendite.lotti.avanza_esito'),
    },
    // Stessa API di `avanza_step`, testi propri: su un lotto riaperto quella
    // chiamata RIFA' lo step corrente e il lotto resta in DRAFT — annunciare
    // «Pipeline avanzata» sarebbe falso (collaudo NC resi, 2026-08-22).
    rigenera_bozza: {
      api: (id, _opzioni, config) => runLottoPipeline(id, {}, config),
      title: 'vendite.lotti.rigenera_header',
      message: 'vendite.lotti.rigenera_conferma',
      esito: () => t('vendite.lotti.rigenera_esito'),
    },
    rilancia_step: {
      api: (id, _opzioni, config) => runLottoPipeline(id, {}, config),
      title: 'vendite.lotti.rerun_header',
      message: 'vendite.lotti.rerun_conferma',
      esito: () => t('vendite.lotti.avanza_esito'),
    },
    numera: {
      // ⭐ La data documento dichiarata nel dialog arriva fin qui: riscrive la
      // data delle fatture non ancora numerate del lotto e ne RIGENERA i piani
      // rate, prima di numerare. `null` = nessuna dichiarazione.
      api: (id, { dataDocumento = null } = {}, config) => numeraLotto(id, { dataDocumento }, config),
      title: 'vendite.lotti.numera_header',
      message: 'vendite.lotti.numera_conferma',
      esito: () => t('vendite.lotti.numera_lotto_esito'),
      // ⛔ Non passa dalla conferma secca: la numerazione CHIEDE una data
      // (FE-2). Vedi `numeraDialog` piu' sotto.
      chiedeData: true,
    },
    ristampa: {
      api: (id, _opzioni, config) => ristampaLotto(id, config),
      title: 'vendite.lotti.ristampa_header',
      message: 'vendite.lotti.ristampa_conferma',
      esito: (res) => t('vendite.lotti.ristampa_esito', { n: res?.accodate ?? 0 }),
      // La ristampa accoda e basta: niente da ricaricare nel chiamante.
      skipDone: true,
    },
    annulla: {
      api: (id, _opzioni, config) => resetLottoDraft(id, config),
      title: 'vendite.lotti.reset_header',
      message: 'vendite.lotti.reset_conferma',
      avviso: 'vendite.lotti.reset_avviso_accrediti',
      danger: true,
      acceptLabel: 'vendite.lotti.reset_accept',
      esito: (res) => t('vendite.lotti.reset_esito', {
        fatture: res?.deleted_fatture ?? 0,
        attivita: res?.updated_attivita ?? 0,
      }),
    },
    riporta_a_draft: {
      api: (id, _opzioni, config) => riportaLottoADraft(id, config),
      title: 'vendite.lotti.riporta_draft_header',
      message: 'vendite.lotti.riporta_draft_conferma',
      avviso: 'vendite.lotti.reset_avviso_accrediti',
      danger: true,
      acceptLabel: 'vendite.lotti.riporta_draft_accept',
      esito: (res) => t('vendite.lotti.riporta_draft_esito', {
        fatture: res?.deleted_fatture ?? 0,
        attivita: res?.riemesse_attivita ?? 0,
      }),
    },
  }

// I motivi di arresto del driver pipeline (`_drive_lotto_until_done`) che sono
// un ESITO BUONO. Tutto il resto — `ERRORE`, `BLOCCATO_CRITICITA`,
// `GUARD_MAX_ITER` — è un fallimento.
//
// 🔴 PERCHE' QUESTA LISTA ESISTE (difetto trovato in-app il 2026-08-21). Gli
// endpoint del runner rispondono **200 anche quando la catena si ferma per
// errore**: il fallimento non è un errore HTTP, è un campo dell'esito
// (`motivo_stop` + `errore`), perché la catena può aver eseguito qualche step
// prima di fermarsi e quel lavoro va raccontato. `useApiHandler` vede un 200 e
// non ha niente da segnalare — quindi chi legge l'esito DEVE guardare
// `motivo_stop`, altrimenti annuncia come riuscita un'operazione fallita.
//
// Misurato: «Rendi definitive» su un lotto con una nota di credito la cui
// fattura non è ancora numerata mostrava il toast verde «Fatture numerate».
// Il documento non era numerato, il DB aveva rifiutato con il suo motivo, e
// all'operatore non arrivava niente.
const MOTIVI_STOP_OK = ['COMPLETATO', 'FERMATO_A_STATO']

// Scopo: il verdetto su una risposta del runner. Chi non porta `motivo_stop`
//   (ristampa, annulla, riporta a draft) non è un esito di catena: per quelli
//   il 200 è già la risposta, e si resta su «riuscito».
//   `messaggio` è quello del DB quando c'è — è l'unico che dice QUALE
//   documento sblocca la strada — con ripiego sul codice di arresto, mai su
//   una frase generica che nasconde il motivo.
function verdettoRunner(res) {
  const motivo = res?.motivo_stop
  if (!motivo || MOTIVI_STOP_OK.includes(motivo)) return { ok: true }
  return {
    ok: false,
    messaggio: res?.errore?.message || motivo,
    // ⭐ IL BERSAGLIO ARRIVA DA QUI, e non dall'envelope (2026-08-24). Questi
    // endpoint rispondono 200 anche quando falliscono, quindi `useApiHandler`
    // non vede nessun errore e il canale che disegna il gesto altrove — l'
    // envelope `error.targets` — qui non passa proprio. `errore` porta gli
    // STESSI nomi, e da lì si prende.
    // ⚠️ È il messaggio PILOTA del cantiere a passare di qua
    // (`E_FATTURA_RETTIFICATA_SENZA_NUMERO`, «numera prima il documento 820»):
    // senza questa riga il caso che ha fatto nascere tutto resterebbe l'unico
    // senza pulsante.
    bersagli: estraiBersagli(res?.errore),
  }
}

  // ⭐ FE-2 — LO STATO DEL DIALOG DELLA DATA, in UNA sede sola. I consumatori
  //   sono due (il drawer e la lista) e ognuno rende il proprio
  //   `<NumerazioneDataDialog>` legato a questo stato: la LOGICA resta qui, il
  //   template e' loro. Duplicarla sarebbe la stessa trappola per cui questo
  //   composable e' nato.
  const numeraDialog = ref({ visible: false, lottoId: null })

  // Scopo: la corsa vera di un verbo — chiamata, verdetto sul `motivo_stop`,
  //   toast, refresh. Estratta dalla conferma perche' i percorsi che ci
  //   arrivano sono DUE: la conferma secca (tutti gli altri verbi) e il dialog
  //   della data (`numera`). Una copia per percorso avrebbe fatto divergere
  //   proprio la lettura dell'esito, che e' la parte delicata (§ MOTIVI_STOP_OK).
  async function _corri(lottoId, chiaveVerbo, opzioni = {}) {
    const verbo = VERBI[chiaveVerbo]
    const res = await execute(() => gesto.invia(
      { verbo: chiaveVerbo, lottoId, ...opzioni },
      (config) => verbo.api(lottoId, opzioni, config),
    ))
    // `!== null` e non `if (res)`: un esito vuoto è comunque un successo
    // (memoria feedback_drawer_result_check).
    if (res === null) return false
    const verdetto = verdettoRunner(res)
    if (!verdetto.ok) {
      // ⚠️ Si ricarica LO STESSO: la catena può essersi fermata DOPO aver
      // eseguito qualche step, e la lista deve mostrare dove è arrivata.
      notify.errorConAzioni(
        verdetto.messaggio,
        azioniDaBersagli(verdetto.bersagli, auth),
      )
      if (!verbo.skipDone) await onDone?.()
      // La chiamata e' andata (il runner ha risposto): il gesto e' chiuso,
      // anche se la catena si e' fermata — riprovare e' un gesto nuovo.
      return true
    }
    notify.success(verbo.esito(res))
    if (!verbo.skipDone) await onDone?.()
    return true
  }

  // Scopo: conferma la numerazione con la data scelta nel dialog. Risponde
  //   `true` se la chiamata e' andata: il dialog si chiude solo allora.
  async function confermaNumera(dataDocumento) {
    const lottoId = numeraDialog.value.lottoId
    if (lottoId == null) return true
    return _corri(lottoId, 'numera', { dataDocumento })
  }

  // Scopo: esegue un verbo su un lotto — conferma, chiamata, toast, refresh.
  //   Usato dal drawer, che ha già il blob capability e quindi mostra
  //   disabilitate le azioni non eseguibili.
  function esegui(lottoId, key) {
    const verbo = VERBI[key]
    if (!verbo) return
    // ⭐ La numerazione non chiede «sei sicuro?»: chiede CON QUALE DATA. Il
    //   dialog e' la conferma, e porta con se' il pavimento del sezionale.
    if (verbo.chiedeData) {
      // Aprire il dialog e' un gesto nuovo: la key si azzera qui, e il dialog
      // resta aperto fino all'esito (vedi `NumerazioneDataDialog`).
      gesto.azzera()
      numeraDialog.value = { visible: true, lottoId }
      return
    }
    confirmAction({
      header: t(verbo.title),
      // ⚠️ L'avviso si APPENDE qui e non dentro la stringa di conferma: la
      // frase e' la stessa per i tre percorsi di reset (annulla lotto, riporta
      // a draft, elimina la singola fattura) e tre copie divergerebbero — con
      // l'aggravante che a divergere sarebbe cio' che l'operatore legge prima
      // di un'operazione non annullabile.
      message: verbo.avviso ? `${t(verbo.message)} ${t(verbo.avviso)}` : t(verbo.message),
      ...(verbo.danger ? { danger: true, acceptLabel: t(verbo.acceptLabel) } : {}),
      // Il gesto se c'è, il toast di prima se non c'è: `errorConAzioni` ricade
      // da sé su `error` con un array vuoto (dentro `_corri`).
      onAccept: () => _corri(lottoId, key),
    })
  }

  // Scopo: come `esegui`, ma per chi NON ha il blob capability sotto mano — la
  //   lista. Prima di chiedere conferma legge la capability di QUEL lotto
  //   (dettaglio, endpoint già esistente) e, se il DB dice no, mostra il motivo
  //   invece di far partire una chiamata destinata a fallire.
  //
  //   È il prezzo di una chiamata sola, pagato solo quando l'operatore agisce
  //   davvero: la lista resta senza capability per riga (scelta del team DB,
  //   §3.3 della risposta) e senza precondizioni ricopiate. Porta il PERMESSO
  //   (`azioni_permesse`, §15.14 — chi non ha l'azione non vede la voce), non il
  //   VERDETTO: quello resta qui, al click.
  //
  //   ⛔ Le tre chiavi di pipeline non sono nel blob per costruzione — ma «non
  //   c'è un verdetto da chiedere» NON vuol dire «si procede diretti», ed è
  //   così che era scritto fino al 2026-09-08: da lì passavano senza nemmeno
  //   rileggere la riga. La regola di proposta esiste ed è una sola
  //   (`verbiPipeline`): quello che mancava non era il verdetto, era il DATO
  //   FRESCO su cui applicarla. La riga della lista può avere minuti — il lotto
  //   nel frattempo può essere stato annullato, numerato o preso in carico da
  //   un collega — e il dettaglio lo si sta già leggendo per tutti gli altri
  //   verbi. Si rilegge anche per questi tre e si rivaluta la STESSA regola:
  //   nessuna seconda copia, e la lista vecchia smette di essere autorevole.
  //   ⚠️ Il rifiuto vero resta del runner (guard di transizione a DB): questo
  //   è il non-proporre, non il cancello.
  async function eseguiVerificato(lottoId, key) {
    const dettaglio = await execute(() => getLotto(lottoId))
    if (dettaglio === null) return
    const azione = (dettaglio.capabilities?.available_actions ?? []).find((a) => a.key === key)
    // ⭐ DUE FAMIGLIE, UNA SOLA DOMANDA: «la riga fresca propone ancora questo
    //   verbo?». Per i verbi di stato la risposta è nel blob del DB; per i tre
    //   di pipeline, che nel blob non ci sono per costruzione, è `verbiPipeline`
    //   — la stessa regola con cui il kebab li ha proposti, riapplicata al dato
    //   fresco. La differenza sta tutta in questa riga; il seguito è comune.
    const ancoraProposto = VERBI_PIPELINE.includes(key)
      ? verbiPipeline(dettaglio).includes(key)
      : azione !== undefined
    // Verbo sparito fra il render della lista e il click (qualcun altro ha
    // fatto avanzare o annullato il lotto): non è un errore di sistema, è una
    // lista vecchia — si avvisa e si ricarica.
    if (!ancoraProposto) {
      notify.warn(t('vendite.lotti.azione_non_piu_disponibile'))
      await onDone?.()
      return
    }
    // Proposto ma non eseguibile ADESSO: il motivo lo dà il DB. ⚠️ Vale solo
    // per i verbi del blob — sui tre di pipeline `azione` è `undefined`, e
    // `undefined === false` è falso: si prosegue, che è corretto.
    if (azione?.enabled === false) {
      notify.warn(testoMotivi(t, te, azione) || t('vendite.lotti.azione_non_piu_disponibile'))
      return
    }
    esegui(lottoId, key)
  }

  // Scopo: i verbi di PIPELINE proponibili su un lotto (testata o riga di
  //   lista). Sono i due che il DB non espone, quindi la regola vive qui — ma
  //   in una sede sola, condivisa da drawer e lista.
  //
  //   `avanza_step` solo da DRAFT: è l'unico stato da cui la pipeline avanza
  //   (DRAFT→EMESSA). Da EMESSA il passo successivo è la numerazione, che ha
  //   verbo e permesso propri (I-7); oltre, il lotto è chiuso e non ha più
  //   step. Prima la condizione era `!isEmessa`, e proponeva «Avanza step»
  //   anche sui lotti DEFINITIVA — invisibile nel drawer di un lotto alla
  //   volta, evidente in una lista dove i chiusi sono la maggioranza.
  //
  //   ⭐ Da DRAFT i verbi sono DUE e si escludono, perché la stessa chiamata
  //   fa due cose diverse (runner, `deve_rifare_step_corrente`):
  //     · lotto RIAPERTO → il run RIFA' lo step corrente, il lotto resta in
  //       DRAFT      → «Rigenera la bozza»
  //     · lotto normale → il run AVANZA, DRAFT→EMESSA → «Avanza step»
  //   Trovato in collaudo (NC resi, 2026-08-22): dopo «Riporta in lavorazione»
  //   servono due pressioni — la prima rigenera, la seconda avanza — ed è
  //   corretto; a essere sbagliato era che il pulsante le chiamasse uguali e
  //   annunciasse «Pipeline avanzata» anche quando non era avanzato niente.
  //   ⚠️ Il flag `riaperto` arriva dal BE (`fatturazione_lotti.riaperto_il`):
  //   NON si deduce qui, o diventerebbe una seconda regola accanto a quella
  //   del runner.
  //   ⛔ LA SOGLIA DI CONGELAMENTO VIENE PRIMA DI TUTTO, ed è l'ordine il
  //   punto. `stato_lotto` racconta com'è andato l'ULTIMO GIRO; lo stato
  //   fiscale dice se una pipeline ha ancora senso. Sono due assi, e il
  //   secondo comanda: su un documento congelato — DEFINITIVA, INVIATA,
  //   REGISTRATA, ANNULLATA — non c'è nessuno step da rifare, per bene o per
  //   male che sia finito il giro precedente.
  //
  //   🔴 Il difetto che questo ordine chiude (segnalato dal team DB,
  //   2026-09-07): con il ramo `ERRORE` per primo, un lotto ANNULLATA rimasto
  //   in `stato_lotto = 'ERRORE'` si vedeva proporre «Rilancia lo step» — su
  //   un documento terminale, che non ha nemmeno una transizione in uscita.
  //   ⚠️ Il ramo era **irraggiungibile per un dato**, non per costruzione:
  //   finché l'annullo portava anche `stato_lotto` a COMPLETATO nessun lotto
  //   annullato era in ERRORE. Tolta quella falsificazione a DB, il difetto è
  //   emerso — non è nato lì.
  //
  //   ⛔ E NON è «tutto ciò che non è DRAFT», che era la scorciatoia da una
  //   riga: su un lotto EMESSA finito in ERRORE il rilancio dello STESSO step
  //   è la via d'uscita definita da Tid (D-Q p.1, «correggo l'anagrafica →
  //   rieseguo lo step»), e spegnerlo la toglierebbe. La domanda non è «in che
  //   stato è», è «quello stato congela il documento?».
  //
  //   ⭐ E la risposta arriva dal CATALOGO (`config.stati_doc_fiscale.congela_fiscale`,
  //   esposto sulla riga dal 2026-09-08), non da un elenco di codici scritto
  //   qui. Era l'ennesima copia della soglia che `D33` ha portato a leggere il
  //   database: l'ultima copia fuori dal DB è stata tolta da `LottoDrawer` il
  //   2026-08-31 (F5) con la stessa motivazione — *una copia in un template il
  //   DB non la vede, e il giorno che il confine si sposta non fallisce:
  //   propone un verbo che verrà rifiutato*. Uno stato nuovo a catalogo entra
  //   nel gate senza toccare questo file.
  function verbiPipeline(lotto) {
    // Fail-closed: `false` è l'unico valore che apre. `null` (lotto senza stato
    // fiscale, il JOIN è LEFT) e `undefined` (riga vecchia, prima che il BE
    // esponesse il campo) valgono «non lo so» — e su un verbo che riesegue la
    // pipeline «non lo so» non può voler dire «vai». Stessa disciplina del
    // `can_reset_fattura` in `LottoDrawer`.
    if (lotto?.stato_congela_fiscale !== false) return []
    if (lotto?.stato_lotto === 'ERRORE') return ['rilancia_step']
    if (lotto?.stato_lotto === 'IN_ESECUZIONE') return []
    if (lotto?.stato_doc_fiscale_codice !== 'DRAFT') return []
    return lotto?.riaperto ? ['rigenera_bozza'] : ['avanza_step']
  }

  // Scopo: verbi PLAUSIBILI per una riga di lista, dai soli campi che la riga
  //   porta (stato fiscale + stato lotto). ⚠️ Non è il verdetto e non deve
  //   diventarlo: dice cosa ha senso PROPORRE, mentre se l'azione si può fare
  //   davvero lo stabilisce il DB al click (`eseguiVerificato`). Tenerla qui,
  //   in una sede sola, è ciò che impedisce che ricompaia sparsa nei template.
  //
  //   ⭐ I VERBI DI STATO (numera, riporta in bozza, annulla) li dice la riga:
  //   `azioni_permesse` sono i passaggi manuali che QUESTO operatore può fare
  //   dallo stato del lotto (`script.fn_doc_azioni_permesse`,
  //   brief-modello-documento-vendita §15.14), lo stesso lettore delle
  //   capability del dettaglio. Prima si deducevano dal codice dello stato
  //   (EMESSA → numera e riporta, DRAFT → annulla): il kebab proponeva
  //   «Rendi definitive» anche a chi non aveva `numera_fatture_lotti`, e il
  //   dettaglio lo nascondeva — lista e drawer si contraddicevano.
  //   Fail-closed: un campo assente (riga vecchia) non propone niente.
  //   ⚠️ Solo le chiavi che qui hanno una chiamata (`VERBI`), e non quelle di
  //   pipeline: un passaggio nuovo a matrice senza verbo nel frontend non
  //   diventa una voce che non saprebbe cosa chiamare.
  function verbiPlausibili(row) {
    const permesse = Array.isArray(row?.azioni_permesse) ? row.azioni_permesse : []
    const verbi = [...verbiPipeline(row)]
    verbi.push(...permesse.filter((k) => VERBI[k] && !VERBI_PIPELINE.includes(k)))
    // La ristampa non è un passaggio di stato: stampare è leggere (I-4). Si
    // legge `ristampabile` della riga, lo stesso predicato del gate del
    // backend, e non il codice dello stato confrontato con un letterale.
    // Fail-closed: un campo assente non propone la ristampa.
    if (row?.ristampabile === true) verbi.push('ristampa')
    return verbi
  }

  // Scopo: le voci per RowActionsMenu di una riga di lista. Label e icone
  //   sono quelle del drawer (etichetta dal catalogo DB, icona e colore dal verbo): il kebab della
  //   lista e la barra del drawer non possono chiamare la stessa cosa in due
  //   modi diversi.
  function azioniRiga(row, { readonly = false } = {}) {
    // `unref`: il chiamante può passare il computed `isReadonly` da JS, dove
    // (a differenza del template) non c'è auto-unwrap — un ref è sempre truthy.
    if (unref(readonly)) return []
    return verbiPlausibili(row).map((key) => {
      const ui = LOTTO_AZIONE_PIPELINE_UI[key]
      const labelKey = ui?.label_key ?? `vendite.lotti.azione_${key}`
      return {
        key,
        label: t(labelKey),
        icon: ui ? ui.icon : aspettoAzione(key).icona,
        severity: ui ? ui.severity : aspettoAzione(key).severity,
        ...(LOTTO_AZIONE_PERMESSO[key] ? { action: LOTTO_AZIONE_PERMESSO[key] } : {}),
        command: () => eseguiVerificato(row.id, key),
      }
    })
  }

  return {
    loading,
    esegui,
    eseguiVerificato,
    numeraDialog,
    confermaNumera,
    verbiPipeline,
    verbiPlausibili,
    azioniRiga,
  }
}
