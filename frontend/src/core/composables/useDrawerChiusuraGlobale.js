// Scopo: LA CHIUSURA GLOBALE DEI DRAWER — un segnale solo che chiude tutto
// quello che e' aperto sopra la pagina, a qualunque profondita'.
//
// ⭐ IL PROBLEMA CHE RISOLVE (rilievo in-app di Tid, 2026-08-19). I drawer di
// questo software si IMPILANO: da un ordine si apre il DDT collegato, dal DDT il
// reso, e ogni drawer monta a sua volta la barra collegamenti col proprio
// `DocumentoDrawerHost`. La pila non ha una profondita' fissa e nessuno la
// conosce per intero. Quando qualcosa porta l'utente su un'ALTRA ROTTA — il
// «apri la coda filtrata» del pannello merce, una voce di menu, un link — i
// drawer sono teleportati sul body e vivono sotto KeepAlive: la rotta cambia
// sotto e loro restano davanti. Si atterra sulla lista con tre pannelli sopra.
//
// ⛔ LA STRADA CHE NON FUNZIONA e' quella provata per prima: far emettere a chi
// naviga un evento che il drawer OSPITE intercetta. Chiude un anello solo — il
// suo — e la pila sopra resta intera. Ogni anello nuovo vorrebbe il suo
// cablaggio, e basta dimenticarne uno perche' il difetto torni in un punto solo.
//
// ⭐ LA FORMA GIUSTA e' quella dei formati a pila dei gestionali classici: una
// PROPRIETA' SOLA, uguale per tutte le finestre; quando si alza, tutto quello
// che sta sotto si chiude. Qui la proprieta' e' questo modulo: ogni drawer
// registra COME si chiude, e `chiudiTuttiIDrawer()` lo chiede a tutti insieme.
// Chi apre drawer non deve sapere chi altro e' aperto — che e' il solo modo per
// cui una pila di profondita' ignota si chiude tutta.
//
// Dove si registra: nei DUE proprietari dello stato di apertura —
// `useDrawerState` (il drawer di testa di ogni view lista) e
// `useDocumentoDrawer` (ogni drawer impilato dalla barra collegamenti). I drawer
// interni a un drawer (note, indirizzi, dialog) non servono: il loro contenuto
// vive DENTRO il genitore e sparisce quando il genitore si chiude.
//
// Dove si alza il segnale: `router/index.js`, su cambio di PATH. Non sulla
// query: i filtri di lista e i deep-link si ripuliscono da soli con
// `router.replace` sulla stessa pagina, e chiudere i drawer li' sarebbe un
// pannello che sparisce da solo mentre si filtra.
import { getCurrentScope, onScopeDispose } from 'vue'

// Le chiusure vive, in ordine di registrazione. Set e non array: la stessa
// funzione non si registra due volte, e la rimozione non ha da cercare indici.
const _chiusure = new Set()

/**
 * Registra la chiusura di un drawer nel segnale globale.
 *
 * Se chiamata dentro uno scope reattivo (setup di un componente, o un
 * `effectScope`) si de-registra da sola allo smontaggio: un drawer smontato che
 * restasse nel Set verrebbe chiuso a vuoto per sempre — e su una view
 * KeepAlive che monta e smonta a ripetizione sarebbe una perdita che cresce.
 *
 * @param {Function} chiudi - come si chiude QUESTO drawer
 * @returns {Function} de-registrazione manuale (per chi non ha uno scope)
 */
export function registraDrawerChiudibile(chiudi) {
  _chiusure.add(chiudi)
  const rimuovi = () => _chiusure.delete(chiudi)
  if (getCurrentScope()) onScopeDispose(rimuovi)
  return rimuovi
}

/**
 * Chiude TUTTO quello che e' aperto. Non ritorna niente e non fallisce: e' un
 * segnale, non un'operazione.
 *
 * ⚠️ Si itera su una COPIA: una chiusura puo' smontare un componente e quindi
 * de-registrare se stessa (o un figlio) mentre il ciclo gira — mutare il Set
 * sotto l'iteratore salterebbe silenziosamente il drawer successivo, cioe'
 * lascerebbe aperto proprio uno degli anelli che questo modulo esiste per
 * chiudere.
 *
 * ⚠️ E ogni chiusura e' isolata: se una solleva, le altre devono comunque
 * partire. Un drawer rotto non e' una buona ragione per lasciarne aperti altri
 * quattro sopra la pagina d'arrivo.
 */
export function chiudiTuttiIDrawer() {
  // Snapshot, non il Set vivo (vedi sopra). Estratto in una costante perche'
  // lo spread dentro il `for…of` e' indistinguibile, per il linter, da una copia
  // inutile — qui e' il punto della funzione.
  const daChiudere = Array.from(_chiusure)
  for (const chiudi of daChiudere) {
    try {
      chiudi()
    } catch (e) {
      console.warn('chiusura globale drawer: una chiusura ha sollevato', e)
    }
  }
}
