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
import { unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useNotify } from '../../core/composables/useNotify'
import { labelOrCode } from '../../core/utils/i18nLabel'
import {
  getLotto,
  numeraLotto,
  riportaLottoADraft,
  ristampaLotto,
  resetLottoDraft,
  runLottoPipeline,
} from '../api/lotti'

// Permesso di processo per verbo. La numerazione ha un gate fiscale SEPARATO
// (I-7); annullamento e ritorno in lavorazione condividono `reset_lotto_draft`
// (stessa classe di potere: cancellare fatture pre-fiscali); la ristampa non ne
// ha — stampare è leggere (I-4).
export const LOTTO_AZIONE_PERMESSO = {
  avanza_step: 'genera_fatture_lotti',
  rilancia_step: 'genera_fatture_lotti',
  numera: 'numera_fatture_lotti',
  annulla: 'reset_lotto_draft',
  riporta_a_draft: 'reset_lotto_draft',
}

// Presentazione dei due verbi che il DB non espone (vedi testata): il resto
// delle azioni prende label/icona/severity dal `meta` di catalogo.
export const LOTTO_AZIONE_PIPELINE_UI = {
  avanza_step: { label_key: 'vendite.lotti.avanza', icon: 'pi pi-forward', severity: undefined },
  rilancia_step: { label_key: 'vendite.lotti.rerun', icon: 'pi pi-replay', severity: 'warn' },
}

// Icona/severity dei verbi di stato per il kebab della lista. Nel drawer
// arrivano dal `meta` di catalogo insieme al resto del blob; la riga di lista il
// blob non ce l'ha, quindi qui si rispecchiano i valori seedati il 2026-08-04 —
// se cambiano a catalogo vanno cambiati anche qui. Sono presentazione, non
// regole: nessun verdetto passa da questi due oggetti.
const LOTTO_AZIONE_ICONA = {
  numera: 'pi pi-verified',
  ristampa: 'pi pi-print',
  annulla: 'pi pi-times-circle',
  riporta_a_draft: 'pi pi-undo',
}

const LOTTO_AZIONE_SEVERITY = {
  numera: 'success',
  ristampa: 'secondary',
  annulla: 'danger',
  riporta_a_draft: 'warn',
}

