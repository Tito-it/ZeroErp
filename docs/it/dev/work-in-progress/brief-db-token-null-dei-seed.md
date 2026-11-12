# Brief DB — Il NULL nei CSV di seed: la regola sul comportamento vero del caricatore

## ⏭️ Chi riparte — aggiornato al 2026-11-13

**Riparte: team BE**, con la richiesta di §6 (`seed_csv` sulla regola vera). I giri A, B e D5 sono applicati e
i loro pgTAP sono verdi (2026-11-13). Dopo il push del BE, la sessione DB fa il giro C (§4): `nullValue:` esce dai
caricatori e il guardrail lo vieta. Poi il brief si archivia.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Le misure sul caricatore (bytecode e render offline) e il censimento | §1, §3 | — |
| 2 | ✅ Tid | D3 (a) di `brief-db-nullvalue-vuoto-cinque-mirror` §9.1: la regola si riscrive, in un brief suo (2026-11-12) | — | 1 |
| 3 | ✅ sessione DB | Giro A: guardrail, linee guida, `fatturazione_pipeline.csv` a `NULL` | §4 | 2 |
| 4 | ✅ Tid | D1 … D4: accettate le proposte (2026-11-13) | §5 | 1 |
| 5 | **team BE** ⏭️ | `seed_csv` e `gen_seed_lista.py` sulla regola vera; il commento di `check_i18n_keys.py` | §6 | 2 |
| 6 | ✅ sessione DB | Giro B: D1, D2 e D3 su `messaggi_errore` (CSV, `90_end`, pgTAP, manual); il CSV di `note_stili` | §5.1 | 4 |
| 6-bis | ✅ Tid | D5 (a): la stringa vuota la porta a NULL il verbo del pannello (2026-11-13) | §5.2 | 6 |
| 6-ter | ✅ Tid | Apply di `20261112-53` … `-56` e i tre pgTAP di §5.1: verdi (2026-11-13) | §5.1 | 6 |
| 6-quater | ✅ sessione DB | Giro D5: il verbo del pannello (`-57`, chiude il buco di `-36`) e `note_stili.note` (`-58`) | §5.3 | 6-bis |
| 6-quinquies | ✅ Tid | Apply di `-57` e `-58`, e i due pgTAP di §5.3: verdi (2026-11-13) | §5.3 | 6-quater |
| 7 | sessione DB | Giro C: `nullValue:` esce dai 208 caricatori, il guardrail lo vieta | §4 | 5 |
| 8 | sessione DB | Archiviazione | — | 6-quinquies, 7 |

**Decisioni aperte di Tid**: nessuna. **Da committare**: i giri A, B e D5 e questo brief, su `dev/db-tid`.
✅ La doc auto-generata è rigenerata da Tid (2026-11-13) e dice `separatore` `NOT NULL`: le due righe di
`sistema_codici` sono uscite da `CELLA_VUOTA_DEBITO`, che ora è vuoto (§5.1). Da committare con la doc rigenerata.

**Brief vicini verificati**: `brief-db-nullvalue-vuoto-cinque-mirror.md` (i cinque mirror con `nullValue: ""`:
§9 e §9.1 hanno fatto nascere questo brief, e lì resta un rimando; il suo giro 3 su `email_reply_to` non si
tocca); `brief-db-lista-colonna-campo-sorgente-null.md` (archiviato: il BB `seed_csv` è nato lì, sulla premessa
che qui si corregge). Nessun altro brief aperto tocca i caricatori o il token dei CSV.

## 1. Che cosa fa il caricatore (misurato il 2026-11-12, Liquibase 5.0.4)

Misurato in due modi: sul bytecode di `tools/liquibase/5.0.4/internal/lib/liquibase-core.jar` e col render
offline (`updateSQL --url=offline:postgresql`) di un changelog sintetico, con `loadUpdateData` e `loadData` e un
CSV costruito.

