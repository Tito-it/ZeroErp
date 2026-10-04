# Brief DB — Righe di contratto e offerta: l'esclusione è solo «non si vende», e le due tabelle obbediscono alle stesse regole

> **Chi chiede:** sessione BE/FE (`dev/backend-tid`), 2026-10-04: richiesta arrivata **senza brief**,
> scritta qui dal team DB (§1-§4 sono la richiesta, §5 la risposta). **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6).
> **Decisione:** di Tid, 2026-10-04. Riguarda `vendite.contratti_righe` e
> `vendite.offerte_commerciali_eccezioni`.
> **Origine:** il seguito di `brief-db-contratto-esclusione-non-modificabile` e di
> `brief-db-erogazione-obbligatoria-righe-fatturate` (stessa giornata).
> **Stato:** ✅ **DB chiuso il 2026-10-04**: applicato da Tid (`20261004-40…-49`, `-70…-76` e i tre
> CSV), pgTAP verdi nella sua corsa (§7). Due stop all'apply, corretti prima che il changeSet
> entrasse (§5.7). ⏳ Resta il giro BE/FE (§6).
> **Da leggere per primo:** §6 (che cosa resta al BE/FE), poi §5.6 (la decisione R5a «lock
> pieno», e che cosa comporta).

## 1. La regola

Un'**ESCLUSIONE** dice solo che il documento non vende quell'articolo del listino. Sul contratto e
sull'offerta, senza differenze:

* **non porta dati di fatturazione**: `prezzo_unitario`, `quantita`, `qta_operativa`,
  `uom_operativa_id`, `factor_to_base`, `tipo_erogazione`, `fonte_quantita_attesa`, `periodicita`,
  `generazione_canone` e `competenza_canone` restano vuoti, per vincolo;
* **non si modifica**: si crea («Escludi») e si cancella («Ripristina articolo»).

## 2. Il difetto

