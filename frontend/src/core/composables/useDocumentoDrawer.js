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
import { registraDrawerChiudibile } from './useDrawerChiusuraGlobale'
import { drawerEntita } from '../drawerEntita'

export function useDocumentoDrawer(onClose = null) {
  const visible = ref(false)
  const tipo = ref(null)
  const id = ref(null)

  // Scopo: apre il drawer del documento (chiave registry + id di dominio).
  //        Chiave sconosciuta o id mancante = no-op: la guardia sta QUI e i
  //        caller non la ripetono (era copiata in 3 componenti). Aprire l'host
  //        su una chiave senza drawer lascerebbe comunque il pannello vuoto.
  function apri(tipoCodice, docId) {
    if (docId == null || !tipoCodice || !drawerEntita(tipoCodice)) return
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

  // ⭐ QUI si chiude la CASCATA. Ogni drawer impilato monta la propria barra
  // collegamenti, che monta il proprio host: registrandosi qui, un ordine che ha
  // aperto un DDT che ha aperto un reso si chiude tutto insieme al primo cambio
  // di rotta — e nessuno dei tre ha dovuto sapere degli altri due.
  //
  // 🔴 SI CHIUDE E BASTA: niente `onVisibleChange(false)`, quindi `onClose` NON
  // scatta. La prima versione (2026-08-19) passava di li' «per fare la stessa
  // strada della X in testata», e ha prodotto un difetto vero: `onClose` e' un
  // callback di RICARICO, e la chiusura globale lo faceva partire su OGNI host
  // registrato a OGNI cambio di rotta — anche su drawer chiusi, con le loro
  // prop a null. `CommessaGestioneDrawer` passa `reloadAll()`, che finiva per
  // chiedere `/vendite/commesse/null/stato/`: 404, toast d'errore, e siccome
  // scattava a ogni navigazione l'avviso non se ne andava piu'.
  // Misurato in `dbops.request_log`: 19 chiamate a quel path, la prima poche ore
  // dopo il commit che introdusse la chiusura globale, nessuna prima.
  // ⚠️ E non e' nemmeno la semantica giusta: `onClose` vuol dire «l'operatore ha
  // chiuso il drawer, ricarica cio' che c'e' sotto». Qui sotto non c'e' piu'
  // niente — si sta lasciando la pagina, e la view che la ospita ricarica da se'
  // quando torna attiva (KeepAlive, `onActivated`).
  // ⚠️ Il guard su `visible` non e' cosmetico: senza, si scriverebbe su un ref
  // gia' falso una volta per host a ogni navigazione, per sempre.
  registraDrawerChiudibile(() => {
    if (visible.value) visible.value = false
  })

  return { visible, tipo, id, apri, onVisibleChange }
}