| Colonna nel caricatore | cella vuota | `null`, `NULL`, `Null`, anche fra virgolette |
| --- | --- | --- |
| dichiarata `type: STRING` | `''` | NULL |
| dichiarata `STRING` con `defaultValue` | il default | NULL |
| dichiarata `NUMERIC`, `BOOLEAN`, `DATE`, `DATETIME`, `JSON`, `COMPUTED` | NULL | NULL |
| non dichiarata in `columns:` | NULL | NULL |

* **`nullValue:` non esiste.** `LoadDataChange` non ha quel setter. I suoi attributi sono `file`, `separator`,
  `quotchar`, `encoding`, `commentLineStartsWith`, `relativeToChangelogFile`, `usePreparedStatements` e
  `columns`. Liquibase ignora l'attributo **senza errore**. Prova: con `nullValue: XX` la cella `XX` arriva come
  `'XX'`. Il segnaposto vero è `nullPlaceholder`, per colonna, e nessun file del repo lo usa.
* **Il checksum non lo vede.** Lo stesso changeSet con `nullValue: "NULL"`, con `""` e senza l'attributo dà lo
  stesso checksum (`9:fea072f5…`). Togliere l'attributo non fa rigirare niente e non rompe la validazione,
  nemmeno sui changeSet senza `runOnChange`.
* `loadData` e `loadUpdateData` rendono allo stesso modo. Non è verificato `loadData` online con prepared
  statement: oggi lo usano due file, con colonne che non hanno celle vuote.
* Una stringa che vale davvero `null` non si può caricare da un CSV. Nessun dato del modello la chiede.

**La regola che ne segue.** Nei CSV di seed l'assenza si scrive **`NULL`** (maiuscolo, la convenzione). La
cella vuota vuol dire `''` su una colonna `STRING` e NULL su tutte le altre: quindi su una colonna testo si
scrive vuota **solo** se il valore voluto è la stringa vuota. Il `nullValue` del mirror non c'entra.

## 2. Che cosa raccontava la documentazione, e dove

La premessa che il `nullValue` del mirror decida il token stava in:

* `linee-guida-sql` §11.2, riga «scrivere un `NULL`» (corretta nel giro A);
* la regola `nullvalue-vuoto` di `scripts/guardrail_forme_changeset.py`, che guardava solo i caricatori con
  `nullValue: ""`: il difetto sotto `nullValue: "NULL"` non lo vedeva (§3; riscritta nel giro A);
* le pagine `manual/` di `ui.lista_colonna`, `config.iva_assoggettamenti` e `config.email_account`, che citano
  il `nullValue` del mirror (corrette nel giro A);
* il lato BE (§6): il BB `seed_csv` (`token_nullo`), il descrittore `CSV_SEED` di `scripts/gen_seed_lista.py`
  e un commento di `scripts/check_i18n_keys.py`.

Il resto di `linee-guida-sql` è giusto: §11.2, «Nel confronto una cella vuota si legge come la carica il
loader», e «Un CSV esportato deve portare il TOKEN `NULL`» descrivono già il comportamento vero.

## 3. Il censimento (fatto datato, 2026-11-12)

Su 212 caricatori, 208 dichiarano `nullValue` (99 `"NULL"`, 109 `""`), e 206 di questi sono `runOnChange`.
Celle vuote su una colonna `STRING` senza `defaultValue`, con lo stato su dbdev:

**Colonna testo nullable**: l'assenza ha due forme possibili.

| Tabella.colonna | Mirror (`80_data/changelog/`) | `''` su dbdev | Lettura del modello |
| --- | --- | --- | --- |
| `config.sistema_codici.separatore` | `20250813-05`, `20260524-25` | 3 su 10 | ⚠️ `''` è **il valore giusto** («nessun separatore»): `script.fn_generate_codice` fa `prefix \|\| sep \|\| …`, e con NULL il codice generato sarebbe NULL. Ad avere torto è la nullabilità |
| `config.iva_natura.user_insert` | `20250816-01` | 21 su 21 | colonna di audit: il caso di `magazzino.causali` (`brief-db-nullvalue-vuoto-cinque-mirror` D1-c) |
| `config.note_stili.note` | `20260519-02` | 5 su 5 | assenza vera: NULL |
| `config.messaggi_errore.causa` | `20260614-08` | 321 su 1216 | assenza vera: NULL |
| `config.messaggi_errore.soluzione` | `20260614-08` | 327 su 1216 | assenza vera: NULL |

