# Brief DB — Le righe di una distinta annullata escono dalle code

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-29. **A chi:** Tid
> (decisioni, §5), poi team DB (`dev/db-tid`); la ricaduta BE/FE è nel §6.
> **Origine:** collaudo in-app della casella di ricerca
> ([collaudo-in-app-casella-ricerca-liste.md](collaudo-in-app-casella-ricerca-liste.md),
> riga «Pagamenti → Coda del riconciliatore»). In coda «Da abbinare» compare
> una riga che appartiene a una distinta **annullata**.
> **Stato:** ✅ **decisioni prese da Tid** — strada (opzione 1: le righe escono
> dalle code lato **lettura**, l'annullo non le tocca) il 2026-09-29; **D-1, D-2,
> D-3 il 2026-09-30** (§5); **D-4, D-5 il 2026-09-30** (§8.3). Piano DB al §9;
> ✅ **DB CONSEGNATO il 2026-09-30** (§10: `20260930-30 → -33`): applicato da Tid su dev,
> pgTAP verdi. ✅ **BE/FE il 2026-09-30** (§11): R-1, R-2, R-4, R-5. ⏳ **R-3
> fermo** sulla sede DB del motivo: ✅ **D-6 approvata da Tid il 2026-09-30**,
> ⏳ **al team DB** (§11.3, richiesta §11.4). Collaudo: ✅ la riga di
> un'annullata sparisce dalla coda e nel drawer resta in sola lettura, col badge
> «Modalità consultazione» (Tid, 2026-09-30).
> ✅ **BRIEF CHIUSO il 2026-09-30** (Tid). La R-3 con la D-6 (P-9 … P-12, §11.4)
> **non è chiusa**: passa in `.codex/PROJECT_CONTEXT.md` § «Aperto — Media priorità».
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

## 8. Ritorno del team DB — analisi (2026-09-30)

Letto dalla doc auto-gen e dal seed il 2026-09-30. Sono fatti di struttura, e
nessuno si appoggia a un conteggio.

### 8.1 Cosa c'è già, e cambia la forma della richiesta

* **Il `DELETE` ha già una sede, e non è `guard_distinta_finale`.**
  `trgfn_vendite_contabili_righe_guard_contenuto` è `INSERT/UPDATE/DELETE`, e
  sul `DELETE` e sulla disattivazione (`attivo` da true a false) **chiama**
  `script.fn_check_riga_contabile_eliminabile`, di cui solleva il primo motivo.
  Oggi una riga sotto un'annullata **non si elimina già**: il motivo 1
  (`DISTINTA_FINALE`) copre CHIUSA e ANNULLATA insieme.
  ⇒ Per D-2 non serve un evento in più sul trigger (e nemmeno rinominarlo in
  `_ins_upd_dlt`). Il motivo 1 si **sdoppia** nella check: prima
  `DISTINTA_ANNULLATA` (`righe_lavorabili = false`, codice nuovo), poi
  `DISTINTA_FINALE` per le altre finali. Il cestino e il rifiuto restano una
  sede sola (§12.5.2), e il backend, che legge già la check in LATERAL, riceve
  il motivo nuovo senza toccare codice.
* **Ordine dei guard `BEFORE ROW`.** `a10_guard_contenuto` parla prima di
  `a10_guard_distinta_finale`. Sotto una finale la sua porta 2 tace, e la porta
  1 passa dalla check: le due strade arrivano allo stesso codice.
* **La quinta mossa si legge sulla distinta DI PARTENZA** (`OLD.contabile_id`):
  è la distinta dove la riga *sta*. Così copre anche il tentativo di tirare una
  riga **fuori** da un'annullata, che oggi le quattro mosse non vedono, perché
  guardano solo la distinta d'arrivo. Si valuta **prima** delle altre quattro
  (lo specifico batte il generico): una riattivazione sotto un'annullata
  risponde `…_ANNULLATA`, non `…_FINALE`. ⚠️ La porta della tardiva non la
  apre: la tardiva vale solo sotto una CHIUSA registrata, e
  `fn_posta_riga_tardiva` rifiuta l'annullata prima di scrivere.
* **FK.** Tutte le FK di `vendite_contabili_righe` sono `NO ACTION`: nessun
  `SET NULL` o `CASCADE` produce scritture implicite sulle righe congelate.

### 8.2 Le madri che scrivono righe (la verifica chiesta al §4.2)

Sei funzioni scrivono `pagamenti.vendite_contabili_righe`:

| Madre | Scrive sotto un'annullata? |
| --- | --- |
| `fn_posta_contabile` | no: muove le righe mentre la distinta è VALIDATA |
| `fn_posta_riga_tardiva` | no: rifiuta l'annullata prima di scrivere |
| `fn_crea_distinta_correzione` | no: inserisce sotto la distinta nuova |
| `fn_conferma_sistemazione` | no: inserisce sotto la distinta nuova |
| 🔴 `vendite.fn_sync_contabili_fondo_fattura` | **sì** |
| 🔴 `vendite.fn_cancella_fondo_fattura` | **sì** |

Il modello ammette il caso. La matrice non distingue l'origine, quindi una
distinta **GENERATA** (fondi fattura, sistemazioni) va in ANNULLATA come una
manuale. `guard_validazione` limita alla MANUALE solo `VALIDATA → BOZZA`, e il
backend propone ANNULLATA senza guardare l'origine. Sotto una GENERATA annullata:

* **il sync dei fondi** ritrova la riga dell'atto (`attivo` e
  `fondo_source_id`, senza guardare la distinta). Ne fa un `UPDATE` che la
  **sposta** in una distinta VALIDATA nuova. ⚠️ **Oggi** questo resuscita
  denaro che «non è mai successo», e le quattro mosse non lo vedono perché
  guardano solo l'arrivo. **Col congelamento** l'`UPDATE` viene rifiutato,
  dentro `fn_ricalcola_totali_fattura`: un 500 sul percorso vivo della
  pipeline, a ogni ricalcolo di quella fattura;