* L'esclusione nasceva **piena**: il drawer mandava quantità 1, fonte `FISSA` e un'erogazione, e
  i trigger della riga riempivano il resto (fonte di default, UdM e fattore dall'articolo). Dati
  che nessuno aveva scelto, su una riga che non si vende. `fonte_quantita_attesa` era `NOT NULL`
  per tutte le righe, quindi un'esclusione vuota non era nemmeno scrivibile.
* Il CHECK di stamattina (`chk_*_erogazione_per_tipo_eccezione`, `20261004-30`) lasciava
  l'erogazione dell'esclusione «libera».
* Le due tabelle, gemelle per progetto («mirror fedele», COMMENT della tabella dell'offerta),
  avevano regole diverse: sul contratto c'erano il blocco delle righe fuori bozza, il guard
  dell'aggiunta fuori listino, il guard dell'esclusione del componente di un bundle, il lock su
  `tipo_eccezione` e il guard «l'esclusione non si modifica»; sull'offerta nessuno dei cinque.
  `fn_push_offerta_a_contratto` copia le righe 1:1: un'offerta che passa poteva generare un
  contratto rifiutato al push.
* Il drawer dell'offerta deduceva i verbi di riga da solo: il contratto li riceve dal DB.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| R1 | Le colonne vuote sull'esclusione, sulle due tabelle. CHECK del tipo `tipo_eccezione <> 'ESCLUSIONE' OR (colonne IS NULL)`. `fonte_quantita_attesa` obbligatoria solo per le righe che non sono esclusioni (stessa forma di `chk_*_erogazione_per_tipo_eccezione`). Il CHECK sull'erogazione di stamattina passa da «libera» a «vuota» |
| R2 | I trigger che oggi riempiono l'esclusione la devono saltare: `trgfn_righe_default_fonte_qta`, `trgfn_qta_from_operativa`, la propagazione della quantità ai componenti. Da verificare i CHECK `coerenza_fonte_erogazione`, `fonte_qta`, `qta_operativa_nonzero`, `coerenza_canone` con le colonne vuote |
| R3 | «Non si modifica» anche sull'offerta: lo stesso guard `_a05_` del contratto, meglio portato in `script`, generico per le due tabelle (regola del 2) |
| R4 | Le azioni di riga anche sull'offerta: una funzione di lista come `fn_contratto_righe_preview`, così il drawer dell'offerta rende i verbi del DB |
| R5 | Le asimmetrie fra le due tabelle: (a) righe fuori bozza; (b) `guard_aggiunta_fuori_listino`; (c) `guard_esclusione_figlio_bundle`; (d) lock su `tipo_eccezione`. Chiuderle sull'offerta, o motivare sul modello quelle che non servono |
| R6 | Le righe esistenti fuori regola: il team DB sceglie come sistemarle (non siamo in produzione). Il changeSet non deve fallire in CI su un DB da zero |
| R7 | Elencare chi scrive le due tabelle e verificare che nessuno scriva su un'esclusione le colonne di R1 |
| R8 | Un codice per «colonna valorizzata su un'esclusione», col campo nel canale `COLUMN`; per il resto si riusano i codici del contratto. Ognuno con policy e ripiego senza `%s` |
| R9 | pgTAP costruiti, sulle due tabelle |

## 4. Fuori perimetro

* Le righe `OVERRIDE` e `AGGIUNTA` restano modificabili come oggi.
* La matrice erogazione × fonte e il CHECK sul prezzo non cambiano.

## 5. Risposta del team DB (2026-10-04)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-04. Tutti i punti scritti. Un punto
> deciso da Tid durante il giro (§5.6). ✅ Applicato e verde il 2026-10-04 (§7).

### 5.1 Che cosa è stato scritto

| changeSet | Fase | Cosa | R |
| --- | --- | --- | --- |
| `20261004-40-alter-righe-eccezione-fonte-per-tipo-eccezione` | `00_schema/vendite` | `fonte_quantita_attesa` DROP NOT NULL; `chk_contrighe_fonte_per_tipo_eccezione` e `chk_offerte_eccezioni_fonte_per_tipo_eccezione`; COMMENT del CHECK sull'erogazione («vuota», non più «libera») | R1 |
| `-41-update-fn-get-stato-testata-documento-offerta` | `20_code/script` | il lettore DEFINER dello stato delle testate impara `OFFERTA` (stato da `config.stati_doc_offerte`, etichetta «Offerta <codice>») | R5a |
| `-42-create-fn-documento-listino-operativo` | `20_code/vendite` | **nasce** `vendite.fn_documento_listino_operativo(documento, id)`: versione di listino operativa e variazione di contratto o offerta, in un posto solo | R4, R5 |
| `-43-create-fn-check-esclusione-articolo-documento` | `20_code/script` | **nasce** `script.fn_check_esclusione_articolo_documento(documento, id, articolo)`, generica | R5c |
| `-44-create-trgfn-righe-guard-esclusione-figlio-bundle` | `20_code/script` | **nasce** `script.trgfn_righe_guard_esclusione_figlio_bundle()`, generica | R5c |
| `-45-create-trgfn-righe-guard-aggiunta-fuori-listino` | `20_code/script` | **nasce** `script.trgfn_righe_guard_aggiunta_fuori_listino()`, generica; il messaggio nomina il documento con l'etichetta | R5b |
| `-46-create-trgfn-righe-guard-esclusione-immutabile` | `20_code/script` | **nasce** `script.trgfn_righe_guard_esclusione_immutabile()`, generica | R3 |
| `-47-create-trgfn-righe-guard-esclusione-senza-dati` | `20_code/script` | **nasce** `script.trgfn_righe_guard_esclusione_senza_dati()`: `E_RIGA_ESCLUSIONE_CON_DATI` col campo | R1, R8 |
| `-48-update-trigger-contratti-righe-esclusione-solo-non-si-vende` | `20_code/vendite` | contratto: i tre guard sulle funzioni generiche (stessi nomi, stesso `WHEN`); `default_fonte_qta` e `qta_from_operativa` con `WHEN (NEW.tipo_eccezione <> 'ESCLUSIONE')`; nasce `trg_contratti_righe_a10_guard_esclusione_senza_dati_ins` | R1, R2, R3, R5 |
| `-49-create-trigger-offerte-eccezioni-esclusione-e-simmetria` | `20_code/vendite` | offerta: «fuori bozza», «non si modifica», aggiunta fuori listino, figlio di bundle, «senza dati»; gli stessi due `WHEN` | R1, R2, R3, R5 |
| `-70-create-fn-documento-righe-eccezione` | `20_code/vendite` | **nasce** `vendite.fn_documento_righe_eccezione(documento, id)`: le righe eccezione delle due tabelle nella stessa forma | R4 |
| `-71-create-fn-documento-righe-preview` | `20_code/vendite` | **nasce** `vendite.fn_documento_righe_preview(documento, id)`: il corpo della lista, dal corpo vivo di `fn_contratto_righe_preview` | R4 |
| `-72-update-fn-contratto-e-offerta-righe-preview-involucri` | `20_code/vendite` | `fn_contratto_righe_preview` diventa involucro di una riga (firma e colonne invariate); **nasce** `fn_offerta_righe_preview` | R4 |
| `-73-drop-funzioni-righe-contratto-ritirate` | `20_code/vendite` | **ritiro** di `vendite.trgfn_contratti_righe_guard_esclusione_immutabile`, `_guard_aggiunta_fuori_listino`, `_guard_esclusione_figlio_bundle` e di `script.fn_check_esclusione_articolo_contratto` | regola del 2 |
| `-74-update-fn-offerta-righe-espanse-da-listino-operativo` | `20_code/vendite` | `fn_offerta_righe_espanse` chiede la versione al risolutore (era la quarta copia) | regola del 2 |
| `-75-comment-lock-fuori-bozza-e-guard-erogazione` | `20_code/vendite` | solo COMMENT: il building block «fuori bozza» ha un adottante in più; il guard dell'erogazione non dice più «libera» | debito doc |
| `-76-alter-righe-eccezione-esclusione-senza-dati` | `00_schema/vendite` | **bonifica** delle esclusioni già scritte (R6), poi `chk_contrighe_esclusione_senza_dati` e `chk_offerte_eccezioni_esclusione_senza_dati` | R1, R6 |
| CSV `config/codici_errore`, `config/messaggi_errore` | `80_data` | `E_RIGA_ESCLUSIONE_CON_DATI` (messaggio 1195); messaggi **neutri** per i codici riusati (450, 455/488, 1192, 1193); note dei codici aggiornate | R8 |
| CSV `dbops/automation_lock_columns` | `80_data` | `vendite.offerte_commerciali_eccezioni.tipo_eccezione` → `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` | R5d |
| `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` | pgTAP | **nuovo**, 26 test, tutto costruito | R9 |

⚠️ **Numerazione:** `-50…-59` sono di un'altra sessione DB aperta lo stesso giorno (brief
permessi/tetto area), comparsi mentre scrivevo. I miei, nati come `-50…-55`, sono stati
rinumerati a `-70…-75` prima della consegna; `-60…-69` restano liberi per loro.

Doc `manual/`: nuove le pagine delle nove funzioni nate; cancellate le quattro delle funzioni
ritirate (la storia passa nelle pagine che le sostituiscono); aggiornate `contratti_righe`,
`offerte_commerciali_eccezioni`, `fn_contratto_righe_preview`, `fn_offerta_righe_espanse`,
`fn_get_stato_testata_documento`, `trgfn_doc_righe_lock_fuori_bozza`,
`trgfn_righe_guard_erogazione_obbligatoria`, `fn_listino_versione_in_vigore`, `listini_versioni`
e la guida `gestione-contratti` (un link).

### 5.2 Le scelte, e perché

* **R1 — due CHECK, due regole.** La fonte «obbligatoria tranne sull'esclusione» (-40) ha la
  stessa forma del CHECK sull'erogazione. «Sull'esclusione i dieci campi sono vuoti» (-76) è un
  CHECK a sé, con l'elenco dei campi **vietati**: la domanda è «quali dati della vendita», e un
  campo aggiunto domani (una nota) non è detto che lo sia. È il rovescio del guard `_a05_`, che
  elenca le colonne **ammesse** in `UPDATE`. Il CHECK sull'erogazione di stamattina non cambia
  testo: dice l'obbligo sulle altre righe; il «vuota» lo dice -76. Gli altri CHECK della riga
  (`coerenza_canone`, `coerenza_fonte_erogazione`, `fonte_qta`, `qta_operativa_nonzero`,
  `tipo_erog`, `prezzo_per_tipo_eccezione`) sono soddisfatti dai campi vuoti: un CHECK su `NULL`
  passa. Verificato (test 6 e 11 del pgTAP nuovo).
* **R1/R8 — guard e CHECK, come per l'erogazione.** Il guard parla prima e manda codice e campo
  (`campo` = il primo valorizzato, nel canale `COLUMN`; `colonne` = tutti); il CHECK è la rete.
  ⭐ **Il guard è solo `BEFORE INSERT`**, di proposito: un'esclusione si scrive solo nascendo.
  Il suo `UPDATE` lo rifiuta il guard `_a05_`, il cambio di tipo verso `ESCLUSIONE` il lock su
  `tipo_eccezione`, ciascuno col suo rimedio. Montato anche in `UPDATE`, avrebbe parlato prima
  del lock («g» < «l») con il rimedio sbagliato («svuota il campo» invece di «elimina e
  ricrea»): lo ha mostrato il test 15 di `test-contratto-esclusione-non-modificabile`.
* **R2 — la deroga sta nel `WHEN` del trigger, non nelle funzioni.**
  `trgfn_righe_default_fonte_qta` e `trgfn_qta_from_operativa` sono building block generici (la
  seconda serve sei tabelle): non devono sapere che esiste un tipo di riga `ESCLUSIONE`. Chi sa
  che l'esclusione non ha quantità è la tabella. Senza, la prima avrebbe messo `FISSA` (ramo
  `ELSE` della matrice, con erogazione vuota) e la seconda avrebbe sollevato `E_QTA_MISSING`
  (fonte vuota non è «diversa da FISSA»). La propagazione ai componenti (`AFTER UPDATE OF
  quantita`) non cambia: un'esclusione non si aggiorna e non ha componenti (l'init la salta).
