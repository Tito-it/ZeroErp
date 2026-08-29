// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la selezione dei LOTTI da numerare, per la lista Lotti.
// ------------------------------------------------------------
//
// ⭐ PERCHÉ NON BASTA `useSelezioneToggle`. Quel BB nasce per i pannelli a
//    lista INTERA (smistamento preventivi, evasione ordine): il suo
//    `toggleAll` fa `selected = [...selezionabili]`, cioè SOSTITUISCE la
//    selezione. Qui la lista è paginata e per giunta divisa in due schede —
//    «lotti del mese» e «recuperi» — quindi spuntare «tutti» nella seconda
//    butterebbe via quanto spuntato nella prima, in silenzio: l'operatore se
//    ne accorgerebbe solo dal contatore del pulsante.
//    ✅ Dal 2026-08-27 il seleziona-tutto di pagina NON si riscrive più qui: è
//    `toggleAllInPagina`/`allInPagina`/`anyInPagina`, estratti nel BB. Questo
//    file e la lista gruppi della Lente 1 se l'erano scritto a mano tutti e
//    due, e nel frattempo altre TRE liste paginate avevano usato `toggleAll`
//    lo stesso — la regola è passata dal commento alla funzione.
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
//
// ⚠️ Una riga può smettere di essere selezionabile SOTTO I PIEDI (un collega
//    numera quel lotto, un giro lo fa avanzare). Senza il prune resterebbe
//    spuntata con la casella disabilitata — quindi non più rimovibile, contata
//    nel pulsante e ri-sottomessa a ogni atto.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSelezioneToggle } from '../_shared/righe/useSelezioneToggle'
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
// ⚠️ Va passato il Set reattivo e non un predicato: il prune sotto deve
//    SCATTARE quando parte un giro, e un predicato non è una dipendenza che
//    Vue possa osservare. Stessa forma della lista gruppi del cruscotto
//    competenza, che sorveglia `[gruppi, gruppiInCorso]` per la stessa ragione.
export function useSelezioneLotti({ righeVisibili, abilitata, chiaviInGiro = null }) {
  const { t } = useI18n()
  const selezione = ref([])

  const inGiro = (row) => (chiaviInGiro ? chiaviInGiro.value.has(row?.id) : false)

  // Scopo: questo lotto si può spuntare? Numerabile E non già in volo.
  //        Sede UNICA del predicato: lo usano le caselle, il seleziona-tutto,
  //        il guard del toggle e il prune.
  const selezionabile = (row) => lottoNumerabile(row) && !inGiro(row)

  // Le righe della PAGINA che si possono spuntare. Il BB vuole l'elenco delle
  // selezionabili: qui è per pagina, ed è coerente col seleziona-tutto sotto.
  const selezionabiliInPagina = computed(
    () => (righeVisibili.value ?? []).filter(selezionabile),
  )

  const {
    isSelected, toggleRow,
    allInPagina: tuttiInPagina,
    anyInPagina: alcuniInPagina,
    toggleAllInPagina: toggleTuttiInPagina,
  } = useSelezioneToggle({
    selected: selezione,
    selezionabili: selezionabiliInPagina,
    rowKey: 'id',
  })

  // ⚠️ Sorvegliate le righe visibili: al cambio pagina/scheda una riga già
  //    spuntata può ricomparire con uno stato diverso. Si toglie dalla
  //    selezione SOLO ciò che la pagina corrente dichiara non più
  //    selezionabile: le righe di altre pagine non sono in discussione qui.
  // ⚠️ Sorvegliati ENTRAMBI i motivi per cui una riga smette di essere
  //    spuntabile: il cambio delle righe visibili (cambio pagina/scheda, o uno
  //    stato cambiato sotto i piedi) E l'ingresso in un giro. Il secondo non
  //    dipende da una fetch, quindi un watch sulle sole righe non scatterebbe
  //    all'avvio di una numerazione — ed è proprio lì che serve: le righe
  //    appena spedite devono USCIRE dalla selezione, o il contatore del
  //    pulsante conterebbe lavoro già in volo e il giro dopo lo rimanderebbe.
  watch([righeVisibili, () => chiaviInGiro?.value], ([righe]) => {
    // Motivo 1 — la PAGINA dichiara la riga non più selezionabile (stato
    // cambiato sotto i piedi). Si guarda solo ciò che la pagina mostra: le
    // righe di altre pagine non sono in discussione qui.
    const nonPiu = new Set(
      (righe ?? []).filter((r) => !selezionabile(r)).map((r) => r.id),
    )
    // Motivo 2 — la riga è IN VOLO, e questo vale OVUNQUE si trovi, anche su
    // una pagina che non stiamo guardando.
    // ⚠️ È la differenza che conta: si può spuntare a pagina 1, andare a
    //    pagina 2 e inviare. Con il solo motivo 1 quella riga resterebbe
    //    spuntata e invisibile, e il giro successivo la rimanderebbe — cioè
    //    esattamente ciò che l'uscita dalla selezione deve impedire.
    const filtrata = selezione.value.filter((r) => !nonPiu.has(r.id) && !inGiro(r))
    if (filtrata.length === selezione.value.length) return
    selezione.value = filtrata
  })

  // Il motivo per cui una riga non si spunta, sulla casella spenta. ⚠️ Sulle
  // righe spuntabili torna `undefined` e non stringa vuota: un tooltip vuoto
  // comparirebbe comunque, come un rettangolo senza testo.
  function motivoNonSelezionabile(row) {
    // Il lotto è in volo: il motivo è quello, non lo stato del documento.
    if (inGiro(row)) return t('vendite.lotti.lotto_in_giro_tooltip')
    if (lottoNumerabile(row)) return undefined
    return t('vendite.lotti.non_numerabile_motivo', {
      stato: row?.stato_doc_fiscale_descrizione || row?.stato_doc_fiscale_codice || '—',
    })
  }

  function azzera() {
    selezione.value = []
  }

  return {
    // `null` quando il verbo non è disponibile: la lista non rende nemmeno la
    // colonna delle caselle.
    perLista: computed(() => (abilitata.value ? {
      isSelezionato: isSelected,
      isSelezionabile: selezionabile,
      motivoNonSelezionabile,
      toggle: toggleRow,
      tuttiInPagina,
      alcuniInPagina,
      toggleTuttiInPagina,
    } : null)),
    selezione,
    ids: computed(() => selezione.value.map((r) => r.id)),
    azzera,
  }
}
