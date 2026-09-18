// Scopo: ritiro dinamico delle colonne di una DataTable quando lo spazio non
// basta (packing a somma), per evitare la scrollbar orizzontale — tipicamente
// all'apertura della sidebar. Le colonne a `priorita` piu' bassa si ritirano
// per prime in una riga di espansione (zero dati persi); identificatore,
// azione e colonne fissate non si ritirano mai.
//
// DEROGA DOCUMENTATA allo standard "responsive CSS-first, niente JS di
// detection" (frontend-standards.md §"Pattern lista"): le media query CSS
// reagiscono solo a `window.innerWidth`, ma l'apertura della sidebar NON
// cambia la larghezza della finestra — restringe solo l'area contenuto. Le
// media query sono cieche a questo evento; l'unico modo per reagire alla
// larghezza REALE del contenitore (che cambia sia col viewport sia con la
// sidebar) e' osservarla con un ResizeObserver. Non e' una scelta di comodo:
// l'alternativa puramente-CSS per questo caso non esiste.
//
// Algoritmo (packing a somma, decisione Tid 2026-06-02): ogni colonna
// contribuisce con la sua `larghezza` (= larghezza_default del catalogo);
// quando la somma supera la larghezza del contenitore si ritira la colonna a
// `priorita` piu' bassa (tiebreaker: `ordine` piu' alto = piu' a destra),
// finche' la somma rientra. Nessuna compressione intermedia e nessuna
// `larghezza_min` (riusa lo standard `larghezza_default`).
//
// ⛔ IL CONTO VALE SOLO SE LA TABELLA RENDE QUELLE LARGHEZZE. Fino al
//    2026-09-18 non lo faceva: la tabella e' `width: max-content`, quindi ogni
//    colonna era larga quanto il suo contenuto piu' lungo e la larghezza di
//    catalogo era solo un minimo. Il packing diceva «entra tutto» sui numeri
//    dichiarati, il browser rendeva quelli veri, e la differenza usciva come
//    scrollbar orizzontale — di piu' a sidebar CHIUSA, perche' con piu' spazio
//    il packing ritirava meno e lasciava piu' colonne libere di sbordare.
//    Da quel giorno `ListaConfigurabile` passa la larghezza anche come TETTO
//    delle celle (`--col-w`, main.css §liste responsive): un contenuto piu'
//    lungo va in ellissi, visibile, e la somma dichiarata e' quella resa.

import { computed, ref, unref, watch, onMounted, onBeforeUnmount } from 'vue'

// ⭐ ESPORTATE, perche' i conti del packing valgono solo se la tabella rende
//    ESATTAMENTE questi numeri: `ListaConfigurabile` li usa come `width` e come
//    tetto delle celle (`--col-w`). Due copie dello stesso numero — una qui e
//    una nel template — e' il modo in cui il packing e il rendering si sfilano.
export const DEFAULT_COL_WIDTH = 120 // px, fallback quando il catalogo non dichiara larghezza
export const DEFAULT_EXPANDER_WIDTH = 48 // px, colonna expander PrimeVue (= 3rem in ListaConfigurabile)
// Larghezza colonna azioni nelle due varianti: INLINE (più pulsanti icona
// affiancati, desktop) vs COMPATTA (singolo kebab ⋮). Comprimere le azioni a
// kebab è la PRIMA leva di recupero spazio, PRIMA di ritirare colonne dati.
export const DEFAULT_ACTIONS_COMPACT_WIDTH = 56 // px, kebab singolo
// La variante INLINE e' larga quanto i pulsanti che contiene, e quanti sono lo
// sa solo il chiamante: la riserva si calcola dal NUMERO di azioni
// (`larghezzaAzioniInline(n)`), non da una costante.
// ⚠️ ACCOPPIATI A MANO ai token del tema e a main.css: un pulsante icon-only
//    `size="small"` e' `button.sm.icon.only.width` = 2rem (Aura), il gap di
//    `.app-row-actions-inline` e' 0.25rem, il padding orizzontale della cella
//    e' `--app-table-cell-padding-x` = 0.5rem per lato. Fino al 2026-09-18 la
//    riserva era una costante (130px, «~3-4 pulsanti») che copriva TRE pulsanti:
//    quattro (Soggetti, Fornitori, CommessaGestione) o sei (Clienti) la
//    superavano in silenzio, e la differenza usciva come scrollbar orizzontale.
export const ACTIONS_INLINE_BUTTON_WIDTH = 32 // px, 2rem
export const ACTIONS_INLINE_GAP = 4 // px, 0.25rem
export const ACTIONS_CELL_PADDING_X = 16 // px, 0.5rem per lato
export const DEFAULT_ACTIONS_INLINE_COUNT = 4

// Scopo: riserva (px) della colonna azioni con `n` pulsanti inline.
export function larghezzaAzioniInline(n) {
  const count = Math.max(1, Number(n) || DEFAULT_ACTIONS_INLINE_COUNT)
  return ACTIONS_CELL_PADDING_X + count * ACTIONS_INLINE_BUTTON_WIDTH + (count - 1) * ACTIONS_INLINE_GAP
}

