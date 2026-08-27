// Scopo: BB "toggle selezione con righe non selezionabili" (estratto
// 2026-07-15, ok Tid — uniforma i 4 pannelli-azione con selezione multipla:
// smistamento preventivi, evasione ordine, crea-reso DDT, ri-spedizione reso).
//
// PrimeVue 4 non ha più un predicato per-riga di selezionabilità sul
// DataTable (`isDataSelectable` rimosso): la Column selectionMode="multiple"
// rende OGNI riga spuntabile, incluse quelle già lavorate (smistate/evase/
// esaurite). Prima ogni pannello arrangiava un workaround diverso (setter che
// "rimbalza" nei preventivi, nessun guard nei pannelli BB). Qui vive la
// macchina unica: i template usano una Column checkbox CUSTOM il cui
// `:disabled` viene da `isSelectable`, e il guard di `toggleRow` è la difesa
// di coerenza (una riga non selezionabile non entra MAI in `selected`,
// qualunque cosa faccia il template).
//
// Config (tutti reattivi):
// - selected: Ref<row[]> — la selezione corrente (posseduta dal caller/BB).
// - selezionabili: Ref|Computed<row[]> — le sole righe lavorabili (residuo>0,
//   stato RESIDUA, ...): fuori da qui una riga non è né spuntabile né spuntata.
// - rowKey: chiave riga (default 'id').
//
// ⭐ DUE FORME DI SELEZIONA-TUTTO, e si sceglie in base alla lista:
//   · lista INTERA (dialog)  -> `toggleAll` / `allSelected` / `anySelected`
//   · lista PAGINATA         -> `toggleAllInPagina` / `allInPagina` / `anyInPagina`
//   Prendere la prima coppia su una lista paginata fa perdere in silenzio la
//   selezione delle altre pagine: vedi il blocco in fondo al file.
import { computed } from 'vue'

export function useSelezioneToggle({ selected, selezionabili, rowKey = 'id' }) {
  const selectableKeys = computed(
    () => new Set(selezionabili.value.map(r => r[rowKey])),
  )
  const selectedKeys = computed(
    () => new Set(selected.value.map(r => r[rowKey])),
  )

  function isSelectable(row) {
    return selectableKeys.value.has(row[rowKey])
  }

  function isSelected(row) {
    return selectedKeys.value.has(row[rowKey])
  }

  // Guard: una riga non selezionabile non entra in selezione (no-op), anche
  // se il template dimenticasse il :disabled.
  function toggleRow(row) {
    if (!isSelectable(row)) return
    selected.value = isSelected(row)
      ? selected.value.filter(r => r[rowKey] !== row[rowKey])
      : [...selected.value, row]
  }

  // Header "seleziona tutto": riferito alle SOLE selezionabili.
  const allSelected = computed(
    () => selezionabili.value.length > 0
      && selezionabili.value.every(r => selectedKeys.value.has(r[rowKey])),
  )

  // Selezione parziale: alimenta lo stato `indeterminate` della checkbox
  // header (informazione che il selectionMode nativo dava e la Column custom
  // deve ristabilire).
  // ⚠️ Guarda TUTTA la selezione, non la pagina: su una lista paginata è vero
  //    anche quando in questa pagina non c'è spuntato niente. Il gemello di
  //    pagina è `anyInPagina`, sotto.
  const anySelected = computed(
    () => selected.value.length > 0 && !allSelected.value,
  )

  // ⛔ SOSTITUISCE la selezione con le righe correnti. È il seleziona-tutto dei
  //    dialog a lista INTERA, dove `selected ⊆ selezionabili` per costruzione e
  //    sostituire equivale ad aggiungere.
  //    Su una lista PAGINATA non usare questo: usa `toggleAllInPagina`.
  function toggleAll() {
    selected.value = allSelected.value ? [] : [...selezionabili.value]
  }

  // ─────────────────────────────────────────────────────────────────────────
  // LISTE PAGINATE
  //
  // ⭐ Perché esistono questi tre. `toggleAll` qui sopra sostituisce, quindi su
  //    una lista paginata spuntare «tutti» in pagina 2 butta via quanto era
  //    spuntato in pagina 1 — in silenzio, e l'operatore se ne accorge solo dal
  //    contatore del pulsante. La selezione riga-per-riga invece compone bene
  //    fra le pagine (`toggleRow` accoda), quindi il difetto si vede SOLO
  //    passando dall'intestazione.
  //
  // ⛔ La regola era scritta come DISCIPLINA — un commento «attenzione, non
  //    riusare toggleAll qui» — in `useSelezioneLotti` e nella lista gruppi
  //    della Lente 1, che se lo erano riscritto a mano tutti e due. Non è
  //    bastato: **altre TRE liste paginate** — `ResiCodaTable`,
  //    `CommessaGestioneDrawer` e i residui di competenza — hanno usato
  //    `toggleAll` lo stesso, e quest'ultima proprio nel file dove il commento
  //    di avvertimento stava cento righe più su. Estratto il 2026-08-27
  //    (regola del 2, ok Tid): la funzione giusta diventa quella che si ha
  //    sotto mano, invece di una da ricordarsi di non usare.
  //    ⚠️ Su cinque liste paginate, tre erano rotte: il commento come presidio
  //    aveva un tasso di riuscita del 40%.
  //
  // ⚠️ `toggleAll` NON è stato toccato: per i due dialog a lista intera è
  //    corretto, ed è il loro comportamento.

  // Tutte quelle della pagina sono spuntate. ℹ️ È lo STESSO computed di
  // `allSelected`, non un secondo calcolo: quello guarda già le sole
  // `selezionabili`, cioè la pagina. Il nome esiste perché il consumatore
  // paginato prenda tre nomi coerenti fra loro invece di doversi ricordare
  // che uno dei tre si chiama in un altro modo.
  const allInPagina = allSelected

  // Selezione parziale DELLA PAGINA (stato `indeterminate` della checkbox
  // header su una lista paginata).
  const anyInPagina = computed(
    () => !allSelected.value
      && selezionabili.value.some(r => selectedKeys.value.has(r[rowKey])),
  )

  // Seleziona-tutto DI PAGINA: aggiunge o toglie le sole righe correnti e
  // lascia INTATTO il resto della selezione.
  function toggleAllInPagina() {
    const chiavi = new Set(selezionabili.value.map(r => r[rowKey]))
    if (allSelected.value) {
      selected.value = selected.value.filter(r => !chiavi.has(r[rowKey]))
      return
    }
    const gia = selectedKeys.value
    selected.value = [
      ...selected.value,
      ...selezionabili.value.filter(r => !gia.has(r[rowKey])),
    ]
  }

  return {
    isSelectable, isSelected, toggleRow,
    // Lista INTERA (dialog).
    toggleAll, allSelected, anySelected,
    // Lista PAGINATA.
    allInPagina, anyInPagina, toggleAllInPagina,
  }
}
