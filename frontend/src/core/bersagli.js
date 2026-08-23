// Scopo: ⭐ DAL BERSAGLIO DI UN ERRORE A UN GESTO. Il backend, quando lo sa,
//        dice su QUALE cosa l'errore e' successo (envelope `error.targets`,
//        forma `[{type, id}]`); qui quella coordinata diventa un'azione — «Apri
//        la fattura 820» — oppure NIENTE.
//
// ⭐ PERCHE' ESISTE, in una riga: all'operatore non serve il NOME del record,
//    gli serve ARRIVARCI. Un identificativo dentro una frase, per quanto umano,
//    resta una cosa da ricopiare a mano in un campo di ricerca.
//    Brief: docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md (§1, §2).
//
// ⛔ IL BERSAGLIO E' UN'OFFERTA, NON UNA PROMESSA (§4.3 del brief). Puo' puntare
//    a qualcosa che chi legge non puo' aprire: permessi, area bloccata, tipo
//    senza destinazione. In tutti quei casi si restituisce `null` e il pulsante
//    NON compare — il messaggio si mostra lo stesso.
//    ⚠️ Mai un pulsante che porta in un vicolo cieco: e' peggio di nessun
//    pulsante, perche' promette una via d'uscita che non c'e'.
//
// ⚠️ UN RESOLVER SOLO, PIU' SUPERFICI. Il toast (`useApiHandler`) e l'icona di
//    riga (`ErroreRigaInfo`, sugli errori persistiti dei giri asincroni) passano
//    entrambi di qui. Se divergessero, lo stesso errore direbbe due cose diverse
//    a seconda di come e' arrivato a video.
import { DOCUMENTO_DRAWERS, DOCUMENTO_DRAWER_TIPI } from '../vendite/_shared/documenti/documentoDrawers'
import { READONLY_DOMAINS } from './constants'

// ⭐ LA MAPPA TIPO → DESTINAZIONE, e la scoperta che l'ha resa corta: le chiavi
// di `DOCUMENTO_DRAWER_TIPI` **sono gia'** i `config.sorgenti.codice_interno`,
// cioe' lo stesso vocabolario su cui il team DB ha costruito `config.tipi_entita`.
// La tabella non era da inventare, era da riconoscere.
//
// ⚠️ Un tipo che NON e' qui dentro non e' un difetto: e' un'entita' che
// nessuna schermata sa ancora raggiungere (oggi `TASK_RUN`). Il degrado e'
// dichiarato — nessun pulsante — e la CI del database presidia il verso
// opposto (`dbops.vw_bersagli_non_dichiarati`: un tipo scritto e non a catalogo
// fa fallire la build).
//
// ⚠️ `area` serve al guard dei permessi: un operatore con l'area BLOCCATA non
// deve vedere un pulsante che lo porterebbe su un 403.
const DESTINAZIONI = Object.freeze({
  FATTURA: {
    area: READONLY_DOMAINS.VENDITE,
    drawer: DOCUMENTO_DRAWER_TIPI.FATTURA,
    // L'indirizzo della traduzione lo DICHIARA IL DATABASE, in
    // `config.tipi_entita.etichetta_key`: qui si ripete la stessa chiave, non
    // se ne inventa una. E' il patto dei tre livelli gia' scritto in
    // frontend-standards (il DB emette l'indirizzo, il FE lo risolve).
    etichettaKey: 'config.tipi_entita.fattura',
  },
  COMMESSA: {
    area: READONLY_DOMAINS.VENDITE,
    drawer: DOCUMENTO_DRAWER_TIPI.COMMESSA,
    etichettaKey: 'config.tipi_entita.commessa',
  },
  LOTTO: {
    area: READONLY_DOMAINS.VENDITE,
    // Il lotto non ha un drawer nel registry: ha una LISTA, e ci si arriva col
    // deep-link `?open=<id>` che la view apre da sola (stesso meccanismo gia'
    // in servizio su `vendite-contratti`).
    rotta: { name: 'vendite-lotti', queryKey: 'open' },
    etichettaKey: 'config.tipi_entita.lotto',
  },
  // ⛔ `TASK_RUN` NON C'E', ed e' deliberato. E' a catalogo perche' serve al
  //    giornale degli eventi dell'altro cantiere, non al bersaglio: nessuna
  //    schermata mostra un giro per id, quindi non c'e' nessun posto dove
  //    mandare l'operatore. Il giorno che ci sara', si aggiunge una riga qui.
})