**Colonna testo NOT NULL**: `''` è l'unica forma possibile, quindi non è il difetto di questo brief. Restano
come note:

| Tabella.colonna | `''` su dbdev | Lettura |
| --- | --- | --- |
| `dbops.sec_functions_owner.arg_types` | 2 su 5 | giusto: funzioni senza argomenti |
| `ui.lista_colonna.etichetta` | 4 su 1167 | le colonne id di `resi_da_accreditare` e `resi_da_riconsegnare`, senza intestazione |
| `config.parameters.default_value` | 6 su 54 | «nessun default» scritto `''` in una colonna NOT NULL |
| `config.codici_postali.codice` | 1 su 8098 | la riga 5474, un CAP vuoto: un dato che manca |
| `vendite.fatturazione_pipeline_task_policy.user_update` | 0 su 27 | `''` nel CSV: è la colonna di audit nel CSV (D1-c, come sopra). ⚠️ Corretto il 2026-11-13: la tabella **non ha trigger**, e il «trigger di audit la riscrive» era falso. Lo scratch, costruito da zero, ha 13 `''` su 27: su dbdev le righe erano state riscritte per un'altra strada |

**Grafia**: un solo file scrive `null` in minuscolo, `vendite/fatturazione_pipeline.csv` (16 celle). Il DB è
giusto, perché il caricatore lo riconosce.

**Il vicolo cieco** che ha fatto nascere le misure: `brief-db-nullvalue-vuoto-cinque-mirror` §9.1. Sotto
`nullValue: ""`, svuotare quelle 16 celle le avrebbe scritte `''`, e su una colonna intera l'apply si sarebbe
fermato.

## 4. I giri senza decisioni di modello

**Giro A (2026-11-12, scritto).**

1. `scripts/guardrail_forme_changeset.py`: la regola `nullvalue-vuoto` diventa **`cella-vuota-string`**. Guarda
   **ogni** caricatore, con qualunque `nullValue` o senza. Scatta sulla cella vuota di una colonna `STRING`
   senza `defaultValue` quando la colonna della tabella è testo nullable. I cinque casi di §3 stanno nel suo
   registro `CELLA_VUOTA_DEBITO`, ciascuno con la sua decisione, e una riga morta fa rosso. Una regola nuova,
   **`null-grafia`**, rifiuta una cella che è la parola null in una grafia diversa da `NULL`.
2. `linee-guida-sql` §11.2, la riga «scrivere un `NULL`»: la regola di §1.
3. `vendite/fatturazione_pipeline.csv`: le 16 celle `null` diventano `NULL`. Il render offline del mirror è
   identico prima e dopo (`utility_id = NULL`, `tipo_doc_fiscale_id = NULL`).
4. Le tre pagine `manual/` di §2: il token è `NULL`, senza più il rimando al `nullValue`.

**Giro C (aspetta §6).** `nullValue:` esce dai 208 caricatori: è una dichiarazione che non succede niente, e chi
la legge ci crede. Il checksum non cambia (§1). Il guardrail lo rifiuta su ogni caricatore, con una regola
`nullvalue-ignorato`. **Chi cambia per primo: il BE.** Oggi `seed_csv` solleva su un caricatore senza
`nullValue`: togliere l'attributo prima farebbe rossa la CI dei test backend.

## 5. Le decisioni di Tid

**D1 — `config.sistema_codici.separatore`.** `''` è il valore («nessun separatore»), NULL è l'errore:
`fn_generate_codice` concatena con `||`. Proposta: `NOT NULL DEFAULT ''`, in `90_end`, dopo aver censito chi
scrive la tabella (linee-guida-sql §11.14). Il CSV resta con la cella vuota, che lì è giusta. Alternativa: lasciare
nullable e mettere `coalesce` nei lettori (scartata nella proposta: sposta su ogni lettore una regola della
colonna).

