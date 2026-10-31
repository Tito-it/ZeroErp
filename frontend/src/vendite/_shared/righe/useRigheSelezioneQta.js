// Scopo: BB "selezione righe con quantità" (estratto 2026-07-14, regola del
// 2 alla 3ª copia, ok Tid — unifica la macchina di OrdineEvasioneDialog,
// DdtResoDialog e ResoRiconsegnaDialog): tabella di righe con residuo, selezione
// multipla, quantità editabile per riga (default = residuo) e semantica
// "tutto-vs-selezione" (selezione completa e intatta ⇒ il caller può inviare
// null e delegare al BE il residuo effettivo, race-proof).
//
// Il composable possiede SOLO la macchina di stato; restano nel caller (perché
// divergono davvero): le colonne di dominio (la tabella e' il BB
// `TabellaSelezioneRighe`, dal 2026-10-31), il watch sull'id del padre, il
// flusso confirm/execute/notify dell'azione e la shape del payload (iniettata
// via `buildPayloadRighe(mapRow)`).
//
// Config:
// - fetchRighe: async () => rows — il caller filtra/normalizza le righe che
//   vuole in tabella (es. solo riapre_residuo per la ri-consegna).
// - residuoDi: (row) => Number — quantità ancora lavorabile della riga
//   (campo diverso per consumer: qta_residua_operativa / qta_resa_residua_operativa
//   / qta_residua base).
// - rowKey: chiave riga per selezione/qtaMap (default 'id'; 'ddt_riga_id' nel
//   pannello crea-reso).
// - readonly: () => bool — in readonly la preselezione resta vuota (consuntivo).
// - preselezione: 'tutto' (default) | 'nessuna' — politica di seed al load.
//   'tutto' preseleziona le righe lavorabili e riempie le quantità col residuo
//   ("lavora tutto": evasione ordine e ri-consegna, dove chiudere il residuo è
//   l'esito atteso e il default risparmia lavoro). 'nessuna' lascia selezione
//   vuota e quantità NON compilate: è il crea-reso (decisione Tid 2026-07-25),
//   dove quali righe tornano indietro e in che quantità è un DATO DI FATTO che
//   solo l'operatore conosce — proporre "tutto reso" invita a confermare un
//   reso totale per inerzia, e il reso totale flippa il DDT a RESO.
// - onLoaded: (rows) => void opzionale — seed di mappe extra del caller
//   (es. tipo/motivo per riga nel crea-reso).
// - visibile: () => bool — la visibilita' del dialog che monta la macchina.
//   Con questa il BB tiene la FOTOGRAFIA (D-14, 2026-10-03, regola del 2, ok
//   Tid): selezione e quantita' sono lavoro dell'operatore, e uscire dopo
//   averle toccate chiede. ⭐ Si fissa alla fine di OGNI `loadRighe` — anche
//   la ricarica dopo un gesto gia' salvato riscrive selezione e quantita', ed
//   e' la nuova base, non una modifica (la copia che lo dimenticava chiedeva
//   «modifiche non salvate» a chi non aveva toccato niente). Espone
//   `chiudiConConferma` per `conferma-uscita` di AppDialog.
// - statoExtra: () => object opzionale — lo stato del caller da fotografare
//   insieme (le mappe tipo/motivo del crea-reso).
import { computed, ref } from 'vue'
import { useSelezioneToggle } from '../../../core/composables/useSelezioneToggle'
import { useFotografiaDialog } from '../../../core/composables/useFotografiaDialog'

