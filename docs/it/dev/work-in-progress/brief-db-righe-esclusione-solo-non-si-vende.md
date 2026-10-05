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
> ✅ **BE/FE primo giro** fatto il 2026-10-04 (§9); il resto aspetta il §8.
> ✅ **Secondo giro DB** (§8 → risposta in §10): `20261005-10…-19`, la lista `vendite.offerta_righe`
> (106) nei CSV, note di tre codici; applicato su dbdev il 2026-10-05 (letto da `databasechangelog`).
> ✅ **BE/FE secondo giro** fatto il 2026-10-05 (§11): l'endpoint della lista, il drawer dell'offerta
> sui verbi del DB col BB condiviso col contratto, le sette chiavi, le policy. Tutto il §6 e il §10.7
> sono chiusi: ⏳ resta solo la decisione di archiviare il brief (§11.4).
> **Da leggere per primo:** §11 (consegna BE/FE del secondo giro), poi §10.7 e §6.

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

## 8. Secondo giro DB — richiesta della sessione BE/FE (2026-10-04)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB.
> **Decisione:** di Tid, 2026-10-04: le due cose qui sotto si fanno adesso, in questo brief (niente
> brief nuovo). Il resto del §6 lo fa il BE/FE senza aspettare.

### 8.1 R-DB2-A — La lista delle righe dell'offerta, configurabile come quella del contratto

Risponde a R-BE-5 (§6). Il drawer dell'offerta passa da una `DataTable` in memoria sulla tabella cruda
a `DrawerTabLista`, come il contratto: stessa ricerca, export, colonne, verbi del DB.

* Registrare la lista configurabile **`vendite.offerta_righe`** sulla funzione
  `vendite.fn_offerta_righe_preview(offerta_id)`: `ui.lista_definizione`, `lista_colonna`, `lista_preset`.
* **Stesse colonne, stesso ordine e stesso preset** di `vendite.contratto_righe` (lista 103):
  `articolo_codice`, `articolo_descrizione`, `qta_operativa`, `prezzo_finale`, `override_prezzo`,
  `uom_codice`, `tipo_erogazione`, `prezzo_listino`, `origine`, `azioni` (`tipo_colonna = azione`).
  Stessi attributi (`multi_emittente`, `perimetro_emittente`, `ricerca_min_caratteri`) salvo una
  ragione di modello, da scrivere.
* Le chiavi i18n delle intestazioni: le stesse della 103 se il DB le condivide, altrimenti l'elenco
  delle nuove, che il FE scrive nello stesso giro.

Lato BE/FE, a consegna fatta: `OffertaRigheListaRepository` (`RigheListaMixin` su
`fn_offerta_righe_preview`), le view `…/righe/lista/` ed export con `build_lista_figlia_views`, e il
drawer su `DrawerTabLista`.

### 8.2 R-DB2-B — I quattro punti del §5.8, chiusi

| # | Cosa | Perché |
| --- | --- | --- |
| B1 | 🟠 **`fn_crea_revisione_offerta` copia anche `offerte_commerciali_eccezioni_componenti`**, con il remapping sulle eccezioni nuove; il commento della funzione («non ha tabelle figlie che richiedano remapping») va corretto | una revisione di un'offerta con un bundle nasce senza componenti, e il push la porta così nel contratto: difetto di modello, non di simmetria |
| B2 | **Scale uguali fra le gemelle**: `prezzo_unitario` e `fonte_quantita_attesa` (e ogni altra colonna che il confronto trovasse diversa) con lo stesso tipo sulle due tabelle. Quale delle due scale vince lo decide il team DB sul modello | il push copia 1:1: un valore valido sull'offerta può fallire sul contratto |
| B3 | **Lock «solo in bozza» sui componenti**, contratto e offerta: `trgfn_doc_righe_lock_fuori_bozza` (o la forma che il team DB ritiene giusta per una tabella nipote) su `contratti_righe_componenti` e `offerte_commerciali_eccezioni_componenti` | oggi li protegge di fatto il ricalcolo della riga madre (§5.6): è un effetto, non una regola |
| B4 | **`contratti_righe.attivo` e `meta` NOT NULL** come sull'offerta (default già presenti) | simmetria fra le gemelle |

pgTAP costruiti per ognuno: la revisione di un'offerta con un bundle porta i componenti (e il push li
porta nel contratto); un valore al limite della scala passa da offerta a contratto; un componente fuori
bozza rifiutato, sulle due tabelle; `attivo`/`meta` a NULL rifiutati sul contratto.

Ricadute BE/FE attese: nessuna su B1, B2, B4. B3: un codice nuovo, se nasce, da registrare.

## 9. Consegna BE/FE, primo giro (2026-10-04)

Tutto il §6 che non dipende dal §8.

