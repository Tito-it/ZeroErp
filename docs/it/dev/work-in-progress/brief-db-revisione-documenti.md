# Brief DB — Revisione dello schema `documenti`: la documentazione, i difetti di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-14

**Riparte: Tid**, col via al giro 1 e il range dei numeri. Il giro 0 (la documentazione) è fatto; i difetti sono
censiti; le dodici decisioni sono prese (2026-11-14). **Nessun giro di sviluppo è iniziato**: nessun changeSet, nessun
pgTAP scritto.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Giro 0: le 36 pagine `manual/` allo standard (31 riscritte, 5 nuove), la guida `documenti-e-stampe` riallineata | §8 | — |
| 2 | ✅ sessione DB | Censimento in sola lettura: difetti, metadati, pgTAP, ricadute BE | §3-§6 | — |
| 3 | ✅ Tid | Le decisioni Q1-Q12 | §7 | 2 |
| 4 | ✅ Tid | Doc auto-generata rigenerata: le 5 pagine nuove sono nelle schede, l'indice ha le descrizioni nuove (verificato il 2026-11-14) | §8.3 | 1 |
| 5 | Tid | Lanciare a mano su dbdev lo script di Q11 (quando vuole: non dipende dai giri) | [sql-una-tantum-storicizza-documenti-dbdev.sql](sql-una-tantum-storicizza-documenti-dbdev.sql) | 3 |
| 6 | ✅ team BE | BE1, subito: il testo dell'overlap delle versioni è stantio — riscritto il 2026-11-15 | §6 | — |
| 7 | Tid | Il via al giro 1, col range dei numeri | §2 | 3 |
| 8 | sessione DB | Giri 1-5, uno alla volta: changeSet, pgTAP, COMMENT, pagine `manual/`; l'apply è di Tid | §2 | 7 |
| 9 | team BE | Le altre ricadute di §6, quando il giro DB corrispondente è applicato | §6 | 8 |

