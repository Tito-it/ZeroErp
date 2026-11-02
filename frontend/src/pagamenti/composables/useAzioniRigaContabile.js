// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: LE AZIONI DI RIGA DI UNA RIGA CONTABILE — «quale voce, spenta con
//        quale motivo» — in UNA sede per le due superfici che le rendono: il
//        drawer della distinta e la coda del riconciliatore (estratto il
//        2026-09-19 alla seconda occorrenza, ok Tid — brief validata-e-tardiva
//        FE-4).
//
// ⭐ LE VOCI VENGONO DALLA MATRICE, per lo stato in cui la riga si trova
//    (`transizioniRiga()[stato]`, letta dal database), e si INCROCIANO col
//    catalogo, che dice come si chiama a video e se e' terminale. ⛔ Nessun
//    elenco di stati scritto qui: una copia nel frontend nasconderebbe lo
//    stato che nasce domani senza dirlo — e prima del 14/09 il drawer offriva
//    SCARTATA su una ABBINATA, che il database rifiutava.
//
// ⭐ L'UNICA transizione esclusa dai «porta a» e' quella col VERBO PROPRIO:
//    ad ABBINATA non ci si porta cambiando stato, ci si arriva scegliendo la
//    fattura — ed e' lei a decidere se «Abbina» si accende: si abbina da dove
//    la matrice ammette ABBINATA, e si RI-abbina da ABBINATA (il dialogo si
//    apre gia' sulla destinazione, D20-e).
//
// ⭐ IL VERBO CAMBIA CON LA TESTATA (D20-b): sotto una distinta REGISTRATA
//    «Abbina» diventa «Abbina e registra» — la tardiva, che scrive un
//    movimento e passa dallo stesso cancello della registrazione. Il fatto lo
//    dice chi chiama (`testataDi(riga)` → `registrata`), letto dal backend
//    (`data_conferma` sul dettaglio, `contabile_registrata` sulla coda): qui
//    non si ricalcola nessuna regola.
//
// ⭐ «Permesso ⇒ nascondi, stato ⇒ disabilita col motivo»: in sola lettura
//    NIENTE (e' un permesso); una riga gia' registrata, un foglio le cui
//    righe non si lavorano piu' (l'annullato), uno stato da cui non si abbina
//    spengono la voce e DICONO perche'. Il
//    cestino lo spegne il DATABASE (`elimina_blocco_*`, la stessa check che
//    il guard chiama per rifiutare) — qui si legge, con `bloccoMotivo`.
//
// ⚠️ E' una FABBRICA: ogni chiamante ne ha una sua, col suo `t`. Un oggetto
//    condiviso legherebbe la coda al `t` del drawer montato per primo.
import { useI18n } from 'vue-i18n'

import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { MANAGE_ICONS } from '../../core/constants'
import { formatCurrency } from '../../core/utils/format'
import { cambiaStatoRiga, eliminaRiga } from '../api/pagamenti'
import { AZIONE_REGISTRA_DISTINTA } from '../vocabolari'

// Lo stato col VERBO PROPRIO: ci si arriva con «Abbina», non con «Porta a».
export const STATO_RIGA_CON_VERBO_PROPRIO = 'ABBINATA'

// I DUE MODI di «Abbina»: il verbo normale e la tardiva («abbina e registra»).
export const MODO_ABBINA = Object.freeze({ ABBINA: 'abbina', REGISTRA: 'registra' })

// ⭐ Le icone delle transizioni. ⚠️ E' una mappa COSMETICA: se il catalogo
//    cresce, uno stato sconosciuto prende l'icona generica e funziona lo
//    stesso — mentre un elenco cablato semplicemente non lo mostrerebbe.
// ⛔ SCARTATA NON E' IL CESTINO (D17-e, 14/09): «scarta» vuol dire «denaro
//    arrivato, non nostro» e conta nella quadratura; «elimina» toglie una riga
//    digitata male. Il cestino e' di «Elimina», e basta.
export const ICONA_TRANSIZIONE_RIGA = Object.freeze({
  DA_ABBINARE: MANAGE_ICONS.ABBINA,
  SOSPESA: MANAGE_ICONS.SOSPENDI,
  SCARTATA: MANAGE_ICONS.DISATTIVA,
})