* **R3, R5b, R5c — tre funzioni generiche in `script`, le copie ritirate nello stesso giro.**
  Argomenti del trigger: il documento (`CONTRATTO`, `OFFERTA`) dove serve, e la colonna del
  padre. I tre trigger del contratto **conservano il nome** (li leggono pgTAP e presidi) e
  passano alle funzioni nuove; le quattro funzioni del solo contratto escono (-73).
* **La versione di listino in un posto solo.** Guard dell'aggiunta, check dell'esclusione e
  lista delle righe partono dalla stessa domanda («quale versione vale per questo documento?»),
  che era scritta quattro volte (anche in `fn_offerta_righe_espanse`). Portarla all'offerta
  copiando avrebbe fatto sei copie: nasce `fn_documento_listino_operativo`, e le quattro la
  chiamano. Il push copia la versione fissata dell'offerta nel contratto: lo stesso risolutore
  dà quindi la stessa versione ai due capi.
* **R4 — una lista per i due documenti.** `fn_documento_righe_preview` è il corpo vivo di
  `fn_contratto_righe_preview` (`20261004-14`) con tre cambi soli (testata dal risolutore,
  eccezioni da `fn_documento_righe_eccezione`, «Escludi» dalla check generica). Le due funzioni
  per documento sono involucri di una riga, perché il building block del backend
  (`RigheListaMixin`) legge da `fn(padre)`. Verbi identici: DA_LISTINO → `SOVRASCRIVI_PREZZO`,
  `ESCLUDI`; OVERRIDE → `MODIFICA`, `RIPRISTINA_LISTINO`; ESCLUSIONE → `RIPRISTINA_ARTICOLO`;
  AGGIUNTA → `MODIFICA`, `RIMUOVI`. La richiesta abbreviava «OVERRIDE/AGGIUNTA → MODIFICA»: ho
  tenuto i verbi completi del contratto, perché il drawer dell'offerta deve fare le stesse cose.
