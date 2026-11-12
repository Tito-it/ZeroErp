# Brief DB — Cinque mirror scrivono `''` dove la colonna ammette `NULL`

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: Tid**, con l'apply e i pgTAP del giro 3 (il `CHECK` su `email_reply_to`, §7, scritto e provato sullo
scratch il 2026-11-12), poi l'archiviazione. Il tema del token NULL dei CSV (§9, §9.1) prosegue in
`brief-db-token-null-dei-seed.md`.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Il guardrail `nullvalue-vuoto` e il censimento dei cinque mirror | §1, §2 | — |
| 2 | ✅ Tid | D1 per `note` ed `email_reply_to`: `NULL`; il via | §3 | 1 |
| 3 | ✅ sessione DB | Giro 1: `iva_assoggettamenti.note`, `email_account.email_reply_to` | §5 | 2 |
| 4 | ✅ Tid | D1-b (`NULL` + `CHECK`) e D1-c (`user_insert` a §7, colonne di audit fuori dal CSV) | §6 | 3 |
| 5 | ✅ sessione DB | Giro 2: `name_template`, `trigger_name`, `causali` | §8 | 4 |
| 6 | ✅ Tid | Apply e pgTAP dei giri 1 e 2: applicati il 2026-11-12, verdi | §5, §8 | 3, 5 |
| 7 | ✅ Tid | Rigenerare la doc auto-generata (vincoli e default nuovi) e committare: in `83d21a13d` (PR #100) | — | 6 |
| 8 | ✅ team BE | La PATCH dell'account email porta `''` a `None`: fatta il 2026-11-12, committata in `0216782d6b` (PR #103) | §7 | — |
| 9 | ✅ sessione DB, poi **Tid** ⏭️ | Giro 3: il `CHECK` su `email_reply_to`, scritto e provato sullo scratch; apply, pgTAP e doc auto-generata a Tid | §7 | 7, 8 |
| 10 | ✅ Tid | D2 (b), il 2026-11-12: ⚠️ sospesa, la premessa è falsa (§9.1) | §9 | — |
| 10-bis | ✅ Tid | D3 (a), il 2026-11-12: la regola si riscrive, in `brief-db-token-null-dei-seed.md` | §9.1 | 10 |
| 11 | ✅ sessione DB | Il tema passa a `brief-db-token-null-dei-seed.md`: qui non resta lavoro di §9 | §9.1 | 10-bis |
| 13 | sessione DB | Archiviazione | — | 9, 11, 12 |

**Decisioni aperte di Tid**: `causali.data_update`, fuori perimetro (§8, note). **Da committare**:
questo brief (§9), il giro 3 (§7) e l'archiviazione di `brief-db-lista-colonna-campo-sorgente-null`, su
`dev/db-tid`.

**Brief vicini verificati**: `brief-db-lista-colonna-campo-sorgente-null.md` (lo stesso difetto su
`ui.lista_colonna`, già corretto: il giro qui ne riprende la forma); `brief-db-guardrail-forme-residue.md`
(archiviato, ha fatto nascere il guardrail). Nessuno copre questi cinque mirror.

## 1. Il difetto

Un caricatore con `nullValue: ""` scrive la cella vuota di una colonna `STRING` come stringa vuota. Dove la
colonna della tabella è di testo e nullable, l'assenza ha così due forme: `''` dal seed, `NULL` da chi scrive
la riga per altra strada. Chi legge deve accettarle entrambe, e chi se ne dimentica sbaglia in silenzio. La
forma giusta è `NULL` (la stessa decisione di Tid su `lista_colonna`, 2026-11-12).

Dal 2026-11-12 il guardrail `scripts/guardrail_forme_changeset.py`, regola `nullvalue-vuoto`, ferma i casi
nuovi. I cinque che c'erano stanno nel suo registro `NULLVALUE_DEBITO`, e una riga che non viola più fa rosso
il cancello: si toglie nello stesso giro in cui si corregge il suo mirror.

## 2. I cinque, come fatto datato (dbdev, 2026-11-12)

| Mirror (`80_data/changelog/`) | Tabella | Colonna | Righe con `''` / righe |
| --- | --- | --- | --- |
| `20250814-04-upsert-config-iva-assoggettamenti` | `config.iva_assoggettamenti` | `note` | 3 / 3 |
| `20250918-02-upsert-dbops-automations_rule_table` | `dbops.automation_rules_tbl` | `name_template` | 17 / 24 |
| `20251001-51-upsert-magazzino-causali-table` | `magazzino.causali` | `user_insert` | 10 / 16 |
| `20260123-11-upsert-automation-delete-block-ruoli` | `dbops.automation_delete_block` | `trigger_name` | 8 / 8 |
| `20260329-60-upsert-config-email-account` | `config.email_account` | `email_reply_to` | 1 / 1 |

I conteggi non decidono niente: la regola vale anche per una riga sola.

## 3. Decisione D1

> ⚠️ Decisa in parte, 2026-11-12: Tid approva la proposta qui sotto. `note` ed `email_reply_to` vanno a `NULL`
> (giro 1, §5). Sulle altre tre il giro ha letto chi le usa: le risposte e le decisioni ancora aperte
> (D1-b, D1-c) sono in §6.

**D1 — Per ogni colonna: `NULL`, oppure la colonna diventa NOT NULL?** Prima di correggere si chiede al
modello che cosa vuol dire la cella vuota:

* `note`, `email_reply_to`: un'assenza vera, quindi `NULL`;
* `name_template`, `trigger_name`: sono nomi generati dalle automazioni. Se un nome serve sempre, la cella
  vuota è un nome che manca, e il rimedio è il nome, o un `NOT NULL`, non il `NULL`;
* `magazzino.causali.user_insert`: una colonna di audit vuota nel seed. Va scritta, non annullata.

Proposta: `NULL` per le prime due; per le altre tre, il giro legge chi le usa e porta a Tid la risposta,
colonna per colonna.

## 4. Il giro, per ciascun mirror

La forma di `lista_colonna` (`80_data/20260806-15` e `90_end/20261112-30`):

1. il mirror passa a `nullValue: "NULL"`, e le celle vuote delle colonne nullable portano il token, anche quelle
   non testo, che col token nuovo non accetterebbero la cella vuota;
2. un `CHECK (<colonna> IS NULL OR btrim(<colonna>) <> '')` in `90_end`, preceduto dalla conversione delle `''`
   rimaste fuori dal CSV;
3. si censiscono i lettori della colonna e i lettori del CSV (script, test del backend), come in
   `brief-db-lista-colonna-campo-sorgente-null` §5.1: un lettore del CSV che non conosce il token prende `'NULL'`
   per un valore;
4. la riga del mirror esce da `NULLVALUE_DEBITO`.

Il loader si prova col render offline di Liquibase (`updateSQL --url=offline:postgresql`) su una copia del
mirror senza `preConditions`.

## 5. Giro 1 — `note` ed `email_reply_to` (applicato il 2026-11-12, pgTAP verdi)

| Colonna | Mirror e CSV | `CHECK` | Presidio |
| --- | --- | --- | --- |
| `config.iva_assoggettamenti.note` | `80_data/20250814-04` a `nullValue: "NULL"`; nel CSV le tre celle `""` diventano `NULL` | `90_end/20261112-36`: conversione delle `''` rimaste, poi `chk_iva_assoggettamenti_note_non_vuota` | `config/test-iva-assoggettamenti-note-non-vuota-v1` (plan 6) |
| `config.email_account.email_reply_to` | `80_data/20260329-60` a `nullValue: "NULL"`; nel CSV il token va su `email_reply_to` e su `unita_organizzativa_id` (NUMERIC: col token nuovo la cella vuota non passerebbe) | ⏸️ non ancora: §7 | — |

Le due righe sono uscite da `NULLVALUE_DEBITO`, e il guardrail è verde. Sono aggiornate anche le pagine
`config/manual/iva_assoggettamenti.md` ed `email_account.md`. La doc auto-generata si rigenera dopo l'apply.

**Censimento (§4 punto 3)**:

* *Chi legge il CSV*: per tutti e due i file, solo il loro mirror. Nessuno script e nessun test del backend
  legge questi CSV. Il nome `email_account.csv` compare in `00_schema/20260629-05` solo in un commento.
* *Chi scrive `note`*: solo il seed. Nessuna funzione del database e nessun endpoint la scrivono.
  ⚠️ **Corretto il 2026-11-13**: la scrive anche il **pannello generico** (`iva_assoggettamenti` ha
  `pannello = true`), che in modifica manda `''` quando si svuota il campo. Col `CHECK` di `-36` quella modifica
  dà `23514`. La decisione su dove la stringa vuota diventa NULL è D5 di `brief-db-token-null-dei-seed.md` §5.2.
  ✅ **Chiuso il 2026-11-13** (D5 (a) di Tid): il verbo del pannello porta a NULL la stringa vuota destinata a
  una colonna di testo nullable (`20_code/config/20261112-57`). `-36` resta com'è. Presidio:
  `config/test-fn-pannello-scrivi-stringa-vuota-v1`, test 1-4.
* *Chi scrive `email_reply_to`*: il seed, la creazione dal pannello (`email_views.py`, `.strip() or None`,
  quindi `NULL`) e la **PATCH** dal pannello, che scrive `''` quando si svuota il campo (§7).
* *Chi legge `email_reply_to`*: `fn_resolve_email_account` lo restituisce com'è. `email_service.py` mette il
  `Reply-To` solo se il valore è vero in Python, quindi `''` e `NULL` vanno già allo stesso modo. Il drawer
  del frontend lo mostra con `|| ''`. Nessun lettore cambia comportamento.

**Prove fatte (2026-11-12)**:

* `scripts/prova_changeset.py` su `90_end/20261112-36` col pgTAP, sullo scratch. Senza l'estratto 2 ok e 4
  not ok: il vincolo non c'è ancora, e lo scratch ha ancora le `''` del seed vecchio. Con l'estratto 6 ok su 6.
  Il catalogo resta identico.
* Render offline dei due mirror, copie senza `preConditions`. `note = NULL`, `email_reply_to = NULL` e
  `unita_organizzativa_id = NULL`, sia nell'`UPDATE` sia nell'`INSERT`.

## 6. Le altre tre colonne: che cosa dice il modello (letto il 2026-11-12)

> ⚠️ Decise il 2026-11-12: Tid approva D1-b e D1-c come proposti qui sotto. Per il punto 2 di D1-c la
> sessione ha seguito §11.2 di `linee-guida-sql` («se il valore giusto è il default della tabella, la
> colonna si toglie dal CSV e dall'elenco `columns:`»), non `type: SKIP`. Il giro è in §8.

**D1-b — `name_template` e `trigger_name`: proposta `NULL` + `CHECK`.** Per tutte e due la cella vuota è
un'assenza vera, e non c'è un nome che manca:

* `dbops.automation_rules_tbl.name_template`. Secondo il contratto
  (`dbops/manual/automation_rules_tbl.md`, «Il nome: il template»), il template è obbligatorio solo per le
  regole che montano un trigger: `TX_ID`, `AUDIT_UPDATE`, `STORICO`, `LOCK_COLUMNS`, `DATE_VALIDITA`,
  `CODICE_MAIUSCOLO` e `ATTIVO`. Lo presidia già `chk_automation_rules_tbl_regola_valida`, attraverso
  `dbops.fn_regola_automazione_valida`, che usa `NULLIF(btrim(…), '')` e accetta quindi anche il `NULL`. Le
  regole `CLEANUP_*` e `STORICO_PROVISION` «non montano trigger e non hanno template». Nel CSV le celle vuote
  stanno solo su queste. Un `NOT NULL` sarebbe sbagliato per il modello.
* `dbops.automation_delete_block.trigger_name`. Secondo il contratto
  (`dbops/manual/automation_delete_block.md`), è il nome del trigger «se non si vuole quello del template.
  Vuoto vuol dire template». È un override facoltativo. `dbops.fn_nome_oggetto_dichiarato` già usa
  `NULLIF(btrim(p_nome), '')`, quindi il `NULL` non cambia il nome risolto.

Giro 2, se Tid approva: lo stesso del giro 1, col `CHECK` in `90_end`. Prima di scriverlo va fatto il
censimento di chi scrive le due tabelle. Le due funzioni qui sopra sono le lettrici, non le scrittrici.

**D1-c — `magazzino.causali`: il difetto è nel modello delle colonne di audit, non nel `nullValue`.**
Secondo la struttura (doc auto-generata), `user_insert` è `text` nullable **senza default**, contro
`linee-guida-sql` §7, che vuole `user_insert TEXT NOT NULL DEFAULT CURRENT_USER`. Nel CSV, inoltre,
`user_insert` e `user_update` sono vuote in tutte le righe. `user_update` è `NOT NULL`, quindi il guardrail
non la vede, ma il loader la scrive comunque come `''`: è la stessa malattia su una colonna che il registro
non copre. Convertire in `NULL` sarebbe sbagliato: un'audit vuota non è un'assenza. Proposta:

1. `user_insert` portata a §7: in `90_end`, prima la conversione di `''` e `NULL`, poi `SET DEFAULT
   CURRENT_USER` e `SET NOT NULL`;
2. nel CSV le due colonne prendono il valore del seed, come fanno `iva_assoggettamenti` (`titodb`) ed
   `email_account` (`SEED`). In alternativa escono dal mirror con `type: SKIP`, e allora vale il default;
3. la riga esce da `NULLVALUE_DEBITO`.

Da decidere: 2 col valore o 2 con `SKIP`. E se la stessa forma (audit `''` in un seed `NOT NULL`) va cercata
negli altri mirror, magari con una regola del guardrail. Sarebbe lavoro fuori da questo brief.

## 7. Richiesta al team BE — la PATCH dell'account email

`EmailAccountDetailView.patch` (`backend/apps/amm_software/api/email_views.py`, ciclo su `codice`, …,
`email_reply_to`) fa `.strip()` del valore e lo passa a `update_account`, cioè a `execute_dynamic_update`.
Il drawer (`EmailAccountDrawer.vue`) manda `email_reply_to: ''` quando il campo è vuoto, quindi la PATCH scrive
`''`. La creazione, nello stesso file, usa già `.strip() or None`.

Richiesta, elenco chiuso:

* `email_views.py`, `patch`: per `email_reply_to` (l'unica colonna nullable del ciclo) `''` dopo lo strip
  diventa `None`;
* `tests/api/test_email_views_fase6.py`: il test della PATCH col payload del drawer (`email_reply_to: ""`)
  asserisce che `update_account` riceve `None`.

> ✅ **Fatto dal team BE, 2026-11-12** (da committare). In `EmailAccountDetailView.patch`, dopo il ciclo
> di strip, un `email_reply_to` uguale a `''` diventa `None`. `update_account` → `execute_dynamic_update`
> gira con `skip_none=False`, quindi il `None` scrive `NULL` e non salta la colonna. Il test è
> `backend/apps/amm_software/tests/api/test_email_views_fase6.py::TestEmailAccountPatchChiavi::test_patch_payload_del_drawer_passa`
> (il percorso nell'elenco qui sopra era senza `backend/apps/amm_software/`); il modulo è verde, 22 test.
> Il frontend non cambia: il drawer manda ancora `''`, e la normalizzazione è del BE. Nessun altro
> scrittore BE delle cinque colonne: le tabelle `iva_assoggettamenti`, `automation_rules_tbl` e
> `automation_delete_block` non sono scritte da codice Python fuori dai test.

> ✅ **Lato DB, giro 3 (2026-11-12)**, scritto e provato, da applicare.
> `90_end/20261112-43-add-chk-email-account-email-reply-to-non-vuoto`: conversione delle `''` rimaste, poi
> `chk_email_account_email_reply_to_non_vuoto` (`email_reply_to IS NULL OR btrim(email_reply_to) <> ''`).
> Presidio `config/test-email-account-reply-to-non-vuoto-v1` (plan 8): costruisce INSERT e UPDATE, perché la
> modifica dal pannello è un UPDATE. Censimento degli scrittori: il seed, la creazione e la PATCH, che scrivono
> tutti `NULL`; nessuna funzione del database. Prove con `scripts/prova_changeset.py` sullo scratch: il test
> nuovo senza l'estratto 3 ok e 5 not ok (manca il vincolo, e lo scratch ha ancora `''` dal seed vecchio), con
> l'estratto 8 su 8. I due pgTAP vicini (`test-fn-resolve-email-account`, `test-fn-email-sistema`) danno 7 e 12 ok
> con e senza. Il catalogo resta identico. La pagina `config/manual/email_account.md` è aggiornata.

**Chi cambia per primo**: il BE. Finché la PATCH scrive `''`, il DB non mette il `CHECK` su `email_reply_to`.
Messo prima, svuotare il campo dal pannello darebbe un `23514`. Quando il BE ha fatto il push, la sessione DB
scrive in `90_end` la conversione e il `CHECK` (`chk_email_account_email_reply_to_non_vuoto`), col suo
pgTAP.

## 8. Giro 2 — `name_template`, `trigger_name`, `causali` (applicato il 2026-11-12, pgTAP verdi)

| Colonna | Mirror e CSV | `90_end` | Presidio |
| --- | --- | --- | --- |
| `dbops.automation_rules_tbl.name_template` | `80_data/20250918-02` a `nullValue: "NULL"`; nel CSV 17 celle prendono `NULL` | `20261112-37`: conversione, poi `chk_automation_rules_tbl_name_template_non_vuoto` | `dbops/test-registri-automazioni-nomi-non-vuoti-v1` (plan 8, per tutte e due le colonne) |
| `dbops.automation_delete_block.trigger_name` | `80_data/20260123-11` a `nullValue: "NULL"`; nel CSV 8 celle prendono `NULL` | `20261112-38`: conversione, poi `chk_automation_delete_block_trigger_name_non_vuoto` | lo stesso |
| `magazzino.causali.user_insert` | `80_data/20251001-51`: `user_insert` e `user_update` escono dal CSV e da `columns:`; `nullValue` resta `""` | `20261112-39`: le audit vuote prendono il ruolo che migra, poi `user_insert` `SET DEFAULT CURRENT_USER` e `SET NOT NULL` | `magazzino/test-causali-audit-insert-v1` (plan 3) |

`NULLVALUE_DEBITO` è vuoto e il guardrail è verde. Sono aggiornate le pagine `manual/` di
`automation_rules_tbl`, `automation_delete_block` e `causali`.

**Censimento (§4 punto 3)**:

* *Chi legge i tre CSV*: solo il loro mirror. Su `causali.csv` ci sono anche due commenti
  (`00_schema/20260915-02`, `80_data/20260915-04`).
* *Chi scrive `name_template`*: il seed, e `80_data/20260110-13` (la regola `LOCK_COLUMNS`, col template).
  `80_data/20261109-74` aggiorna solo `existence_strategy`. I pgTAP inseriscono `NULL`.
* *Chi scrive `trigger_name`*: il seed. I pgTAP inseriscono senza la colonna, oppure con un nome vero.
* *Chi scrive `causali`*: il seed e il pannello di configurazione. La tabella è in `config.tabelle_gestibili`,
  e `config.fn_pannello_colonne_scrivibili` salta `user_insert` fra le colonne di sistema. Fino a questo giro,
  quindi, una causale creata dal pannello nasceva con `user_insert` `NULL`: ora prende il default.
* *Chi legge*: `fn_regola_automazione_valida` e `fn_nome_oggetto_dichiarato` usano già `NULLIF(btrim(…), '')`.
  Nessun lettore cambia comportamento, e i nomi dei trigger non cambiano.

**Prove fatte (2026-11-12)**:

* `scripts/prova_changeset.py`, sullo scratch:
  * `-37` e `-38` col test nuovo: senza l'estratto 3 ok e 5 not ok, con l'estratto 8 su 8;
  * `-37` e `-38` coi tre pgTAP vicini (`test-registro-regole-vincoli-v1`, `test-delete-block-convergenza-v1`,
    `test-cleanup-at-regola-unica-v1`): stesso esito con e senza (19, 16 e 14 ok);
  * `-39` col test nuovo: senza 0 su 3, con 3 su 3.

  Il catalogo resta identico.
* Render offline dei tre mirror: 17 `name_template = NULL`, 8 `trigger_name = NULL`. Gli `INSERT` e gli
  `UPDATE` di `causali` non nominano più `user_insert` né `user_update`.

**Note**:

* ⚠️ `causali.data_update` è anche lei fuori da §7: nullable e senza default. Il mirror la riempie con
  `defaultValue: "NOW()"`. Non è nel perimetro di D1-c: la decide Tid.
  Letto il 2026-11-12: il buco è nel contratto, non nel dato, perché `trgfn_audit_data_user_generic` la scrive
  sempre, in INSERT e in UPDATE. Secondo la doc auto-generata, la stessa forma (`data_update` nullable) ce
  l'hanno altre 12 tabelle, fra cui `config.tipi_soggetto*`, `forme_giuridiche*`, `stradario` e
  `magazzino.assets`: è un tema di famiglia, non di questo brief. Tid ha scelto di deciderlo a parte
  (2026-11-12): il giro 3 non la tocca.
* ✅ Il mirror delle regole dichiarava `- column: { name: rules_type }`, ma il CSV ha `rule_type`: la colonna
  si caricava dall'intestazione del CSV, quindi la riga non aveva effetto. Corretta nel giro 3 (2026-11-12, ok
  di Tid), con una nota di REV in testa al mirror. Il render offline è identico prima e dopo.
* Il mirror delle regole è in CRLF. Le righe nuove seguono il file, per non cambiarne il fine riga.

## 9. Il token `null` scritto a mano (aperto il 2026-11-12, dalla nota di `brief-db-lista-colonna-campo-sorgente-null` §5.3)

> ⚠️ **Superata da §9.1** (2026-11-12). La premessa è falsa: Liquibase 5.0.4 **non ha** un attributo
> `nullValue` sul change, e lo ignora. La proposta qui sotto (celle vuote al posto di `null`) è stata provata
> col render offline e **romperebbe l'apply**: la cella vuota di una colonna `STRING` arriva come `''`, e
> `utility_id` è intera. D2, approvata da Tid il 2026-11-12 nella forma (b), è sospesa in attesa di D3.

**Il comportamento di Liquibase**, letto sul bytecode di `tools/liquibase/5.0.4` (2026-11-12):

* il caricatore confronta la cella col `nullValue` in modo **esatto** (`LoadDataChange.isNullValue`); solo
  senza `nullValue` riconosce `NULL` senza distinguere maiuscole e minuscole;
* con `loadUpdateData` (tutti i mirror tranne due `loadData`) il valore passa poi da `CharType.objectToSql`,
  ereditato da `VarcharType`, che scrive SQL `NULL` per **ogni** stringa che in minuscolo è `null`. Sulle
  colonne `NUMERIC` fa lo stesso `setValueNumeric`;
* quindi con `loadUpdateData` una cella `null`, `Null` o `NULL` arriva al DB come NULL **qualunque sia il
  `nullValue`**, anche sotto `nullValue: ""`. Il caso di `loadData` (prepared statement) non è verificato.

**Il difetto** è della stessa famiglia di §1: la stessa assenza ha due grafie nel CSV, la cella vuota (il token
dichiarato) e la parola `null`. Chi legge il CSV senza conoscere questa regola del loader sbaglia in silenzio. È
il caso del BB `seed_csv` del backend, che confronta solo col `nullValue` e rende la cella `null` come stringa
`'null'`.

**Fatto datato** (scansione dei CSV di `80_data/sql/`, 2026-11-12): l'unico file con `null` scritto in una forma
diversa da `NULL` è `vendite/fatturazione_pipeline.csv`, colonne `utility_id` e `tipo_doc_fiscale_id` (8 righe
su 8), caricato da `20260128-06` con `nullValue: ""`. Su dbdev le 8 righe sono NULL in tutte e due le colonne.
Il dato non decide il giro: la regola vale per qualunque file.

**Proposta**:

* *DB*: nel CSV le 16 celle diventano vuote, cioè il token dichiarato dal mirror. Il DB non cambia, ma cambia
  il checksum del mirror, che va trattato come gli altri mirror toccati dai giri 1 e 2. Il guardrail
  `nullvalue-vuoto`, o una regola nuova dello stesso script, rifiuta una cella che in minuscolo è `null` ma non
  è il `nullValue` dichiarato.
* *BE* (richiesta, elenco chiuso): `backend/apps/core/tests/_seed_csv.py`, `seed_csv` rende `None` anche la cella
  che in minuscolo è `null`, oltre al token del file. Il test `backend/apps/core/tests/test_seed_csv.py` lo prova
  su un file costruito. Chi cambia per primo è indifferente: oggi nessun test legge `fatturazione_pipeline.csv`
  tramite `seed_csv`.

**D2 — Tid**: il giro si fa? E il presidio: si estende `nullvalue-vuoto` o nasce una regola a parte?

### 9.1 Che cosa fa davvero il caricatore (misurato il 2026-11-12)

**Il vicolo cieco, scritto perché non si riprovi.** Il giro D2 (b) ha portato a vuote le 16 celle `null` di
`fatturazione_pipeline.csv` e ha scritto la regola `null-scritto-a-mano`. Il render offline del mirror
(`updateSQL --url=offline:postgresql`, copia senza `preConditions`) ha dato `utility_id = ''`: su una colonna
intera l'apply si sarebbe fermato. Il CSV e la regola sono stati annullati prima di qualunque apply.

**I fatti** (bytecode di `tools/liquibase/5.0.4` e render offline sulla copia del mirror `20260128-06`):

* `LoadDataChange` **non ha** un attributo `nullValue`. I suoi setter sono `file`, `separator`, `quotchar`,
  `encoding`, `commentLineStartsWith`, `relativeToChangelogFile`, `usePreparedStatements`, `columns`. Il
  `nullValue:` scritto nei mirror (206 file in `db/changelog`) Liquibase lo **ignora senza errore**. Il segnaposto
  vero è `nullPlaceholder`, **per colonna** (`LoadDataColumnConfig`): nessun file di `db/changelog` lo usa.
* Senza `nullPlaceholder`, il caricatore riconosce come NULL la cella che è la parola `null` **in qualunque
  grafia** (`isNullValue` → `StringUtil.equalsWordNull`, `equalsIgnoreCase`). Il render lo conferma: `null`,
  `Null` e `NULL` diventano SQL `NULL`.
* Su una colonna `STRING` la cella vuota resta `''`; il render lo conferma.
* Prova del token inventato: il mirror copiato con `nullValue: XX` e una cella `XX` rende `utility_id = 'XX'`.
  L'attributo non ha effetto.

**Che cosa significa per il modello.**

* Il token NULL dei CSV di seed è **uno solo per tutto il progetto, `NULL`**, e non lo decide il mirror. I giri
  che sono passati a `nullValue: "NULL"` (giri 1 e 2 qui, `lista_colonna`) danno il risultato giusto, ma perché
  le celle scrivono `NULL`, non per il `nullValue`.
* `nullValue: ""` non ha mai fatto niente: la cella vuota di una `STRING` era `''` comunque. Il difetto di §1 è
  reale, ma non dipende dal `nullValue` dichiarato. Una cella vuota in una colonna testo nullable scrive `''`
  **anche** sotto `nullValue: "NULL"`. Il guardrail `nullvalue-vuoto` guarda solo i caricatori con
  `nullValue: ""`, quindi non vede gli altri.
* `fatturazione_pipeline.csv` non ha un difetto di dato: `null` è il token vero. Ha solo una grafia diversa
  dalla convenzione (`NULL`) e un `nullValue: ""` che non fa niente.
* Il BB `seed_csv` del backend (`token_nullo` legge il `nullValue`, e ne segue la regola per `lista_colonna.csv`)
  poggia sulla stessa premessa. La regola vera è più semplice: `None` per la cella che in minuscolo è `null`,
  `''` per la cella vuota, su ogni file.
* Le sedi che raccontano il `nullValue` come se funzionasse vanno lette e corrette: `linee-guida-sql` §11.7 e la
  riga «scrivere un `NULL`» della tabella in fondo, la testata della regola `nullvalue-vuoto`, il catalogo BB
  backend (`seed_csv`). Il censimento non è fatto.

**Da non dare per verificato**: le colonne `NUMERIC`, `DATE` e `BOOLEAN` con cella vuota (il render di prova non
ha cambiato il tipo della copia), e `loadData` con prepared statement (i due file `loadData`).

> ✅ **Decisa da Tid il 2026-11-12: (a).** Il giro è in `brief-db-token-null-dei-seed.md`, che riprende le misure di
> questa sezione e le completa (tutti i tipi di colonna, il checksum, il censimento di ogni caricatore).

**D3 — Tid**: come si riprende il tema?

* (a) ⭐ **La regola si riscrive sul comportamento vero, in un giro solo**: il token è `NULL`, scritto così;
  `nullValue:` esce dai mirror, perché dichiara una cosa che non succede (o resta, se Tid preferisce non toccare
  206 file, ma la linea guida dice che non conta niente); il guardrail `nullvalue-vuoto` guarda **ogni**
  caricatore, con qualunque `nullValue`; una regola nuova vieta `null` in una grafia diversa da `NULL`;
  `fatturazione_pipeline.csv` passa a `NULL`. Al BE si chiede di semplificare `seed_csv` (via `token_nullo` e il
  descrittore `CSV_SEED` per il token). Prima si misura il caso `NUMERIC`/`DATE`/`BOOLEAN`.
* (b) Solo la documentazione e il BB: si corregge ciò che si racconta, il guardrail resta com'è, e i 206
  `nullValue` restano come rumore innocuo.

Il tema è più largo di questo brief, che censiva cinque mirror: se Tid sceglie (a), è un brief suo (un tema, un
brief), e qui resta un rimando.