**D2 — `config.iva_natura.user_insert` e `fatturazione_pipeline_task_policy.user_update`.** Proposta: la forma di
D1-c di `magazzino.causali` (Tid, 2026-11-12). Le colonne di audit escono dal CSV e da `columns:`, e
`user_insert` arriva a linee-guida-sql §7 (`NOT NULL DEFAULT CURRENT_USER`), dopo la conversione delle `''`.

**D3 — `config.note_stili.note`, `config.messaggi_errore.causa` e `soluzione`.** Proposta: la forma dei giri 1 e 2
di `brief-db-nullvalue-vuoto-cinque-mirror`. Nel CSV la cella vuota diventa `NULL`, e in `90_end` c'è la
conversione e poi il `CHECK (<col> IS NULL OR btrim(<col>) <> '')`. Per `messaggi_errore`, prima del `CHECK` si
censiscono i lettori di `causa`/`soluzione` (`fn_log_and_raise_error` e il BE) e i changeSet che appendono al
CSV. ⚠️ Il CSV è scritto da molte sessioni: il giro va fatto in una finestra concordata.

**D4 — Le note NOT NULL di §3** (`parameters.default_value`, `codici_postali` riga 5474,
`lista_colonna.etichetta` vuota). Non sono il difetto di questo brief. Proposta: fuori perimetro, ciascuna da
decidere a parte. La riga 5474 è un dato che manca, non una forma.

> ✅ **Decise da Tid il 2026-11-13**: D1 … D4 come proposte.

### 5.1 Giro B (applicato il 2026-11-13, pgTAP verdi)

| Decisione | Seed | `90_end` | pgTAP |
| --- | --- | --- | --- |
| D1 `sistema_codici.separatore` | CSV invariato (la cella vuota è il valore); nota nei due mirror | `20261112-53`: i NULL diventano `''`, poi `SET DEFAULT ''` e `SET NOT NULL` | `config/test-sistema-codici-separatore-v1` (plan 3) |
| D2 `iva_natura.user_insert` | `80_data/20250816-01`: `user_insert` e `user_update` escono dal CSV e da `columns:` | `20261112-54`: le audit vuote prendono il ruolo che migra, poi `user_insert` `SET DEFAULT CURRENT_USER` e `SET NOT NULL` | `config/test-iva-natura-audit-insert-v1` (plan 4, anche per `task_policy`) |
| D2 `fatturazione_pipeline_task_policy` | `80_data/20260218-05`: le stesse due colonne escono | `20261112-56`: solo la conversione (le due colonne sono già a §7) | lo stesso, test 4 |
| D3 `messaggi_errore.causa`, `soluzione` | `80_data/20260614-08`: 321 + 327 celle a `NULL`; la nota di testata del 2026-08-05 è marcata superata | `20261112-55`: conversione, poi `chk_messaggi_errore_causa_non_vuota` e `chk_messaggi_errore_soluzione_non_vuota` | `config/test-messaggi-errore-causa-soluzione-non-vuote-v1` (plan 8) |
| D3 `note_stili.note` | `80_data/20260519-02`: 5 celle a `NULL` | fatto nel giro D5 (§5.3) | §5.3 |

* **Censimento.** Chi scrive `sistema_codici`: il seed e il pannello. In creazione il campo vuoto non viaggia e
  vale il default, in modifica viaggia `''`, quindi `NOT NULL DEFAULT ''` è la forma che il pannello sa già
  scrivere. Chi legge `causa`/`soluzione`: `fn_log_and_raise_error` (le passa al `RAISE` con `coalesce(…, '')`),
  `fn_log_error_only`, il BE per JOIN (`str | None`), il drawer del log (le mostra solo se valorizzate). Nessun
  lettore distingue `''` da NULL. `messaggi_errore` non è nel pannello. Il CSV lo leggono solo il mirror,
  `estrai_classi_codici_errore.py` e gli indicatori, che non leggono le due colonne.