export function useLottoAzioni({ onDone } = {}) {
  const { t, te } = useI18n()
  const { execute, loading } = useApiHandler()
  const notify = useNotify()
  const { confirmAction } = useConfirmAction()

  // Un verbo = chiamata + testi di conferma + esito. `danger` porta con sé la
  // conferma forte (rosso + label esplicita) sui due distruttivi.
  const VERBI = {
    avanza_step: {
      api: (id) => runLottoPipeline(id),
      title: 'vendite.lotti.avanza_header',
      message: 'vendite.lotti.avanza_conferma',
      esito: () => t('vendite.lotti.avanza_esito'),
    },
    rilancia_step: {
      api: (id) => runLottoPipeline(id),
      title: 'vendite.lotti.rerun_header',
      message: 'vendite.lotti.rerun_conferma',
      esito: () => t('vendite.lotti.avanza_esito'),
    },
    numera: {
      api: (id) => numeraLotto(id),
      title: 'vendite.lotti.numera_header',
      message: 'vendite.lotti.numera_conferma',
      esito: () => t('vendite.lotti.numera_esito'),
    },
    ristampa: {
      api: (id) => ristampaLotto(id),
      title: 'vendite.lotti.ristampa_header',
      message: 'vendite.lotti.ristampa_conferma',
      esito: (res) => t('vendite.lotti.ristampa_esito', { n: res?.accodate ?? 0 }),
      // La ristampa accoda e basta: niente da ricaricare nel chiamante.
      skipDone: true,
    },
    annulla: {
      api: (id) => resetLottoDraft(id),
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
      api: (id) => riportaLottoADraft(id),
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

  // Scopo: i motivi ostativi del DB in testo leggibile. `reason_key` mancante a
  //   catalogo → si mostra il codice macchina, mai il path della chiave
  //   (fail-visible, stessa regola di mapAvailableActionsToDrawerActions).
  function motiviTesto(action) {
    return (action?.reasons ?? [])
      .map((r) => (r.reason_key ? labelOrCode(t, te, r.reason_key, r.reason || '') : r.reason || ''))
      .filter(Boolean)
      .join('\n')
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
  return { ok: false, messaggio: res?.errore?.message || motivo }
}

  // Scopo: esegue un verbo su un lotto — conferma, chiamata, toast, refresh.
  //   Usato dal drawer, che ha già il blob capability e quindi mostra
  //   disabilitate le azioni non eseguibili.
  function esegui(lottoId, key) {
    const verbo = VERBI[key]
    if (!verbo) return
    confirmAction({
      title: t(verbo.title),
      // ⚠️ L'avviso si APPENDE qui e non dentro la stringa di conferma: la
      // frase e' la stessa per i tre percorsi di reset (annulla lotto, riporta
      // a draft, elimina la singola fattura) e tre copie divergerebbero — con
      // l'aggravante che a divergere sarebbe cio' che l'operatore legge prima
      // di un'operazione non annullabile.
      message: verbo.avviso ? `${t(verbo.message)} ${t(verbo.avviso)}` : t(verbo.message),
      ...(verbo.danger ? { danger: true, acceptLabel: t(verbo.acceptLabel) } : {}),
      onAccept: async () => {
        const res = await execute(() => verbo.api(lottoId))
        // `!== null` e non `if (res)`: un esito vuoto è comunque un successo
        // (memoria feedback_drawer_result_check).
        if (res === null) return
        const verdetto = verdettoRunner(res)
        if (!verdetto.ok) {
          // ⚠️ Si ricarica LO STESSO: la catena può essersi fermata DOPO aver
          // eseguito qualche step, e la lista deve mostrare dove è arrivata.
          notify.error(verdetto.messaggio)
          if (!verbo.skipDone) await onDone?.()
          return
        }
        notify.success(verbo.esito(res))
        if (!verbo.skipDone) await onDone?.()
      },
    })
  }

  // Scopo: come `esegui`, ma per chi NON ha il blob capability sotto mano — la
  //   lista. Prima di chiedere conferma legge la capability di QUEL lotto
  //   (dettaglio, endpoint già esistente) e, se il DB dice no, mostra il motivo
  //   invece di far partire una chiamata destinata a fallire.
  //
  //   È il prezzo di una chiamata sola, pagato solo quando l'operatore agisce
  //   davvero: la lista resta senza capability per riga (scelta del team DB,
  //   §3.3 della risposta) e senza precondizioni ricopiate.
  //
  //   I due verbi di pipeline non sono nel blob per costruzione: per loro non
  //   c'è verdetto da chiedere e si procede diretti.
  async function eseguiVerificato(lottoId, key) {
    if (key === 'avanza_step' || key === 'rilancia_step') {
      esegui(lottoId, key)
      return
    }
    const dettaglio = await execute(() => getLotto(lottoId))
    if (dettaglio === null) return
    const azione = (dettaglio.available_actions ?? []).find((a) => a.key === key)
    // Verbo sparito fra il render della lista e il click (qualcun altro ha
    // fatto avanzare il lotto): non è un errore di sistema, è una lista vecchia.
    if (!azione) {
      notify.warn(t('vendite.lotti.azione_non_piu_disponibile'))
      await onDone?.()
      return
    }
    if (azione.enabled === false) {
      notify.warn(motiviTesto(azione) || t('vendite.lotti.azione_non_piu_disponibile'))
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
  function verbiPipeline(lotto) {
    if (lotto?.stato_lotto === 'ERRORE') return ['rilancia_step']
    if (lotto?.stato_lotto === 'IN_ESECUZIONE') return []
    return lotto?.stato_doc_fiscale_codice === 'DRAFT' ? ['avanza_step'] : []
  }

  // Scopo: verbi PLAUSIBILI per una riga di lista, dai soli campi che la riga
  //   porta (stato fiscale + stato lotto). ⚠️ Non è il verdetto e non deve
  //   diventarlo: dice cosa ha senso PROPORRE, mentre se l'azione si può fare
  //   davvero lo stabilisce il DB al click (`eseguiVerificato`). Tenerla qui,
  //   in una sede sola, è ciò che impedisce che ricompaia sparsa nei template.
  function verbiPlausibili(row) {
    const stato = row?.stato_doc_fiscale_codice
    const verbi = [...verbiPipeline(row)]
    if (stato === 'EMESSA') verbi.push('numera', 'riporta_a_draft')
    if (stato === 'DEFINITIVA') verbi.push('ristampa')
    if (stato === 'DRAFT') verbi.push('annulla')
    return verbi
  }

  // Scopo: le voci per RowActionsMenu di una riga di lista. Label e icone
  //   restano quelle del catalogo DB (le stesse del drawer): il kebab della
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
        icon: ui?.icon ?? LOTTO_AZIONE_ICONA[key],
        severity: ui ? ui.severity : LOTTO_AZIONE_SEVERITY[key],
        ...(LOTTO_AZIONE_PERMESSO[key] ? { action: LOTTO_AZIONE_PERMESSO[key] } : {}),
        command: () => eseguiVerificato(row.id, key),
      }
    })
  }

  return {
    loading,
    esegui,
    eseguiVerificato,
    verbiPipeline,
    verbiPlausibili,
    azioniRiga,
    motiviTesto,
  }
}
