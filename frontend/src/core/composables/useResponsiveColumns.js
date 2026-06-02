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

import { computed, ref, unref, watch, onMounted, onBeforeUnmount } from 'vue'

const DEFAULT_COL_WIDTH = 120 // px, fallback quando il catalogo non dichiara larghezza
const DEFAULT_EXPANDER_WIDTH = 48 // px, colonna expander PrimeVue (= 3rem in ListaConfigurabile)
// Larghezza colonna azioni nelle due varianti: INLINE (più pulsanti icona
// affiancati, desktop) vs COMPATTA (singolo kebab ⋮). Comprimere le azioni a
// kebab è la PRIMA leva di recupero spazio, PRIMA di ritirare colonne dati.
const DEFAULT_ACTIONS_INLINE_WIDTH = 130 // px, ~3-4 pulsanti inline
const DEFAULT_ACTIONS_COMPACT_WIDTH = 56 // px, kebab singolo
// Margine per scrollbar verticale (classic ~15-17px su Win/Linux non-overlay) +
// padding/bordo: tenuto a 16px per non reintrodurre lo scroll orizzontale
// proprio sul filo del contenitore quando compare la scrollbar verticale.
const DEFAULT_SAFETY = 16

// Scopo: split delle colonne in visibili + ritirate in base alla larghezza
// reale del contenitore.
//
// Param:
//   - containerRef: ref a un elemento DOM la cui clientWidth e' lo spazio
//     disponibile per la tabella (tipicamente il root della lista).
//   - columns: ref/computed di descrittori colonna
//     `{ codice, larghezza, priorita, ordine, tipo_colonna, fissata }`
//     (le SOLE colonne dati: la colonna azioni e' gestita via `hasActions`).
//   - options: { hasActions, actionsWidth, expanderWidth, safety }
//     (valori scalari o ref).
//
// Ritorna: { containerWidth, visibleColumns, hiddenColumns }.
export function useResponsiveColumns(containerRef, columns, options = {}) {
  const containerWidth = ref(0)
  let ro = null
  let rafId = null

  // Coalescing via requestAnimationFrame: il ResizeObserver fira ad ogni frame
  // durante l'animazione della sidebar (~0.2s) — una sola misura per frame
  // evita ricomputazioni ridondanti e il "ballottaggio" delle colonne.
  function measure() {
    if (rafId != null) return
    const raf =
      typeof requestAnimationFrame !== 'undefined'
        ? requestAnimationFrame
        : (cb) => setTimeout(cb, 16)
    rafId = raf(() => {
      rafId = null
      const el = containerRef.value
      if (el) containerWidth.value = el.clientWidth
    })
  }

  onMounted(() => {
    measure()
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => measure())
      if (containerRef.value) ro.observe(containerRef.value)
    } else if (typeof window !== 'undefined') {
      // Fallback (ResizeObserver assente): almeno il resize finestra.
      window.addEventListener('resize', measure)
    }
  })

  // Se l'elemento osservato cambia (v-if/remount), ri-osserva.
  watch(containerRef, (el, old) => {
    if (ro) {
      if (old) ro.unobserve(old)
      if (el) ro.observe(el)
    }
    measure()
  })

  onBeforeUnmount(() => {
    if (rafId != null && typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(rafId)
      rafId = null
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

    const widthOf = (c) => (c.larghezza && c.larghezza > 0 ? c.larghezza : DEFAULT_COL_WIDTH)
    // identificatore / azione / colonne fissate: mai ritirate.
    const isPinned = (c) =>
      c.tipo_colonna === 'identificatore' || c.tipo_colonna === 'azione' || c.fissata === true

    // Larghezza non ancora nota (primo render): mostra tutto, niente flash di
    // ritiro a vuoto. Il measure() in onMounted la valorizza subito dopo.
    if (!W) return { visible: cols, hidden: [], actionsCompact: false }

    const pinnedSum = cols.filter(isPinned).reduce((s, c) => s + widthOf(c), 0)
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
      if (pinnedSum + compactActionsW + expanderW + keptSum + safety <= W) break
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