* **La finestra concordata su `messaggi_errore.csv`.** Al momento della riscrittura il file non aveva modifiche
  aperte. Una sessione che aggiunge una riga senza causa o soluzione scrive `NULL`: il guardrail
  (`cella-vuota-string`) rifiuta la cella vuota, perché la riga è uscita dal registro dei debiti.
* **`task_policy` ha avuto bisogno di `-56`.** La prova sullo scratch ha trovato 13 `user_update` vuote: la
  tabella non ha trigger di audit, e il §3 diceva il contrario (corretto).
* **Riscrittura dei CSV.** I file mescolano celle quotate e non quotate, e il modulo `csv` di Python le avrebbe
  riquotate: si è usato un tokenizzatore che conserva il testo grezzo di ogni cella e cambia solo quelle bersaglio.
  Il diff contiene solo le celle e le colonne previste.
* **Guardrail.** Le righe di `iva_natura`, `note_stili` e `messaggi_errore` escono da `CELLA_VUOTA_DEBITO`.
  Restano le due di `sistema_codici`: la regola legge la nullabilità dalla doc auto-generata, e quando questa,
  rigenerata, dirà `NOT NULL`, le due righe diventeranno morte e il cancello chiederà di toglierle.
  ✅ Tolte il 2026-11-13, dopo la rigenerazione della doc: `CELLA_VUOTA_DEBITO` è vuoto.
* **Prove.** Render offline dei cinque mirror: `iva_natura` e `task_policy` senza colonne di audit, `note = NULL`,
  321 `causa = NULL` e 327 `soluzione = NULL` senza nessuna `''`, `separatore = ''` sulle tre righe senza
  separatore. `scripts/prova_changeset.py` sullo scratch: `-53` 3/3, `-54` + `-56` 4/4, `-55` 8/8. Senza
  l'estratto i rossi sono quelli attesi, perché i vincoli non ci sono ancora. Guardrail verde.
* **Manual**: `sistema_codici`, `iva_natura`, `messaggi_errore`. Quella di `note_stili` è nel giro D5.

### 5.2 D5 — La stringa vuota che arriva dal pannello (decisa: (a), 2026-11-13)

**Il fatto.** Il pannello generico (`config.fn_pannello_scrivi` → `script.fn_scrivi_riga_da_jsonb`) scrive il
valore come arriva, con `jsonb_populate_record`. Il drawer (`GenericConfigDrawer.vue`) in creazione non manda un
campo vuoto, che quindi vale il default. **In modifica** manda il campo cambiato così com'è: svuotare una nota
manda `''`. Due tabelle del pannello hanno o avrebbero il `CHECK` «mai la stringa vuota»:

* `config.iva_assoggettamenti.note` (`pannello = true`), col `CHECK` dal giro 1 di
  `brief-db-nullvalue-vuoto-cinque-mirror` (`90_end/20261112-36`, già applicato). **Oggi svuotare la nota dal
  pannello dà `23514`.** Il censimento di quel giro aveva guardato il drawer dedicato di `email_account`, non il
  pannello generico;
* `config.note_stili.note` (`pannello = true`): il suo `CHECK` avrebbe lo stesso buco.

**La domanda.** Dove diventa NULL una stringa vuota diretta a una colonna testo nullable:

* **(a) nel verbo del pannello** (lavoro DB): `config.fn_pannello_scrivi`, prima della scrittura, porta a `null`
  la stringa vuota o di soli spazi destinata a una colonna testo **nullable**. Una sede per tutte le tabelle del
  pannello e per ogni chiamante del verbo. Le colonne `NOT NULL` (come `separatore`) ricevono `''` come oggi;
* **(b) nel drawer** (lavoro FE): `versoPayload` manda `null` per `''` quando la colonna è testo e `nullable`.
  Copre solo quel drawer: un altro chiamante del verbo scriverebbe ancora `''`;
* **(c) un trigger di normalizzazione per tabella**: una copia per tabella, contro la regola del 2. Scartata.