* **la cancellazione dell'atto** cancella le righe dell'atto aprendo la GUC
  `zeroerp.allow_contabile_riga_delete_override`, che salta la check. Se il
  congelamento sta nella check, questa madre **lo scavalca** e toglie contenuto
  a un documento annullato. Se sta altrove, l'atto **non si cancella più**: la
  FK `NO ACTION` lo lega per sempre a una riga che nessuno può toccare.

⇒ È la condizione del §4.2: il congelamento così com'è rompe due madri. Serve
**D-4** prima di scrivere.

### 8.3 Decisioni

| # | Domanda | Proposta DB |
| --- | --- | --- |
| D-4 | Una distinta **non manuale** si può annullare? | ✅ **No: l'annullo è un gesto della MANUALE** (Tid, 2026-09-30). Whitelist sull'origine in `trgfn_vendite_contabili_guard_validazione`, accanto a «`VALIDATA → BOZZA` solo MANUALE». La generata la governa il giro che l'ha prodotta: per togliere un fondo si cancella l'atto, per togliere una sistemazione la si annulla. Annullarne la testata a mano era un gesto che il sync disfa al ricalcolo successivo, e col congelamento sarebbe diventato un blocco. L'AUTOMATICA non esiste ancora: con la whitelist cade nel rifiuto, e la riaprirà il cantiere dell'import se servirà. **Alternativa scartata**: tenere l'annullo e far trattare alle due madri le righe sotto un'annullata come «morte». Il sync ne avrebbe creata una seconda per lo stesso atto, e la cancellazione avrebbe dovuto scegliere tra scavalcare D-3 e restare bloccata per sempre. |
| D-5 | Il rifiuto dell'annullo non manuale riusa `E_CONTABILE_RIAPERTURA_NON_MANUALE`? | ✅ **No, codice nuovo `E_CONTABILE_ANNULLO_NON_MANUALE`** (team DB, 2026-09-30). Il messaggio di quello esistente dice «non si riapre»: riusarlo metterebbe davanti all'operatore la frase di un altro gesto. Stessi valori (codice della distinta, «arrivata da un file» / «prodotta dal sistema») e stessa classe `CONFLITTO_STATO`. |