**Decisioni aperte di Tid:** nessuna. **Da committare:** il giro 0 (36 pagine `manual/`, la guida, la doc
auto-generata dello schema), questo brief, lo script di Q11, la riga di `.codex/PROJECT_CONTEXT.md`. **Segnalazione fuori perimetro**, da decidere se e dove: §9.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-14. **A chi:** Tid e team DB.
> **Origine:** revisione della documentazione dello schema `documenti` chiesta da Tid: allinearla allo standard e
> alle funzionalità, togliere le parti stantie, elencare ciò che non è fatto. Metodo dei brief di revisione di
> `catalogo` e `dbops`.
> **Brief vicini verificati:** nessun brief aperto ha per tema gli oggetti di `documenti`.
> [brief-db-stati-documento-dal-vocabolario](brief-db-stati-documento-dal-vocabolario.md) ha toccato le versioni dei
> template il 2026-11-14 (stampabilità dalla validità, obsolete immutabili): è applicato, e le pagine descrivono lo
> stato dopo quel giro. Nel [registro dei residui](registro-residui-aperti.md) stanno già quattro voci dello schema,
> che qui non si ricopiano (§3.5).

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/documenti/…`), fresca al
2026-11-14: rigenerata dopo l'ultimo changeSet dello schema (`20261114-04`). Prima di scrivere un giro si riverifica:
un changeSet successivo sull'oggetto la rende stantia.

## 1. Il perimetro

Lo schema `documenti`: 13 tabelle (sette vocabolari, i modelli con versioni e asset, le stampe con file ed eventi),
3 viste, 20 funzioni (7 funzioni e 13 trigger function). Si contano anche i trigger generici montati sulle tabelle
dello schema (regola ATTIVO, lock, storico) e i difetti di altri schemi trovati leggendo i chiamanti.

Ogni difetto si regge sul modello: che cosa ammettono colonne, vincoli e corpi. Nessun conteggio di righe entra come
motivo; dove compare un numero, è un fatto datato al 2026-11-14.

## 2. Il piano: i giri, nell'ordine in cui si fanno

✅ **Ordine deciso da Tid il 2026-11-14 (Q12).** Per gravità; i lavori sugli stessi oggetti vanno insieme, così ogni
tabella si apre una volta sola. Ogni giro comprende changeSet, pgTAP del presidio (che costruisce i propri soggetti),
COMMENT e pagine `manual/` riallineati; poi l'apply di Tid e il via al giro dopo.

| Giro | Classe | Contenuto | Ricadute BE/FE | Perché insieme |
| --- | --- | --- | --- | --- |
| 1 | A + B + C | **Le stampe sono storia.** D1 + D8 (eccezioni ATTIVO), D2 (coerenza solo alla nascita), D10 + D20 (PDF obbligatorio e non cancellabile), D12 (`id` nello snapshot), D7 + D11 (ritiro di stati ed evento senza scrittore), D18 (il BB «rifiuta sempre» in `script`, con il ritiro di tutte le copie, anche fuori schema) | BE3, BE7 | Le tre tabelle della stampa, la regola ATTIVO verso di esse, i «rifiuta sempre»: il trigger del file (D20) nasce già sul BB |
| 2 | B + C | **I vocabolari.** Sola lettura per l'app (Q10), i formati di file nel DB e `ALTRO` ritirato (D15), una forma sola (D16) | BE5 | Le sette tabelle di lookup |
| 3 | B | **La pubblicazione.** Fuori bozza solo da «Pubblica» (D3), niente pubblicazione di una bozza spenta (D4), i controlli della copia (D13) | BE4 | `fn_pubblica_template_documento_versione`, `protect_pubblicata`, `fn_crea_bozza_da_versione` |
| 4 | B + C | **Risoluzione, scarto, asset.** Lo stato `STANDARD_NON_STAMPA` (D5), il «?» nel messaggio (D9), «asset utilizzabile oggi» nel DB (D19) | BE6, BE6-bis | Le viste della risoluzione e dello scarto, `template_asset` |
| 5 | C | **Pulizia.** I metadati di §4 e i codici errore di §3.4, i pgTAP deboli di §5 | BE2 (e BE1, se non già fatto) | Quello che nessun giro precedente ha già aperto |

Fuori dai giri: lo script di Q11 (§3.6), a mano su dbdev. Chiusi senza modifiche: D6, D14, D17 (§3.3).

## 3. I difetti di codice

Forma compatta: **fatto** · **correzione decisa** · **presidio**. Le classi sono quelle del brief `dbops`:

* **A**: contraddice un contratto deciso, oppure è sbagliato ogni volta che il ramo si percorre;
* **B**: un caso che il modello ammette e che non è gestito;
* **C**: pulizia, doppie sedi.

| Classe | Difetti aperti | Chiusi senza modifiche |
| --- | --- | --- |
| **A** | D1 | — |
| **B** | D2, D3, D4, D5, D7, D8, D9, D10, D20 | D6 |
| **C** | D11, D12, D13, D15, D16, D18, D19 | D14, D17 |

### 3.1 Classe A

**D1 — Una stampa tiene acceso per sempre ciò che cita** · giro 1 · Q1. Trovato da tutte e tre le aree, da tre lati.

* **Fatto.** `documenti_generati` e `documenti_generati_file` non hanno `attivo`, e
  `dbops.trgfn_prevent_deactivate_if_children` conta ogni riga di una figlia senza `attivo`. Nessuna FK delle due
  tabelle è in `dbops.automazione_attivo_eccezioni`, e una stampa non si cancella. Quindi un modello, una versione, un
  tipo di documento, una sorgente o un'azienda con una sola stampa non si spengono più; lo stesso vale per un tipo di
  file con un solo file. Il rifiuto `E_ATTIVO_BLOCK_CHILDREN_EXIST` indica un rimedio impossibile, mentre la
  risoluzione tratta «modello spento» come uno stato normale (`MODELLO_SPENTO`) e la guida dice «spegnere tutti i
  propri modelli di un tipo riporta allo standard». I controlli dal lato della stampa scattano solo alla nascita: la
  stampa non ha bisogno che il padre resti acceso.
* **Correzione decisa.** Le FK della stampa (`template_documento_id`, `template_versione_id`,
  `tipo_documento_output_id`, `sorgente_tipo_id`, `emittente_fiscale_id`) e `documenti_generati_file.file_tipo_id` in
  `automazione_attivo_eccezioni`, con il motivo «una stampa è storia, non un figlio vivo». È la forma di
  `vendite.fatture_stampa_coda.tipo_documento_output_id`, già lì, e della Q31 di `catalogo`.
* **Presidio.** pgTAP che costruisce un modello d'azienda, una stampa e il suo file, poi spegne modello, versione, tipo,
  tipo di file e azienda (`lives_ok`), e verifica che la risoluzione ripieghi sullo standard.

### 3.2 Classe B

**D2 — `check_coerenza` rilegge il modello di oggi anche sull'UPDATE della stampa** · giro 1 · Q2.
Il trigger è `INSERT OR UPDATE` e rilegge sorgente, tipo e azienda del modello come sono adesso; del modello è
bloccata solo `standard`. Se una di queste cambia dopo la stampa, ogni UPDATE della stampa vecchia (anche di `meta`)
dà `E_DOCUMENTI_GENERATO_COERENZA`. · Il trigger solo all'INSERT: sull'UPDATE quei campi li tiene fermi
`protect_snapshot`. Nessun lock sul modello. · pgTAP: modello cambiato dopo la stampa, poi UPDATE di `meta`.

**D3 — Si pubblica senza passare dalla pubblicazione** · giro 3 · Q3.
`protect_pubblicata` guarda solo `OLD.stato`. Un UPDATE BOZZA → PUBBLICATA/OBSOLETA, o un INSERT che nasce fuori
bozza, salta il controllo della forma dei dati e la chiusura della precedente (resta il vincolo di non
sovrapposizione). In più `chk_template_documenti_versioni_valido_dal_pubblicata` pretende `valido_dal` solo dalla
PUBBLICATA: una OBSOLETA inserita senza inizio vale da `-infinity`. · Uno stato fuori bozza si scrive solo da
`fn_pubblica_template_documento_versione` (la porta che la funzione apre già per la chiusura vale anche per la
pubblicazione); il seed dello standard, scritto dall'owner, passa. Il CHECK diventa su `stato <> 'BOZZA'`. · pgTAP come
app: UPDATE di una bozza a PUBBLICATA e INSERT di una PUBBLICATA rifiutati; OBSOLETA senza `valido_dal` rifiutata.

**D4 — Pubblicare una bozza spenta lascia il modello senza stampa** · giro 3.
`fn_pubblica_template_documento_versione` non guarda `attivo` della bozza: pubblica una versione che non stampa e
chiude quella attiva. Da `p_valido_dal` il modello non stampa più. · Rifiuto con un codice nuovo. · pgTAP: bozza
spenta e pubblicata attiva; rifiuto, la pubblicata intatta.

**D5 — La copia sparisce dallo scarto quando lo standard d'origine non stampa** · giro 4 · Q4.
In `vw_template_personalizzati_scarto` lo standard di riferimento entra con un join interno su
`vw_template_versioni_stampabili`. Uno standard d'origine spento o senza versione valida toglie la copia dalla vista, e
la lista la mostra senza stato. Lo stesso per una copia senza origine, se la coppia non ha uno standard predefinito che
stampa. · Lo stato esplicito `STANDARD_NON_STAMPA`; la copia resta in vista. Scartato il ripiego sul predefinito: può
essere uno standard diverso da quello copiato. · pgTAP: lo standard d'origine spento, la riga attesa con lo stato
nuovo.

**D7 — Lo stato della stampa non ha un verbo né una regola dei passaggi** · giro 1 · Q6.
Il CHECK ammette `GENERATO`, `ARCHIVIATO`, `ANNULLATO`; nessuna funzione DB e nessun servizio scrivono gli ultimi due,
e un UPDATE diretto riporta una stampa `ANNULLATO` a `GENERATO`. Lo stato lo legge solo il badge del FE. · Ritiro di
`ARCHIVIATO` e `ANNULLATO`: la colonna resta col solo `GENERATO`. L'annullo di una stampa, quando un processo lo
chiederà, nasce col suo verbo. · pgTAP: uno stato ritirato rifiutato.

**D8 — Una versione standard da cui deriva una copia non si spegne** · giro 1 · Q1.
La regola ATTIVO su `derivata_da_versione_id` (BLOCK e REQUIRE) tratta l'origine come figlio vivo: una versione
standard vecchia non si ritira finché una copia ne deriva. Riguarda solo l'owner. · `derivata_da_versione_id` in
`automazione_attivo_eccezioni`, con D1. · pgTAP: lo spegnimento dell'origine riesce.

**D9 — Il messaggio di «nessun modello» dice «?» come documento** · giro 4.
`fn_risolvi_template_applicabile`, con il tipo omesso su una sorgente senza modelli stampabili, solleva
`E_DOCUMENTI_TEMPLATE_NON_RISOLTO` col nome del documento a «?». · La descrizione della sorgente quando il tipo non
c'è. · pgTAP sul messaggio.

**D10 — Una stampa senza file principale** · giro 1 · Q7.
Il DB non chiede che una stampa abbia il suo file principale: lo garantisce il servizio, scrivendoli nella stessa
transazione. «Al più uno» c'è già (`uq_documenti_generati_file_principale`, parziale); «almeno uno» no. · Un
constraint trigger differito: a fine transazione ogni stampa ha il suo principale. Col `DELETE` del file bloccato
(D20) basta il controllo alla nascita della stampa. · pgTAP: una stampa senza file rifiutata al commit.

**D20 — Il file di una stampa si cancella** · giro 1 · Q7. Trovato il 2026-11-14, durante le domande.
`documenti_generati_file` non ha un trigger sul `DELETE`, a differenza della stampa e degli eventi; `zeroerp_app` ha il
privilegio e la policy RLS è `ALL`. Cancellando la riga del PDF principale la stampa perde il suo file: download e
ristampa non lo ritrovano, e l'hash conservato non verifica più niente. `protect_file` copre solo l'UPDATE. Nessun
servizio oggi cancella un file. · Un trigger sul `DELETE` che rifiuta sempre, montato sul BB di D18. · pgTAP come app:
DELETE di un file rifiutato.

### 3.3 Chiusi senza modifiche

| # | Che cosa | Perché si chiude |
| --- | --- | --- |
| D6 | Un logo nuovo è un asset nuovo con un codice nuovo, e una versione nuova di ogni modello che lo cita | Q5: è la regola voluta. Conferma la decisione del 2026-10-01 (`work-done/brief-be-documenti-risorse-esterne-render-pdf.md` §4.6): lo stesso `codice_interno` indica sempre gli stessi byte, ed è ciò su cui si regge la ristampa fedele. La pagina `template_asset` e la guida §2.4 la scrivono come regola |
| D14 | I motori di render stanno nel vocabolario e in `_ENGINE_WHITELIST` del servizio di render | Q8a: è il progetto (`work-done/sviluppo-documenti.md` §5.5, 2026-04-29): un motore è codice, e una riga non installa un programma. Il buco vero (l'app aggiunge una riga che il codice non sa usare) lo chiude la Q10, nel giro 2 |
| D17 | `protect_snapshot` e `protect_file` sembrano copie di `automation_lock_columns` | Q9a: non lo sono. `script.trgfn_lock_columns` ha la porta `zeroerp.allow_lock_columns_override`, che ogni sessione può aprire; la prova d'audit di una stampa è «mai». Significato diverso. Resta D12 |

### 3.4 Classe C — pulizia, doppie sedi, codici

| # | Giro | Dove | Fatto | Correzione decisa |
| --- | --- | --- | --- | --- |
| D11 | 1 | `documenti_generati_eventi` | `STORAGE_ORPHAN` è nel CHECK, ma il file orfano nasce proprio quando la stampa non esiste, e `documento_generato_id` è NOT NULL: nessuno lo può scrivere (il BE lo sa e lo mette nel log) | Ritiro dal CHECK (Q6) |
| D12 | 1 | `trgfn_documenti_generati_protect_snapshot` | Non confronta `id`: su una stampa senza figli il cambio passa | `id` nel confronto; il trigger resta proprio (Q9a) |
| D13 | 3 | `fn_crea_bozza_da_versione` | Senza origine dichiarata non verifica che origine e destinazione abbiano lo stesso tipo e la stessa sorgente (lo garantisce il servizio); il numero `max+1` concorrente arriva come 23505 grezzo | Il controllo nel verbo; il conflitto con un codice suo |
| D15 | 2 | `tipi_asset_documento` | I formati ammessi per tipo stanno solo nel servizio degli asset; `ALTRO` è attivo nel seed, ma ogni caricamento è rifiutato. `meta` dei quattro lookup storici non ha lettori | Q8b: ogni tipo dichiara i suoi formati nel vocabolario, il DB controlla il `mime_type` dichiarato alla scrittura dell'asset, il BE legge la lista da lì e continua a controllare i byte; `ALTRO` ritirato; `meta` dei lookup che restano senza lettori ritirato |
| D16 | 2 | sette vocabolari | Due forme: i quattro lookup storici senza `etichetta_key` né `ordine`, i tre della versione senza `attivo` né il CHECK sulla descrizione; «fattura vendita» minuscola | Una forma sola |
| D18 | 1 | i quattro «rifiuta sempre» di `documenti` (`block_delete` di stampa e asset; `block_delete` e `block_update` degli eventi) | La stessa funzione con codice e contesto diversi. `script.trgfn_delete_block_by_guc` ha un bypass da GUC: semantica diversa. `trgfn_template_documenti_versioni_block_delete` è condizionato: non è una copia | Q9b: BB «rifiuta sempre» in `script`, che riceve il codice. Nello stesso giro si ritirano le quattro copie e quelle fuori schema che, lette una per una, dicono la stessa cosa (candidati: `vendite.trgfn_event_log_append_only`, `anagrafiche.trgfn_stiva_movimenti_append_only`); ok cross-dominio di Tid. Il trigger del file (D20) nasce sul BB |
| D19 | 4 | asset | «Asset attivo e valido oggi» vive solo nel BE (`_ASSET_UTILIZZABILE_OGGI`), con due lettori (render e lista): una regola senza sede DB | Una vista o una funzione di `documenti`, letta dal BE |

**Codici errore** (giro 5, salvo dove un giro prima apre il codice). `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` è in
inglese, accanto a `E_EVENTO_DOCUMENTO_*_VIETATA`: due prefissi e due lingue per la stessa famiglia.
`E_DOCUMENTI_VERSIONE_OVERLAP` lo emette solo il BE, traducendo il vincolo per nome.
`E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` vale ora anche per l'OBSOLETA e per l'origine di una copia, e il testo
dice «pubblicata». Le classi sono tutte coerenti.

**Che cosa si ritira** (riepilogo): `STORAGE_ORPHAN` (D11), `ARCHIVIATO` e `ANNULLATO` (D7), `ALTRO` e i `meta` senza
lettori (D15), le quattro copie del «rifiuta sempre» (D18). Il secondo ramo di `block_delete` delle versioni ripete la
FK RESTRICT verso la stampa: è voluto (dà il codice parlante), e resta.

### 3.5 Già nel registro dei residui (non si ricopiano)

* **Residui di `brief-db-modelli-documento-standard`**: la numerazione della versione nuova in due sedi (servizio e
  `fn_crea_bozza_da_versione`).
* **Le variabili di una versione di template non si validano alla pubblicazione** (`context_schema` mai letto).
* **Le versioni pubblicate stampano coi margini delle colonne (15 mm)**.
* **`HTML_MARKDOWN_BLOCKS` si sceglie ma non fa niente**: confermato, il render non legge `formato_template`.

### 3.6 Un fatto di macchina, non un difetto di codice

Fatto datato (dbdev, 2026-11-14). Le sette tabelle di `documenti` registrate in `config.storico_set_storicizza`
(i quattro lookup storici, modelli, versioni, asset) hanno su dbdev righe con `storicizza = false`: nei lookup tutte
tranne `FATTURA_VENDITA`, contro il `true` dei CSV; in modelli, versioni e asset quelle nate prima del default.
`maintenance.fn_apply_storicizza_defaults` cambia il `DEFAULT` della colonna, non le righe esistenti. Su un'installazione
nuova il caso non c'è. ✅ Q11: correzione a mano su dbdev, nessun changeSet. Lo script è
[sql-una-tantum-storicizza-documenti-dbdev.sql](sql-una-tantum-storicizza-documenti-dbdev.sql): una transazione,
conteggi prima e dopo, lo lancia Tid come owner. Tocca anche le date d'audit delle righe. Altri schemi non guardati.

## 4. I metadati

Nessuno cambia il comportamento; ognuno dice il falso o cronaca a chi legge. Si correggono nel giro che apre
l'oggetto, il resto nel giro 5. Il COMMENT si riscrive intero, secondo `linee-guida-sql.md` §5d.

### 4.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `documenti_generati_eventi` | «Eventi v1: GENERATO, SCARICATO, STORAGE_ORPHAN»: mancano `ALLEGATO_AGGIUNTO` e `RISTAMPA_FEDELE` (e `STORAGE_ORPHAN` esce col giro 1) |
| M2 | COMMENT `documenti_generati_file`, colonna `is_principale` | «In Fase A un solo PDF_FINALE»: esiste `ALLEGATO`, e gli allegati si aggiungono dopo |
| M3 | corpo di `trgfn_template_asset_block_delete` | «documenti generati che referenziano via template_asset_id»: nessuna colonna punta a `template_asset` |
| M4 | corpo di `trgfn_template_asset_protect_file` | «Campi modificabili: meta, validita»: sono liberi anche `descrizione`, `codice`, `attivo` |
| M5 | messaggio di `E_DOCUMENTI_ASSET_DELETE_BLOCKED` | «gli asset sono immutabili una volta creati»: è immutabile il file |
| M6 | descrizioni di `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE`, `_NON_RISOLTO`, `_SENZA_PREDEFINITO` | «versione PUBBLICATA»: stampa anche l'OBSOLETA nella sua validità |
| M7 | nota di `E_EVENTO_DOCUMENTO_DELETE_VIETATA` | Nomina `trgfn_documenti_generati_eventi_a10_*`, che non esiste |

### 4.2 Senza COMMENT

* Quasi tutte le colonne delle tabelle dello schema: `documenti_generati` (tranne le `sorgente_*` e il progressivo),
  `documenti_generati_eventi`, `documenti_generati_file` (tranne `is_principale`), `template_asset` (tranne
  `validita`), gran parte di `template_documenti` e `template_documenti_versioni`; tutte le colonne dei quattro lookup
  storici; `id`, `codice`, `descrizione` e l'audit dei tre vocabolari della versione.
* Tutte le colonne delle tre viste.
* CHECK, UNIQUE e FK, tranne una decina.
* I trigger propri dello schema, tranne `trg_documenti_generati_a10_guard_sorgente_ins_upd`.
* I COMMENT di tabella dei quattro lookup storici sono di una riga e generici.

### 4.3 Marcatori, nomi di brief, id

* **Funzioni:** `fn_guard_versione_contesto` («D-C4», brief), `fn_risolvi_template_applicabile`,
  `fn_template_esito_risoluzione`, `fn_template_motivo_non_coerente`, `fn_crea_bozza_da_versione`,
  `fn_personalizza_template_standard` («D-2, D-6, D-9»); le trigger function con «Guard A1 … A7-bis»
  (`block_delete` di stampa, asset e versioni, `protect_snapshot`, `protect_file`, `protect_pubblicata`),
  `check_coerenza` («Guard A6», «rev 2026-10-21», id di changeSet, brief), `guard_versione_contesto`,
  `guard_derivata_da`, `template_standard_guard_sola_lettura`.
* **Viste:** `vw_template_risoluzione_emittente`, `vw_template_personalizzati_scarto` («rev 2026-10-21», id, brief).
* **Tabelle, colonne, vincoli:** `formati_pagina`, `formati_template`, `orientamenti_pagina` (brief);
  `template_documenti.standard`; `template_documenti_versioni.formato_template`, `page_format`, `page_orientation`,
  `versione_contesto`, `derivata_da_versione_id`; `validita` di `template_asset` e delle versioni («rev 2026-05-14»);
  `documenti_generati_eventi.evento_tipo` (date di nascita dei valori);
  `chk_template_documenti_standard_senza_emittente`, `uq_template_documenti_id_tipo_sorgente`.
* **Cronaca nei corpi:** `check_coerenza`, `fn_guard_versione_contesto`, `protect_file` («per futuro Fase B»),
  `fn_risolvi_template_applicabile` («rev 20261021-09», «§10.3 K-2»), le due funzioni di personalizzazione. Si
  toccano solo se un giro riscrive comunque la funzione: non si apre un `CREATE OR REPLACE` per un commento.
* **`config.codici_errore`:** le descrizioni dei sei codici della risoluzione, `E_DOCUMENTI_GENERATO_DELETE_BLOCKED`
  (id di changeSet), `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` e `_NON_VERIFICABILE` (brief). Finiscono nei commenti
  di `error_policies_generated.py`: si correggono nel CSV e il BE rigenera (BE2).
* **Fuori schema:** la nota di `dbops.automazione_overlap` sulle versioni («refactor-overlap-v2 fase2», id) e quella
  di `automation_lock_columns` su `template_documenti.standard` (brief, id).

## 5. I pgTAP

Si scrivono o si correggono nel giro che apre l'oggetto; il resto nel giro 5.

* **Iterano su ciò che c'è** (verdi per sottrazione su un DB da zero): `test-documenti-generati.sql` test 4 (un altro
  emittente attivo preso dai dati, `999999` in mancanza); `test-documenti-template-asset.sql` test 3 («skip soft se
  em2 assente»); `test-documenti-template-standard-app-v1.sql` test 3-6 (skip senza seed: lo standard va costruito
  come owner prima del `SET ROLE`); `test-documenti-seed-idempotenti.sql` test 1-8 e `test-documenti-lookup.sql`
  test 14 (conteggi «>= N» e duplicati su colonne già UNIQUE).
* **Casi non costruiti:**
  * coerenza della stampa: la versione di un altro modello, il motivo `SORGENTE`;
  * `protect_snapshot`: i passaggi NULL ↔ valore su `sorgente_riga` e `generato_da_user_id`, il motivo
    dell'`IS DISTINCT FROM`; `protect_file`: oltre a `storage_key` e `is_principale`, niente;
  * asset: `mime_type`, `file_name`, `file_size_bytes`, il cambio ammesso di `codice` e delle date, il lock di
    `codice_interno`;
  * pubblicazione: `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO`, `_VERSIONE_NOT_FOUND`, `_VERSIONE_PUBBLICA_STATO_INVALIDO`,
    lo stesso `valido_dal` di una pubblicata (23P01), la retrodatazione dentro un'OBSOLETA;
  * versioni: il DELETE di un'OBSOLETA e di una bozza usata da una stampa;
  * `fn_crea_bozza_da_versione`: i rami `E_PARAMETRO_INVALIDO`;
  * `fn_template_motivo_non_coerente`: i motivi `SORGENTE` e `TIPO` provati direttamente;
  * `vw_template_risoluzione_emittente`: l'esito `NON_RISOLTO` e la parità con la stampa su quell'esito;
  * i blocchi di spegnimento dei vocabolari.
* **Header con id di changeSet e nomi di brief:** `test-documenti-versione-contesto-v1.sql`,
  `test-sorgente-documenti-generati-v1.sql`.

## 6. Ricadute su BE e FE

Da girare al team quando il giro DB corrispondente è applicato, salvo BE1.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | subito | `template_versioni_admin_service.py:108-113`: il testo dell'overlap («un'altra versione PUBBLICATA attiva … Chiudi quella esistente prima») è stantio dal 2026-11-14: contano anche le OBSOLETA, e il rimedio è una data d'inizio dopo la più recente (la precedente si chiude da sola). Il vincolo ha ancora il nome `ex_template_documenti_versioni_no_overlap_pubblicata`, quindi la traduzione aggancia; il translator preferisce `ServiceError.message`: l'utente vede il testo vecchio |
| BE3 | 1 | Con D1 chiuso, spegnere un modello che ha stampato riesce: verificare che il form non lo pre-blocchi |
| BE7 | 1 | D7/D11: gli stati e l'evento ritirati escono dal servizio (`document_generation_service.py:89` ha anche un commento «seed Fase A»; i commenti su `STORAGE_ORPHAN` a `:25`, `:420`, `:825`, `:1463`, `storage/base.py:33`, `template_asset_admin_service.py:265` diventano «file orfano, solo nel log»); il badge di `DocumentiGeneratiSorgenteList.vue:104` resta col solo `GENERATO` |
| BE5 | 2 | D15: `_MIME_WHITELIST_PER_TIPO` (`template_asset_admin_service.py:53-75`) si ritira, la lista si legge dal vocabolario dei tipi di asset; il form può mostrare i formati ammessi; `ALTRO` esce dalla tendina. `_ENGINE_WHITELIST` (`render_service.py:54`) resta |
| BE4 | 3 | D3: l'applicazione non scrive più uno stato fuori bozza: verificare che nessun servizio lo faccia fuori da `fn_pubblica_template_documento_versione` |
| BE6 | 4 | D19: `_ASSET_UTILIZZABILE_OGGI` (`documenti_repository.py:404`) legge la sede DB |
| BE6-bis | 4 | D5: lo stato nuovo `STANDARD_NON_STAMPA` della vista dello scarto, nella lista «Modelli documento» e nell'i18n |
| BE2 | 5 | `error_policies_generated.py`: rigenerare dopo la pulizia delle descrizioni (§4.3); oggi i commenti portano brief, «Fase A», id e «PUBBLICATA, attiva e valida» |
| BE8 | — | `template_service.py:36`, `_STATI_VERSIONE_VALIDI`, ricopia gli stati della versione: da verificare se serve, o se si leggono dal DB |

## 7. Le decisioni di Tid — tutte prese il 2026-11-14

| # | Domanda | Decisione | Scartato, e perché |
| --- | --- | --- | --- |
| Q1 ✅ | D1, D8: le stampe e l'origine di una copia bloccano lo spegnimento? | **(a) No: eccezioni ATTIVO.** La stampa è storia, non un figlio vivo (forma di `fatture_stampa_coda` e Q31 di `catalogo`) | (b) ritiro con `obsoleto_dal`: colonna nuova e risoluzione da riscrivere |
| Q2 ✅ | D2: il controllo di coerenza della stampa | **(a) Solo alla nascita.** Nessun lock su sorgente, tipo e azienda del modello | (b) lock del modello dopo la prima stampa: domanda di modello non necessaria, form BE da riallineare |
| Q3 ✅ | D3: chi porta una versione fuori bozza | **Solo «Pubblica»**; il seed dell'owner passa; `valido_dal` obbligatorio per ogni stato fuori bozza | Affidarsi al BE: il modello «una scrittura = un verbo» protegge da un backend che sbaglia |
| Q4 ✅ | D5: la copia il cui standard d'origine non stampa | **(a) Stato `STANDARD_NON_STAMPA`** | (b) ripiego sul predefinito: confronterebbe con uno standard diverso da quello copiato |
| Q5 ✅ | D6: il logo che cambia | **(a) Resta così**: conferma la decisione del 2026-10-01 (§4.6 del brief BE delle risorse del render) | (b) il logo che segue le date: revocava quella decisione e toccava chiave, render e ristampa |
| Q6 ✅ | D7, D11: stati e evento della stampa senza scrittore | **(a) Ritiro** di `ARCHIVIATO`, `ANNULLATO`, `STORAGE_ORPHAN`; l'annullo nascerà col suo verbo quando un processo lo chiederà | (b) verbo con la matrice adesso: nessun consumatore |
| Q7 ✅ | D10, D20: la stampa e il suo PDF | **Tutti e due**: il file non si cancella mai, e a fine transazione ogni stampa ha il suo principale | Uno solo dei due: lascia aperto l'altro buco |
| Q8 ✅ | D14, D15: sede di motori e formati | **8a: i motori restano nel codice** (progetto del 2026-04-29). **8b: i formati nel DB**, `ALTRO` ritirato; completa la decisione 67 (2026-04-29), che non ne diceva la sede | 8a nel DB: un motore è codice. 8b nel BE: è una regola di business |
| Q9 ✅ | D17, D18: le «copie» | **9a: le immutabilità della stampa restano trigger propri** (il registro ha una porta che ogni sessione apre). **9b: BB «rifiuta sempre» in `script`**, con il ritiro di tutte le copie anche fuori schema (ok cross-dominio) | 9b solo in `documenti`, o niente BB: violano la regola del 2 |
| Q10 ✅ | I sette vocabolari | **Sola lettura per l'app**, nella lista `v_tabelle_sola_lettura_app` (§11.8), come `config.aree_funzionali` (D-P9, 2026-09-28). Verificato: `lookup = true`, `pannello = false`, nessuno li scrive | Solo i tre della versione: lascia aperto il motore inesistente (Q8a) |
| Q11 ✅ | `storicizza` su dbdev | **A mano**, sulle sette tabelle registrate (esteso dalla sessione: anche modelli, versioni, asset) | Un changeSet: codice per un problema di dati |
| Q12 ✅ | L'ordine dei giri | **Come in §2**: le stampe e il BB nel giro 1 | Il BB in un giro a parte |

## 8. Giro 0 — la documentazione, 2026-11-14 (fatto)

Scritto dalla sessione DB su richiesta di Tid, con tre agenti per area (stampe; modelli, versioni e asset;
risoluzione e vocabolari). Le pagine sono lette dai corpi (`pg_get_functiondef`, `pg_get_viewdef`), da
`pg_trigger`/`pg_constraint` di dbdev, dalle schede auto-generate e dai pgTAP. Descrivono il comportamento di oggi,
difetti compresi: ognuno sta al presente in una sezione «⚠️ Che cosa oggi non copre», e si toglie quando il giro che lo
corregge è applicato.

### 8.1 Che cosa è scritto

* **Le 36 pagine `docs/it/dbzero/documenti/manual/`.** Le 31 esistenti riscritte nella cornice; sette in formato
  vecchio (titolo `#`, DDL in un blocco `sql`) rifatte da capo. Cinque nuove: `formati_pagina`, `formati_template`,
  `orientamenti_pagina`, `trgfn_template_documenti_versioni_guard_derivata_da`,
  `trgfn_template_standard_guard_sola_lettura`.
