import { ref, computed, watch } from 'vue'

// Orchestrazione della ComponentiDialog (modello unificato BoM) condivisa dai
// drawer riga di vendita: preventivi, offerte, contratti. Estratta dalla
// "regola del 2" (2026-05-31) dopo che il refactor `qta_operativa` ha reso i
// tre drawer uniformi sul campo quantità sorgente (`form.qta_operativa`).
//
// Cosa centralizza:
//  - stato dialog (`componentiDialogVisible`) + payload delta (`componentiPayload`)
//  - `showComponentiDialog`: quando la dialog è pertinente (CREATE su articolo
//    composito con UoM + quantità operativa valida)
//  - auto-apertura al primo set valido di (articolo, UoM) — con guardia anti
//    riapertura sullo stesso tuple
//  - `onComponentiConfirm`: memorizza il payload e calcola l'anteprima del
//    prezzo padre (`total / qtaPadre`) per gli articoli compositi
//  - `apriComponentiDialog` (riapertura manuale) e `resetComponentiDialog`
//
// Le differenze fra i domini sono passate come getter dal chiamante, NON
// inchiodate qui (altrimenti si rompe in silenzio uno dei domini):
//  - `isCreate`: !isEdit (preventivi/offerte) | formMode === 'create' (contratti)
//  - `isComposito`: articoloObj?.is_composito === true (uguale nei tre)
//  - `isPadreComposito`: per il write del prezzo padre — CASO A o is_composito
//    (preventivi) | is_composito (offerte/contratti)
//  - `qtaValida`: guard quantità per l'auto-apertura (rilevante solo per i
//    compositi, vedi `isComposito`). Default `qta_operativa > 0`: la pipeline
//    di preview del bundle (`ComponentiDialog`) assume quantità padre positiva
//    (fetch preview + calcolo `qtaPadre`). NB: il guard di SAVE della riga è
//    invece `<> 0` (negativi ammessi, es. resi) ed è gestito dal `canSave` del
//    drawer, non qui. Le eccezioni offerta passano `() => true` perché la qta
//    può essere null per fonti CONSUMO/LETTURE.
//
// IMPORTANTE (reattività): `form` va passato come Ref e `isCreate`/`isComposito`/
// `isPadreComposito`/`qtaValida` come funzioni-getter, non come valori
// "fotografati": il watch e i computed dipendono dalla loro reattività.
export function useComponentiDialog({
  form,
  isCreate,
  isComposito,
  isPadreComposito,
  qtaValida = () => (form.value.qta_operativa || 0) > 0,
}) {
  const componentiDialogVisible = ref(false)
  const componentiPayload = ref(null)

  // La dialog è pertinente solo in CREATE, su articolo composito, con UoM e
  // quantità operativa valorizzate. La quantità è `qta_operativa` (sorgente
  // operatore, UoM operativa) — uniforme nei tre domini post-refactor.
  const showComponentiDialog = computed(
    () => isCreate()
      && isComposito()
      && !!form.value.articolo_id
      && !!form.value.uom_operativa_id
      && qtaValida(),
  )

  // Watch su (articolo, UoM): cambia il CONTESTO di pricing → invalida i prezzi
  // suggeriti precedenti, reset del payload + auto-apertura per nuova
  // valorizzazione. La quantità NON è qui: cambiarla non invalida i prezzi
  // unitari dei componenti (modello: prezzo × coeff_qta_snapshot × qty_padre;
  // solo il summary va scalato). In EDIT non scatta mai.
  let _autoOpenedFor = null
  watch(
    () => [form.value.articolo_id, form.value.uom_operativa_id],
    ([articoloId, uomId]) => {
      if (!isCreate()) return
      componentiPayload.value = null
      const tupleKey = `${articoloId}|${uomId}`
      if (showComponentiDialog.value && _autoOpenedFor !== tupleKey) {
        _autoOpenedFor = tupleKey
        componentiDialogVisible.value = true
      } else if (!showComponentiDialog.value) {
        _autoOpenedFor = null
        componentiDialogVisible.value = false
      }
    },
  )

  // Auto-chiusura: se il contesto rende la dialog non piu' pertinente (es.
  // l'utente cambia tipo eccezione a ESCLUSIONE su un articolo composito dopo
  // che la dialog si era aperta — `isComposito` torna false), chiudila e scarta
  // il payload: non deve restare aperta ne' contribuire ai `componenti_overrides`
  // del save. Generico: vale ogni volta che `showComponentiDialog` diventa false.
  watch(showComponentiDialog, (pertinente) => {
    if (!pertinente) {
      componentiDialogVisible.value = false
      componentiPayload.value = null
      _autoOpenedFor = null
    }
  })

  // Riapertura manuale (CREATE): bottone "Modifica componenti" sotto il form,
  // per correggere gli override prima del save (l'auto-open scatta solo al
  // primo set valido).
  function apriComponentiDialog() {
    componentiDialogVisible.value = true
  }

  function onComponentiConfirm(payload) {
    // payload = { overrides, attivazioni, summary }; null se nessuna modifica.
    componentiPayload.value = payload
    // Anteprima prezzo padre lato client: il summary ritorna
    // `total = SUM(prezzo_componente × quantita_componente)` con
    // `quantita_componente = coeff_qta_snapshot × qta_padre`. Quindi
    // `total / qtaPadre = SUM(prezzo × coeff_qta_snapshot)` = prezzo unitario
    // padre per UNA unità — stesso valore che il trigger DB scriverà al save.
    // Il campo prezzo resta disabled per i compositi: l'operatore vede il
    // valore senza editarlo; al save il payload non include `prezzo_unitario`
    // per i compositi, quindi il BE resta fonte canonica (nessun drift).
    if (isPadreComposito() && payload?.summary?.qtaPadre > 0) {
      form.value.prezzo_unitario = payload.summary.total / payload.summary.qtaPadre
    }
  }

  // Reset dello stato dialog (visibilità + payload + guardia auto-open). I reset
  // di stato specifici del drawer (articoloObj, righe selezionate, ...) restano
  // a carico del chiamante.
  function resetComponentiDialog() {
    componentiDialogVisible.value = false
    componentiPayload.value = null
    _autoOpenedFor = null
  }

  return {
    componentiDialogVisible,
    componentiPayload,
    showComponentiDialog,
    apriComponentiDialog,
    onComponentiConfirm,
    resetComponentiDialog,
  }
}