**Proposta: (a).** La regola «l'assenza è NULL» sta nel database, e il verbo generico è la sede unica della
scrittura dal pannello. Chiude il buco di `-36` senza toccarlo, e permette il `CHECK` di `note_stili`
nello stesso giro.

> ✅ **Decisa da Tid il 2026-11-13: (a)**, con la correzione del buco di `-36`. Il giro è §5.3.

### 5.3 Giro D5 (applicato il 2026-11-13, pgTAP verdi)

| Oggetto | changeSet | pgTAP |
| --- | --- | --- |
| `config.fn_pannello_scrivi`: passo 2-bis | `20_code/config/20261112-57` | `config/test-fn-pannello-scrivi-stringa-vuota-v1` (plan 7) |
| `config.note_stili.note` | `90_end/20261112-58`: conversione, poi `chk_note_stili_note_non_vuota` | `config/test-note-stili-note-non-vuota-v1` (plan 6) |

* **Il passo 2-bis.** Prima della scrittura, una stringa vuota o di soli spazi destinata a una colonna di testo
  **nullable** (categoria di tipo `S` in `pg_type`, quindi anche varchar, char e i domini su questi) diventa
  `null`. Una colonna `NOT NULL` riceve il valore com'è. Un testo vero passa intatto, spazi ai bordi compresi:
  il verbo decide solo fra «vuoto» e «assente», non ripulisce i valori. Il resto del corpo è quello vivo di
  `20261017-07`, e il rollback lo rimette.
* **Perché nel verbo e non in un BB.** Oggi il chiamante è uno solo; gli altri chiamanti di
  `script.fn_scrivi_riga_da_jsonb` non cambiano. Quando servirà a un secondo verbo, diventerà un BB (regola del 2).
* **Il buco di `-36`** si chiude senza toccarlo: il test 1 del pgTAP nuovo, senza l'estratto, riproduce il
  `23514`, e con l'estratto passa. Il brief vicino lo annota al suo giro 1.
* **Ordine.** `20_code` gira prima di `90_end`, quindi il verbo cambia prima che nasca il `CHECK` di `note_stili`.
* **Prove** sullo scratch (`scripts/prova_changeset.py`): `-57` + `-58` col pgTAP del verbo, 7/7 (senza: si ferma
  al test 1, il buco); col pgTAP di `note_stili`, 6/6; il pgTAP esistente del verbo
  (`config/test-fn-pannello-scrivi-v1`) resta 15/15 con `-57`.
* **Manual**: `fn_pannello_scrivi`, `note_stili`, `iva_assoggettamenti`. La doc auto-generata si rigenera
  dopo l'apply.

## 6. Richiesta al team BE (elenco chiuso)

La regola vera (§1) è più semplice di quella su cui il BB è nato, e vale per ogni file:

* `backend/apps/core/tests/_seed_csv.py`: `seed_csv` rende `None` la cella che in minuscolo è `null`, su ogni
  file. Rende `''` la cella vuota di una colonna dichiarata `type: STRING` (senza `defaultValue`) dal caricatore,
  e `None` la cella vuota di ogni altra colonna. Si ritirano `token_nullo` e il rifiuto del file senza
  `nullValue`, che dopo il giro C sarebbe ogni file. Il test `test_seed_csv` lo prova su file costruiti: la cella
  `null` minuscola, la vuota `STRING` e la vuota non `STRING`.
* `scripts/gen_seed_lista.py`: il campo `nullo` di `CSV_SEED` e il commento che lo spiega («NON è lo stesso per
  tutti») vanno riscritti. Il token è `NULL` per tutti e quattro i CSV, e la cella vuota di una colonna `STRING`
  è `''`.
* `scripts/check_i18n_keys.py`, riga 346: il commento che cita il `nullValue` del mirror.
* `backend/apps/core/tests/_seed_csv.py`, riga 16: il commento cita la regola `nullvalue-vuoto`, che ora si chiama
  `cella-vuota-string`.
* Il catalogo BB backend, voce `seed_csv`: la stessa correzione.

**Chi cambia per primo**: il BE, prima del giro C. Il giro A e il giro B non toccano ciò che il BE legge.
