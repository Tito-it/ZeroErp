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
// ⚠️ UN RESOLVER SOLO, TRE SUPERFICI — e sono TRE perche' l'errore arriva a
//    video per tre strade diverse:
//      · `useApiHandler`   → il toast, su una chiamata fallita (envelope);
//      · `useLottoAzioni`  → il toast, su un esito del runner che risponde 200
//                            col fallimento DENTRO il payload;
//      · `ErroreRigaInfo`  → l'icona di riga, sugli errori PERSISTITI dei giri
//                            asincroni, che si leggono ore dopo.
//    Se il resolver si sdoppiasse, lo stesso errore direbbe due cose diverse a
//    seconda di come e' arrivato — e nessuno se ne accorgerebbe, perche' le tre
//    strade non si incontrano mai.
import { DOCUMENTO_DRAWER_TIPI, drawerEntita } from './drawerEntita'
import { MANAGE_ICONS, READONLY_DOMAINS } from './constants'
import { NAV_ICONS } from './navigation'
import { FORME_ID, idNellaForma } from './utils/idNellaForma'

// ⭐ LA MAPPA TIPO → DESTINAZIONE, e la scoperta che l'ha resa corta: le chiavi
// di `DOCUMENTO_DRAWER_TIPI` **sono gia'** i `config.sorgenti.codice_interno`,
// cioe' lo stesso vocabolario su cui il team DB ha costruito `config.tipi_entita`.
// La tabella non era da inventare, era da riconoscere.
//
// ⚠️ Un tipo che NON e' qui dentro non e' un difetto: e' un'entita' che nessuna
// schermata sa ancora raggiungere. Il degrado e' dichiarato — nessun pulsante —
// e la CI del database presidia il verso opposto
// (`dbops.vw_bersagli_non_dichiarati`: un tipo scritto e non a catalogo fa
// fallire la build).
//
// I CAMPI:
//   `forma`    ⭐ LA FORMA DELL'ID che la destinazione si aspetta
//              (`FORME_ID.INTERO` | `FORME_ID.UUID`, BB `idNellaForma`). Il
//              brief lo scrive esplicitamente: *«l'id e' opaco, la differenza
//              e' dichiarata e il frontend non deve dedurla dal formato del
//              valore»*. Serve a sapere se convertire a numero: le prop `*Id`
//              dei drawer numerici sono dichiarate `Number`, e una stringa e' un
//              difetto silenzioso in produzione.
//              ⚠️ Fino al 2026-11-11 era `chiave: 'id' | 'uid'`, specchio di
//              `config.tipi_entita.key_selector`, e `id` voleva dire «intero».
//              Ma `key_selector` dice QUALE colonna, non che forma ha: per
//              ARTICOLO e' `id`, e `catalogo.articoli.id` e' un uuid. Con la
//              vecchia regola il suo bersaglio si sarebbe scartato in silenzio.
//   `drawer`   chiave del registro dei drawer (`drawerEntita`) (il caso normale: un
//              documento si apre, non si "visita").
//   `rotta`    per le entita' che hanno una pagina: `queryKey` per un
//              deep-link `?open=<id>`, `param` per una rotta con `:id`.
//   `icona`    ⭐ IL SEGNO DELLA COSA DOVE SI VA, e si IMPORTA dal registro
//              della navigazione invece di scriverlo qui: il pulsante deve
//              portare lo stesso segno della voce di menu che apre la stessa
//              entita', o chi ha cliccato non la riconosce quando ci arriva.
//              ⛔ Prima era UNA sola per tutti — il `MANAGE_ICONS.VAI_A` di oggi, cioe'
//              «un collegamento» — che dice come ci si va e non DOVE si va
//              (rilievo di Tid, 2026-09-08). In un kebab con due voci era il
//              segno identico su due destinazioni diverse.
//              ⚠️ Importato e non ricopiato: una stringa ripetuta e' la seconda
//              sede, e il giorno che l'icona dei documenti cambia il bersaglio
//              resterebbe indietro **senza fallire**.
//   `area`     schema DB per il guard dei permessi (`isAreaBlocked`).
//   `richiedeAdmin`  per le rotte del dominio `amm-software`, dove il route
//              guard non guarda l'area ma `isSuperAdmin`: se il pulsante non
//              rispettasse la stessa regola porterebbe su «accesso negato».
const DESTINAZIONI = Object.freeze({
  FATTURA: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    drawer: DOCUMENTO_DRAWER_TIPI.FATTURA,
    // L'indirizzo della traduzione lo DICHIARA IL DATABASE, in
    // `config.tipi_entita.etichetta_key`: qui si ripete la stessa chiave, non
    // se ne inventa una. E' il patto dei tre livelli gia' scritto in
    // frontend-standards (il DB emette l'indirizzo, il FE lo risolve).
    etichettaKey: 'config.tipi_entita.fattura',
    icona: NAV_ICONS.FATTURE,
  },
  COMMESSA: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    drawer: DOCUMENTO_DRAWER_TIPI.COMMESSA,
    etichettaKey: 'config.tipi_entita.commessa',
    // ⚠️ La commessa non ha una voce di navigazione (nessuna lista propria):
    //    la sua icona vive gia' in `MANAGE_ICONS`, centralizzata li' il
    //    2026-07-25 proprio dall'azione «Apri commessa» di un drill-down.
    icona: MANAGE_ICONS.COMMESSA,
  },
  LOTTO: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    // Il lotto non ha un drawer nel registry: ha una LISTA, e ci si arriva col
    // deep-link `?open=<id>` che la view apre da sola (stesso meccanismo gia'
    // in servizio su `vendite-contratti`).
    rotta: { name: 'vendite-lotti', queryKey: 'open' },
    etichettaKey: 'config.tipi_entita.lotto',
    icona: NAV_ICONS.LOTTI,
  },
  CONTRATTO: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    drawer: DOCUMENTO_DRAWER_TIPI.CONTRATTO,
    etichettaKey: 'config.tipi_entita.contratto',
    icona: NAV_ICONS.CONTRATTI,
  },
  ORDINE_VENDITA: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    drawer: DOCUMENTO_DRAWER_TIPI.ORDINE_VENDITA,
    etichettaKey: 'config.tipi_entita.ordine_vendita',
    icona: NAV_ICONS.ORDINI,
  },
  PREVENTIVO: {
    area: READONLY_DOMAINS.VENDITE,
    // ⭐ `id`, e la storia vale la riga. Il catalogo nasceva con `uid` — la
    //    chiave con cui `config.sorgenti` collega il documento — e con quella
    //    qui non si apriva niente: la rotta e' `<int:preventivo_id>` e la prop
    //    del drawer e' `Number`. Il team DB ha corretto il 2026-08-24
    //    (`20260824-10`), e la regola che ne e' uscita sta nel loro changeSet:
    //    *il valore di `key_selector` si MISURA sulle rotte del frontend; non si
    //    eredita, e non si deduce dal fatto che una colonna `uid` esista.*
    forma: FORME_ID.INTERO,
    drawer: DOCUMENTO_DRAWER_TIPI.PREVENTIVO,
    etichettaKey: 'config.tipi_entita.preventivo',
    icona: NAV_ICONS.PREVENTIVI,
  },
  FLUSSO: {
    area: READONLY_DOMAINS.PRATICHE,
    forma: FORME_ID.INTERO,
    // ⭐ La dashboard pratiche apre un flusso dal solo id: chiede al backend
    //    dove vive (`/pratiche/flussi/<id>/pratica/`) e prosegue. Fino al
    //    2026-08-24 il deep-link voleva ANCHE `pratica_id` e senza quello non
    //    faceva niente — il bersaglio porta il solo flusso, perche' la pratica
    //    non e' cio' di cui l'errore parla.
    rotta: { name: 'pratiche-gestione', queryKey: 'flusso_id' },
    etichettaKey: 'config.tipi_entita.flusso',
    icona: NAV_ICONS.PRATICHE,
  },
  DEFINIZIONE_WORKFLOW: {
    area: READONLY_DOMAINS.AMM_SOFTWARE,
    forma: FORME_ID.INTERO,
    // ⭐ L'unica destinazione che e' una PAGINA con un parametro di percorso, e
    // non un drawer: il dettaglio strutturale di un'edizione e' troppo ricco
    // per un pannello (lo dice il commento della rotta stessa).
    rotta: { name: 'amm-software-definizione-editor', param: 'id' },
    // ⚠️ Il route guard di `amm-software` NON guarda l'area: guarda `isSuperAdmin`.
    // Un pulsante che non rispettasse la stessa regola porterebbe l'operatore
    // su «accesso negato», che e' il vicolo cieco che il §4.3 vieta.
    richiedeAdmin: true,
    etichettaKey: 'config.tipi_entita.definizione_workflow',
    // La voce «Definizioni workflow» del menu amm-software porta questo segno.
    icona: NAV_ICONS.DEFINIZIONI_WORKFLOW,
  },
  // ⭐ ARTICOLO e PROMO_ARTICOLO (2026-11-11, S-BE-1 di brief-db-revisione-
  //    dbops): il require ATTIVO mette il bersaglio sul padre SPENTO, e il
  //    padre spento piu' comune e' l'articolo. Ci si arriva col deep-link
  //    `?open=` delle due liste (BB `useIngressoDaQuery`).
  //    ⚠️ Il pulsante APRE e basta: riattivare resta dei permessi di chi
  //    clicca (drawer in sola lettura) e del DB (`fn_riattiva_articolo`).
  ARTICOLO: {
    area: READONLY_DOMAINS.CATALOGO,
    // ⚠️ `key_selector` e' `id`, ma l'id dell'articolo e' un UUID.
    forma: FORME_ID.UUID,
    rotta: { name: 'catalogo-articoli', queryKey: 'open' },
    etichettaKey: 'config.tipi_entita.articolo',
    // La voce «Articoli» del menu catalogo porta questo segno.
    icona: NAV_ICONS.CATALOGO,
  },
  PROMO_ARTICOLO: {
    area: READONLY_DOMAINS.VENDITE,
    forma: FORME_ID.INTERO,
    rotta: { name: 'vendite-promo-articoli', queryKey: 'open' },
    etichettaKey: 'config.tipi_entita.promo_articolo',
    icona: NAV_ICONS.PROMO_ARTICOLI,
  },
  // ⛔ I tipi del catalogo che NON sono qui non sono una svista: nessuna
  //    schermata li apre dal solo id. `TASK_RUN` (serve al giornale degli
  //    eventi, non al bersaglio); ASSET, ARTICOLO_COMPONENTE, LISTINO_VERSIONE
  //    e le righe (verificato il 2026-11-11, N5 di S-BE-1: la versione di
  //    listino vuole anche il listino, un componente vive nella distinta del
  //    suo articolo). Il degrado e' dichiarato: nessun pulsante.
})