* **R5d nel registro, non in un trigger.** Dal 2026-09-26 `dbops.automation_lock_columns` è
  l'unica sede dei lock di colonna: una riga CSV, il trigger lo genera `ci_apply`.
* **R8 — i codici riusati, con messaggi neutri.** Tre dei quattro codici da riusare dicevano
  «contratto» nel **messaggio**: sull'offerta l'operatore avrebbe letto una cosa falsa. I codici
  restano (R8 chiede di riusarli, e il backend li ha già in policy); cambiano i testi:
  `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` «Un articolo escluso non si modifica…»,
  `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` «Il tipo di una riga non si cambia (colonna %s)…»,
  `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` «Articolo [%s] gia' presente nel listino di %s…», dove il
  secondo valore ora è l'**etichetta** del documento («Contratto C-…», «Offerta OF-…») invece
  dell'id del contratto. Il nome dei codici dice «CONTRATTO» per storia: scritto nelle note.
* **I nomi dei trigger dell'offerta, e chi parla prima.** Fra i `BEFORE ROW` parla per primo il
  nome minore. Sull'offerta i trigger generati hanno il prefisso lungo
  `trg_offerte_commerciali_eccezioni_` e vengono prima di **tutti** quelli scritti a mano col
  prefisso corto `trg_offerte_eccezioni_`. I due rifiuti `_a05_` («fuori bozza», «non si
  modifica») devono parlare prima del lock generato: hanno quindi il prefisso lungo (che è anche
  quello della regola dei nomi), accorciati per stare nei 63 caratteri
  (`…_a05_doc_bozza_ins_upd_dlt`, `…_a05_guard_escl_immut_upd`; «doc» < «guard», quindi «fuori
  bozza» parla prima, come sul contratto). I guard `_a10_` restano col prefisso corto dei
  fratelli. Ordine verificato sul catalogo dopo la generazione del lock (§5.7).