* **Dopo le decisioni:** `template_asset` scrive D6 come regola voluta; `render_engine_documento` scrive la lista dei
  motori nel codice come voluta, e fra i limiti l'app che può aggiungere un motore; `documenti_generati_file` scrive
  fra i limiti il `DELETE` ammesso (D20).
* **Nessun blocco comune.** I vocabolari sono due famiglie con regole diverse: il testo comune sarebbe un paragrafo.
* **`guide/documenti-e-stampe.md`:** §3.1 (stampa anche l'obsoleta nella sua validità); header e §12 (mancavano gli
  eventi della stampa e i tre vocabolari della versione); §2.4 (l'asset: nessun puntatore dalla stampa, il codice
  senza validità, il file immutabile); §11, due garanzie riscritte (il file di un asset non cambia; una stampa e i
  suoi eventi non si cancellano: «lo stato cambia ad archiviato o annullato» era falso).
* Le pagine `storico/manual/` delle tabelle dello schema sono un rimando alla tabella d'origine: non cambiano.

### 8.2 Le parti stantie e false tolte

* **Comuni:** etichette in grassetto senza `>`, bullet `•`, link a `manual/`, a `.md` relativi e a
  `/dev/work-done/…`; primi paragrafi `(latest review …)` che finivano nell'indice; «Fase A/B», «v1», «Guard A1 …
  A7-bis», «Decisione N», «§10.3 K-n», id di changeSet e di messaggio; firme, parametri, DDL ed esempi ricopiati
  (cinque blocchi `sql` nella pagina della pubblicazione).
