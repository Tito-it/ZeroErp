// Scopo: stato di apertura di `DocumentoDrawerHost` — la tripletta
//        (visible, chiave registry, id) + il comando `apri(tipo, id)`.
//        Estratto 2026-07-25 alla 3a copia (regola del 2, ok Tid): era
//        ripetuto identico in LineagePassaggiPanel e nasceva uguale nelle due
//        view drill-down dei cruscotti (Situazione aperta, Backlog).
//        Nessuna fetch, nessun watch: solo lo stato, così l'host resta l'unico
//        proprietario del ciclo di vita del drawer (chunk -> mount nascosto ->
//        apertura). L'apertura con tipo o id mancante e' un no-op: il caller
//        non deve duplicare la guardia.
//
//        `onClose` (opzionale): callback alla CHIUSURA del drawer. Serve ai
//        cruscotti — nel drawer l'operatore puo' aver fatto avanzare il
//        documento (conferma ordine, evasione, approvazione commessa) e la
//        riga che lo ha aperto sarebbe stantia o addirittura fuori perimetro.
//        Chi consuma il drawer in sola consultazione (tappe dei passaggi) lo
//        omette e usa `visible` in v-model.
import { ref } from 'vue'
import { DOCUMENTO_DRAWERS } from './documentoDrawers'

export function useDocumentoDrawer(onClose = null) {
  const visible = ref(false)
  const tipo = ref(null)
  const id = ref(null)

  // Scopo: apre il drawer del documento (chiave registry + id di dominio).
  //        Chiave sconosciuta o id mancante = no-op: la guardia sta QUI e i
  //        caller non la ripetono (era copiata in 3 componenti). Aprire l'host
  //        su una chiave senza drawer lascerebbe comunque il pannello vuoto.
  function apri(tipoCodice, docId) {
    if (docId == null || !tipoCodice || !DOCUMENTO_DRAWERS[tipoCodice]) return
    tipo.value = tipoCodice
    id.value = docId
    visible.value = true
  }

  // Scopo: handler `@update:visible` dell'host — allinea lo stato e, alla
  //        chiusura, notifica il caller (refresh dei dati che il drawer puo'
  //        aver cambiato).
  function onVisibleChange(v) {
    visible.value = v
    if (!v) onClose?.()
  }

  return { visible, tipo, id, apri, onVisibleChange }
}