* **R6 — bonifica nel changeSet, non a mano.** Diverso dal `20261004-30`: lì correggere voleva
  dire scegliere un'erogazione al posto di chi aveva creato la riga, qui «vuoto» è esattamente la
  regola, e la correzione non sceglie niente. Sta nel -76, **dopo** i trigger col `WHEN` (-48/-49)
  e dopo il `DROP NOT NULL` della fonte (-40): l'autogen ordina per numero.
  L'`UPDATE` incontra due rifiuti voluti («non si modifica», «fuori bozza»): si spengono **per
  nome**, i soli due per tabella, il tempo dell'`UPDATE`, nella transazione del changeSet. Sono
  trigger scritti a mano, non generati (linee-guida-sql §11.5; guardrail verde). Audit e `tx_id`
  girano. Su un DB da zero l'`UPDATE` non tocca niente.
  ⚠️ *Vicolo cieco, per chi riapre:* la prima stesura aveva una `preCondition` HALT e la
  correzione a mano, come il -30. Non può funzionare: per svuotare la fonte serve il `DROP NOT
  NULL`, che stava nello stesso changeSet fermato dalla `preCondition`.

### 5.3 Il codice nuovo

| Codice | Classe | Messaggio | Valori |
| --- | --- | --- | --- |
| `E_RIGA_ESCLUSIONE_CON_DATI` | `DATO_ERRATO` | «Un articolo escluso non porta prezzo, quantità né erogazione: questi dati restano vuoti.» (id 1195) | nessuno |

Contesto: `campo` (il primo dato valorizzato, nel canale `COLUMN`), `colonne` (tutti),
`riga_id`, `contratto_id` o `offerta_id`, `articolo_id`. Nessun `bersaglio`.

### 5.4 R7 — chi scrive le due tabelle (censito il 2026-10-04)

| Scrittore | Cosa fa | Scrive dati su un'esclusione? | Fuori bozza? |
| --- | --- | --- | --- |
| `vendite.fn_push_offerta_a_contratto` | `INSERT` nel contratto (DRAFT), copia 1:1 | solo se l'offerta li ha: da oggi non può | no: il contratto nasce DRAFT |
| `vendite.fn_crea_revisione_offerta` | `INSERT` nella revisione (nasce BOZZA), copia 1:1 | come sopra | no |
| BE `ContrattiRepository` / `OfferteRepository` (create, update, delete) | i verbi dei drawer | **sì, oggi**: il drawer manda quantità 1, fonte `FISSA` ed erogazione sull'«Escludi». Da oggi il DB lo rifiuta col campo: vedi §6 | il service lo vieta già |
| BE `approvazioni_prezzo_service` | `UPDATE` di `stato_approvazione_prezzo` | no (un'esclusione non ha prezzo) | ⚠️ vedi §5.6 |
| trigger delle tabelle | `default_fonte_qta`, `qta_from_operativa` | **sì, oggi**: la riempivano. Da oggi la saltano (`WHEN`) | — |
| `trgfn_componenti_ricalcola_padre` (dai componenti) | `UPDATE` del prezzo della riga madre | no: un'esclusione non ha componenti | ⚠️ vedi §5.6 |
| automazioni (pulizia, scadenze, pannello, storico) | — | nessuna nomina le due tabelle | — |

### 5.5 pgTAP

* **Nuovo** `test-righe-esclusione-solo-non-si-vende-v1.sql`, 26 test, tutto costruito (mondo,
  listino con un bundle, contratto, due offerte): i due CHECK letti da `conkey` (dieci campi più
  il tipo, né uno di più né uno di meno); la fonte nullable e il suo CHECK; i cinque trigger
  dell'offerta e i quattro del contratto sulle funzioni giuste, le quattro vecchie ritirate;
  l'esclusione **resta vuota** dopo l'`INSERT` (nessun trigger la riempie); i rifiuti con la
  frase **e** coi canali `CONSTRAINT` / `COLUMN`; un `OVERRIDE` senza fonte riceve ancora `FISSA`;
  sull'offerta `UPDATE` rifiutato, `UPDATE` senza cambi e `DELETE` ammessi; le quattro regole del
  contratto ora sull'offerta (il lock in `skip` dichiarato finché `ci_apply` non lo genera); la
  lista dell'offerta coi verbi e «Escludi» spento; la lista del contratto identica al corpo
  comune (nei due sensi, su sei righe); `fn_offerta_righe_espanse` con la stessa risposta.
* **Adeguati** (17 file): le fixture che creavano esclusioni piene ora le creano vuote
  (`test-contratto-righe-lista`, `-esclusione-non-modificabile`, `-erogazione-obbligatoria`,
  `-guard-esclusione-figlio-bundle`, `-contratti-modalita-pricing`, `-contratti-schema-step22`,
  `-fn-resolve-prezzo-listino-v2-step24`, `test_offerte_eccezioni_componenti`); i test che
  nominavano le funzioni ritirate (`-contratto-righe-lista` 8, 9, 12, `-guard-esclusione-figlio-bundle`
  1, 2, `-listino-versione-in-vigore` 13, `dbops/test-punti-canale-campo` 1); i test sul `NOT NULL`
  della fonte (`coerenza-fonte-erogazione` 1, `offerte_commerciali_eccezioni_struttura` 3); le
  frasi neutre (`-esclusione-non-modificabile` 5-9, 15); il quinto adottante del lock
  (`test-trgfn-doc-righe-lock-fuori-bozza` 2); `step22` test 9, che ora vede parlare il guard
  dell'esclusione prima del CHECK sul prezzo.
* **Fixture dell'offerta riordinate per R5a**: le righe nascono in BOZZA e l'offerta va avanti di
  stato **dopo** (`test_fn_push_offerta_a_contratto`, `test_fn_crea_revisione_offerta`,
  `test_offerte_eccezioni_componenti`). In `test_fn_crea_revisione_offerta` l'articolo
  dell'`AGGIUNTA` è scelto fuori dalla versione di listino; in `test_offerte_eccezioni_componenti`
  lo slot `COMPOSITA-OVR` era un'`AGGIUNTA` di un articolo che la stessa offerta forzava già
  (OVERRIDE): diventa un `OVERRIDE` su un'offerta sua.
* **`test-contratti-righe-componenti` 28**: in `skip` dichiarato. Cercava nei dati
  un'esclusione composita **con quantità**, che da oggi non si può scrivere: sarebbe passato solo
  per coincidenza.
* **`test-fn-check-prezzi-autorizzati` 25, 26, 43, 44**: riscritti per la decisione di §5.6.

### 5.6 ✅ R5a decisa da Tid (2026-10-04): «lock pieno»

**Emerso nel giro.** Il lock «righe solo in bozza» sull'offerta ha un effetto oltre le righe:
quando cambia lo stato di approvazione di un **componente**, il trigger
`trg_oce_comp_z90_ricalcola_padre` fa un `UPDATE` del prezzo della riga madre, e su un'offerta
emessa quell'`UPDATE` è fuori bozza. Lo ha trovato il confronto pgTAP:
`test-fn-check-prezzi-autorizzati` costruiva «un componente rifiutato dopo l'emissione» (test
25, 26) e «un componente tornato in attesa dopo l'emissione» (43, 44) con un `UPDATE` diretto. Sul
contratto è così dal 2026-09-22, con lo stesso building block.

