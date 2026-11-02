// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: quale LOTTO si può spuntare per la numerazione, e perché no. È tutto
//        ciò che questo file contiene: il giro della selezione (caselle,
//        seleziona-tutto di pagina, prune, forma del ritorno) è del telaio
//        `useSelezioneLista`.
// ------------------------------------------------------------
//
// ⭐ RIDOTTO AL DOMINIO il 2026-09-04 (regola del 2, ok Tid). Prima questo file
//    conteneva tutta la trafila — filtrare le selezionabili della pagina,
//    cablare `useSelezioneToggle`, sorvegliare le righe per il prune, comporre
//    `perLista` — e la seconda copia (le code di lavoro) l'ha resa visibile:
//    ~85% in comune, e a divergere era solo il dominio. ⚠️ Il comportamento
//    NON cambia: il telaio porta con sé i DUE motivi del prune, che sono nati
//    qui e sono la parte che non si vede.
//
// ⭐ E LA SELEZIONE ATTRAVERSA LE DUE SCHEDE, di proposito: un lotto di
//    competenza precedente — quello che sta nei «recuperi» — si numera insieme
//    a quelli del mese. È il caso che il verbo di massa non sa fare, perché
//    quello lavora su una competenza sola.
//
// ⛔ SI SPUNTA SOLO CIÒ CHE SI PUÒ NUMERARE, e la casella spenta è una
//    comodità, NON un presidio: il perimetro vero lo applica il backend, che
//    aggiunge comunque lo stato EMESSA. Un lotto non emesso che arrivasse
//    all'API non verrebbe numerato lo stesso.
import { useI18n } from 'vue-i18n'
import { useSelezioneLista } from '../../core/composables/useSelezioneLista'
// ⛔ Il predicato NON è scritto qui: viene da `useLottoAzioni`, che è la sede
//   unica di «cosa si può fare su questo lotto» e da cui il kebab della riga
//   propone «Rendi definitive». Con due copie la casella e il menu della STESSA
//   riga potrebbero contraddirsi — nessun errore, solo un'interfaccia che dice
//   due cose diverse sullo stesso oggetto.
import { lottoNumerabile } from './useLottoAzioni'

// `chiaviInGiro`: Set REATTIVO degli id dei lotti dentro un giro di numerazione
// ancora vivo (`useRigheInGiro` del chiamante). Un lotto in volo NON è
// spuntabile — è così che due selezioni non possono sovrapporsi, e la seconda
// non ri-manda ciò che la prima sta già numerando.
// ⚠️ Va passato il Set reattivo e non un predicato: il prune del telaio deve
//    SCATTARE quando parte un giro, e un predicato non è una dipendenza che
//    Vue possa osservare — per questo viaggia anche in `sorveglia`.
export function useSelezioneLotti({ righeVisibili, abilitata, chiaviInGiro = null }) {
  const { t } = useI18n()

  const inGiro = (row) => (chiaviInGiro ? chiaviInGiro.value.has(row?.id) : false)

  // Sede UNICA del predicato: il telaio lo gira alle caselle, al
  // seleziona-tutto, al guard del toggle e al prune.
  const selezionabile = (row) => lottoNumerabile(row) && !inGiro(row)

  // Il motivo sulla casella spenta. `undefined` sulle righe spuntabili: un
  // tooltip vuoto comparirebbe comunque, come un rettangolo senza testo.
  function motivoNonSelezionabile(row) {
    // Il lotto è in volo: il motivo è quello, non lo stato del documento.
    if (inGiro(row)) return t('vendite.lotti.lotto_in_giro_tooltip')
    if (lottoNumerabile(row)) return undefined
    return t('vendite.lotti.non_numerabile_motivo', {
      stato: row?.stato_doc_fiscale_descrizione || row?.stato_doc_fiscale_codice || '—',
    })
  }

  // ⭐ `escludiOvunque` + `sorveglia` sono il MOTIVO 2 del prune, e qui c'è
  //    perché «è dentro un giro» vive FUORI dalla riga: si può spuntare a
  //    pagina 1, andare a pagina 2 e inviare, e col solo motivo 1 quel lotto
  //    resterebbe spuntato e invisibile — il giro successivo lo rimanderebbe,
  //    cioè esattamente ciò che l'uscita dalla selezione deve impedire.
  //    ⚠️ E non dipende da una fetch: senza `sorveglia` il watch non
  //    scatterebbe all'avvio di una numerazione, che è proprio quando serve.
  return useSelezioneLista({
    righeVisibili,
    abilitata,
    selezionabile,
    motivoNonSelezionabile,
    escludiOvunque: inGiro,
    sorveglia: [() => chiaviInGiro?.value],
  })
}