export function useRigheSelezioneQta({
  fetchRighe,
  residuoDi,
  rowKey = 'id',
  readonly = () => false,
  preselezione = 'tutto',
  onLoaded = null,
  visibile = null,
  statoExtra = () => ({}),
} = {}) {
  const preselezionaTutto = preselezione !== 'nessuna'
  const righe = ref([])
  const loadingRighe = ref(false)
  const selected = ref([])
  // Quantità per riga (keyed per rowKey), default = residuo.
  const qtaMap = ref({})

  // Righe con residuo > 0: le uniche selezionabili/lavorabili. Le altre
  // restano visibili come consuntivo.
  const righeSelezionabili = computed(
    () => righe.value.filter(r => residuoDi(r) > 0),
  )

  // Macchina toggle (BB): checkbox custom nei template (:disabled da
  // isSelectable) + guard che tiene fuori dalla selezione le righe esaurite.
  const { isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected } =
    useSelezioneToggle({ selected, selezionabili: righeSelezionabili, rowKey })

  // La fotografia si fissa a righe caricate, non all'apertura: i dati che
  // arrivano dalla fetch non sono modifiche.
  const fotografia = visibile
    ? useFotografiaDialog(
      () => ({ selezionate: selected.value.map(r => r[rowKey]), qta: qtaMap.value, ...statoExtra() }),
      { visibile, fissaAllApertura: false },
    )
    : null

  // Scopo: carica le righe e applica la politica di seed (`preselezione`):
  //        'tutto' → qtaMap col residuo (0 per le esaurite) + righe lavorabili
  //        preselezionate; 'nessuna' → qtaMap vuota (null = campo non compilato)
  //        e selezione vuota. In readonly la selezione resta comunque vuota.
  async function loadRighe() {
    loadingRighe.value = true
    try {
      const rows = (await fetchRighe()) || []
      righe.value = rows
      const map = {}
      for (const r of rows) map[r[rowKey]] = preselezionaTutto ? residuoDi(r) : null
      qtaMap.value = map
      if (onLoaded) onLoaded(rows)
      selected.value = (readonly() || !preselezionaTutto)
        ? []
        : [...righeSelezionabili.value]
      fotografia?.fissa()
    } finally {
      loadingRighe.value = false
    }
  }

  // Tutte le righe SELEZIONABILI selezionate E nessuna quantità ritoccata
  // rispetto al residuo: il caller può delegare al BE il "tutto il residuo"
  // (payload null, race-proof su lavorazioni concorrenti).
  const coversAllResiduo = computed(() => {
    const selezionabili = righeSelezionabili.value
    if (selezionabili.length === 0) return false
    const selIds = new Set(selected.value.map(r => r[rowKey]))
    if (selIds.size !== selezionabili.length) return false
    return selezionabili.every(
      r => selIds.has(r[rowKey]) && Number(qtaMap.value[r[rowKey]]) === residuoDi(r),
    )
  })

  // Scopo: costruisce il payload righe dalla selezione corrente. Le righe
  //        con qta <= 0 sono scartate; `filterRow(row, qta)` opzionale per
  //        validità extra (es. tipo reso obbligatorio); `mapRow(row, qta)`
  //        produce la voce nella shape del consumer.
  function buildPayloadRighe(mapRow, { filterRow = null } = {}) {
    const out = []
    for (const r of selected.value) {
      const qta = Number(qtaMap.value[r[rowKey]]) || 0
      if (qta <= 0) continue
      if (filterRow && !filterRow(r, qta)) continue
      out.push(mapRow(r, qta))
    }
    return out
  }

  return {
    // Chiave riga, residuo e sola lettura, ri-esposti per `TabellaSelezioneRighe`:
    // la tabella li legge dalla macchina invece di riceverli una seconda volta
    // dal caller (una copia di `readonly` potrebbe dire il contrario della
    // selezione, che in sola lettura la macchina lascia vuota).
    rowKey,
    residuoDi,
    readonly,
    righe,
    loadingRighe,
    selected,
    qtaMap,
    righeSelezionabili,
    coversAllResiduo,
    loadRighe,
    buildPayloadRighe,
    // Toggle API per la Column checkbox custom dei template.
    isSelectable,
    isSelected,
    toggleRow,
    toggleAll,
    allSelected,
    anySelected,
    modificato: fotografia ? fotografia.modificato : computed(() => false),
    chiudiConConferma: fotografia ? fotografia.chiudiConConferma : (chiudi) => chiudi(),
  }
}
