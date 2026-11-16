# Brief DB — Revisione dello schema `documenti`: la documentazione, i difetti di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-16

**Riparte: Tid**, con il commit del giro 1, la decisione Q13 (§11.4) e il via al giro 2. Il giro 1
(`20261115-82 … -90`) è applicato e i suoi pgTAP sono verdi (Tid, 2026-11-16): §11. Il team BE può partire con le
ricadute del giro 1 (§11.6). Il giro 0 (la documentazione) è fatto e committato; le dodici decisioni sono prese
(2026-11-14).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Giro 0: le 36 pagine `manual/` allo standard (31 riscritte, 5 nuove), la guida `documenti-e-stampe` riallineata | §8 | — |
| 2 | ✅ sessione DB | Censimento in sola lettura: difetti, metadati, pgTAP, ricadute BE | §3-§6 | — |
| 3 | ✅ Tid | Le decisioni Q1-Q12 | §7 | 2 |
| 4 | ✅ Tid | Doc auto-generata rigenerata: le 5 pagine nuove sono nelle schede, l'indice ha le descrizioni nuove (verificato il 2026-11-14) | §8.3 | 1 |
| 5 | Tid | Lanciare a mano su dbdev lo script di Q11 (quando vuole: non dipende dai giri) | [sql-una-tantum-storicizza-documenti-dbdev.sql](sql-una-tantum-storicizza-documenti-dbdev.sql) | 3 |
| 6 | ✅ team BE | BE1, subito: il testo dell'overlap delle versioni è stantio — riscritto il 2026-11-15 | §6 | — |
| 7 | ✅ Tid | Il via al giro 1 (2026-11-15), numeri dal primo libero | §2 | 3 |
| 8 | ✅ sessione DB | Giro 1 scritto: nove changeSet, quattro CSV, un pgTAP nuovo, nove riscritti, pagine `manual/` e guida | §11 | 7 |
| 9 | ✅ Tid | Giro 1 applicato, pgTAP verdi (2026-11-16); doc auto-generata rigenerata | §11.5 | 8 |
| 10 | Tid | Q13: la nascita di una stampa da un padre spento | §11.4 | — |
| 11 | team BE | BE3, BE7 e le nuove BE9, BE10 del giro 1 — sbloccate | §6, §11.6 | 9 ✅ |
| 12 | sessione DB | I giri 2-5, uno alla volta, col via di Tid; il prossimo è il 2 (i vocabolari) | §2 | 9 ✅, via di Tid |
| 13 | team BE | Le altre ricadute di §6, quando il giro DB corrispondente è applicato | §6 | 12 |

**Decisioni aperte di Tid:** Q13 (§11.4). **Da committare:** il giro 1 (§11.1: i changeSet, i CSV, i pgTAP, le
pagine `manual/` toccate e le cinque tolte, la guida), questo brief. **Segnalazione fuori perimetro**, da decidere se e
dove: §9.

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
| 1 ✅ applicato il 2026-11-16 (§11) | A + B + C | **Le stampe sono storia.** D1 + D8 (eccezioni ATTIVO), D2 (coerenza solo alla nascita), D10 + D20 (PDF obbligatorio e non cancellabile), D12 (`id` nello snapshot), D7 + D11 (ritiro di stati ed evento senza scrittore), D18 (il BB «rifiuta sempre» in `script`, con il ritiro di tutte le copie, anche fuori schema) | BE3, BE7 | Le tre tabelle della stampa, la regola ATTIVO verso di esse, i «rifiuta sempre»: il trigger del file (D20) nasce già sul BB |
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

⚠️ **Dal 2026-11-15 D1, D2, D7, D8, D10, D11, D12, D18, D20 sono scritti nel giro 1** (§11), non ancora applicati.
Le sezioni qui sotto restano come censimento; la correzione effettiva, con quello che è cambiato rispetto a qui
(il BB di D18 esisteva già), sta in §11.2.

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

## 11. Giro 1 — le stampe sono storia (scritto il 2026-11-15, applicato il 2026-11-16)

### 11.1 Che cosa è scritto