* **Di contenuto:**
  * gli eventi della stampa ne elencavano tre e dicevano gli altri «non ammessi»: sono cinque;
  * un solo tipo di file, `PDF_FINALE`: esiste `ALLEGATO`;
  * un solo tipo di documento, il preventivo: sono sei;
  * `E_DOCUMENTI_GENERATO_COERENZA` come 409 (è `DATO_ERRATO`), la coerenza attribuita alla pipeline;
  * `ordinamento` del file «modificabile in Fase B»: lo è oggi;
  * l'ordine dei guard sulla stampa senza `guard_sorgente`;
  * l'asset: «validità di asset diversi nel tempo per lo stesso emittente» (la chiave non ha la validità), lo stesso
    file con due ruoli (lo vieta `uq_template_asset_emittente_sha256`), `validita` «calcolata dal trigger» (è
    generata), `codice` taciuto fra i campi liberi;
  * «vincolo EXCLUDE USING gist» sulle versioni; il clone del BE «elenca i campi da sé» (chiama
    `fn_crea_bozza_da_versione` dal 2026-10-21);
  * `meta` del motore di render come «capability» (non ha lettori); i formati MIME «policy futura» (esistono, nel BE);
  * la vista della risoluzione taceva che porta anche le aziende spente (il filtro lo mette il BE);
  * un rimedio «disabilitare il trigger con una patch ad hoc».