// ⭐ I VERBI delle transizioni, al posto di «Porta a <stato>» (FE-4): «Sospendi»,
//    «Scarta», «Riporta da abbinare» — e «Riprendi» quando una SCARTATA torna
//    SOSPESA (D20-c: si riprende in mano, non si «sospende»). La chiave e' la
//    COPPIA quando il verbo dipende da dove si parte, lo stato di ARRIVO
//    altrimenti; uno stato senza verbo ripiega su «Porta a …». Mappa
//    cosmetica come le icone: la matrice decide se la voce c'e'.
// 🔴 Le chiavi qui NON le vede `check_i18n_keys` (sono valori di una mappa,
//    non `t('…')`): il presidio e' `useAzioniRigaContabile.spec.js`, che le
//    risolve contro i locales veri.
export const VERBO_TRANSIZIONE_RIGA = Object.freeze({
  'SCARTATA>SOSPESA': 'pagamenti.righe.verbo_riprendi',
  SOSPESA: 'pagamenti.righe.verbo_sospendi',
  SCARTATA: 'pagamenti.righe.verbo_scarta',
  DA_ABBINARE: 'pagamenti.righe.verbo_riporta_da_abbinare',
})

// Scopo: la fabbrica delle azioni di riga.
// @param {object} deps
//   - statiRiga:        () => catalogo degli stati di riga (con `is_final`)
//   - transizioniRiga:  () => `{ stato_da: [stato_a…] }` dalla matrice
//   - testataDi:        (riga) => `{ righeLavorabili, registrata }` — i
//                       fatti della distinta della riga, letti dal backend
//   - readonly:         () => bool — il readonly da PERMESSI
//   - onAbbina:         (riga, modo) => apre il dialogo di abbinamento
//   - ricarica:         () => ricarica la superficie dopo un gesto riuscito
//   - conElimina:       bool — «Elimina» c'e' solo dove il contenuto si lavora
//                       (il drawer); dalla coda non si elimina niente
// @returns {{ buildRowActions, catalogoRiga }}
export function useAzioniRigaContabile({
  statiRiga,
  transizioniRiga,
  testataDi,
  readonly,
  onAbbina,
  ricarica,
  conElimina = false,
}) {
  const { t, te } = useI18n()
  const { execute } = useApiHandler()
  const { confirmAction } = useConfirmAction()

  // Scopo: la riga di catalogo di uno stato. ⚠️ `is_final` viene da li' e NON
  //        si deduce dal nome: `POSTATA` non e' l'unico stato terminale
  //        possibile, e un confronto col nome lascerebbe lavorabile una riga
  //        terminale — cioe' offrirebbe gesti che finiscono in errore.
  function catalogoRiga(codice) {
    return statiRiga().find((s) => s.codice_interno === codice) || null
  }

  // Scopo: il verbo di una transizione, dalla mappa o dal ripiego «Porta a».
  function etichettaTransizione(da, a, descrizione) {
    const chiave = VERBO_TRANSIZIONE_RIGA[`${da}>${a}`] || VERBO_TRANSIZIONE_RIGA[a]
    if (chiave && te(chiave)) return t(chiave)
    return t('pagamenti.righe.porta_a', { stato: descrizione })
  }

  // Scopo: conferma e chiede il cambio di stato; a esito buono ricarica.
  function onCambiaStato(riga, codice, descrizione, terminale) {
    confirmAction({
      header: t('confirm.cambio_stato_title'),
      // ⚠️ La conferma NOMINA lo stato: «vuoi cambiare stato?» non basta a
      //    decidere, adesso che le transizioni possibili sono piu' di due.
      message: t('pagamenti.righe.conferma_stato_a', { stato: descrizione || codice }),
      // ⭐ Rosso = si va in uno stato TERMINALE, e lo dice il catalogo — non il
      //    nome: SCARTATA NON e' terminale (`is_final = false`), ed e' un gesto
      //    reversibile che non merita un allarme.
      danger: terminale === true,
      onAccept: async () => {
        const esito = await execute(
          () => cambiaStatoRiga(riga.id, codice),
          { successMessage: t('pagamenti.righe.stato_cambiato') },
        )
        if (esito !== null) ricarica()
      },
    })
  }

  // Scopo: elimina una riga (attivo = false) dopo conferma. ⭐ Rossa: la riga
  //        sparisce dall'elenco e dalla quadratura. Il rifiuto — se il foglio
  //        non e' piu' in bozza — arriva dal database con la sua frase.
  function onElimina(riga) {
    confirmAction({
      header: t('confirm.delete_title'),
      message: t('pagamenti.righe.conferma_elimina', {
        importo: formatCurrency(riga.importo),
        riferimento: riga.riferimento_ente || '—',
      }),
      danger: true,
      onAccept: async () => {
        const esito = await execute(
          () => eliminaRiga(riga.id),
          { successMessage: t('pagamenti.righe.eliminata') },
        )
        if (esito !== null) ricarica()
      },
    })
  }

  // Scopo: le voci del kebab per UNA riga.
  function buildRowActions(riga) {
    // ⛔ In sola lettura si NASCONDE: li' non e' lo stato, e' il permesso — e
    //    «non hai il permesso» non e' qualcosa che l'operatore possa risolvere
    //    da li'. ⚠️ `RowActionsMenu` non conosce `hideWhenReadonly` (lo onora
    //    `DrawerActionsBar`, non lui): il filtro va fatto qui.
    if (readonly()) return []

    const testata = testataDi(riga) || {}
    const rigaFinale = catalogoRiga(riga.stato_codice)?.is_final === true
    // ⭐ «Le righe di questo foglio si lavorano ancora?» lo dice il CATALOGO
    //    degli stati della distinta (`righe_lavorabili`, D-1 del brief
    //    righe-distinta-annullata): false sull'annullata, che «non e' mai
    //    successa»; true sulla chiusa, dove sospese e scartate hanno un futuro
    //    (D20-b/c). E' la stessa bandiera con cui il guard le congela.
    //    ⛔ Fino al 30/09 era `finale && !registrata`: uno stato mescolato a un
    //    fatto della testata, e la risposta viveva solo qui.
    //    ⚠️ `=== false`: una testata che non porta la bandiera non spegne
    //    niente — il rifiuto vero resta quello del database.
    const foglioSpento = testata.righeLavorabili === false
    // ⭐ Il motivo dice QUALE blocco e' scattato: «la riga e' gia' registrata»
    //    e «il foglio e' chiuso» si rimediano in due modi diversi, e una voce
    //    grigia senza spiegazione non si rimedia affatto.
    const motivoBlocco = rigaFinale
      ? t('pagamenti.righe.gia_registrata')
      : foglioSpento
        ? t('pagamenti.distinte.foglio_annullato')
        : undefined
    const bloccata = motivoBlocco !== undefined

    const uscite = transizioniRiga()[riga.stato_codice] || []

    // ── Abbina / Abbina e registra ──────────────────────────────────
    // Si abbina da dove la matrice ammette ABBINATA, e si RI-abbina da
    // ABBINATA. Da SCARTATA no: prima «Riprendi» (→ SOSPESA), e la voce lo dice.
    const abbinabile = riga.stato_codice === STATO_RIGA_CON_VERBO_PROPRIO
      || uscite.includes(STATO_RIGA_CON_VERBO_PROPRIO)
    const modo = testata.registrata === true ? MODO_ABBINA.REGISTRA : MODO_ABBINA.ABBINA
    const abbina = {
      key: 'abbina',
      label: modo === MODO_ABBINA.REGISTRA
        ? t('pagamenti.abbina.e_registra')
        : t('pagamenti.abbina.azione'),
      icon: modo === MODO_ABBINA.REGISTRA ? MANAGE_ICONS.REGISTRA : MANAGE_ICONS.BILLING_ACCOUNT,
      // ⚠️ Solo la tardiva scrive un movimento, e passa dal cancello della
      //    registrazione: senza il permesso la voce NON si propone (permesso ⇒
      //    nascondi). Il cancello vero resta il backend.
      ...(modo === MODO_ABBINA.REGISTRA ? { action: AZIONE_REGISTRA_DISTINTA } : {}),
      disabled: bloccata || !abbinabile,
      tooltip: motivoBlocco
        || (!abbinabile ? t('pagamenti.abbina.non_da_questo_stato') : undefined),
      command: () => onAbbina(riga, modo),
    }

    // ── Le transizioni, dalla matrice ───────────────────────────────
    const transizioni = uscite
      .filter((codice) => codice !== STATO_RIGA_CON_VERBO_PROPRIO)
      .map((codice) => {
        const stato = catalogoRiga(codice)
        const descrizione = stato?.descrizione || codice
        return {
          key: `stato-${codice}`,
          label: etichettaTransizione(riga.stato_codice, codice, descrizione),
          icon: ICONA_TRANSIZIONE_RIGA[codice] || MANAGE_ICONS.CONFIRM,
          severity: stato?.is_final ? 'danger' : undefined,
          disabled: bloccata,
          tooltip: motivoBlocco,
          command: () => onCambiaStato(riga, codice, descrizione, stato?.is_final),
        }
      })

    const azioni = [abbina, ...transizioni]

    // ── Elimina (D17), solo dove il contenuto si lavora ─────────────
    // Il cestino, spento COL MOTIVO che manda il database: la stessa check
    // che il guard chiama per rifiutare, quindi tooltip e 409 non possono dire
    // due cose diverse. ⛔ Nessun `if stato === …` qui.
    if (conElimina) {
      const eliminaBloccata = bloccoAttivo(riga, 'elimina_blocco', 'can_eliminare')
      azioni.push({
        key: 'elimina',
        label: t('pagamenti.righe.elimina'),
        icon: MANAGE_ICONS.DELETE,
        severity: 'danger',
        disabled: eliminaBloccata,
        tooltip: eliminaBloccata ? motivoBloccoRiga(t, te, riga, 'elimina_blocco') : undefined,
        command: () => onElimina(riga),
      })
    }

    return azioni
  }

  return { buildRowActions, catalogoRiga }
}