La ricaduta BE/FE è l'azione «Annulla» su una distinta non manuale: spenta col
motivo (stato ⇒ disabilita, §12.1), e ripiego e policy per il codice nuovo (§9).

## 9. Piano DB (2026-09-30)

Numeri indicativi da `20260930-11`: si ricontrollano sul `databasechangelog`
al momento di scrivere.

| # | Cosa | Dove |
| --- | --- | --- |
| P-1 | `righe_lavorabili boolean NOT NULL DEFAULT false` su `vendite_contabili_stati`, con `COMMENT` (la differenza CHIUSA/ANNULLATA) | `00_schema/pagamenti` |
| P-2 | La colonna in coda a `vendite_contabili_stati.csv` (true su BOZZA, IMPORTATA, VALIDATA, CHIUSA; false su ANNULLATA). `- column:` e `columnExists` nel mirror `20260821-30` (`runOnChange` + `ANY`, si ritocca) | `80_data` |
| P-3 | `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` ed `E_CONTABILE_ANNULLO_NON_MANUALE` in `codici_errore.csv` e `messaggi_errore.csv`. Nota di `E_RIGA_CONTABILE_DISTINTA_FINALE` aggiornata: dalla check ora arriva solo sotto una CHIUSA | `80_data` |
| P-4 | `script.fn_check_riga_contabile_eliminabile`: motivo `DISTINTA_ANNULLATA` (`righe_lavorabili = false`), **prima** di `DISTINTA_FINALE`; `reason_key` `pagamenti.righe.elimina_reason.distinta_annullata`. Copre il `DELETE` e la disattivazione tramite `guard_contenuto`, che la chiama già | `20_code/script` |
| P-5 | `trgfn_vendite_contabili_righe_guard_distinta_finale`: quinta mossa su ogni `UPDATE` di una riga la cui distinta di **partenza** (`OLD.contabile_id`) ha `righe_lavorabili = false`. Si valuta per prima e non apre la porta della tardiva. Il commento «ciò che NON si rifiuta» si riscrive. Il `COMMENT` di `guard_contenuto` si aggiorna (il residuo dichiarato si chiude sotto l'annullata) | `20_code/pagamenti` |
| P-6 | `trgfn_vendite_contabili_guard_validazione`: regola 3, ingresso in ANNULLATA solo se `origine = 'MANUALE'` (D-4) | `20_code/pagamenti` |
| P-7 | pgTAP nuovo con i casi del §4.3, mutazione compresa, più l'annullo di una GENERATA rifiutato e di una MANUALE ammesso. Da ritoccare: `test-stati-contabili-vocabolario` (la bandiera), il caso 5 di `test-posta-riga-tardiva-v1` (`'%annullata%'` passerebbe per coincidenza anche con la quinta mossa) e la fixture di `test-vendite-contabili-stato-obbligatorio` (§10.2). ⚠️ Scritto il 30-09: il caso «annullata» della check sta nel file nuovo (test 6-7, 9), non in `test-righe-contabili-eliminazione-v1`, che resta com'era | `db/pgtap` |
| P-8 | Doc manuale: `vendite_contabili_stati`, `guard_distinta_finale`, `guard_validazione`, `transizioni_stati_contabile` | `manual/` |

⚠️ **Prima dell'apply**: le distinte GENERATA già in ANNULLATA sul DB di
sviluppo si sistemano a mano, se ce ne sono. Il guard nuovo guarda solo il
passaggio, quindi non le rifiuta, ma le loro righe restano congelate e il sync
ci inciamperebbe.

**Richieste a BE/FE, in aggiunta al §6:**

* ⚠️ la chiave `pagamenti.righe.elimina_reason.distinta_annullata` va nei
  locales it/en **nello stesso giro**: `check_i18n_keys` la cerca nel corpo della
  check e fa fallire la CI finché manca;
* policy generata e ripiego per i due codici nuovi;
* «Annulla» su una distinta non manuale: spento col motivo, non nascosto (§12.1).

## 10. Consegna DB (2026-09-30)

✅ **Applicato da Tid su dev il 2026-09-30, pgTAP verdi** (corsa del runner, come
app: copre anche la RLS che la prova sullo scratch del §10.3 non vedeva). I numeri partono da
`-30` perché `-14 … -21` li ha presi in parallelo il cantiere documenti, e
`-22 … -29` restano liberi per lui.

### 10.1 I changeSet

| File | Cosa |
| --- | --- |
| `00_schema/pagamenti/20260930-30-alter-vendite-contabili-stati-add-righe-lavorabili` | P-1: la colonna, `NOT NULL DEFAULT false`, con `COMMENT` |
| `80_data/changelog/20260821-30-riancora-mirror-stati-contabili` *(ritoccato: `runOnChange` + `ANY`)* e `80_data/sql/pagamenti/vendite_contabili_stati.csv` | P-2: la colonna in coda al CSV, `- column:` e `columnExists` nel mirror |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | P-3: `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` (id 1180) ed `E_CONTABILE_ANNULLO_NON_MANUALE` (id 1181), `CONFLITTO_STATO`; nota di `E_RIGA_CONTABILE_DISTINTA_FINALE` aggiornata. ⚠️ Id lasciati larghi: il cantiere documenti sta occupando 1169-1170 in parallelo |
| `20_code/script/20260930-31-update-fn-check-riga-contabile-eliminabile-annullata` | P-4: motivo 1a `DISTINTA_ANNULLATA` e, **in alternativa** (`ELSIF`), 1b `DISTINTA_FINALE`. Firma con `%TYPE` |
| `20_code/pagamenti/20260930-32-update-trgfn-righe-guard-distinta-finale-annullata` | P-5: la quinta mossa, valutata per prima, su `OLD.contabile_id`, con `IS FALSE` (una testata non letta non si dice «annullata»). Riscritto anche il `COMMENT` di `guard_contenuto` (il residuo dichiarato si restringe alla CHIUSA) |
| `20_code/pagamenti/20260930-33-update-trgfn-vendite-contabili-guard-validazione-annullo-manuale` | P-6: regola 3, sulla **bandiera** dello stato d'arrivo e non sul letterale `ANNULLATA`: la collisione col giro nasce dal congelamento |
| `docs/it/dbzero/*/manual/` | P-8: `vendite_contabili_stati`, `trgfn_vendite_contabili_righe_guard_distinta_finale`, `trgfn_vendite_contabili_guard_validazione`, `transizioni_stati_contabile`, `fn_check_riga_contabile_eliminabile` |

Il trigger `trg_vendite_contabili_righe_a10_guard_distinta_finale_ins_upd` non
cambia: nessun evento `DELETE` in più e nessuna rinomina (§8.1).

### 10.2 I pgTAP

* **nuovo** `db/pgtap/pagamenti/test-righe-distinta-annullata-congelate-v1.sql`,
  22 test. Si asserisce il **codice** (campo `CONSTRAINT` dell'eccezione), non la
  frase;
* `test-stati-contabili-vocabolario`: test 9 (la bandiera è `false` solo su
  ANNULLATA) e 10 (non è derivabile da `is_final`: CHIUSA è finale e lavorabile),
  plan 10;
* `test-posta-riga-tardiva-v1`, caso 5: `'%annullata%'` →
  `'%si registra in ritardo solo%'`, la frase propria della tardiva;
* ⚠️ `test-vendite-contabili-stato-obbligatorio`: la fixture inseriva la testata
  **senza origine**, cioè GENERATA (il default della colonna), e poi la annullava
  con un `UPDATE` nudo. Da D-4 quell'`UPDATE` avrebbe fatto abortire il file.
  L'origine ora è `MANUALE`, dichiarata: il soggetto del test è il filtro su
  `is_final`.

### 10.3 La prova (sullo scratch `zeroerp_ci`, transazione ritirata)

L'SQL è stato **estratto dagli YAML**, con il seed simulato (la bandiera dal CSV,
più le sole righe nuove dei due cataloghi errori: niente upsert completo, che
impicca il dblink), e poi il corpo del pgTAP, in `BEGIN … ROLLBACK`. Lo scratch è
stato riletto dopo la prova, ed è intatto.

* il test nuovo: **22/22**;
* **mutazione**: senza `-32` rossi 3-5, 8, 12-14 e a cascata 9-10; senza `-31`
  rossi 6-7, 9; senza `-33` rossi 21-22. Il test vede tutte e tre le regole;
* **i 30 pgTAP esistenti** che nominano gli oggetti toccati (righe, testata,
  check, guard, sync, cancellazione e posting): con e senza l'SQL estratto gli
  stessi numeri. Sei hanno rossi **già prima**: `test-distinta-numerazione-registro-v1`
  (2), `test-rls-pagamenti-perimetro` (9, da owner la RLS non c'è) e i quattro
  dei fondi fattura (`ERRORE_FIXTURE` sullo scratch, già in baseline);
* `plpgsql_check` sulle tre funzioni: nessun `error:`. Restano i due warning già
  presenti sulla check (`STABLE` che chiama il raise nei guard di chiamata);
* guardrail statici (letterali, `runOnChange`, preCondition/seed): verdi.

⚠️ **Che cosa la prova NON copre.** La RLS: da owner non c'è, e la misura arriva
dalla corsa di Tid, che gira come app. Poi i quattro pgTAP dei fondi fattura, che
sullo scratch non arrivano ai loro test e girano solo su dbdev. Il loro percorso
(sync e cancellazione sotto GENERATE VALIDATE) non incontra la quinta mossa,
perché nessuno di loro annulla una distinta.

### 10.4 Richieste a BE/FE (in aggiunta al §6)

| # | Chi | Cosa |
| --- | --- | --- |
| R-1 | FE | ⚠️ **stesso giro**: chiave `pagamenti.righe.elimina_reason.distinta_annullata` nei locales it/en. `check_i18n_keys` la trova nel corpo della check e fa fallire la CI finché manca |
| R-2 | BE | policy generata e ripiego senza `%s` per `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` ed `E_CONTABILE_ANNULLO_NON_MANUALE`. Il guardrail `test_error_codes_db_policy_guardrail` li trova nei corpi |
| R-3 | BE + FE | «Annulla» su una distinta **non manuale**: spento col motivo, non nascosto (§12.1). La regola è sul catalogo (`righe_lavorabili` dello stato d'arrivo) e sull'`origine` della testata: il dettaglio può esporre `can_annullare` + il motivo senza copiarla. ⚠️ Una copia in Python di «origine = MANUALE» sarebbe la seconda sede: meglio leggerla dal DB, come `can_validare` |
| R-4 | BE | i test Django che annullano una distinta devono crearla `MANUALE`. Il default della colonna è `GENERATA`: la stessa trappola di `test-vendite-contabili-stato-obbligatorio` |
| R-5 | BE + FE | il §6 invariato: la coda filtra su `righe_lavorabili`, il dettaglio e la riga la espongono, il frontend smette di derivare `finale && !registrata` |

### 10.5 Stato al 2026-09-30

| Parte | Stato |
| --- | --- |
| DB (P-1 … P-8) | ✅ applicato su dev, pgTAP verdi |
| CI da zero | ⏳ alla prossima PR `dev/db-tid` → `Tito-dev`. ⚠️ Finché manca R-1, `check_i18n_keys` è rosso per la `reason_key` nuova |
| BE: coda filtrata e bandiera esposta (§6, R-5) | ✅ 2026-09-30 (§11.1) |
| BE: policy e ripieghi dei due codici (R-2) | ✅ 2026-09-30 (§11.1) |
| DB: check delle condizioni di transizione (D-6, §11.4) | ⏳ al team DB (D-6 approvata da Tid il 2026-09-30) |
| BE/FE: «Annulla» e «Porta a Bozza» spenti col motivo sulle non manuali (R-3) | ⏳ dopo D-6 |
| BE: test Django con distinte `MANUALE` quando annullano (R-4) | ✅ 2026-09-30 (§11.1) |
| FE: chiave i18n `distinta_annullata` (R-1), azioni di riga lette dalla bandiera (§6) | ✅ 2026-09-30 (§11.2) |
| Collaudo in-app (§6): la riga sparisce dalla coda | ✅ 2026-09-30, Tid: una `DA_ABBINARE` caricata a mano, distinta annullata → la coda «Da abbinare» si svuota |
| Collaudo in-app (§6): nel drawer la riga resta, in sola lettura, col motivo | ✅ 2026-09-30, Tid, dopo la correzione del badge (§11.2, riga D-3) |

Chiuso da Tid il 2026-09-30 a collaudo verde: la R-3 (D-6) continua in
PROJECT_CONTEXT § «Aperto — Media priorità».

## 11. Consegna BE/FE (2026-09-30)

Sessione `dev/backend-tid`, sul DB di sviluppo con `20260930-30 → -33`
applicati (merge #1734).

### 11.1 Backend

| # | Cosa | Dove |
| --- | --- | --- |
| R-5 | La coda seleziona solo righe con `cst.righe_lavorabili IS TRUE` (fail-closed: con la LEFT JOIN uno stato non letto non è «lavorabile»). La riga della coda porta `contabile_righe_lavorabili`, e il dettaglio e la lista delle distinte portano `stato_righe_lavorabili` (nella proiezione condivisa `_DISTINTA_SELECT`: è una colonna di catalogo e costa zero) | `pagamenti_repository.py`, `types.py` |
| R-2 | `error_policies_generated.py` rigenerato: due classi nuove, nessuna classe cambiata. Ripieghi senza `%s` per i due codici | `core/services/` |
| R-4 | Nessun test Django annullava una distinta sul DB vero. I test nuovi usano la fixture `_monta`, che la costruisce `MANUALE` | — |
| test | `AnnullataTests` (3 test, DB vero, soggetti costruiti): (1) la DA_ABBINARE e la SOSPESA ci sono in coda prima e **non** ci sono dopo l'annullo, e la bandiera del dettaglio passa da true a false; (2) nel drawer la riga resta, il cestino è spento con `DISTINTA_ANNULLATA` e la sua `reason_key`, e un cambio di stato è un 409 `E_RIGA_CONTABILE_DISTINTA_ANNULLATA`; (3) l'annullo di una non manuale è un 409 `E_CONTABILE_ANNULLO_NON_MANUALE`. **Mutazione**: senza il filtro della coda, (1) è rosso | `tests/db/test_validata_e_tardiva_db.py` |

### 11.2 Frontend

| # | Cosa |
| --- | --- |
| §6 | `useAzioniRigaContabile`: `testataDi(riga)` porta `{ righeLavorabili, registrata }` e il foglio si spegne su `righeLavorabili === false`, non più su `finale && !registrata`. La coda passa `contabile_righe_lavorabili` e il drawer passa `stato_righe_lavorabili` |
| §6 | Il motivo si divide in due chiavi: `pagamenti.distinte.foglio_annullato` («le sue righe si leggono soltanto»), che è il tooltip delle azioni e il messaggio del drawer sull'annullata, e `foglio_chiuso`, riscritta per la finale con righe lavorabili: nomina lo stato dal catalogo (`{stato}`, oggi «Chiusa») e dice «non accetta righe nuove; sospese e scartate si lavorano ancora». Prima la frase era una sola e sulla CHIUSA diceva «non si modificano più», dove invece la tardiva è aperta |
| R-1 | `pagamenti.righe.elimina_reason.distinta_annullata` in it/en. `distinta_finale` è riscritta per la sola CHIUSA, perché dalla check ora arriva solo da lì |
| — | `config_panel.campi.righe_lavorabili` in it/en: il pannello config degli stati mostra la colonna nuova, e `test_config_panel_registro_db` la pretende |
| test | Il test della coda la legge **intera**, pagina per pagina: con una pagina sola le righe della fixture potevano cadere fuori, e «non c'è» sarebbe passato per la popolazione e non per il filtro. |
| test | Spec del composable: foglio spento sulla bandiera, bandiera true e non registrata che non spegne niente, cestino dell'annullata col motivo della check |
| D-3 | (collaudo di Tid, 2026-09-30) Sull'annullata mancava il badge «Modalità consultazione» del titolo: il drawer leggeva il readonly **solo dai permessi**. Ora fa da provider della catena readonly (frontend-standards §catena readonly): permessi + prop `readonly` + stato (`stato_righe_lavorabili === false`, non `stato_is_final`: sotto la CHIUSA si lavora ancora), con `provide(READONLY_KEY)`. Le azioni di riga e il `RatePickerDialog` leggono il readonly **da permessi** (`readonlyPermessi`): sull'annullata restano visibili, spente col motivo. ⚠️ Niente `app-readonly` sul contenuto: `pointer-events: none` spegnerebbe il click sulla riga e i tooltip |

Verdi: pagamenti + core Django (1838 test, DB vero), vitest pagamenti,
`check_i18n_keys`, `genera_error_policies --check`. I rossi di `core` che
restano **non sono di questo brief**, e c'erano già prima:
`causale_magazzino` senza etichetta, `versione_contesto` NOT NULL sui template, e
i ripieghi di `E_DOCUMENTI_VERSIONE_CONTESTO_*`, del brief
documenti-versione-contesto-template, che la rigenerazione ha reso visibili.

Worker gunicorn ricaricati il 2026-09-30: il BE nuovo è attivo per il collaudo.

### 11.3 R-3 è fermo: manca la sede del motivo — D-6 (✅ Tid, 2026-09-30)

La R-3 chiede «Annulla» spento **col motivo** su una non manuale, letto dal DB
come `can_validare`. Ma `can_validare` legge una **check**
(`fn_check_contabile_validabile`), mentre la regola 3 vive **solo nel corpo del
guard** (`trgfn_vendite_contabili_guard_validazione`). Non c'è niente da
leggere. Le strade dal lato BE sono tutte copie:

* ricalcolare in Python o in SQL del repository «stato d'arrivo con
  `righe_lavorabili = false` e `origine <> 'MANUALE'`» è la seconda sede, che la
  R-3 stessa esclude;
* proporre la voce e lasciar parlare il 409 contraddice §12.1 (stato ⇒
  disabilita col motivo).

⭐ **E la stessa lacuna c'è già sulla regola 2** (`VALIDATA → BOZZA` solo MANUALE,
`E_CONTABILE_RIAPERTURA_NON_MANUALE`): oggi «Porta a Bozza» su una generata
validata si propone acceso e finisce in 409. Sono due regole dello stesso guard,
con la stessa forma (transizione × origine), e la matrice non le vede.

**Proposta al team DB (D-6):** una check sola per le condizioni di transizione
che la matrice non porta:

`script.fn_check_contabile_transizione(p_contabile_id bigint, p_stato_a text) → jsonb`

nella forma di `fn_check_contabile_validabile` (array di motivi
`{codice, reason, reason_key, dettaglio, valori}`, `[]` = ammessa), con i motivi
`RIAPERTURA_NON_MANUALE` (regola 2) e `ANNULLO_NON_MANUALE` (regola 3). Il
guard la chiama con `fn_raise_primo_motivo_se_presente`, come fa già per la
regola 1, così il rifiuto e il pulsante spento non possono divergere.
`reason_key` `pagamenti.distinte.transizione_reason.riapertura_non_manuale` e
`.annullo_non_manuale`, da mettere nei locales nello stesso giro.

⚠️ La regola 1 (VALIDATA) ha già la sua check con un secondo argomento
(l'importo dichiarato). Se debba entrare nella stessa check o restare a parte lo
decide il team DB. Dal BE basta sapere che ogni transizione ha **una** check da
leggere.

**Ricaduta BE/FE, dopo il DB:** il dettaglio espone, per ogni uscita della
testata, il blocco con il motivo (`transizioni_blocco: {stato_a: {reason,
reason_key, dettaglio}}`, letto con il BB `sql_lateral_primo_motivo` su ogni
uscita della matrice). Il drawer spegne «Porta a …» col motivo: «Annulla» sulle
non manuali (R-3) e, per simmetria, «Porta a Bozza» sulle non manuali.

### 11.4 Richiesta al team DB (D-6, approvata da Tid il 2026-09-30)

| # | Cosa |
| --- | --- |
| P-9 | `script.fn_check_contabile_transizione(p_contabile_id bigint, p_stato_a text) → jsonb`, nella forma di `fn_check_contabile_validabile`: array di motivi `{codice, reason, reason_key, dettaglio, valori}`, `[]` se la transizione è ammessa. Motivi, in quest'ordine: `RIAPERTURA_NON_MANUALE` (regola 2, `E_CONTABILE_RIAPERTURA_NON_MANUALE`, `VALIDATA → BOZZA` su una non MANUALE) e `ANNULLO_NON_MANUALE` (regola 3, `E_CONTABILE_ANNULLO_NON_MANUALE`, stato d'arrivo con `righe_lavorabili = false` su una non MANUALE). `STABLE`, firma con `%TYPE` dove serve. ⚠️ `p_stato_a` è il `codice_interno`, perché il BE lo conosce dalla matrice. Se il team DB preferisce l'id, lo dica: il BE si adegua |
| P-10 | `trgfn_vendite_contabili_guard_validazione`: le regole 2 e 3 chiamano la check con `fn_raise_primo_motivo_se_presente`, come fa già la regola 1, e il corpo non tiene più i due `IF` in proprio. È la condizione perché il pulsante spento e il 409 non possano divergere |
| P-11 | `reason_key` `pagamenti.distinte.transizione_reason.riapertura_non_manuale` e `.annullo_non_manuale`, con `dettaglio` che porta i valori della frase (codice della distinta, origine leggibile). ⚠️ `check_i18n_keys` le trova nel corpo: il BE/FE le mette nei locales **nello stesso giro** del push, come per R-1 |
| P-12 | pgTAP con soggetti costruiti: check `[]` su una MANUALE (annullo e riapertura), motivo giusto su una GENERATA (per entrambe le regole), guard che rifiuta con lo stesso codice del primo motivo, e mutazione (senza la chiamata alla check, il rifiuto sparisce) |
| — | Se la regola 1 (VALIDATA, con l'importo dichiarato) debba entrare nella stessa check o restare a parte lo decide il team DB: al BE basta **una** check leggibile per ogni transizione |

**Dopo il push DB, lato BE/FE:** il dettaglio espone `transizioni_blocco:
{stato_a: {reason, reason_key, dettaglio}}` su ogni uscita della matrice (BB
`sql_lateral_primo_motivo`), e il drawer spegne «Porta a …» col motivo.
Test: su una GENERATA validata «Annulla» e «Porta a Bozza» sono spenti col
motivo, e il 409 del guard porta lo stesso codice.
