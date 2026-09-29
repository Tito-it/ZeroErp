# Brief DB — Le righe di una distinta annullata escono dalle code

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-29. **A chi:** Tid
> (decisioni, §5), poi team DB (`dev/db-tid`); la ricaduta BE/FE è nel §6.
> **Origine:** collaudo in-app della casella di ricerca
> ([collaudo-in-app-casella-ricerca-liste.md](collaudo-in-app-casella-ricerca-liste.md),
> riga «Pagamenti → Coda del riconciliatore»). In coda «Da abbinare» compare
> una riga che appartiene a una distinta **annullata**.
> **Stato:** ✅ **decisioni prese da Tid** — strada (opzione 1: le righe escono
> dalle code lato **lettura**, l'annullo non le tocca) il 2026-09-29; **D-1, D-2,
> D-3 il 2026-09-30** (§5). Pronto per il team DB.
>
> **In una riga:** `ANNULLATA` vuol dire *«non è mai successa»*, ma una coda di
> lavoro continua a proporre le sue righe. Il frontend le mostra con tutte le
> azioni spente, e il guard del DB ammette ancora di sospenderle o scartarle:
> **tre sedi, tre risposte** alla stessa domanda, *«le righe di questa distinta
> si lavorano ancora?»*. ⇒ La proposta è dare alla domanda **una** sede, nel
> catalogo degli stati della distinta, e farla leggere da tutti.

---

## 1. Il difetto

Una riga `DA_ABBINARE` (o `SOSPESA`) sotto una distinta `ANNULLATA`:

* **resta nella coda** del riconciliatore (`GET /api/v1/pagamenti/righe/?coda=…`).
  `PagamentiRepository.list_righe_coda` filtra su `r.attivo` e sullo **stato
  della riga**, e non guarda lo stato della distinta;
* **non si può lavorare**: il frontend spegne tutte le azioni con il motivo
  «Questa distinta è in uno stato finale: le righe non si modificano più»
  (`pagamenti.distinte.foglio_chiuso`; `useAzioniRigaContabile.js`,
  `foglioSpento = finale && !registrata`);
* **ci resta per sempre**: in una coda di lavoro, una voce che nessuno può
  chiudere.

⚠️ Non si vede da nessun errore, ed è il motivo per cui è arrivato dal
collaudo: la coda è piena di lavoro «da fare» che non esiste.

## 2. Cosa dice il modello — letto dalla struttura

Fatti di struttura letti il 2026-09-29 dalla doc auto-gen e dal seed. Descrivono
il punto di partenza, e non decidono la forma.

* **`ANNULLATA` è finale e vuol dire «non è mai successa»**
  ([transizioni_stati_contabile](/dbzero/pagamenti/manual/transizioni_stati_contabile)).
  Il guard di chiusura lo scrive in chiaro: *«una distinta annullata non deve
  contare in nessun conto, righe pronte comprese»*
  (`trgfn_vendite_contabili_guard_chiusura`).
* **I saldi lo rispettano già.** `fn_get_saldo_fattura_contabili` e
  `fn_get_saldi_rate` contano solo le righe sotto una distinta con
  `is_final IS FALSE`. Il difetto non tocca gli importi, ma solo le code di lavoro.
* **Il guard d'ingresso lo rispetta a metà.**
  `trgfn_vendite_contabili_righe_guard_distinta_finale` vieta che una riga
  **diventi pronta** (`is_postabile`) sotto una distinta finale, ma lascia
  passare di proposito sospendere e scartare: *«dire che cosa ne è stato di quel
  denaro, che è l'unica cosa che resta da fare»*. È giusto sotto una **CHIUSA**,
  dove la `SOSPESA` ha un futuro (la registrazione tardiva, D20-b). Sotto una
  **ANNULLATA** non c'è niente da dire, perché quel denaro, per il registro, non
  è mai arrivato.
* **`CHIUSA` e `ANNULLATA` sono entrambe `is_final`**, ma sono opposte per le
  righe: sotto la prima si lavorano ancora (la tardiva), sotto la seconda no.
  `is_final` quindi **non basta** a rispondere, ed è il motivo per cui il
  frontend ha dovuto derivare la risposta a mano (`finale && !registrata`), con
  un fatto della testata (`data_conferma`) preso in prestito.
* **Da dove nascono le righe «morte».** Entrare in `VALIDATA` pretende che non ci
  siano righe non lavorate (`fn_check_contabile_validabile`, motivo
  `RIGHE_NON_LAVORATE`, D20-a). Una `DA_ABBINARE` sotto una finale arriva quindi
  solo da `BOZZA → ANNULLATA`. Una `SOSPESA` può arrivare anche da
  `VALIDATA → ANNULLATA`. Il modello ammette entrambi i casi.

## 3. La proposta — una bandiera nel catalogo

La domanda *«sotto questo stato le righe si lavorano ancora?»* è una proprietà
dello **stato della distinta**, statica e con una sola risposta per stato. La
sua sede è il catalogo, con la stessa forma di `is_registrabile` (D20-d): una
bandiera, e non una `fn_check`.

`pagamenti.vendite_contabili_stati.righe_lavorabili boolean NOT NULL DEFAULT false`:

| Stato | `righe_lavorabili` | Perché |
| --- | --- | --- |
| `BOZZA` | `true` | si sta inserendo |
| `IMPORTATA` | `true` | il file è arrivato, le righe si abbinano |
| `VALIDATA` | `true` | pronta da registrare, e le righe si possono ancora correggere |
| `CHIUSA` | `true` | registrata: sospese e scartate hanno ancora un futuro (tardiva, «Riprendi») |
| `ANNULLATA` | `false` | non è mai successa |

* ⚠️ Default `false`, **fail-closed**: uno stato nuovo senza la bandiera non
  apre il lavoro sulle righe finché qualcuno non lo decide.
* ⚠️ Il valore sta nel CSV del seed (`vendite_contabili_stati.csv`), mai in un
  `UPDATE`, come per `is_registrabile`.

La leggono tutti e tre:

1. **Il guard** (§4): sotto una distinta con `righe_lavorabili = false` le
   righe si congelano, cioè niente cambi di stato, niente correzioni e niente
   eliminazione (D-3).
2. **Il backend** (§6): la coda seleziona solo righe con `righe_lavorabili`, e la
   espone sulla riga e sul dettaglio della distinta.
3. **Il frontend** (§6): spegne le azioni leggendo la bandiera, e non la deriva
   più da `finale && !registrata`.

## 4. Richiesta al team DB

1. **Colonna e seed.** `righe_lavorabili` su `pagamenti.vendite_contabili_stati`
   come nel §3, con `COMMENT` che dica il perché (la differenza tra CHIUSA e
   ANNULLATA) e il mirror del CSV.
2. **Guard, quinta mossa: righe congelate (D-3).** In
   `trgfn_vendite_contabili_righe_guard_distinta_finale`: su **ogni** `UPDATE` e
   su ogni `DELETE` di una riga la cui distinta ha `righe_lavorabili = false` si
   **rifiuta** con `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` (D-2). Vale per il
   cambio di stato (anche verso `SOSPESA` o `SCARTATA`) **e** per la correzione
   di un dato (`motivo_sospeso`, riferimento, date, importo, `attivo`…).
   Annullata vuol dire sola lettura.
   * Le quattro mosse di oggi restano come sono (su CHIUSA **e** ANNULLATA,
     tramite `is_final`): nascere, essere riattivata, essere spostata **sotto**
     una finale. La quinta copre ciò che resta, cioè toccare una riga che è già lì.
   * ⚠️ Il trigger oggi è `INSERT`/`UPDATE`: per il `DELETE` serve l'evento in
     più (o il gemello `fn_check_riga_contabile_eliminabile`, se è la sede
     giusta: il cestino si spegne prima del click e il guard rifiuta con la
     stessa check).
   * ⚠️ Va riscritto il commento *«ciò che NON si rifiuta»*: sospendere, scartare
     e correggere restano ammessi **solo** dove le righe sono lavorabili (sotto
     una CHIUSA, per la tardiva).
   * ⚠️ **Da verificare dal team DB**: nessuna madre scrive righe sotto una
     distinta annullata (sync dei fondi, correzioni, sistemazioni). Se una lo
     facesse, il congelamento la romperebbe: va detto nel brief di ritorno quale
     e perché, prima di aprire un varco.
3. **pgTAP** (i soggetti si **costruiscono**, non si cercano nei dati):
   * una `DA_ABBINARE` sotto una `BOZZA` poi annullata → `SOSPESA` rifiutata,
     `SCARTATA` rifiutata, `motivo_sospeso` modificato rifiutato, `DELETE`
     rifiutato, tutti con `E_RIGA_CONTABILE_DISTINTA_ANNULLATA`;
   * una `SOSPESA` sotto una `VALIDATA` poi annullata → `SCARTATA` e
     `DA_ABBINARE` rifiutate, correzione del motivo rifiutata;
   * una `SOSPESA` sotto una `CHIUSA` → `SCARTATA` ammessa, e la tardiva passa
     ancora (non-regressione D20-b);
   * il seed porta la bandiera come nella tabella del §3 (uno stato con valore
     diverso fa fallire il test);
   * una riga sotto una `BOZZA` (non annullata) → correzione del motivo ammessa
     (il congelamento non si allarga);
   * mutazione: senza la quinta mossa, i primi due casi passano.
4. **Documentazione manuale**: `vendite_contabili_stati` (la bandiera),
   `trgfn_vendite_contabili_righe_guard_distinta_finale` (la quinta mossa), e una
   riga in `transizioni_stati_contabile` accanto a *«ANNULLATA — non è mai
   successa»*.

## 5. Decisioni per Tid

| # | Domanda | Decisione |
| --- | --- | --- |
| D-1 | La sede della risposta è una **bandiera di catalogo** (`righe_lavorabili`), e non la derivazione `is_final AND data_conferma IS NULL`? | ✅ **Sì** (Tid, 2026-09-30). La derivazione mescola uno stato con un fatto della testata e va riscritta in ogni lettore: è quella che oggi vive solo nel frontend. |
| D-2 | Il rifiuto della quinta mossa usa un **codice nuovo** o riusa `E_RIGA_CONTABILE_DISTINTA_FINALE`? | ✅ **Codice nuovo** `E_RIGA_CONTABILE_DISTINTA_ANNULLATA`, «la distinta è annullata: le sue righe si leggono soltanto» (Tid, 2026-09-30). Il rimedio è diverso: sotto una chiusa si dice che cosa ne è stato del denaro, sotto un'annullata non c'è niente da fare. |
| D-3 | Sotto un'annullata si rifiutano solo i **cambi di stato**, o ogni scrittura sulla riga? | ✅ **Ogni scrittura: le righe si congelano** (Tid, 2026-09-30). Il drawer della distinta annullata dice già *«Annullata: non ha toccato niente»*: è un documento chiuso, e un documento annullato non si ritocca. Lasciare aperta la correzione dei dati terrebbe viva una porta che nessuna schermata usa. Annullata = sola lettura. ⚠️ La prima proposta era «solo i cambi di stato», con l'argomento che una nota non sposta denaro: scartata perché il criterio non è il denaro ma il documento. |

## 6. Ricaduta backend e frontend (dopo il DB)

**Backend** (`dev/backend-tid`):

* `list_righe_coda`: condizione `cst.righe_lavorabili IS TRUE` accanto a quella
  sullo stato della riga. La coda è una lista di **lavoro**, e ciò che non si
  lavora non ci sta.
* La riga della coda e il dettaglio della distinta espongono
  `contabile_righe_lavorabili` (in `_RIGA_CODA_SELECT` e nel dettaglio). Il
  frontend smette di derivarlo.
* Se D-2 = codice nuovo: policy generata **e** ripiego senza `%s` (il flusso
  solito dei codici nuovi).
* Test: la coda non restituisce le righe di un'annullata (repository, con
  `EXPLAIN` sul DB vero per la colonna nuova); l'endpoint espone la bandiera.

**Frontend**:

* `useAzioniRigaContabile`: `testataDi(riga)` porta `righeLavorabili`, e le azioni
  si spengono su `righeLavorabili === false`. Il motivo
  `pagamenti.distinte.foglio_chiuso` («… in uno stato finale …») va ritoccato:
  lo stato finale che spegne le righe è uno solo, quello annullato.
* Nel drawer della distinta le righe di un'annullata **restano visibili**: è il
  documento, non una coda. **Sola lettura** (D-3): azioni di riga spente, il
  click apre la riga senza form modificabile, niente cestino.
* Collaudo: una distinta con una riga `DA_ABBINARE`, annullata → la riga sparisce
  dalla coda; nel drawer della distinta resta, in sola lettura, con il motivo.

## 7. Fuori perimetro, e perché

* **L'annullo che si porta dietro le righe** (opzione 2, scartata da Tid il
  2026-09-29): scrivere uno stato su ogni riga duplicherebbe sulla riga un fatto
  che sta già sulla testata. Servirebbe inoltre uno stato nuovo, perché
  `SCARTATA` vuol dire *«denaro arrivato ma non nostro»*, che è un'altra cosa.
* **I saldi**: già corretti (§2), nessuna modifica.