| ChangeSet | Che cosa | Difetti |
| --- | --- | --- |
| `20261115-82` (`20_code/script`) | `script.trgfn_prevent_modification_generic` riceve dal montaggio il codice (`TG_ARGV[0]`) e le colonne della riga per la frase (le `date` in GG/MM/AAAA); senza argomenti resta `E_TABELLA_OP_NON_CONSENTITA` | D18 |
| `-83` (`20_code/documenti`) | I quattro rifiuti di stampa, eventi e asset rimontati sul BB col loro codice; il `DELETE` del file rifiutato (`E_FILE_DOCUMENTO_DELETE_VIETATA`, nuovo); le quattro funzioni proprie ritirate | D18, D20 |
| `-84` (`20_code/anagrafiche`) | Il registro dei movimenti di plafond IVA sul BB (stesso codice, stessa frase); `anagrafiche.trgfn_stiva_movimenti_append_only` ritirata | D18 |
| `-85` (`00_schema/documenti`) | `chk_documenti_generati_stato` solo `GENERATO`; `STORAGE_ORPHAN` fuori dal CHECK degli eventi; COMMENT di stato, eventi e file al presente | D7, D11, M1, M2 |
| `-86` (`20_code/documenti`) | `check_coerenza` solo `BEFORE INSERT` (trigger `…_check_coerenza_ins`); COMMENT al presente | D2 |
| `-87` (`20_code/documenti`) | `protect_snapshot` confronta anche `id`; COMMENT al presente | D12 |
| `-88` (`20_code/documenti`) | `trgfn_documenti_generati_guard_file_principale`, constraint trigger differito `AFTER INSERT`, `SECURITY DEFINER`: a fine transazione la stampa ha il suo principale (`E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE`, nuovo, `TECNICO`) | D10 |
| `-89` (`20_code/dbops`) | `dbops.fn_pgtap_stampa_con_pdf`: la fixture che registra una stampa col suo PDF (§11.3) | — |
| `-90` (`80_data/changelog`) | Via da `dbops.stati_check_dichiarazioni` le righe ANNULLATO e ARCHIVIATO della stampa (sarebbero `DEBITO_ESTINTO`) | D7 |

**CSV** (mirror `runOnChange` di `80_data`): `dbops/automazione_attivo_eccezioni.csv` +7 righe (le cinque FK della
stampa, `documenti_generati_file.file_tipo_id`, `template_documenti_versioni.derivata_da_versione_id`: D1, D8);
`config/codici_errore.csv` e `messaggi_errore.csv` (i due codici nuovi, id 1502-1503; le note e i testi che citavano
le funzioni ritirate, `STORAGE_ORPHAN` e gli stati ARCHIVIATO/ANNULLATO: M5, M7 e le soluzioni false);
`dbops/stati_check_dichiarazioni.csv` −2 righe.

**pgTAP**: nuovo `documenti/test-documenti-stampa-e-storia-v1.sql` (15 test, soggetti costruiti: un'azienda nuova,
il suo modello predefinito, una stampa). Riscritti perché il giro ne cambia il contratto: `test-documenti-generati`
(il 9 ora prova che ARCHIVIATO è rifiutato), `-generati-file`, `-generati-eventi` (il 4 ora prova che STORAGE_ORPHAN
è rifiutato), `-versione-contesto-v1`, `-template-standard-v1`, `test-sorgente-documenti-generati-v1` (il 12 su
`meta`), `rls/test-rls-documenti-satelliti`, `anagrafiche/test-stiva-movimenti-annullo-v1` (il test 0 cerca il
montaggio sul BB).

**Doc**: le pagine `manual/` di stampa, file, eventi, asset, modelli, versioni, tipi di output e di file,
`check_coerenza`, `protect_snapshot`, `protect_file` dell'asset, il BB in `script` (riscritta da capo: era in
formato vecchio, con SQL e un corpo falso), il registro delle eccezioni, le due pagine del plafond IVA; nuove
`trgfn_documenti_generati_guard_file_principale` e `dbops/manual/fn_pgtap_stampa_con_pdf`; **tolte** le cinque
delle funzioni ritirate. Guida `documenti-e-stampe` §11, le garanzie.

### 11.2 Che cosa è cambiato rispetto al censimento

* **Il BB «rifiuta sempre» c'era già.** `script.trgfn_prevent_modification_generic`, montato su
  `dbops.transaction_ids`, senza argomenti e con un codice solo. Il censimento di D18 proponeva un BB nuovo: si è
  esteso quello (un secondo accanto al primo sarebbe stata la terza versione della stessa regola). Il primo
  argomento del log passa da `'database'` allo schema della tabella; le chiavi del contesto diventano `tabella`,
  `operazione`, `id` (nessun lettore delle vecchie nel BE né nei pgTAP).
* **Fuori schema, una copia sola.** `anagrafiche.trgfn_stiva_movimenti_append_only` dice la stessa cosa e si
  ritira; la sua frase porta tipo e data del movimento, e per questo il BB riceve anche le colonne.
  `vendite.trgfn_event_log_append_only` resta: ha la porta di manutenzione e la retention, è un guard proprio.
  Cercati su dbdev il 2026-11-15 tutti i trigger function che sollevano senza condizioni: nessun'altra copia
  (`internal.trgfn_block_project_metadata` è fuori dagli schemi applicativi, con un `RAISE` nudo: non toccata).
* **Stampa e file in una CTE sola non funzionano da applicazione.** La policy del file risolve l'azienda dalla
  stampa (`script.fn_resolve_emittente_fiscale_id('documento_generato', …)`), che nella snapshot della CTE non c'è
  ancora: il file sarebbe negato. Le fixture passano da `dbops.fn_pgtap_stampa_con_pdf` (due istruzioni, come il
  servizio, nella finestra differita del solo guard nuovo). Vicolo cieco provato e scartato.
* **Il registro del presidio C1 portava ANNULLATO e ARCHIVIATO** come esenti: usciti dal CHECK sono debito
  estinto (`-90`). `STORAGE_ORPHAN` nel registro non c'era.