// Scopo: ⭐ IL CONFINE, e passa TUTTO di qui. Il backend parla inglese
//        (`{type, id}`, come ogni chiave dell'envelope), questo lato parla
//        italiano (`{tipo, id}`, come il resto del dominio): la traduzione
//        avviene in questa funzione e in nessun altro posto.
//
//        ⛔ NON E' PIGNOLERIA, e' il bug che questa funzione esiste per non
//        far ripetere. Il percorso dell'errore PERSISTITO passava l'array
//        grezzo direttamente al resolver, che legge `tipo`: trovava
//        `undefined`, non risolveva niente e **il pulsante non compariva mai**.
//        Nessun errore, nessun avviso — solo un gesto che non c'e'. Chiunque
//        aggiunga una quarta superficie deve passare da qui.
//
//        ⚠️ Il backend valida gia': i controlli qui sotto non sono una seconda
//        validazione, sono il guard che impedisce a un payload inatteso di
//        arrivare fino al template.
export function normalizzaBersagli(grezzi) {
  if (!Array.isArray(grezzi)) return []
  return grezzi
    .filter(
      (b) =>
        b &&
        typeof b.type === 'string' &&
        // ⚠️ Scalare, e non solo `!= null`: un oggetto passerebbe il controllo e
        // diventerebbe la stringa `[object Object]` — cioè un pulsante che apre
        // il nulla invece di nessun pulsante.
        (typeof b.id === 'string' || typeof b.id === 'number') &&
        String(b.id).trim() !== '',
    )
    .map((b) => ({ tipo: b.type, id: String(b.id) }))
}

// Scopo: I bersagli dell'ENVELOPE d'errore (`error.targets`) — la forma che
//        arriva da una chiamata fallita e dal blob `errore` del runner.
//        ⚠️ Gli errori PERSISTITI portano lo stesso array sotto un altro nome
//        (`errore_bersagli` della riga): li normalizza `ErroreRigaInfo` con
//        `normalizzaBersagli`, che e' la stessa funzione.
export function estraiBersagli(errore) {
  return normalizzaBersagli(errore?.targets)
}

// Scopo: ⭐ IL DEGRADO DEL §4.3, in un posto solo. Dice se questo bersaglio e'
//        raggiungibile DA CHI STA GUARDANDO ADESSO. `false` = nessun pulsante.
//
//        ⚠️ Il controllo sull'area non e' cosmetico: l'errore lo puo' ricevere
//        un operatore che su `vendite` ha il livello BLOCCATO (il rifiuto puo'
//        arrivare da un giro che non ha lanciato lui). Portarlo su un 403 e'
//        peggio che non offrirgli niente.
function raggiungibile(destinazione, authStore) {
  if (!destinazione) return false
  // ⚠️ Una destinazione senza NÉ drawer NÉ rotta è un errore di configurazione,
  // non un bersaglio: senza questo controllo il pulsante comparirebbe e il
  // click non farebbe niente — che è la forma peggiore del vicolo cieco,
  // perché sembra rotto il software e non la destinazione.
  if (!destinazione.drawer && !destinazione.rotta) return false
  if (destinazione.drawer && !DOCUMENTO_DRAWERS[destinazione.drawer]) return false
  if (!destinazione.area) return true
  // `isAreaBlocked` e' la stessa lettura che fa il route guard: una regola sola.
  return !authStore?.isAreaBlocked?.(destinazione.area)
}

// Scopo: ⭐ Il bersaglio risolto in qualcosa che si puo' PREMERE, o `null`.
//        Ritorna `{ tipo, id, etichettaKey, drawer, rotta }`: il COSA, non il
//        come — chi lo consuma decide se aprirlo in un drawer o navigare, e la
//        traduzione dell'etichetta resta al chiamante (che ha il suo `t`).
//
//        ⚠️ Non importa `useAuthStore` da se': lo store si passa. Cosi' questa
//        funzione resta pura e verificabile, e non trascina Pinia in ogni file
//        che la usa.
export function risolviBersaglio(bersaglio, authStore) {
  const destinazione = DESTINAZIONI[bersaglio?.tipo]
  if (!raggiungibile(destinazione, authStore)) return null
  return {
    tipo: bersaglio.tipo,
    id: bersaglio.id,
    etichettaKey: destinazione.etichettaKey,
    drawer: destinazione.drawer ?? null,
    rotta: destinazione.rotta ?? null,
  }
}

// Scopo: I bersagli raggiungibili, in ordine. ⚠️ Gli irraggiungibili escono
//        SILENZIOSAMENTE: non sono un errore da segnalare, sono il degrado
//        previsto — «il messaggio si mostra lo stesso, il pulsante non compare».
export function bersagliRisolti(bersagli, authStore) {
  return (bersagli || [])
    .map((b) => risolviBersaglio(b, authStore))
    .filter(Boolean)
}
