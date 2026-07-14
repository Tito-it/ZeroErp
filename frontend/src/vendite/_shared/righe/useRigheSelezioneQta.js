// Scopo: BB "selezione righe con quantità" (estratto 2026-07-14, regola del
// 2 alla 3ª copia, ok Tid — unifica la macchina di OrdineEvasionePanel,
// DdtResoPanel e ResoRiconsegnaPanel): tabella di righe con residuo, selezione
// multipla, quantità editabile per riga (default = residuo) e semantica
// "tutto-vs-selezione" (selezione completa e intatta ⇒ il caller può inviare
// null e delegare al BE il residuo effettivo, race-proof).
//
// Il composable possiede SOLO la macchina di stato; restano nel caller (perché
// divergono davvero): il template/colonne, il watch sull'id del padre, il
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
// - onLoaded: (rows) => void opzionale — seed di mappe extra del caller
//   (es. tipo/motivo per riga nel crea-reso).
import { computed, ref } from 'vue'

export function useRigheSelezioneQta({
  fetchRighe,
  residuoDi,
  rowKey = 'id',
  readonly = () => false,
  onLoaded = null,
} = {}) {
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

  // Scopo: carica le righe, seeda qtaMap col residuo (0 per le esaurite) e
  //        preseleziona le selezionabili (lavora-tutto di default).
  async function loadRighe() {
    loadingRighe.value = true
    try {
      const rows = (await fetchRighe()) || []
      righe.value = rows
      const map = {}
      for (const r of rows) map[r[rowKey]] = residuoDi(r)
      qtaMap.value = map
      if (onLoaded) onLoaded(rows)
      selected.value = readonly() ? [] : [...righeSelezionabili.value]
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
    righe,
    loadingRighe,
    selected,
    qtaMap,
    righeSelezionabili,
    coversAllResiduo,
    loadRighe,
    buildPayloadRighe,
  }
}