### 11.3 Fatti datati (dbdev, 2026-11-15)

* 135 stampe non hanno un file principale. Il guard giudica le nascite, non la popolazione: non le tocca, e
  la scheda della stampa lo dice fra i limiti. Nessuna stampa fuori GENERATO, nessun evento STORAGE_ORPHAN: i due
  CHECK nuovi passano.
* Il proprietario di stampa e file non ha `FORCE ROW LEVEL SECURITY`: la lettura `SECURITY DEFINER` del guard
  vede il file.

### 11.4 ⛔ Q13 — decisione aperta di Tid: la nascita da un padre spento

**Fatto.** L'eccezione ATTIVO (Q1) toglie **sia** il block sul padre **sia** il require sul figlio: per quelle FK
il motore non genera nessuno dei due. Quindi, dopo il giro 1, il database non chiede più che modello, versione,
tipo di output, sorgente e azienda siano accesi **quando la stampa nasce**. Lo garantisce solo la risoluzione del
servizio prima del render (`fn_risolvi_template_applicabile`, che sceglie solo versioni stampabili). Il censimento
di D1 diceva «i controlli dal lato della stampa scattano solo alla nascita» come se restassero: non restano.

**Strade.**

* **(a) Resta così** (la forma di `fatture_stampa_coda`): «che cosa può stampare lo decide la risoluzione». Un
  `INSERT` diretto da un modello spento passa la coerenza. Già scritto nelle pagine fra i limiti.
* **(b) La coerenza alla nascita chiede anche la stampabilità**: `check_coerenza`, che dal giro 1 gira solo
  all'`INSERT`, verifica che la versione sia stampabile per l'azienda alla data (la stessa domanda della
  risoluzione, da un BB, non ricopiata). Costo: un changeSet nel giro 1 o nel 4 (che riapre la risoluzione), e la
  domanda su che cosa conta come «alla data» per una stampa.

**Raccomandazione della sessione:** (b), nel giro 4 insieme alla risoluzione. È la protezione da un backend che
sbaglia, e la regola esiste già in un posto solo.

### 11.5 Per l'apply (Tid)

✅ **Fatto il 2026-11-16:** Tid ha applicato il giro e lanciato i pgTAP, verdi; la doc auto-generata è rigenerata (le
schede delle cinque funzioni ritirate sono tolte, nascono quelle del guard e della fixture). Resta il commit. I passi,
per la storia:

1. `/verifica-db` in una sessione nuova, sul lavoro non committato.
2. L'apply. Dopo, sui database già vivi, i trigger ATTIVO delle sette FK si tolgono al giro successivo del motore
   (job serale); per averli subito: `SELECT dbops.fn_ritira_attivo_eccezioni();`. Fino ad allora i test 7-10 del
   pgTAP nuovo e il 9 di `test-automazione-attivo-eccezioni-v1` sono rossi.
3. I pgTAP come applicazione: i nove del giro (§11.1) più `dbops/test-stati-check-scrittori-v1`. Provati sullo
   scratch con l'estratto in `ROLLBACK`, da owner, tutti verdi tranne il 16 di `test-documenti-generati-eventi`
   (asserisce il `42501` della RLS: da owner è rosso per costruzione). Verdi anche i presidi trasversali
   (`comment-al-presente`, `riferimenti-morti`, `security-definer-search-path`, `catalogo-messaggi-errore`,
   `builder-pgtap-vincoli-immediate`, `codici-errore-identita`, `trigger-attivo-orfani`) e i cancelli statici della
   CI.
4. La doc auto-generata rigenerata: le schede delle cinque funzioni ritirate vanno via, e quella della funzione
   nuova nasce. ⚠️ Fino alla rigenerazione le cinque schede vecchie includono pagine `manual/` che non ci sono più:
   la build della doc si rompe lì.

### 11.6 Richieste al team BE (sbloccate dal 2026-11-16)

Oltre a BE3 e BE7 di §6:

| # | File | Che cosa |
| --- | --- | --- |
| BE7 (in più) | `frontend/src/documenti/components/DocumentiGeneratiSorgenteList.vue:105-106` | Il badge di ARCHIVIATO e ANNULLATO esce: lo stato è solo GENERATO |
| BE9 | `docs/it/dev/backend/catalogo-building-block-backend.md:1368-1369`, poi `python3 scripts/gen_indice_bb.py` | Le due righe di `E_EVENTO_DOCUMENTO_*_VIETATA` nominano funzioni ritirate: il trigger è ora sul BB `script.trgfn_prevent_modification_generic` |
| BE10 | `backend/apps/core/services/error_policies_generated.py` (rigenerato), `error_messages_fallback.py` | I codici nuovi `E_FILE_DOCUMENTO_DELETE_VIETATA` (`CONFLITTO_STATO`) e `E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE` (`TECNICO`), e le note riscritte di cinque codici. Il fallback di `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` (`:448`) dice «la tabella e' append-only per audit»: si allinea se il fallback ricopia il catalogo |

Il servizio di stampa non cambia: scrive già stampa e PDF nella stessa transazione, e non cancella file.