Nessun percorso reale produce quei casi: l'emissione esige prezzi tutti autorizzati, e i prezzi
si cambiano solo in bozza. **Decisione di Tid: lock pieno, come sul contratto, senza eccezioni.**
Dopo l'emissione niente cambia sulle righe dell'offerta, nemmeno lo stato di approvazione; una
nuova richiesta passa da una revisione, che nasce in bozza.

Conseguenze:

* i test 25 e 43 provano ora che quell'`UPDATE` è rifiutato («fuori bozza»); il 26 e il 44 che
  «Accetta» e «Crea revisione» sono accesi coi prezzi dell'emissione;
* i controlli «prezzo rifiutato verso ACCETTATA» e «prezzo in attesa in `fn_crea_revisione_offerta`»
  restano come rete, ma per l'offerta non hanno più una strada che li raggiunga. Il building
  block che li fa è lo stesso del preventivo, dove sono provati (test 40);
* ⚠️ **correzione al censimento R7**: la mia prima stesura diceva «il workflow dei prezzi decide
  prima dell'emissione». Vero per le righe, non per i **componenti**, che non hanno un lock
  proprio ma passano dalla riga madre. Scritto qui perché è il tipo di scrittore che un
  censimento per «chi scrive la tabella» non vede: un trigger di un'altra tabella.

### 5.7 La prova (2026-10-04)

Sullo scratch `zeroerp_ci`, da owner, in transazioni annullate: l'SQL **estratto** dai 17 YAML
(`yaml.safe_load`, in ordine di numero, `ON_ERROR_STOP`), le righe CSV nuove o cambiate
**simulate** con `INSERT … ON CONFLICT` (non prova il loader `loadUpdateData`), e per i lock
`dbops.fn_run_automations_lock_columns('CI', ARRAY['vendite'], false)` nella stessa transazione.