### 8.3 Le verifiche

Su tutte le 36 pagine passano i sei controlli di `standard-guide.md` §«Verifica di una pagina `manual/`»; in più nessun
link morto (controllato file per file), nessun blocco di codice, data al 14 novembre 2026. La build della doc non è
lanciata. La doc auto-generata è rigenerata dopo il giro 0 (verificato il 2026-11-14): le schede delle cinque tabelle
e funzioni nuove includono la loro pagina, e `documenti/index.md` ha le descrizioni nuove, senza marcatori.

## 9. Fuori perimetro — segnalazione per Tid

**La porta di `script.trgfn_lock_columns` la apre ogni sessione.** Trovato il 2026-11-14 verificando la Q9a.
`zeroerp.allow_lock_columns_override` è una variabile di sessione: chiunque la imposti a `on`, applicazione compresa,
salta ogni blocco di colonna registrato in `dbops.automation_lock_columns`, in tutti gli schemi. È nata come «uscita
dichiarata per correggere un refuso su un codice appena creato». Il modello dei permessi dichiara di proteggere da un
backend che sbaglia, non da uno manomesso: una porta aperta di proposito non è un errore del backend, ma un `SET` di
troppo in un servizio la attraversa senza rumore. Non è di `documenti`, e qui non si corregge: decide Tid se aprirne
un brief (`dbops`/`script`) o lasciarla com'è.

## 10. Alla chiusura

* Ogni pagina `manual/` toccata passa la verifica di `standard-guide.md`, con la data aggiornata, e perde la riga di
  «⚠️ Che cosa oggi non copre» del difetto chiuso.
* I pgTAP nuovi costruiscono i propri soggetti: nessuno itera su ciò che c'è.
* Il brief va in `work-done/` quando i giri sono applicati e le ricadute BE chiuse o passate a un brief BE.