// Scopo: ⭐ I NOMI DEI TIPI, per chi un bersaglio se lo COMPONE invece di
//        riceverlo dal backend.
//
// ⭐ PERCHE' ESISTE (2026-09-06). La maggioranza dei bersagli arriva
//    dall'envelope o dal `meta` di una segnalazione: chi li rende non li
//    scrive, li passa. Ma due superfici li compongono da sé — l'icona d'errore
//    dei gruppi in competenza e il kebab dei documenti presi in carico dal
//    lotto — perché lì la cosa da aprire è già una colonna della riga, e
//    chiederla al backend sarebbe lo stesso dato due volte.
//
// ⛔ Alla terza occorrenza la stringa `'COMMESSA'` era scritta a mano in tre
//    template, e il modo in cui sbaglia è MUTO: un tipo che non sta nella mappa
//    non risolve, `bersagliRisolti` lo scarta e il pulsante semplicemente non
//    compare. Nessun errore, nessun avviso — solo un gesto che manca.
//
// ⚠️ Si DERIVA dalle chiavi di `DESTINAZIONI`, non si riscrive: un elenco
//    parallelo sarebbe la seconda sede della stessa cosa, e il giorno in cui
//    una destinazione cambia nome resterebbe indietro senza fallire.
// ⛔ Da NON confondere con `DOCUMENTO_DRAWER_TIPI`, che oggi porta gli stessi
//    nomi: sono due vocabolari distinti che coincidono per caso — uno dice
//    «quale entità», l'altro «quale pannello» — e appoggiarsi all'altro
//    significherebbe legarsi a una coincidenza.
export const BERSAGLIO_TIPI = Object.freeze(
  Object.fromEntries(Object.keys(DESTINAZIONI).map((tipo) => [tipo, tipo])),
)

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
    // ⚠️ `trim` anche nel valore, non solo nel controllo: senza, un `" 12 "`
    //    passerebbe il filtro e finirebbe TALE E QUALE nell'etichetta del
    //    pulsante — «Apri Fattura  12 ».
    .map((b) => ({ tipo: b.type, id: String(b.id).trim() }))
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
  if (destinazione.drawer && !drawerEntita(destinazione.drawer)) return false
  // ⚠️ Le due regole di accesso sono DIVERSE e vanno guardate come le guarda il
  // route guard: `amm-software` su `isSuperAdmin`, tutto il resto sull'area.
  if (destinazione.richiedeAdmin && !authStore?.isSuperAdmin) return false
  if (!destinazione.area) return true
  // `isAreaBlocked` e' la stessa lettura che fa il route guard: una regola sola.
  return !authStore?.isAreaBlocked?.(destinazione.area)
}

// Scopo: L'identificativo nella forma che la destinazione dichiara (`forma`),
//        o `null`. La regola (intero > 0, uuid valido) sta nel BB
//        `idNellaForma`, che serve anche il deep-link delle liste.
function identificativo(destinazione, id) {
  return idNellaForma(id, destinazione.forma)
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
  const id = identificativo(destinazione, bersaglio.id)
  // Un id che non ha la forma dichiarata: il database non
  // dovrebbe produrlo, e se succede vale la regola di sempre — si scarta in
  // silenzio, non si offre un pulsante che apre il vuoto.
  if (id === null) return null
  return {
    tipo: bersaglio.tipo,
    icona: destinazione.icona,
    id,
    // ⛔ Niente `idEtichetta`, tolto il 2026-09-08: l'etichetta del pulsante NON
    //    porta più l'identificativo, perché quella è la chiave primaria e non il
    //    numero con cui una persona chiama il documento. Un campo che nessuno
    //    legge invita a rimetterlo in una frase.
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