| # | Fatto |
| --- | --- |
| R-BE-1 | `E_RIGA_ESCLUSIONE_CON_DATI` generato (`DATO_ERRATO`, zero classi mosse) e col ripiego senza `%s` |
| R-BE-2 | ripieghi neutri per `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`, `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`, `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`; policy rigenerate |
| R-BE-3 | «Escludi» del contratto manda solo `articolo_id` e `tipo_eccezione`. Offerta: il service non pretende più la fonte in create (come il contratto, che non l'ha mai pretesa), e neppure lo schema OpenAPI; il form non mostra e non manda i dati di fatturazione sull'esclusione. Nessuna pre-validazione: parla il DB — ritirato anche il 400 dei due service sul **prezzo** di un'esclusione in create (stessa regola, altro codice), provato sul DB vero da `test_contratto_esclusione_con_prezzo_rifiutata_col_campo`. Offerta: un'esclusione aperta dalla lista si vede in sola lettura (anche `ordine`/`attivo`: il guard `_a05_` rifiuta ogni colonna) |
| R-BE-4 | `OffertaEccezioneRow`: `fonte_quantita_attesa` e `factor_to_base` diventano `str \| None`. Gli altri lettori (stampe, commesse, push, assistente AI) non toccano la fonte; i due drawer la leggono già con guardia. Commenti «NOT NULL» corretti (drawer contratto, `constants.js`) |
| R-BE-6 | nessun cambio: il controllo di bozza del service resta e parla prima. Il percorso «approva/rifiuta prezzo» dell'offerta non guarda lo stato, ma una riga in attesa non esiste su un'offerta emessa (l'emissione la blocca), e ora il DB rifiuta comunque |
| Test | `test_contratto_esclusione_non_modificabile_db` riscritto sulle due tabelle (6 test, DB vero, mondo importato dal test gemello dell'erogazione): «Escludi» crea la riga vuota; un dato rifiutato col campo; il PATCH rifiutato. Due test mock dell'offerta non mandano più la fonte sull'esclusione |
| Service, create | `contratti_service` non pre-valida piu' il prezzo di un'ESCLUSIONE in create (il 400 `E_VENDITE_VALIDATION`): e' uno dei dieci dati che il guard DB rifiuta col campo; il test mock ora prova che la richiesta arriva al repository |
| Drawer offerta, modifica | un'esclusione aperta in modifica ha i campi spenti, il salvataggio spento e l'avviso `vendite.offerte.esclusione_non_modificabile` (it, en) |
| Doc | `api_contratti.md`, `api_offerte.md`, `modello-contratti.md`: funzioni ritirate sostituite dalle generiche, regola «esclusione vuota», codice nuovo, le regole del contratto ora anche sull'offerta. Commenti BE con nomi vecchi corretti (anche `trgfn_contratti_righe_guard_pending` → `script.trgfn_righe_guard_pending`) |

⏳ **Transitorio dichiarato, fino al §8.1**: sull'offerta l'esclusione si crea ancora dal form (vuota),
perché «Escludi» nasce dalle righe del listino, che il drawer vedrà solo con la lista nuova. Allo stesso
modo il click su un'esclusione dell'offerta apre ancora il form, ma in sola lettura con l'avviso: la regola
la decide il DB (il salvataggio risponderebbe 409), il form la rispecchia finche' i verbi non arrivano.
Con il §8.1 il drawer passa a `DrawerTabLista` coi verbi del DB, e l'opzione esce dal form (R-BE-5,
R-BE-7).

Verifica: test BE vendite + core (3930) con `ZEROERP_TEST_DB_E2E=1` verdi; vitest 668/668; eslint e
build puliti; nessuna chiave i18n rotta.


## 10. Secondo giro DB — risposta (2026-10-05)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-05. Tutti i punti del §8 scritti. ⏳ Niente
> applicato: l'apply e la corsa pgTAP sono di Tid.

### 10.1 Che cosa è stato scritto

| changeSet | Fase | Cosa | § |
| --- | --- | --- | --- |
| `20261005-10-alter-contratti-righe-tipi-come-offerta` | `00_schema/vendite` | contratto: `prezzo_unitario` `numeric(18,6)`, i quattro codici di erogazione `varchar(32)`; smonta e rimonta identico `trg_contratti_righe_a10_default_fonte_qta_ins_upd` (`UPDATE OF fonte_quantita_attesa`) | B2 |
| `-11-alter-offerte-eccezioni-factor-to-base-scala-articolo` | `00_schema/vendite` | offerta: `factor_to_base` `numeric(18,6)`; preCondition «nessuna riga con più di sei decimali» | B2 |
| `-12-alter-contratti-righe-attivo-meta-not-null` | `00_schema/vendite` | contratto: `attivo`, `meta` `NOT NULL`; preCondition «nessuna riga a NULL» | B4 |
| `-13-alter-offerte-eccezioni-componenti-tipi-come-famiglia` | `00_schema/vendite` | componenti dell'offerta: cinque colonne a `numeric` senza scala; smonta e rimonta `trg_oce_comp_a10_prezzo_obbligatorio_ins_upd` | B2 |
| `-14-alter-offerte-eccezioni-componenti-ordine-not-null` | `00_schema/vendite` | componenti dell'offerta: `ordine` `NOT NULL`; preCondition «nessuna riga a NULL» | B2 |
| `-15-create-fn-get-testata-id-di-riga` | `20_code/script` | **nasce** `script.fn_get_testata_id_di_riga(documento, riga)`: lettore `SECURITY DEFINER` riga → testata (CONTRATTO, OFFERTA, RESO) | B3 |
| `-16-update-trgfn-doc-righe-lock-fuori-bozza-livello-riga` | `20_code/vendite` | il building block impara il quarto argomento, il **livello** (`TESTATA` default, `RIGA`) | B3 |
| `-17-create-trigger-componenti-lock-fuori-bozza` | `20_code/vendite` | `trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt`, `trg_oce_comp_a05_doc_bozza_ins_upd_dlt` | B3 |
| `-18-update-resi-righe-rientri-lock-su-bb` | `20_code/vendite` | rientri del reso: la loro copia della regola si **ritira**, adottano il building block a livello RIGA; il guard resta per la coerenza, in `_a10_` | B3, regola del 2 |
| `-19-update-fn-crea-revisione-offerta-copia-componenti` | `20_code/vendite` | la revisione copia i componenti, rimappati riga per riga | B1 |
| CSV `ui/lista_definizione`, `lista_colonna`, `lista_preset`, `lista_preset_colonna` | `80_data` | lista **106** `vendite.offerta_righe`, colonne **1100-1109**, preset **106** | R-DB2-A |
| CSV `config/codici_errore` | `80_data` | solo note: `E_RIGA_DOC_NON_BOZZA` (i nipoti), `E_DOC_RIGHE_LOCK_MONTAGGIO` (il livello), `E_DOC_TIPO_NON_GESTITO` (il lettore nuovo) | B3 |
| `db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` | pgTAP | **nuovo**, 31 test, tutto costruito | tutti |

Nessun codice errore nuovo (B3 riusa `E_RIGA_DOC_NON_BOZZA`). Doc `manual/`: nuova
`script/manual/fn_get_testata_id_di_riga`; aggiornate `trgfn_doc_righe_lock_fuori_bozza`,
`fn_crea_revisione_offerta`, `fn_get_stato_testata_documento`, `contratti_righe`,
`offerte_commerciali_eccezioni`, `contratti_righe_componenti`,
`offerte_commerciali_eccezioni_componenti` (la tabella «differenze» col contratto era stantia:
diceva assenti `attivo`, `ordine`, `meta`), `resi_righe_rientri`.

### 10.2 R-DB2-A — la lista `vendite.offerta_righe`

Gemella della 103, campo per campo: sorgente `vendite.fn_offerta_righe_preview` (`vista_sql`
NULL), `multi_emittente = f`, `perimetro_emittente = t`, `ricerca_min_caratteri = 3`; stesse dieci
colonne con lo stesso `campo_sorgente`, tipo, formato, larghezza, ordine, flag e priorità; preset di
default `offerta_righe_default` con le stesse colonne nello stesso ordine. Nessuna ragione di modello
per un attributo diverso: le due funzioni hanno la stessa firma di uscita e lo stesso perimetro.

**Le intestazioni hanno chiavi dell'offerta**, non quelle della 103: ogni lista di righe di
documento ha il suo namespace (`vendite.preventivi.riga_*`, `vendite.ordini.riga_*`,
`vendite.contratti.col_*`…). Due esistono già (`vendite.offerte.col_articolo` «Articolo»,
`vendite.offerte.col_tipo_erogazione` «Erogazione»: per coerenza l'etichetta di ripiego della colonna
è «Erogazione», non «Tipo» come sul contratto). **Sette sono nuove**, il FE le scrive:

| Chiave | it | en (proposta) |
| --- | --- | --- |
| `vendite.offerte.col_descrizione` | Descrizione | Description |
| `vendite.offerte.col_qta` | Qta | Qty |
| `vendite.offerte.col_prezzo_finale` | Prezzo finale | Final price |
| `vendite.offerte.col_prezzo_forzato` | Prezzo forzato | Forced price |
| `vendite.offerte.col_uom` | UoM | UoM |
| `vendite.offerte.col_prezzo_listino` | Prezzo listino | List price |
| `vendite.offerte.col_origine` | Origine | Origin |

⚠️ `check_i18n_keys` le segnala già (7 «intestazioni senza traduzione»), e gira anche in
pre-commit sui CSV.

### 10.3 B1 — la revisione porta con sé i componenti

`fn_crea_revisione_offerta` copia le righe attive **una alla volta** con `RETURNING`, e per
ciascuna i suoi componenti sull'id nuovo: la forma di `fn_push_offerta_a_contratto`. La gemella del
preventivo rimappa con un `ROW_NUMBER` sui due insiemi, che regge finché gli id nuovi nascono
nell'ordine della `SELECT`: qui la corrispondenza la dà l'inserimento stesso.

* Si copiano **tutti** i componenti delle righe copiate, anche gli **opzionali spenti**: spegnere
  un opzionale è una scelta dell'offerta (gli obbligatori non si spengono, c'è il guard), e la
  revisione è la stessa offerta. È la regola del push.
* Stato e pratica di approvazione 1:1, come sulle righe. Un componente in attesa non arriva fin
  lì: il guard di testa (`fn_check_prezzi_in_attesa`) guarda anche i componenti attivi.
* I trigger del componente lavorano come alla nascita: la quantità si ricalcola dalla madre, il
  prezzo della madre dai componenti attivi — cioè lo stesso della rev N (test 14).
* Il commento sbagliato del corpo («nessuna tabella figlia») è sostituito dalla spiegazione.

### 10.4 B2 e B4 — quale scala vince, sul modello

Il confronto colonna per colonna (catalogo di dbdev, 2026-10-05) ha trovato otto differenze sulle
righe e sette sui componenti. ⭐ **La regola usata: vince la famiglia, non l'una o l'altra
tabella** — per una colonna di riga contano le altre righe di documento e la fonte del dato, per
una colonna di componente le altre tabelle di componenti.

| Coppia | Colonna | Prima (contratto / offerta) | Dopo | Perché |
| --- | --- | --- | --- | --- |
| righe | `prezzo_unitario` | `(15,6)` / `(18,6)` | `(18,6)` | la scala del destino (`fatture_righe`) e di ordine e offerta: si allarga il contratto |
| righe | `fonte_quantita_attesa`, `periodicita`, `generazione_canone`, `competenza_canone` | `varchar(24/12/16/16)` / `varchar(32)` | `varchar(32)` | vocabolari chiusi nei CHECK: la lunghezza è un tetto tecnico, allargare non rifiuta niente |
| righe | `factor_to_base` | `(18,6)` / `(18,8)` | `(18,6)` | la fotografia del fattore dell'articolo (`articoli_uom_operativa`, `(18,6)`), come su tutte le altre righe: si stringe l'offerta |
| righe | `attivo`, `meta` | nullable / `NOT NULL` | `NOT NULL` | B4 |
| componenti | `coeff_qta_snapshot`, `quantita`, `factor_to_base`, `qta_operativa`, `prezzo_unitario` | `numeric` / `(18,6)` e `(18,8)` | `numeric` | le cinque tabelle di componenti: quattro senza scala, l'offerta la sola con: si allinea lei (il verso opposto avrebbe stretto quattro tabelle, arrotondando valori scritti) |
| componenti | `ordine` | `NOT NULL` / nullable | `NOT NULL` | il push lo copia in una colonna `NOT NULL`: un `NULL` faceva morire il push |
| componenti | `user_update` | nullable / `NOT NULL` | **invariato** | ⚠️ differenza **dichiarata**: `NOT NULL` è la regola delle colonne di audit (linee-guida §7), il push non la copia, la scrive il trigger di audit. Allentarla per simmetria toglierebbe un vincolo giusto; il debito è delle altre tabelle (§10.8) |

**Le righe già scritte.** Nessuna correzione automatica: dove il vincolo nuovo può rifiutare una
riga esistente (`-11` arrotonderebbe, `-12` e `-14` vietano il `NULL`) c'è una preCondition
«nessuna riga cattiva» (`expectedResult 0`, legittima per §11.4: un DB da zero la soddisfa). Se
su dbdev scatta, il migrate si ferma e la riga si guarda a mano: scegliere un valore al posto di chi
l'ha scritta (un `attivo` NULL che diventa `true`) non è del migrate, e un `UPDATE` di bonifica
incontrerebbe il lock «fuori bozza». ⚠️ `ALTER TYPE … USING COALESCE` non era una strada per
`attivo`: la colonna è nella lista `UPDATE OF` dei trigger generati da `ci_apply`, e su quelli non
si fa DDL (§11.5). Gli allargamenti non hanno preCondition sui dati: non possono rifiutare niente.

**I trigger da rimontare.** `ALTER COLUMN … TYPE` rifiuta una colonna nominata in un trigger
`UPDATE OF` (la doc auto-gen non lo mostra; letto da `pg_trigger.tgattr`): sono due, scritti a mano,
smontati e rimontati identici nello stesso changeSet (definizione e COMMENT dal catalogo di dbdev e
dello scratch). Nessuna vista legge le colonne toccate. Le firme con `%TYPE` non portano typmod:
nessuna funzione da ricreare.

### 10.5 B3 — «solo in bozza» per le tabelle nipoti

**La forma.** Il building block `vendite.trgfn_doc_righe_lock_fuori_bozza` legge la testata dalla
FK della riga; i componenti hanno la FK verso la **riga**. Impara un quarto argomento, il livello:
con `'RIGA'` risale prima alla testata con `script.fn_get_testata_id_di_riga` (DEFINER del
proprietario: le righe hanno RLS, e un guard invoker scambierebbe «non la vedo» per «non c'è»), poi
fa il controllo di sempre. Riga assente ⇒ passa, come la testata assente. Nel contesto dell'errore
entra `riga_documento_id`. Il lettore ha un elenco **chiuso** di tre tabelle (nessun nome dal
chiamante, nessun SQL dinamico): un DEFINER «leggi la tabella che ti dico» sarebbe una porta su
tutto.

**Regola del 2.** La forma nipote c'era già, scritta a mano due volte: i rientri del reso
(`trgfn_resi_righe_rientri_guard`) e i prelievi della bolla (`trgfn_ddt_righe_prelievi_guard`). I
componenti sarebbero stati la terza e la quarta. Nello stesso giro:

* i **rientri** ritirano la loro copia (`-18`): stesso codice, stessa frase, stessi valori
  (`magazzino/test-reso-carico-v1` test 15 resta verde); la riga ora si legge dal DEFINER e non
  sotto RLS; il guard tiene solo la coerenza del prelievo e scende in `_a10_`, su INSERT/UPDATE;
* i **prelievi no**: in `EMESSO`/`SPEDITO` ammettono il cambio della sola ubicazione d'arrivo. Una
  regola con un'eccezione di dominio non è una copia di quella senza.

**Il difetto che la mutazione ha mostrato, e perché il test lo distingue.** Senza il lock sui
componenti, una loro modifica fuori bozza era rifiutata **lo stesso**: il trigger AFTER che
ricalcola il prezzo della madre fa un `UPDATE` della riga, e lì parla il lock delle righe — stesso
codice, stessa frase. È l'«effetto» del §5.8. I test 16, 18, 24, 26 nella prima stesura passavano
anche senza la regola; ora leggono **da dove** arriva il rifiuto (la pila dell'eccezione: non deve
passare da `trgfn_componenti_ricalcola_padre`). La differenza non è accademica: col solo effetto,
spegnere un componente obbligatorio su un'offerta emessa rispondeva «è obbligatorio» invece di
«l'offerta non è più in bozza» (test 17), e il rifiuto dipendeva da un trigger nato per altro.

**Nomi e ordine.** Contratto: prefisso della tabella, come i generati
(`trg_contratti_righe_componenti_a05_…`). Offerta: prefisso corto dei fratelli scritti a mano
(`trg_oce_comp_a05_…`; il lungo supera i 63 caratteri), che precede anche i generati. Rientri:
`trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt` (il nome pieno supera i 63). Il test 10 verifica
sul catalogo che su ogni nipote il lock sia il primo `BEFORE ROW`.

**Chi scrive i componenti** (censito il 2026-10-05): le due `fn_*_componenti_init` (alla nascita
della riga, in bozza), il push (contratto DRAFT), la revisione (offerta BOZZA), la propagazione
della quantità dalla riga (già sotto lo stesso lock), il backend nei drawer e nel flusso di
approvazione (in bozza; sull'offerta emessa vale già il «lock pieno» del §5.6). Nessuno li scrive
fuori bozza per una strada legittima.

### 10.6 La prova (2026-10-05)

Sullo scratch `zeroerp_ci` (allineato a dbdev: tutti i `20261004-*` applicati), da owner, in
transazioni annullate: l'SQL **estratto** dai dieci YAML (`yaml.safe_load`, in ordine di numero) **e
le loro preConditions** eseguite prima di ciascuno (la lezione del primo giro), con `SET CONSTRAINTS
ALL DEFERRED` davanti come Liquibase; le righe CSV nuove **simulate** con `INSERT … ON CONFLICT` (non
prova il loader).

* I dieci changeSet girano interi, preConditions comprese.
* `test-righe-gemelle-secondo-giro-v1`: **31/31**. **Mutazione** (un changeSet tolto alla volta,
  test finale): senza `-11` rosso 1; senza `-13` rosso 2; senza `-14` rosso 4; senza `-12` rossi 3,
  21, 22; senza `-16` rossi 8, 16-18, 24-26; senza `-17/-18` rossi 9-11, 16-18, 24-26; senza `-19`
  rossi 12, 13, 19 (e 24, 26 a valle: il contratto resta senza componenti); senza `-10` il push del
  prezzo al limite muore per overflow e il file si ferma. Ogni pezzo ha i suoi rossi, e solo quelli.
* **Confronto su 125 pgTAP** che toccano le tabelle, le funzioni, i registri delle liste e dei
  codici, ciascuno com'è e con l'SQL nuovo dopo il suo `BEGIN`, in sequenza: **121 identici**, 4
  diversi, tutti spiegati — `test-trgfn-doc-righe-lock-fuori-bozza` 2 diventa verde (l'elenco degli
  adottanti, aggiornato); `test-contratti-righe-componenti` 13 (TAP 22) conta i trigger della
  tabella, che diventano 14 (aggiornato, poi verde); i due `ui/test-fn-resolve-lista-config*` erano
  un **artefatto della simulazione** — l'`INSERT` con `id` 106 esplicito non muove la sequenza e il
  test, creando una sua lista, prendeva il 106; rilanciati passano, e nel migrate vero il resync
  `runAlways` di `90_end/20260602-17` riallinea le sequenze. I rossi preesistenti sono identici
  prima e dopo.
* `plpgsql_check` sulle quattro funzioni nuove o riscritte: zero errori (un warning, «STABLE che
  chiama una VOLATILE», lo stesso del lettore gemello). `dbops/test-riferimenti-morti-v1` 9/9,
  `script/test-rubinetto-primo-motivo-v1` 7/7, `script/test-catalogo-messaggi-errore-completo` 7/7.
* PreConditions **di catalogo** eseguite anche su dbdev (per nome): tutte al valore atteso; su
  dbdev i trigger `UPDATE OF` sulle colonne cambiate sono esattamente i due rimontati.
* I corpi di partenza (`20260922-02`, `20260928-90`, `20260924-35`) sono uguali al `prosrc` vivo di
  dbdev e dello scratch.
* Guardrail statici verdi: `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
  `grant_ruolo_batch`, `sql_letterali`, `timestamp_senza_fuso`, `v1_congelato`, `pgtap_preambolo`.

**Non provati qui, restano a Tid:** le tre preConditions **sui dati** di dbdev (`-11`, `-12`, `-14`:
come `zeroerp` lo schema `vendite` di dbdev non si legge; sullo scratch danno zero); il loader dei
CSV e il resync delle sequenze; la corsa come app; le suite dell'offerta che sullo scratch vanno in
errore di fixture già prima (`test_fn_crea_revisione_offerta`, `test_fn_push_offerta_a_contratto`,
`test_push_offerta_fissa_qta_operativa`, `test_offerte_commerciali_end_to_end`): non nominano i
componenti, ma le verifica solo la corsa su dbdev.

### 10.7 Lato BE/FE, a secondo giro DB applicato

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-8** | ⛔ **Primo passo**: il seed della lista 106 accende tre test Django che leggono il catalogo — `test_lista_proiezione_campo_sorgente` (`_ESERCIZI`: ogni lista senza vista vuole il suo esercizio), `test_ricerca_full_seed` (la lista ricercabile dichiarata), `test_perimetro_emittente_copertura` (la view o un'esenzione). Sono rossi finché c'è il seed e non l'endpoint: fanno parte del giro di §8.1 (`OffertaRigheListaRepository` + view `…/righe/lista/` ed export) | BE |
| **R-BE-9** | `scripts/gen_seed_lista.py`: la riga `vendite.offerta_righe` nella mappa delle whitelist (repository + costante dell'ordinamento), come per la 103 | BE |
| **R-FE-1** | Le sette chiavi i18n del §10.2 (it, en) | FE |
| **R-BE-10** | Rigenerare le policy degli errori: cambiano le note di `E_RIGA_DOC_NON_BOZZA`, `E_DOC_RIGHE_LOCK_MONTAGGIO`, `E_DOC_TIPO_NON_GESTITO`. Nessun codice nuovo | BE |
| **R-BE-11** | Un componente di contratto o di offerta fuori bozza è rifiutato dal DB (`E_RIGA_DOC_NON_BOZZA`, `CONFLITTO_STATO`, già in policy) col nome del documento. Se un drawer propone azioni sui componenti di un documento non in bozza, vanno spente come quelle delle righe | BE + FE |
| **R-BE-12** | `contratti_righe.attivo` e `meta`: un `null` **esplicito** è ora rifiutato (`23502`), come sull'offerta. `ContrattiRepository.create_riga`/`update_riga` li hanno nell'allowlist: non vanno inoltrati a `null` | BE |
| — | Nessuna ricaduta per B1 (la revisione) e per i tipi di B2: il BE legge i valori, non le scale | — |

### 10.8 Trovato nel giro, non corretto qui

* 🟡 **`fn_crea_revisione_preventivo` copia solo i componenti attivi**, e rimappa le righe con un
  `ROW_NUMBER` che si affida all'ordine di assegnazione degli id. La revisione dell'offerta ora fa
  diversamente su entrambi i punti (§10.3). Da allineare quando si tocca il preventivo, con una
  decisione su cosa significhi un componente spento in una revisione.
* 🟡 **`user_update` nullable su tutte le righe e i componenti di documento** tranne il componente
  dell'offerta: le linee guida (§7) lo vogliono `NOT NULL`. Debito della famiglia, scritto qui
  perché il test 4 lo pinna come asimmetria dichiarata.
* 🟡 **I componenti di preventivo, ordine e DDT non hanno il lock «solo in bozza»**. Il livello RIGA
  del building block li rende un `CREATE TRIGGER` ciascuno; per il preventivo vale la cautela già
  scritta per le sue righe (il flusso di approvazione dei prezzi va censito prima).
* 🟡 `chk_contrighe_comp_quantita_pos` si chiama «positiva» ma vieta solo lo zero (come il gemello
  `chk_oce_comp_quantita_nz`): il nome mente sulla regola.

## 11. Consegna BE/FE, secondo giro (2026-10-05)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-05, a secondo giro DB applicato.
> Due decisioni di Tid nel giro (§11.2).

### 11.1 Che cosa è stato fatto

| # | Fatto |
| --- | --- |
| R-BE-8 | **L'endpoint della lista 106.** `OffertaRigheListaRepository` (`RigheListaMixin` su `vendite.fn_offerta_righe_preview`, gemello di quello del contratto: ordine di partenza `articolo_codice`, chiave `riga_key`, niente filtro `attivo`), `OfferteService.list_righe_pagina` («leggi prima la testata», BB `pagina_dopo_testata`), view `GET offerte/<id>/righe/lista/` ed `export/` dal factory `build_lista_figlia_views` (permesso `offerta_commerciale`, cancello di perimetro sulla PK dell'emittente). I tre test di catalogo accesi dal seed (`test_lista_proiezione_campo_sorgente`, `test_ricerca_full_seed`, `test_perimetro_emittente_copertura`) sono verdi, con `test_liste_configurabili_seed` e `test_ricerca_full_db` |
| R-BE-9 | `scripts/gen_seed_lista.py`: `vendite.offerta_righe` → `_ORDER_COLS_RIGHE_OFFERTA` (`--verifica-ordinamento`: ok) |
| R-FE-1 | Le sette chiavi `vendite.offerte.col_*` (it, en). `check_i18n_keys`: pulito |
| R-BE-10 | Policy rigenerate: cambiano esattamente le note di `E_RIGA_DOC_NON_BOZZA`, `E_DOC_RIGHE_LOCK_MONTAGGIO`, `E_DOC_TIPO_NON_GESTITO` |
| R-BE-11 | Componenti fuori bozza spenti: il drawer delle righe è in sola lettura fuori bozza, sul contratto e sull'offerta (pannello componenti compreso). ⚠️ **Trovato nel giro e chiuso**: sul contratto il blocco arrivava solo dalla catena readonly di `ContrattoDrawer`; la lista dei contratti e il drawer del cliente aprono le righe direttamente, e su un contratto ATTIVO lasciavano verbi, form e componenti accesi (poi il rifiuto del DB). Ora il blocco lo dice l'involucro, chiunque lo monti, dalla **capability del DB** (`can_edit_righe` del contratto, `can_edit_eccezioni` dell'offerta, lette dal dettaglio dai quattro chiamanti), non dallo stato riletto nel frontend. Capability assente = bloccato, sui due documenti (verifica critica 2026-10-05) |
| R-BE-12 | Nessun cambio di codice: il mapper della riga del contratto già non inoltra `attivo: null` e porta `meta: null` a `{}`. Ora un test lo fissa (`ContrattiRigaAttivoMetaNotNullTests`) |
| R-BE-5, R-BE-7 | **Il drawer dell'offerta sui verbi del DB** (§11.2 per la forma): righe del listino con l'overlay delle eccezioni, «Escludi» one-click e vuoto sulla riga del listino, spento col motivo (`escludi_blocco_codice`, es. il componente di un bundle), «Ripristina articolo», «Ripristina prezzo di listino», «Rimuovi», ricerca, export, colonne personalizzabili. Chiude il transitorio del §9: l'esclusione non nasce più dal form e non si apre più in sola lettura |

### 11.2 Le due decisioni di Tid (2026-10-05)

* **Regola del 2 — nasce un BB.** Con la lista 106 il drawer dell'offerta sarebbe stato la seconda
  copia di `ContrattoRigheDrawer`. Nasce `vendite/_shared/righe/RigheEccezioniDrawer.vue` dal corpo
  vivo del contratto; `ContrattoRigheDrawer` (stessa interfaccia: tre chiamanti invariati) e
  `OffertaRigheDrawer` (ex `OffertaEccezioniDrawer`) sono involucri che passano store, scritture, API
  dei componenti, intestazione e blocco di stato; il contesto pricing resta del solo contratto (slot
  `#avvisi`). Registrato nel catalogo BB FE. Sull'offerta escono la `DataTable` in memoria, il tipo di
  eccezione in tendina, l'esclusione nel form e il loro avviso transitorio.
* **Niente toggle «attivo» sull'offerta.** La lista legge le sole eccezioni attive (come quella del
  contratto): un'eccezione spenta dal form sarebbe sparita senza modo di riaccenderla. Un'eccezione
  c'è o si toglie, come sul contratto; la colonna resta a DB col suo default.

⭐ **I testi del BB, due sedi.** Il vocabolario delle righe (origini, tipi, fonti, motivi di
«Escludi», etichette dei campi) resta in `vendite.contratti.*` e vale per i due documenti, come i codici
`E_CONTRATTO_*` riusati dal DB; i soli testi che **nominano il documento** («Rimuovi dall'offerta»)
passano dal namespace del dominio. Quella chiave è costruita, quindi `check_i18n_keys` non la vede: la
presidia `RigheEccezioniDrawer.spec.js`, che legge le chiavi dal sorgente e le cerca nei due
namespace e nelle due lingue. Nuove in `vendite.offerte`: `drawer_righe_titolo`, `gestisci_righe`,
`aggiungi_articolo_tooltip`, `articolo_escluso`, `azione_rimuovi_aggiunta`,
`azione_ripristina_articolo`, `escludi_dialog_titolo`, `ripristina_articolo_dialog_titolo`,
`ripristina_articolo_dialog_messaggio`, `field_qta_operativa_fissa`; `errore_generico` dice «riga»,
non più «eccezione».

### 11.3 Test

* **Le gemelle girano gli stessi test**, non due copie: `test_righe_contratto_offerta_lista` (ex
  `test_righe_contratto_lista`, SQL della pagina) e `test_righe_lista_contratto_offerta_api` (ex
  `test_contratto_righe_lista_api`, view ed export) hanno una classe base e un caso per documento;
  l'offerta entra in `test_righe_pagina_dopo_testata` (sette documenti) e in
  `test_ricerca_liste_db` (DB vero: la riga del listino `L:<articolo>:<uom>`, l'altra gamba della
  funzione rispetto all'aggiunta del contratto).
* FE: `RigheEccezioniDrawer.spec.js` (3); il registro delle `DataTable` grezze scende di una.

Verifica: vedi §11.5.

### 11.4 Da decidere

* **Archiviare il brief.** §6 e §10.7 sono chiusi. Restano i trovati del team DB, che non sono del
  BE/FE e senza una sede si perderebbero con l'archiviazione: §10.8 (revisione del preventivo,
  `user_update` nullable, componenti di preventivo/ordine/DDT senza lock, il nome di
  `chk_contrighe_comp_quantita_pos`).
* ✅ **Chiavi `vendite.offerte` senza lettore: tolte** (ok di Tid, 2026-10-05). 31 rimaste orfane col
  vecchio drawer (`eccezioni_titolo`, `gestisci_eccezioni`, `eccezione_*`, `field_*` e `col_*` della
  vecchia tabella, `tipo_erogazione_*`, `richiedi_approvazione*`, `esclusione_non_modificabile`…) e 5
  gia' morte prima (`tab_eccezioni`, `eccezioni_intro`, `eccezioni_empty`,
  `emissione_warn_versione_mancante`, `push_conferma`). ⚠️ Restano `azione_*`, `push_reason.*` e
  `azione_reason`: il frontend non le scrive per esteso, ma le restituisce il DB (azioni disponibili
  e motivi di blocco dell'offerta).
* `GET offerte/<id>/eccezioni/` non ha più un consumatore nel frontend (il dettaglio porta già le
  eccezioni): resta come API.


### 11.5 Verifica (2026-10-05)

* BE: `apps.vendite`, `apps.core`, `apps.ui` con `ZEROERP_TEST_DB_E2E=1` sul DB di sviluppo, in
  sequenza: **4135 test, OK** (1 skip). ⚠️ Una prima corsa con `--parallel 4` si è fermata nel runner
  («cannot pickle 'traceback'»: un errore di un test non serializzabile fra i processi) senza dire
  quale; in sequenza tutto verde. Non indagato oltre.
* `ruff` pulito sui file toccati; `manage.py check` pulito.
* FE: vitest **681/681**; eslint e build puliti; `check_i18n_keys` pulito; tutti i guard
  `npm run guard:*` verdi (il registro delle `DataTable` grezze riscritto: una in meno).
* Non provato: il drawer a video (collaudo di Tid).