* I 17 changeSet girano interi; il rollback non lascia oggetti.
* `test-righe-esclusione-solo-non-si-vende-v1`: **26/26**, compreso il 20 col lock generato.
  **Mutazione**: tolti i due guard «senza dati», il lock «fuori bozza» e il guard dell'aggiunta
  sull'offerta, sono rossi esattamente i test che li presidiano (4, 5, 7-9, 12, 16, 17) e le
  loro conseguenze (21, 23, 26: l'aggiunta passata finisce in lista); nei 7-9 e 12 parla il
  CHECK, cioè la rete funziona.
* **Bonifica (R6)**: costruite un'esclusione piena su un contratto in bozza e una su un'offerta
  già EMESSA (sei dati ciascuna); dopo i 17 changeSet hanno zero dati, `user_update` di chi
  migra, i quattro trigger riaccesi, i due CHECK presenti.
* **Confronto su 88 pgTAP** che toccano le due tabelle, le funzioni o i registri coinvolti,
  ciascuno com'è e con l'SQL nuovo dopo il suo `BEGIN`, **in sequenza** (in parallelo i miei
  `ALTER TABLE` andavano in deadlock fra loro: un primo giro è da buttare): **nessun file
  peggiora**. I rossi che restano sono identici prima e dopo, tutti di fixture legate ai dati
  (già in `baseline-rossi-ci.tsv`). Quelli dei file adeguati in §5.5 diventano verdi.
* `plpgsql_check` a zero errori sulle dodici funzioni nuove o riscritte;
  `dbops/test-riferimenti-morti-v1` 9/9; `script/test-catalogo-messaggi-errore-completo` 7/7;
  `script/test-rubinetto-primo-motivo-v1` 7/7 (un sito entra, uno esce: il conteggio non cambia).
* Guardrail statici verdi: `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
  `grant_ruolo_batch`, `pgtap_preambolo`, `sql_letterali`, `timestamp_senza_fuso`.

⚠️ **L'apply ha trovato un difetto che la prova non poteva vedere (2026-10-04).** Tid ha
applicato `-40…-72` mentre il giro era in corso; `-73` si è fermato sulla sua `preCondition`
(«Expected '0' got '1'»). Il controllo «nessuna funzione chiama più la check del contratto»
contava anche `vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle`, cioè una delle
funzioni che lo stesso changeSet ritira. Corretto il file (non era entrato: la `preCondition`
ferma prima dell'esecuzione): il controllo esclude le quattro funzioni ritirate. Le due
`preConditions`, estratte dallo YAML ed eseguite su dbdev, danno 0 e 0. ⭐ La lezione: la prova
con l'SQL estratto esegue i `changes`, **non** le `preConditions`; vanno eseguite a parte, sul
database che le incontrerà. Fatto anche per `-74` e `-76` su dbdev: passano.

⚠️ **Secondo stop, al `-76` (stesso giorno).** Su dbdev le esclusioni da svuotare c'erano, e
l'`UPDATE` di `uom_operativa_id` accoda i trigger `DEFERRABLE INITIALLY DEFERRED` «unità di
misura attiva»; con quegli eventi in sospeso, l'`ALTER TABLE … ENABLE TRIGGER` che segue fallisce
(«eventi trigger in sospeso»). La mia prova non lo vedeva perché il suo script girava con
`SET CONSTRAINTS ALL IMMEDIATE` in testa, come i pgTAP; Liquibase no. Riprodotto sullo scratch con
`SET CONSTRAINTS ALL DEFERRED` davanti ai changeSet, corretto con `SET CONSTRAINTS ALL IMMEDIATE`
in testa al `-76` (vale per la sola transazione del changeSet), riprovato: le esclusioni escono
vuote, trigger riaccesi, CHECK presenti. Il `-76` era fallito e annullato, quindi il file si è
potuto correggere.

**Non provati qui, restano a Tid:** l'apply vero (loader dei CSV, `ci_apply` col lock
generato), la corsa come app, e le suite dell'offerta che sullo scratch vanno in errore di
fixture già oggi (`test_fn_push_offerta_a_contratto`, `test_fn_crea_revisione_offerta`,
`test_offerte_eccezioni_componenti` dal 17 in poi, `test_push_offerta_fissa_qta_operativa`):
le ho adeguate leggendo il codice, le verifica solo la corsa su dbdev.

### 5.8 Trovato nel giro, non corretto qui

* 🟠 **La revisione dell'offerta perde i componenti.** `fn_crea_revisione_offerta` copia le
  eccezioni ma non `offerte_commerciali_eccezioni_componenti` (il suo commento dice «non ha
  tabelle figlie che richiedano remapping», e non è vero). Una revisione di un'offerta con un
  bundle `AGGIUNTA` nasce senza componenti, e il push la porta così nel contratto. Da un brief a
  sé.
* 🟡 **Scale diverse fra le gemelle**: `prezzo_unitario` è `numeric(15,6)` sul contratto e
  `numeric(18,6)` sull'offerta; `fonte_quantita_attesa` `varchar(24)` contro `varchar(32)`. Il
  push copia 1:1: un prezzo oltre 10⁹ passa sull'offerta e fallisce sul contratto. Fatto di
  struttura, letto il 2026-10-04.
* 🟡 **Componenti senza lock fuori bozza**, su **tutte e due** le tabelle dei componenti: oggi li
  protegge di fatto il ricalcolo della riga madre (§5.6), che è un effetto, non una regola.
* 🟡 `contratti_righe.attivo` e `meta` sono nullable, sull'offerta no.

## 6. Lato BE/FE, a consegna DB fatta

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-1** | Il codice nuovo `E_RIGA_ESCLUSIONE_CON_DATI` in `error_policies_generated.py` (`DATO_ERRATO`, campo nel canale `COLUMN`) e in `error_messages_fallback.py` (ripiego senza `%s`). Il guardrail `test_error_codes_db_policy_guardrail` lo trova nel corpo del guard | BE |
| **R-BE-2** | I **ripieghi** di tre codici riusati dicono ancora «contratto» (`error_messages_fallback.py`, righe di `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` e `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`, e quello di `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` se c'è): da rendere neutri come i messaggi del DB. Rigenerare le policy (cambiano le note) | BE |
| **R-BE-3** | **«Escludi» crea l'esclusione vuota**, sul contratto e sull'offerta: nel `create` di una riga `ESCLUSIONE` non si mandano quantità, fonte, erogazione, UdM né gli altri sei. Oggi il DB la rifiuterebbe col campo. Lasciar parlare il DB basta; una pre-validazione nel service solo se dice la stessa cosa (stesso codice, stesso campo) | BE + FE |
| **R-BE-4** | `fonte_quantita_attesa` può essere `NULL` (sull'esclusione): i serializer e i tipi che la davano per presente (il §7 del brief dell'esclusione aveva tolto i ripieghi «perché NOT NULL») vanno riletti | BE + FE |
| **R-BE-5** | La lista dell'offerta: `OfferteRepository.list_eccezioni` legge la tabella cruda. Per i verbi del DB (R4) il drawer deve leggere `vendite.fn_offerta_righe_preview(offerta)`, stesse colonne di quella del contratto. **Da decidere nel giro BE/FE**: se diventa una lista configurabile come `vendite.contratto_righe` (lista 103), il DB registra la lista (`ui.lista_definizione`, colonne, preset) in un giro a sé, su richiesta | BE + FE (+ DB) |
| **R-BE-6** | Le righe dell'offerta fuori bozza ora le rifiuta anche il DB (`E_RIGA_DOC_NON_BOZZA`): il controllo del service resta (parla prima), il codice del DB è la rete. Da oggi anche le decisioni di prezzo sui componenti di un'offerta emessa sono rifiutate (§5.6): se il workflow le prevedesse, passano da una revisione | BE |
| **R-BE-7** | Sull'offerta valgono ora «aggiunta fuori listino» ed «esclusione del componente di un bundle»: il drawer dell'offerta può spegnere «Escludi» col motivo (`escludi_blocco_codice`, chiave i18n già esistente `vendite.contratti.escludi_blocco.figlio_di_bundle`) | FE |
| **Doc** | `api_contratti.md`, la doc API delle offerte, `modello-contratti.md`: nominano le funzioni ritirate (`trgfn_contratti_righe_guard_*`, `fn_check_esclusione_articolo_contratto`) | BE |

## 7. Esito

1. ✅ Scritti i 17 changeSet e i tre CSV (§5.1), provati sullo scratch (§5.7).
2. ✅ Applicati da Tid su dbdev il 2026-10-04, in due riprese: `-40…-72`, poi `-73…-76` e i CSV,
   dopo le due correzioni di §5.7 (`preCondition` del `-73`, `SET CONSTRAINTS ALL IMMEDIATE` nel
   `-76`). Letto dal catalogo di dbdev lo stesso giorno: i quattro CHECK
   (`chk_*_fonte_per_tipo_eccezione`, `chk_*_esclusione_senza_dati`) ci sono; le quattro funzioni
   ritirate non ci sono più; il lock generato `trg_offerte_commerciali_eccezioni_a10_lock_columns_upd`
   c'è, quindi il test 20 del pgTAP nuovo gira davvero.
3. ✅ pgTAP lanciati da Tid: verdi (2026-10-04), comprese le suite dell'offerta che lo scratch non
   sapeva eseguire.
4. ⏳ BE/FE (§6). Quando è chiuso, il brief va in `work-done/`.
