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
//    Del BB si riusano quindi `isSelezionato`/`toggle` (il guard di coerenza) e
//    si riscrive il solo seleziona-tutto, che opera SULLA PAGINA CORRENTE
//    aggiungendo o togliendo e lasciando intatto il resto. È la stessa forma
//    già in servizio sulla lista gruppi della Lente 1.
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

export function useSelezioneLotti({ righeVisibili, abilitata }) {
  const { t } = useI18n()
  const selezione = ref([])

  // Le righe della PAGINA che si possono spuntare. Il BB vuole l'elenco delle
  // selezionabili: qui è per pagina, ed è coerente col seleziona-tutto sotto.
  const selezionabiliInPagina = computed(
    () => (righeVisibili.value ?? []).filter(lottoNumerabile),
  )

  const { isSelected, toggleRow } = useSelezioneToggle({
    selected: selezione,
    selezionabili: selezionabiliInPagina,
    rowKey: 'id',
  })

  // ⚠️ Sorvegliate le righe visibili: al cambio pagina/scheda una riga già
  //    spuntata può ricomparire con uno stato diverso. Si toglie dalla
  //    selezione SOLO ciò che la pagina corrente dichiara non più
  //    selezionabile: le righe di altre pagine non sono in discussione qui.
  watch(righeVisibili, (righe) => {
    const nonPiu = new Set(
      (righe ?? []).filter((r) => !lottoNumerabile(r)).map((r) => r.id),
    )
    if (!nonPiu.size) return
    selezione.value = selezione.value.filter((r) => !nonPiu.has(r.id))
  })

  const tuttiInPagina = computed(() => {
    const p = selezionabiliInPagina.value
    return p.length > 0 && p.every((r) => isSelected(r))
  })

  const alcuniInPagina = computed(
    () => !tuttiInPagina.value && selezionabiliInPagina.value.some((r) => isSelected(r)),
  )

  // Seleziona-tutto DELLA PAGINA: aggiunge o toglie, non sostituisce.
  function toggleTuttiInPagina() {
    const chiavi = new Set(selezionabiliInPagina.value.map((r) => r.id))
    if (tuttiInPagina.value) {
      selezione.value = selezione.value.filter((r) => !chiavi.has(r.id))
      return
    }
    const gia = new Set(selezione.value.map((r) => r.id))
    selezione.value = [
      ...selezione.value,
      ...selezionabiliInPagina.value.filter((r) => !gia.has(r.id)),
    ]
  }

  // Il motivo per cui una riga non si spunta, sulla casella spenta. ⚠️ Sulle
  // righe spuntabili torna `undefined` e non stringa vuota: un tooltip vuoto
  // comparirebbe comunque, come un rettangolo senza testo.
  function motivoNonSelezionabile(row) {
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
      isSelezionabile: lottoNumerabile,
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