const DEFAULT_ACTIONS_INLINE_WIDTH = larghezzaAzioniInline(DEFAULT_ACTIONS_INLINE_COUNT)
// Margine per scrollbar verticale (classic ~15-17px su Win/Linux non-overlay) +
// padding/bordo: tenuto a 16px per non reintrodurre lo scroll orizzontale
// proprio sul filo del contenitore quando compare la scrollbar verticale.
const DEFAULT_SAFETY = 16
// Quanto si aspetta che la larghezza SI FERMI prima di rimisurare. Il perche'
// sta sulla `measure()`.
// ⚠️ ACCOPPIATO A MANO a `--app-transition-normal` (0.2s, `theme.css`): deve
//    restare piu' lungo, o si torna a ricalcolare a meta' animazione. Non lo
//    legge da li' di proposito — servirebbe un `getComputedStyle` a ogni
//    istanza di lista per un valore che cambia una volta ogni mai — ma se quella
//    transizione si allunga, questo numero va alzato con lei.
const ASSESTAMENTO_MS = 260

// Scopo: split delle colonne in visibili + ritirate in base alla larghezza
// reale del contenitore.
//
// Param:
//   - containerRef: ref a un elemento DOM la cui clientWidth e' lo spazio
//     disponibile per la tabella (tipicamente il root della lista).
//   - columns: ref/computed di descrittori colonna
//     `{ codice, larghezza, priorita, ordine, tipo_colonna, fissata }`
//     (le SOLE colonne dati: la colonna azioni e' gestita via `hasActions`).
//   - options: { hasActions, actionsInlineWidth, actionsCompactWidth,
//     hasSelection, hasRowExpansion, expanderWidth, safety }
//     (valori scalari o ref).
//     ⚠️ `hasSelection` e `hasRowExpansion` sono le colonne di CHROME che la
//        lista monta fuori dal catalogo (checkbox di selezione; expander
//        sempre presente quando c'e' un dettaglio inline): fino al 2026-09-18
//        non entravano nel conto, e la loro larghezza usciva dal contenitore
//        senza che il packing lo sapesse.
//
// Ritorna: { containerWidth, visibleColumns, hiddenColumns, actionsCompact }.
export function useResponsiveColumns(containerRef, columns, options = {}) {
  const containerWidth = ref(0)
  let ro = null
  let timerId = null

  // Scopo: legge la larghezza vera e la pubblica. Da qui in poi ricalcola il
  //        packing e, se il verdetto cambia, la DataTable ridisegna le colonne.
  function leggi() {
    timerId = null
    const el = containerRef.value
    if (el) containerWidth.value = el.clientWidth
  }

  // ⛔ SI MISURA QUANDO LA LARGHEZZA SI FERMA, NON MENTRE CAMBIA — e il motivo
  //    non e' l'eleganza, e' che il costo non sta nella misura.
  //
  //    Il `ResizeObserver` fira a OGNI FRAME per tutta l'animazione della
  //    sidebar (~0.2s, una dozzina di frame). La misura in se' e' una lettura di
  //    `clientWidth`; quello che costa e' cio' che ne segue — `containerWidth`
  //    cambia, il packing ricalcola, `visibleColumns` cambia, e PrimeVue
  //    RIDISEGNA le colonne di tutta la tabella. Farlo dodici volte dentro
  //    un'animazione di 200ms consuma il budget di ogni frame: la sidebar si
  //    muove a scatti e sembra rallentata.
  //
  // ⭐ E gli undici ricalcoli intermedi sono BUTTATI: l'unico verdetto che
  //    conta e' quello sulla larghezza finale. Il "ballottaggio" delle colonne
  //    che la stesura precedente citava come effetto collaterale era in realta'
  //    il sintomo — le colonne entravano e uscivano seguendo una larghezza che
  //    stava ancora cambiando.
  //
  // ⚠️ TRAILING, non leading: durante il trascinamento del bordo finestra le
  //    colonne restano ferme e si assestano alla fine. E' voluto — un ritiro di
  //    colonna a meta' gesto e' esattamente cio' che disorienta.
  // ⚠️ La finestra (`ASSESTAMENTO_MS`) e' piu' lunga dell'animazione della
  //    sidebar: piu' corta e si ricadrebbe a ricalcolare a meta' corsa, che e'
  //    il difetto che questo codice esiste per togliere.
  function measure({ subito = false } = {}) {
    if (timerId != null) clearTimeout(timerId)
    if (subito) {
      leggi()
      return
    }
    timerId = setTimeout(leggi, ASSESTAMENTO_MS)
  }

  onMounted(() => {
    // ⭐ La PRIMA misura e' immediata: al montaggio non c'e' nessuna animazione
    //    in corso, e aspettare un quarto di secondo mostrerebbe la lista con le
    //    colonne sbagliate e poi un salto.
    measure({ subito: true })
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => measure())
      if (containerRef.value) ro.observe(containerRef.value)
    } else if (typeof window !== 'undefined') {
      // Fallback (ResizeObserver assente): almeno il resize finestra.
      window.addEventListener('resize', measure)
    }
  })

  // Se l'elemento osservato cambia (v-if/remount), ri-osserva.
  // ⚠️ Misura SUBITO: un remount non e' un'animazione in corso, e' un elemento
  //    nuovo che deve nascere con le colonne giuste.
  watch(containerRef, (el, old) => {
    if (ro) {
      if (old) ro.unobserve(old)
      if (el) ro.observe(el)
    }
    measure({ subito: true })
  })

  onBeforeUnmount(() => {
    if (timerId != null) {
      clearTimeout(timerId)
      timerId = null
    }
    if (ro) {
      ro.disconnect()
      ro = null
    } else if (typeof window !== 'undefined') {
      window.removeEventListener('resize', measure)
    }
  })

  const layout = computed(() => {
    const cols = columns.value || []
    const W = containerWidth.value
    const hasActions = !!unref(options.hasActions)
    const inlineActionsW = hasActions
      ? (unref(options.actionsInlineWidth) ?? DEFAULT_ACTIONS_INLINE_WIDTH)
      : 0
    const compactActionsW = hasActions
      ? (unref(options.actionsCompactWidth) ?? DEFAULT_ACTIONS_COMPACT_WIDTH)
      : 0
    const expanderW = unref(options.expanderWidth) ?? DEFAULT_EXPANDER_WIDTH
    const safety = unref(options.safety) ?? DEFAULT_SAFETY
    // Chrome della lista fuori dal catalogo: la colonna di selezione ha la
    // stessa larghezza dell'expander (3rem), e l'expander c'e' SEMPRE quando
    // la lista ha un dettaglio inline — non solo a colonne ritirate.
    const chromeW =
      (unref(options.hasSelection) ? expanderW : 0) +
      (unref(options.hasRowExpansion) ? expanderW : 0)
    // A colonne ritirate l'expander compare: si aggiunge solo se non e' gia'
    // nel chrome per via del dettaglio inline.
    const expanderRitiroW = unref(options.hasRowExpansion) ? 0 : expanderW

    const widthOf = (c) => (c.larghezza && c.larghezza > 0 ? c.larghezza : DEFAULT_COL_WIDTH)
    // identificatore / azione / colonne fissate: mai ritirate.
    const isPinned = (c) =>
      c.tipo_colonna === 'identificatore' || c.tipo_colonna === 'azione' || c.fissata === true

    // Larghezza non ancora nota (primo render): mostra tutto, niente flash di
    // ritiro a vuoto. Il measure() in onMounted la valorizza subito dopo.
    if (!W) return { visible: cols, hidden: [], actionsCompact: false }

    const pinnedSum = chromeW + cols.filter(isPinned).reduce((s, c) => s + widthOf(c), 0)
    const retirable = cols.filter((c) => !isPinned(c))
    const retirableSum = retirable.reduce((s, c) => s + widthOf(c), 0)

    // LIVELLO 1: tutto entra con le azioni INLINE → nessuna compattazione,
    // nessun ritiro.
    if (pinnedSum + inlineActionsW + retirableSum + safety <= W) {
      return { visible: cols, hidden: [], actionsCompact: false }
    }

    // LIVELLO 2 (prima leva di recupero): comprimi le AZIONI a kebab. Se tanto
    // basta, nessuna colonna dati viene ritirata. È il comportamento atteso:
    // meglio un'azione in più click che perdere una colonna dalla vista.
    if (pinnedSum + compactActionsW + retirableSum + safety <= W) {
      return { visible: cols, hidden: [], actionsCompact: true }
    }

    // LIVELLO 3: azioni gia' compatte + ritiro colonne. L'expander comparira'.
    // Ordine di ritiro: priorita' crescente (la piu' bassa per prima); a
    // parita', ordine_default decrescente (la colonna piu' a destra per prima).
    const retireOrder = [...retirable].sort((a, b) => {
      const pa = a.priorita ?? 50
      const pb = b.priorita ?? 50
      if (pa !== pb) return pa - pb
      return (b.ordine ?? 0) - (a.ordine ?? 0)
    })

    const hiddenCodes = new Set()
    let keptSum = retirableSum
    for (const c of retireOrder) {
      if (pinnedSum + compactActionsW + expanderRitiroW + keptSum + safety <= W) break
      hiddenCodes.add(c.codice)
      keptSum -= widthOf(c)
    }

    return {
      visible: cols.filter((c) => !hiddenCodes.has(c.codice)),
      hidden: cols.filter((c) => hiddenCodes.has(c.codice)),
      actionsCompact: true,
    }
  })

  return {
    containerWidth,
    visibleColumns: computed(() => layout.value.visible),
    hiddenColumns: computed(() => layout.value.hidden),
    actionsCompact: computed(() => layout.value.actionsCompact),
  }
}
