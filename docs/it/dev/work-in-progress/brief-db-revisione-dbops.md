# Brief DB — Revisione dello schema `dbops`: i difetti di codice e i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-04

**Riparte: Tid**, con il commit del giro C1 (§10: undici changeSet `20261104-09` … `-19`, applicati e
verdi il 2026-11-04) e le decisioni di §4 per i giri A e B.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Revisione delle 239 pagine `dbops/manual/` allo standard (201 riscritte, 38 nuove); doc fuori schema corretta | §7 | — |
| 2 | ✅ Tid | Si parte dalla classe C; ritiri solo se certi; D17-bis e D74 rimandati (2026-11-04) | §10 | 1 |
| 3 | ✅ sessione DB | Giro C1 scritto e provato sullo scratch; doc riallineata | §10 | 2 |
| 4 | ✅ Tid | Apply del giro C1 su dbdev e scratch (`-09` … `-19`); pgTAP di §10.2 verdi (2026-11-04) | §10.2 | 3 |
| 5 | **Tid** ⏭️ | Commit del giro C1; le decisioni di §4 e l'ordine dei giri A e B di §8 | §4, §8 | — |
| 6 | sessione DB | Giri successivi, nell'ordine deciso da Tid; il residuo C (§10.4) | §8, §10.4 | 5 |
| 7 | team BE | Le ricadute di §5, quando il giro DB corrispondente è applicato | §5 | 6 |
| 8 | sessione DB | Pagine `manual/` riallineate a ogni difetto chiuso; brief in `work-done/` | §1 | 6 |

**Decisioni aperte di Tid:** quelle di §4. **Da committare:** questo brief e il giro C1 (§10.1), con la
doc riallineata.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-04. **A chi:** Tid e team DB; §5 al team BE.
> **Origine:** verifica delle pagine `docs/it/dbzero/dbops/manual/` contro lo standard e contro il
> codice, chiesta da Tid il 2026-11-03: «per la doc procedi, per le anomalie di sviluppo un brief».
> Stessa forma del precedente sullo schema `maintenance`
> ([brief-db-revisione-maintenance](../work-done/brief-db-revisione-maintenance.md), chiuso il 2026-11-03),
> di cui qui non si ri-segnala nessun punto chiuso.
> **Brief vicini verificati:**
> [framework-automazione-db-migliorie](framework-automazione-db-migliorie.md) (2026-03) tocca gli stessi
> runner delle automazioni, ma come elenco di migliorie: recupero da esecuzione parziale, naming del
> populate, trigger manuali contro generati, validazione dell'ambito. Si sovrappone solo a D41 (la parte
> fuori ambito) e a D17-bis (vocabolari chiusi, §2.4 di quel brief): lì vanno annotati, non rifatti. Se i
> due vanno fusi lo decide Tid.
> [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md) §8.1 censisce le fixture
> della bolla e il predicato «natura è merce»: D71 e D72 completano quel censimento. Nessun altro brief
> aperto tratta i difetti qui sotto.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata
(`docs/it/dbzero/<schema>/funzioni/…`), non dagli YAML citati qui: i riferimenti `file:riga` servono a
trovare il punto. Le righe `funzioni/…md:N` sono della scheda auto-generata al 2026-11-03.

⚠️ Ogni difetto è stato ricontrollato sul corpo dalla sessione che ha rivisto il lotto; D1, D3, D5 e D6
anche da chi scrive il brief (✔︎). Prima di scrivere il changeSet si riverifica sulla scheda del giorno.

## 1. Il perimetro

I difetti del **codice** e dei **metadati** dello schema `dbops`, più quelli di altri schemi trovati
leggendo i suoi chiamanti (§6). La documentazione è già allineata: le pagine `manual/` descrivono il
comportamento di oggi, difetti compresi, e vanno aggiornate quando un difetto si chiude.

Ogni difetto si regge sul modello, non su un conteggio: dove compare un numero è un fatto datato.

## 2. I difetti di codice

Forma compatta: **fatto** (dove e perché il modello non lo ammette) · **correzione** · **presidio**.

### 2.0 Le tre classi

I difetti sono esposti per tema (§2.1-§2.9); qui sono pesati. Per la regola zero tutti e tre i tipi
sono difetti: il peso dice l'ordine dei giri, non se si fanno.

* **A — contraddice un contratto deciso, o è sbagliato ogni volta che il ramo si percorre** con la
  configurazione e i seed di oggi (un presidio che dice il falso, una porta che fallisce appena la si
  usa, una fixture che produce una forma che l'applicazione non produce).
* **B — latente**: il modello ammette il caso, ma oggi nessun seed né configurazione lo produce (una
  regola scritta male, due FK corte verso lo stesso padre, un canale che cade, una corsa concorrente).
* **C — pulizia**: copie senza divergenza, oggetti senza chiamanti, etichette sbagliate senza effetto.

| Classe | Difetti |
| --- | --- |
| **A** | D1 (contratto del 2026-07-22: un dblink fallito restituisce la sentinella), D3, D4, D6, D14, D15, D21, D25, D30 (cinque righe del seed senza prefisso), D35, D36, D37, D40, D41, D43, D44, D46, D47, D51, D53, D54, D56, D57, D58, D59, D63, D64, D66, D67, D68, D70 |
| **B** | D2, D5, D7, D8, D9, D10, D11, D12, D13, D16, D17, D18, D19, D20, D22, D23, D24, D26, D27, D28, D29, D32, D33, D34, D38, D39, D45, D49, D52, D60, D69, D71, D73 |
| **C** | D17-bis, D42, D48, D50, D55, D61, D62, D65, D72, D74 — ✅ scritti nel giro C1 (§10) tutti tranne D17-bis e D74; di D61 restano i quattro strumenti DBA (Q9) |

⚠️ D31 non c'è: il ramo del `tx_id` non registrato l'ha già giudicato il brief chiuso
`brief-db-coerenza-tx-id-non-registrato` (2026-07-22), e resta solo il COMMENT falso (M11).

### 2.1 I difetti puntuali del modello

#### D1 ✔︎ — `fn_get_or_create_session_tx_id`: un canale di log irraggiungibile blocca ogni scrittura tracciata

* **Fatto.** `PERFORM script.fn_ensure_logconn()` (`funzioni/fn_get_or_create_session_tx_id.md:43`) sta
  fuori dal blocco protetto (`:83`). `fn_ensure_logconn` assorbe solo `duplicate_object` e `53300`: un
  errore di connessione di classe 08 risale a `trgfn_tx_id_managed`, che lo trasforma in
  `E_TXID_GENERATION` e solleva. Con `myapp.dblink_log_connection` impostato e il canale giù, fallisce
  ogni INSERT/UPDATE senza `tx_id` su ogni tabella tracciata, e `script.fn_log_error_only` smette di
  registrare e comincia a sollevare. Il commento dice «non blocca mai il chiamante».
* **Correzione.** La chiamata dentro il blocco protetto, o `fn_ensure_logconn` che assorbe ogni errore
  di connessione con un WARNING; commento corretto.
* **Presidio.** pgTAP con una stringa di connessione che non si connette e `logconn` assente: la
  funzione restituisce `uuid_nil` senza sollevare, un INSERT su una tabella tracciata riesce.

#### D2 — Parametri `CLEANUP` non validati: un termine malformato ferma il giro e gli INSERT dei registri

* **Fatto.** `ttl_days`, `apply_on_update`, `batch_limit` si convertono fuori dalla rete degli errori
  (`funzioni/fn_run_automations_cleanup.md:126-127,244`) e, per `ttl_days`, in un `BEFORE INSERT`
  (`funzioni/trgfn_cleanup_at_alla_nascita.md:53`). `automation_rules_tbl.params` non ha CHECK. Un
  `ttl_days` non numerico rende impossibile scrivere su `event_log`, `request_log`, `idempotency_keys` e
  sui registri dei login (il login fallisce); uno negativo fa nascere righe già scadute.
* **Correzione.** Validare i `params` quando la regola entra (CHECK o guard: intero ≥ 0, booleano,
  > 0), oppure conversioni dentro la rete con un salto `INVALID_PARAMS`.
* **Presidio.** pgTAP: una regola con `ttl_days` testuale è respinta; il runner in simulazione la salta.

#### D3 ✔︎ — `fn_admin_merge_stradario`: la fusione fallisce appena la via ha un indirizzo

* **Fatto.** L'UPDATE di `anagrafiche.indirizzi_dettaglio.stradario_id` (`funzioni/fn_admin_merge_stradario.md:63-64`)
  non accende `zeroerp.maintenance_indirizzi_dettaglio`: `trgfn_indirizzi_dettaglio_protect_update`
  rifiuta con `E_COLONNA_NON_MODIFICABILE` e la fusione si annulla. Due indirizzi identici sulle due vie
  collidono su `uq_indirizzi_dettaglio_norm_v2`. D8 del brief maintenance dice che «nessun verbo» sposta
  gli indirizzi su un'altra via: il verbo c'è, ed è questo, ma non apre la porta.
* **Correzione.** Se è la riclassificazione delle vie (decisione §4): flag acceso con `set_config(…, true)`
  solo attorno all'UPDATE, spento all'uscita e nel gestore; regola sui doppioni (rifiuto con codice o
  unione). Altrimenti ritiro.
* **Presidio.** pgTAP con due vie e un indirizzo: la fusione lo ripunta, e subito dopo il cambio a mano è
  ancora rifiutato; più un caso col doppione.

#### D4 — `fn_admin_merge_comune` ripunta solo lo stradario

* **Fatto.** L'unico UPDATE è su `config.stradario.comune_id`. Restano sul comune soppresso
  `config.codici_postali`, `anagrafiche.indirizzi`, `anagrafiche.soggetti`,
  `anagrafiche.indirizzi_soggetti`, `vendite.area_geografica_fatturazione_comuni` (tutte FK `comune_id`);
  `uq_stradario_comune_stradario_gen_cp` può respingere l'UPDATE. Il COMMENT dice «chi riferiva l'origine».
* **Correzione.** Figlie derivate da `pg_constraint`, regola sulle collisioni; oppure COMMENT ristretto.
* **Presidio.** pgTAP: dopo la fusione nessuna figlia (da `pg_constraint`) nomina l'origine.

#### D5 ✔︎ — `trgfn_child_requires_active_parent`, `trgfn_child_requires_non_obsolete_parent`: il ramo «padre non trovato» non scatta mai

* **Fatto.** `IF NOT FOUND` dopo `EXECUTE … INTO` (`funzioni/trgfn_child_requires_non_obsolete_parent.md:128-130`):
  `EXECUTE` non aggiorna `FOUND`, che resta quello della `SELECT INTO` precedente. Su un require
  polimorfo senza FK, un padre assente risponde «padre non attivo» nel primo e lascia passare la scrittura
  nel secondo.
* **Correzione.** `GET DIAGNOSTICS … ROW_COUNT`, o `INTO STRICT` con `NO_DATA_FOUND`.
* **Presidio.** pgTAP su TEMP: require polimorfo verso un id inesistente, per entrambe.

#### D6 ✔︎ — Il riconoscimento dei trigger ATTIVO per argomenti non riconosce niente

* **Fatto.** `fn_trigger_exists_block_by_args` e `…_require_by_args` cercano gli argomenti separati da
  `','` (`funzioni/fn_trigger_exists_block_by_args.md:32`), ma `pg_get_triggerdef` li scrive separati da
  `', '`: rispondono sempre falso. Tutte e tre, con `fn_drop_triggers_by_function_args`, cercano
  `dbops.<funzione>(`: PostgreSQL scrive lo schema solo se non è nel `search_path`, e `dbops` è nel default
  di `zeroerp_app` (`scripts/sql/provision_zeroerp.sql:312`). `ILIKE` tratta `_` come jolly. Le strategie
  `BY_FUNCTION`/`BOTH` per ATTIVO sono quindi finte: con `BOTH` (il seed) decide il solo nome, con
  `BY_FUNCTION` ogni giro toglie e ricrea, e la riconciliazione dipende da chi lancia il runner.
* **Correzione.** `t.tgfoid` contro la funzione risolta per schema e nome, e
  `dbops.fn_trigger_argomenti(t.tgargs)` uguale all'array atteso, nelle tre.
* **Presidio.** pgTAP su TEMP: block/require montati dal generatore riconosciuti; un argomento diverso no;
  stesso esito con `dbops` nel `search_path`.

#### D7 — `vw_riferimenti_morti_rientrati`: con la misura fallita dà per rientrate le voci del registro

* **Fatto.** Cerca per ogni voce un difetto `REALE`/`ORFANA` (`views/vw_riferimenti_morti_rientrati.md:24-27`):
  se `plpgsql_check` non ha misurato la funzione esentata (`NON_MISURATO`), la voce esce «da togliere».
  Il guardrail CI conosce il caso e si ferma prima (`scripts/sql/guardrail_riferimenti_morti.sql:84-114`),
  la vista e il digest no. Le anti-join sono scritte due volte, nelle viste e nel guardrail.
* **Correzione.** Escludere le voci con `NON_MISURATO`, o niente righe se la misura ne ha; valutare un
  guardrail che legge le viste.
* **Presidio.** pgTAP con una voce su una funzione costruita perché `plpgsql_check` sollevi.

#### D8 — `vw_duplicate_indexes` propone di togliere l'indice che regge un vincolo

* **Fatto.** Esclude solo la chiave primaria e ordina per `indisunique DESC, indexrelid`
  (`views/vw_duplicate_indexes.md:30,42`): fra due UNIQUE identici può proporre il DROP di quello del
  vincolo, o della replica identity. La sorella per prefisso li esclude.
* **Correzione.** Indici di vincolo (`conindid`) e di replica identity prima nell'ordinamento, ed esclusi
  da `indici_da_droppare`.
* **Presidio.** pgTAP con due UNIQUE identici, uno di vincolo.

#### D9 — `fn_accoda_lavoro` può restituire un id vuoto senza aver accodato

* **Fatto.** Dopo `INSERT … ON CONFLICT DO NOTHING RETURNING id` vuoto, la rilettura
  `stato IN ('PENDING','IN_CORSO')` prende uno snapshot nuovo: se il drenatore ha chiuso il lavoro vivo
  nel frattempo, la funzione restituisce NULL. `fn_accoda_chiusura_scadenze` conterebbe l'azienda come
  accodata, e la sua chiusura slitterebbe alla sveglia dopo.
* **Correzione.** Ripetere l'INSERT se la rilettura non trova il vivo (ciclo dell'upsert), o sollevare.
* **Presidio.** pgTAP a due sessioni (dblink).

#### D10 — `fn_run_automations_attivo`: due FK dalla stessa figlia allo stesso padre, la seconda resta scoperta

* **Fatto.** Template `trg_{child}_a10_{parent}_require_attivo_ins_upd_{fkhash6_if_long}`
  (`80_data/sql/dbops/automation_rules_tbl.csv:4`): l'hash entra solo oltre 63 caratteri, due FK corte
  della stessa coppia danno lo stesso nome e con `BOTH` il runner salta la seconda.
* **Correzione.** `{fkhash6}` sempre, dopo il censimento dei nomi condivisi su dbdev.
* **Presidio.** pgTAP su TEMP con una figlia a due FK: due require e due block.

#### D11 — `dbops.processi`: il ritiro ha due colonne, e i lettori ne leggono una ciascuno

* **Fatto.** Regola di accensione, guard della scelta a mano e sveglia guardano solo `obsoleto_dal`
  (`funzioni/fn_processo_acceso_su_valori.md:23`, `trgfn_processi_accensione_guard.md:57`,
  `maintenance/funzioni/fn_sveglia_accesa.md:51`, `chk_processi_accensione`); panorama, presidi e roster
  `attivo AND obsoleto_dal IS NULL` (`views/vw_processi_programmazione.md:69`, `vw_processi_roster.md:29`).
  Un processo `attivo = false` senza data ha la sveglia accesa, gira, e il panorama non lo mostra.
* **Correzione.** Un CHECK che vieta `attivo = false` senza `obsoleto_dal` (una sede sola del ritiro),
  oppure la regola che legge anche `attivo` (decisione §4).
* **Presidio.** pgTAP costruito sul ramo scelto.

#### D12 — `trgfn_tx_id_managed`: senza il parametro del bypass, l'override di sessione è ignorato

* **Fatto.** Senza riga `tx_id_bypass_enabled` (o con `default_value` NULL) `v_bypass_enabled` resta NULL
  (`funzioni/trgfn_tx_id_managed.md:53`), `IF NOT v_bypass_enabled` (`:93`) non entra e
  `myapp.bypass_tx_id_check` non si legge. `E_ERRORE_PARAMETRI_TABELLA` qui non blocca, contro la
  convenzione E_/W_.
* **Correzione.** `COALESCE(v_bypass_enabled, false)`; un `W_` dedicato, registrato.
* **Presidio.** pgTAP senza la riga del parametro e con il bypass di sessione: sentinella, nessuna generazione.

### 2.2 La stessa regola scritta più volte, già divergente (regola del 2)

| # | Regola | Dove sono le copie | Correzione | Presidio |
| --- | --- | --- | --- | --- |
| D13 | **L'ambito di una corsa** | `fn_run_automations` (`:31-50`) ricalcola invece di chiamare `fn_resolve_scope` (`:22-55`); `fn_resolve_scope` non fa DISTINCT sul registro né `btrim` sull'elenco del chiamante; `fn_seed_fk_index_policy` (`:36`) guarda solo lo schema e ignora `table_like`, e da zero gira prima del seed dell'ambito (`20_code/dbops/20260116-06…:12`), quindi non registra niente | Tutti passano da `fn_resolve_scope` + `fn_table_in_scope`; `array_agg(DISTINCT btrim(…))` | pgTAP su `fn_resolve_scope` (spazi, `*all`, vuoto, schema su più righe); presidio sul testo: nessun runner legge `automation_scope` direttamente |
| D14 | **Il corpo di una funzione senza commenti** | `vw_codici_errore_da_dichiarare`, `vw_bersagli_non_dichiarati`, `vw_magazzino_dipendenze_inverse` tolgono solo `--`; `vw_funzioni_check_codici`, `vw_punti_canale_campo` anche `/* */`; `vw_codici_errore_forme_condizione` solo le righe che iniziano con `--`; `vw_punti_primo_motivo` niente; anche `vw_audit_log_scrittori_fuori_perimetro`, `vw_stati_check_scrittori`. Nessuna rispetta un `--` dentro un letterale: un codice dopo `'--'` sfugge a un cancello, un nome in un commento a blocco accende un cancello | Un BB `fn_prosrc_senza_commenti(text)` IMMUTABLE che rispetta i letterali; censimento con grep `regexp_replace(p.prosrc` | pgTAP con una funzione in `pg_temp` (codice in commento a blocco, codice dopo `'--'`) + presidio sul testo che le viste chiamano il BB |
| D15 | **Il corpo di una funzione `BEGIN ATOMIC`** | `vw_audit_log_scrittori_fuori_perimetro` (`:23`), `vw_stati_check_scrittori` (`:42`, include `lanname = 'sql'`), `fn_find_function_usage` (`:27`), `fn_search_column_usage` (`:62`) leggono `prosrc`, vuoto per `BEGIN ATOMIC` (linee guida SQL §5c): un cancello non vede lo scrittore, un `ESENTE` non diventa mai `DEBITO_ESTINTO` | `prosrc` + `pg_get_functiondef` dove `prosqlbody IS NOT NULL`; si fonde con D14 nello stesso BB | Una `BEGIN ATOMIC` costruita in `test-audit-log-perimetro-scrittori-v1.sql` e `test-stati-check-scrittori-v1.sql` |
| D16 | **La scadenza `CLEANUP_AT`** | `fn_cleanup_at_params` (`:55-64`) prende una regola, senza `exec_mode` né esclusioni; il runner (`fn_run_automations_cleanup.md:66-101`) tutte, con i filtri; senza `base_ts_column` il trigger alla nascita usa `now()` (`:68`), il runner la catena `data_insert` → `executed_at` → `occurred_at` → `created_at` (`:130-140`); il trigger scrive sempre `cleanup_at`. Una tabella esclusa col trigger riceve scadenze mai purgate | Un risolutore unico usato da trigger e job, con filtro, esclusioni e catena; il trigger scrive la colonna dichiarata | pgTAP: due regole sulla stessa tabella, una esclusa, una con solo `executed_at` → stessa scadenza da trigger e job |
| D17 | **La strategia di esistenza** | Ricopiata in `fn_run_automations_tx_id` (`:120-123`), `_audit_update` (`:89-92`), `_storico` (`:130-133`), `_date_validita` (`:90-93`), `_attivo`; un valore diverso da `BY_NAME`/`BY_FUNCTION`/`BOTH` vale «c'è già», in silenzio | `dbops.fn_trigger_esiste(rel, strategia, nome, schema_fn, nome_fn)` che rifiuta una strategia sconosciuta | pgTAP con una strategia sconosciuta: errore o `WARN`, non silenzio |
| D17-bis | **I vocabolari del registro delle regole** | `rule_type`, `exec_mode`, `existence_strategy`, `col_role` sono `text` senza CHECK; `exec_mode` non si normalizza (anche `fn_run_automations_storico_provision` confronta letterale, `_storico` con `upper(btrim)`) | CHECK sui valori, con bonifica — da annotare in `framework-automazione-db-migliorie` §2.4 | INSERT fuori vocabolario che fallisce |
| D18 | **La grammatica degli argomenti dei trigger ATTIVO** | Minimi (3 e 4) e default (`id`, `attivo`) in `fn_trigger_attivo_orfani` e nelle due trgfn; `fn_ritira_attivo_eccezioni` indicizza le posizioni | Una funzione che restituisce gli argomenti normalizzati per nome (linee guida trigger, lettori di `tgargs`) | pgTAP di confronto su trigger di fixture |
| D19 | **Il nome del trigger DELETE_BLOCK** | Composto nel runner (`fn_run_automations_delete_block.md:59-62`) e in `fn_apply_delete_block_trigger.md:39-42`, senza `fn_name_from_template` e il primo senza `NULLIF`: `trigger_name = ''` annuncia «would be created» a ogni giro; una tabella oltre 38 caratteri fa troncare il nome, il controllo per nome non lo trova e il giro dopo prende 42710 (`E_DELETE_BLOCK`) | Nome composto in un posto, con `fn_name_from_template` e `NULLIF` | pgTAP su una tabella di 50 caratteri: due giri, un trigger |
| D20 | **Il nome del trigger di storico** | Ripiego `trg_z90_{table}_storico_upd_dlt` (`fn_run_automations_storico.md:115`) contro il seed `trg_{table}_z90_storico_upd_dlt` (`automation_rules_tbl.csv:6`): una regola `STORICO` senza template monterebbe un secondo trigger | Default uguale al seed, o `name_template` obbligatorio per `STORICO` | CHECK o pgTAP |
| D21 | **Le vie dell'emittente** | `chk_processi_bersagli_via` (`00_schema/dbops/20260904-08…:84`): fiscale, soggetto_ruolo, fattura, contabile, padre; `script.trgfn_guard_emittente_scope` e il risolutore: soggetto_ruolo, fattura, fiscale, contabile, listino, magazzino. Il COMMENT (`:99`) dice «stesso vocabolario» | Una sede del vocabolario, con listino e magazzino, `padre` ricondotto alla via vera | pgTAP che confronta il CHECK con i modi del risolutore letti dalla definizione |
| D22 | **La convenzione dei codici errore** | CHECK `chk_messaggi_errore_codici_legacy_non_conforme` (`00_schema/dbops/20260805-28…:84-85`) e `c_convenzione` in `scripts/sql/guardrail_codice_errore_strutturato.sql:65-77`, che dice «deve restare IDENTICO … nessuno se ne accorge» | Una funzione IMMUTABLE usata da entrambi, o il guardrail che legge `pg_constraint` | pgTAP |
| D23 | **Il nome dell'indice di una riga di policy** | `vw_indici_ridondanti_prefisso` (`:56`) con un LIKE sul nome dell'indice seguito da «ON» (suffissi e `_` jolly → falso `AUTOMAZIONE_FK`); `apply_fk_index_policy` con la sesta parola | Una funzione unica | pgTAP con un nome suffisso di un altro |
| D24 | **Il pattern di un parametro FK surrogato** | `vw_parameter_fk_surrogate_dangling` (`:22,34`) unisce tutti i pattern; `script.fn_check_parameter_fk_surrogate` (`:58`) ne sceglie uno (EXACT, poi il più lungo) | Un risolutore unico, la vista con `LATERAL … LIMIT 1` | pgTAP con EXACT e LIKE sullo stesso codice |
| D25 | **Il lock implicito di `codice_interno`** | `fn_lock_columns_divergenze` (`:79`) lo mette nel lock atteso di ogni tabella che ha la colonna; `vw_non_editable_fields` (`:20-21`) legge solo il registro e non filtra `exec_mode`; il BE compensa a mano (§5) | Un risolutore unico del lock atteso letto da vista e runner | pgTAP: tabella con `codice_interno` e senza riga → `fn_non_editable_fields` lo elenca |
| D26 | **L'interruttore `myapp.log_with_dblink`** | Assente = spento in `fn_audit_*`, acceso in `script.fn_ensure_logconn` (`:23`); `fn_get_or_create_session_tx_id` lo aggira se c'è la stringa di connessione (`:98-123`) | Un BB «il canale è acceso?» con un default solo | pgTAP con `off` e la stringa impostata: sentinella, GUC non pubblicato |
| D27 | **I nomi delle colonne di audit** | `fn_run_automations_audit_update` usa gli override `AUDIT_TS`/`AUDIT_USER` (`:78-79`) solo per decidere se montare; il trigger nasce senza argomenti (`:114-118`) e `script.trgfn_audit_data_user_generic` scrive nomi fissi: con l'override il trigger fallisce alla prima scrittura | Argomenti al trigger, o ritiro della manopola | pgTAP con colonne rinominate e override |
| D28 | **Le condizioni strutturali della distinta** | Le `condition_expr` di `lock_columns_conditional` su `is_composito`, `requires_serial`, `is_solo_componente` (`80_data/changelog/20260522-04…`, `20261013-04…:57`) ricopiano l'`EXISTS` di `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva` (già divergite: `CURRENT_DATE` contro `fn_data_operativa`) | Predicati in funzioni `catalogo.fn_*`, come `fn_articolo_usato` | pgTAP: guard e `fn_non_editable_fields` rispondono uguale |
| D29 | **«Il reso ha fatto rientrare la merce»** | `vw_resi_confermati_senza_carico` con il letterale `'CONFERMATO'`; la gemella della bolla legge `script.vw_stati_doc_ddt_merce_partita` dal 2026-10-12 | BB gemello `script.vw_stati_doc_reso_merce_rientrata` | Test sul viewdef, come il test 8 di `test-vw-stati-doc-ddt-merce-partita-v1.sql` |
| D30 | **Le colonne del guard utility/tipo ruolo** | `fn_apply_automazione_guard_utility_tipo_ruolo` filtra `LIKE '%_soggetto_ruolo_id'` e scarta `soggetto_ruolo_id` (cinque righe del CSV); colonne inesistenti saltate senza traccia, nessun audit, dry run vuoto; lo stesso filtro nel ripiego del seed | Decidere se la forma senza prefisso è ammessa (CHECK sul catalogo o filtro tolto); salti `WARN`, dry run `DRYRUN` | pgTAP con una riga senza prefisso e una con colonna inesistente |

### 2.3 Registri che aggiungono e non tolgono

Tre registri delle automazioni montano oggetti ma non li smontano: il registro dice una cosa e il
database un'altra. Per i lock di colonna il framework ha già adottato la convergenza; conviene
decidere la regola una volta per tutti e tre (§4).

| # | Registro | Fatto | Presidio |
| --- | --- | --- | --- |
| D32 | Lock di colonna | `fn_lock_columns_divergenze` parte da `JOIN regola` (`:145`): un lock montato su una tabella senza regola attiva è invisibile, e spegnendo la regola i lock restano vivi. `test-lock-columns-convergenza.sql` test 4 si dice presidio «su tutto il database» | Un lock montato a mano su una tabella senza regola fa rosso |
| D33 | DELETE_BLOCK | Il trigger si crea se il nome manca e non si toglie mai: `enabled = false`, riga cancellata, `guc_key` cambiato non arrivano al trigger; un `trigger_name` cambiato ne monta un secondo | Spegnere una riga toglie il trigger |
| D34 | Guard utility/tipo ruolo | L'apply legge solo `enabled = true`, e `DROP TRIGGER IF EXISTS` colpisce solo il nome di oggi | Accesa → spenta → rinominata |

### 2.4 Promesse senza esecutore

| # | Che cosa promette | Che cosa succede | Correzione / presidio |
| --- | --- | --- | --- |
| D35 | `shop.ricevute` ha `storicizza DEFAULT true` e `tx_id` | `shop` non è in `automation_scope.csv`: nessun trigger generato, nessuna `storico.ricevute` | Decidere per `shop` (§4); in generale una tabella con colonna-marcatore di automazione sta nell'ambito o è esclusa dichiarata. Presidio: censimento delle colonne-marcatore fuori ambito |
| D36 | `dbops.ai_query_log` ha `cleanup_at`, il COMMENT dice «retention via cleanup_at» | Fuori ambito, nessuna regola `CLEANUP_AT`, nessun trigger alla nascita: le righe (testo digitato dagli utenti) non scadono mai | Scope + regola (termine: §4) + trigger alla nascita; estendere `test-registri-dbops-scadenza-v1.sql` |
| D37 | `dbops.audit_sources` ha `data_update`, `user_update`, `tx_id`, `storicizza` | Fuori ambito: nessuno le scrive, `storicizza = true` non produce storico | Ambito o colonne tolte (§4). Presidio: ogni tabella con `tx_id` ha `trgfn_tx_id_managed`, salvo registro del debito |
| D38 | `automazione_chiusura_scadenze.classe` separa le nature dei bersagli | L'unico chiamante, l'handler della coda, non passa `p_classe` (`backend/apps/core/services/coda_lavori/chiusura_scadenze_handler.py:60`): un bersaglio `MANUTENZIONE`/`AMMINISTRAZIONE`, che il CHECK ammette, verrebbe lavorato con l'identità e la RLS di ogni azienda | (a) solo `DOMINIO` sulle righe attive + handler che passa `'DOMINIO'` (§5), o (b) un esecutore `SISTEMA` |
| D39 | `automazione_chiusura_scadenze.verbo_chiusura` | Porta e verbo si guardano solo nel ramo `FK`: nel ramo `VARCHAR` l'UPDATE è sempre dinamico (sotto la porta fallisce con `E_DOC_STATO_SOLO_DAL_VERBO` invece dell'errore di configurazione), nel ramo `FK` senza porta un verbo dichiarato è ignorato | Porta e verbo valutati prima del dispatch; verbo senza porta → `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` con un motivo nuovo, o verbo usato sempre. Presidio in `test-fn-apply-chiusura-scadenze-v1` |
| D40 | `fn_run_automations_cleanup`: «un rifiuto non ferma il giro» | `RETURNS void`: le tabelle bloccate vanno solo in `audit_log` (`BLOCKED_BY_TABLE`), la corsa resta verde in `vw_job_run_da_guardare` (D5 del brief maintenance non esteso qui) | Un riepilogo jsonb con `_falliti`; estendere `test-cleanup-framework.sql` |
| D41 | `fn_run_automations_delete_block` | Nel giro vero non scrive audit (`:82-104`); la tabella sparita solo nel dry run (`:39-56`); una riga fuori ambito ignorata senza traccia (`:31-33`, da annotare in `framework-automazione-db-migliorie` §2.4) | Audit `OK` e `WARN TABLE_NOT_FOUND` sempre |
| D42 | `vw_run_senza_attore` misura un debito | Dal CHECK `chk_job_run_log_processo_dichiarato` (`90_end/20260905-16…:85`) il debito non può più nascere: in vista restano per sempre i job la cui ultima corsa è anteriore | Ritiro del presidio (`obsoleto_dal` in `presidi.csv`) o filtro sui processi vivi (§4) |
| D43 | `vw_processi_che_bypassano` | Classifica `DEBITO_DICHIARATO` il ruolo `zeroerp_batch_fatturazione`, ritirato il 2026-10-15, e scrive su ogni riga la nota fissa «ritiro previsto alla fase 6-bis» (`views/vw_processi_che_bypassano.md:16,19`): se il ruolo tornasse con BYPASSRLS il presidio tacerebbe | Nome e nota tolti. Presidio in `test-processi-registro.sql` |

### 2.5 Codici errore

| # | Dove | Fatto | Correzione |
| --- | --- | --- | --- |
| D44 | `fn_check_pipeline_task_registered` (`:33,42,62`), `fn_get_pipeline_task_implementation` (`:33,42,87`) | `E_GENERICO` con nomi di parametro nel VARIADIC (linee guida §5); «task non registrato» arriva come 500 | `E_PIPELINE_TASK_HANDLER_NOT_FOUND` / `E_PIPELINE_TASK` (già registrati); `throws_ok` nei test 7-8 di `test-pipeline-task-registry.sql` |
| D45 | `fn_admin_merge_comune`, `fn_admin_merge_stradario` | Tre `RAISE EXCEPTION` in chiaro ciascuna; il debito sta solo in un brief chiuso | `E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`, `E_COMUNE_NON_TROVATO`, `E_STRADARIO_NON_TROVATO`, nel giro di D3/D4 |
| D46 | `trgfn_child_requires_active_parent` | Ogni rifiuto, anche «padre non attivo», esce con `E_ATTIVO_REQUIRE`, classe `TECNICO` (`codici_errore.csv:64`); il BE lo aggira con controlli preventivi (§5) | Un codice `CONFLITTO_STATO` sul modello del block; `E_ATTIVO_REQUIRE` resta per il montaggio |
| D47 | `trgfn_child_requires_non_obsolete_parent` | Argomenti insufficienti e colonne mancanti escono con `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (un 409 per l'operatore) | `E_TRIGGER_ARGOMENTI_INVALIDI` (`codici_errore.csv:699`) nei rami di configurazione |
| D48 | `dbops.automation_lock_columns.error_code` | DEFAULT `'CODICE_NON_MODIFICABILE'` (`00_schema/dbops/20260110-11…:42`), ritirato il 2026-08-05 (`codici_errore.csv:3`); il `COALESCE` di `fn_lock_columns_divergenze` (`:85`) è morto perché la colonna è NOT NULL | `DROP DEFAULT` o `E_CODICE_NON_MODIFICABILE`; `COALESCE` tolto |
| D49 | `trgfn_prevent_deactivate_if_children`, `trgfn_child_requires_active_parent` | Con un argomento facoltativo mancante il ripiego scrive in `error_log` a ogni scatto (lo stesso difetto chiuso il 2026-08-05 per `E_ATTIVO_BLOCK_REF_NULL`) | Argomenti obbligatori, dopo il censimento dei montaggi |
| D50 | `fn_run_automations_tx_id` (`:130`) | La riga `DRYRUN` ha `rule_type = 'E_TX_ID'` | `'TX_ID'` |

### 2.6 Chi legge e con quali occhi

* **D51 — I guard ATTIVO leggono figli e padre sotto la RLS di chi scrive.** `trgfn_prevent_deactivate_if_children`
  e `trgfn_child_requires_active_parent` sono `INVOKER` con `EXECUTE` dinamici sulle tabelle di dominio
  (`db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql:157-166` lo documenta): il block lascia spegnere
  un padre con figli attivi fuori perimetro; il require, differito, conta il contesto al commit.
  Correzione: le due letture in una funzione `SECURITY DEFINER` del migratore con `search_path` stretto.
  ⚠️ Cambia il comportamento delle fixture che chiudono i differiti «nei panni di chi ha scritto»: §4.
* **D52 — Il proprietario della shadow si controlla per nome.** `fn_storico_arma_scope` (`:47-59`) e
  `fn_storico_backfill_scope` (`:115-118`) procedono solo se `v_owner = current_user`;
  `fn_ensure_storico_table` (`:203-204`) usa `pg_has_role(…, 'MEMBER')`. Un membro di `zeroerp_owner`
  senza `SET ROLE` prende un falso `SKIP_OWNER`. Correzione: membership nei due punti. Presidio: un ruolo
  membro arma una shadow di prova e ottiene `ALLINEATA`.

### 2.7 Strumenti che rispondono in modo sbagliato

| # | Oggetto | Fatto | Correzione |
| --- | --- | --- | --- |
| D53 | `fn_find_file_usage` (`:34,37`), `fn_foreign_keys_info` (`:35,39,56`) | Prodotto cartesiano sulle FK composite; la seconda unisce i vincoli per nome senza tabella, filtra senza schema, dipende da `information_schema`. Stessa domanda in due funzioni, nessun chiamante | Una funzione su `pg_constraint` con `unnest(conkey, confkey) WITH ORDINALITY`; l'altra si ritira (o entrambe: §2.8) |
| D54 | `fn_search_column_usage` (`:73`) | Il ramo dei vincoli cerca in `conbin`, dove le colonne sono `:varattno N`: risponde sempre vuoto | `pg_get_constraintdef` o `conkey` |
| D55 | `vw_function_list` (`:23,27`) | `num_args` conta le virgole (sbaglia con `numeric(p,s)`, NULL a zero argomenti); `pg_description` senza `classoid`/`objsubid` | `pronargs`, `obj_description(oid, 'pg_proc')` |
| D56 | `vw_codici_errore_forme_condizione` | `(regexp_match(riga, …))[1]`: un solo codice per riga, il secondo si perde | `dbops.fn_regexp_occorrenze`; baseline B-7 rigenerata, con la ragione nel commit |
| D57 | `fn_get_lookup_codici` e il suo unico consumatore | La paginazione del BE è corretta: chiama con offset 0, ordina col BB `sql_order_clause` con spareggio `id` e ricalcola il totale con `fetch_paged_with_total` (`backend/apps/core/db/dbops_repository.py:415-470`, dal 2026-09-26). Ma passa `p_limit = LOOKUP_MAX_SOURCE_ROWS` (10 000, `:55`) e applica la ricerca **dopo** il taglio: su una tabella più lunga del tetto la ricerca non vede le righe oltre, e quali restano fuori lo decide l'`ORDER BY` della funzione, che non ha spareggio. `p_offset` e l'ordinamento della funzione non li usa nessuno | Il filtro di ricerca dentro la funzione (parametro `p_search`, prima del `LIMIT`), oppure nessun tetto interno; ritirare `p_offset`. Ricaduta BE (§5, BE4) |
| D58 | `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico` | `NOT EXISTS` su tutto il documento, mentre il contratto del posting è un movimento per prelievo e un carico per rientro: lo scarico parziale non accende niente | Domanda alla grana di prelievo/rientro |
| D59 | `fn_apply_automazione_overlap` | Una colonna di chiave inesistente si salta in silenzio: il vincolo nasce con una chiave più corta (più severo), e l'audit `OK` riporta la chiave registrata | Tutte le colonne devono esistere, altrimenti `WARN KEY_COLUMN_MISSING` |
| D60 | `fn_audit_begin`, `fn_audit_end`, `fn_audit_log_once` — ramo dblink | Il ruolo del canale ha diritti solo su `error_log` e `job_run_log` (`scripts/sql/provision_dblink_log_channel.sql:45-51`); `p_parts` NULL diventa `'null'::text[]`; `p_params` NULL il JSON `null`; `fn_audit_end` senza `COALESCE` (`:42-48` contro `:61-67`); il `tx_id` è quello della sessione remota. Acceso, fa fallire la transazione del chiamante | Ritiro del ramo (`begin`/`end` non hanno chiamanti), o grant + `tx_id` esplicito + costruzione unica (§4) |

### 2.8 D61 — Oggetti da ritirare in un changeSet solo

Senza chiamanti in `db/`, `backend/`, `scripts/`, `db/pgtap/`, e con risposte sbagliate o copie di regole
vive. Con il ritiro si cancellano le pagine `manual/` (non si lasciano monconi). Presidio: `hasnt_function`
o `dbops.vw_riferimenti_morti_da_sanare`.

| Oggetto | Perché | Decisione |
| --- | --- | --- |
| `fn_rename_triggers_by_order`, `fn_fix_triggers_events_noorder`, `fn_cleanup_triggers_suffix_2`, `fn_fix_lock_codice_interno_triggers` | Utility una tantum del primo albero (`migrations/50_dbops/20250921-01…`, `20250922-05/-06/-07…`), tre eseguite davvero. Rinominano anche i `CONSTRAINT TRIGGER` con `ALTER TRIGGER` (nome morto in `pg_constraint`), producono nomi fuori dalla regola di oggi, montano lucchetti fuori registro; il DROP di `suffix_2` è irraggiungibile | Ritiro (`DROP FUNCTION IF EXISTS` in `migrations_v2/20_code/dbops`: il primo albero è congelato ma `v2` gira dopo) |
| `fn_fix_triggers_event_tokens` | Nessun changeSet la crea (`git log -S` vuoto): esiste solo su dbdev; il default `'a10'` è rifiutato dal suo controllo; `RAISE` nudo | Stesso `DROP … IF EXISTS` |
| `fn_trigger_exists_cascade_by_args` | Cerca `dbops.trgfn_soft_delete_cascade`, ritirata (`20260101-01-drop-attivo-legacy-objects.yaml:30`) | Ritiro |
| `fn_seed_automazione_overlap` | Seconda sorgente del registro (lo scrivono i changeSet di `80_data`); lanciata, l'upsert sovrascrive le righe curate; la regex del ramo GiST non estrae mai la chiave (`20_code/dbops/20260412-03…:134`) | Ritiro, o diagnosi con NOTICE |
| `fn_set_gucs_conn` | Scrive `app.user_id`/`app.group_ids` che nessuno legge; `app.session_key` lo legge `script.fn_get_parameter_di_sessione` ma senza questa funzione non lo scrive nessuno: il livello «sessione» degli override è sempre spento | Ritiro; per `app.session_key` decisione §4 |
| `fn_normalize_indirizzo` | `indirizzo_dettaglio_id` porta l'id della via; `civico_norm` sempre vuoto; col civico nel testo non trova la via; sede vera `anagrafiche.fn_build_indirizzo_normalizzato` | Ritiro |
| `fn_migrate_add_indirizzo_normalizzato` | Crea una colonna `GENERATED` con una formula sua, divergente da `fn_build_indirizzo_normalizzato`; su una tabella senza colonna entrerebbe in conflitto col trigger | Ritiro |
| `fn_run_automations` | Nessun chiamante; ordine e parti diversi dal giro vero (`dbops.processi.ci_ordine`): niente `STORICO_PROVISION`, delete_block, overlap (`:56-84`) | Ritiro, o ordine letto da `dbops.processi` |
| `fn_find_file_usage`, `fn_foreign_keys_info`, `fn_find_function_usage`, `fn_search_column_usage`, `fn_get_child_fk_col`, `fn_list_indices` | Strumenti DBA senza chiamanti; i primi quattro rispondono in modo sbagliato (D15, D53, D54; il COMMENT di `fn_find_function_usage` è copiato da `fn_find_file_usage`) | Riparare o ritirare (§4) |
| `fn_audit_begin`, `fn_audit_end` | Nessun chiamante; ramo dblink rotto (D60) | Tenere come porta DBA o ritirare (§4) |

### 2.9 Le fixture pgTAP

Le fixture devono produrre i dati nella forma in cui li produce l'applicazione: dove scrivono a mano
accanto a una porta di dominio, un guard nuovo sulla porta non arriva al test.

| # | Fixture | Fatto | Correzione |
| --- | --- | --- | --- |
| D62 | `fn_pgtap_piva_libera` | Le due firme ripetono lo stesso ciclo | La firma senza argomenti delega a quella con salto zero |
| D63 | `fn_pgtap_crea_soggetto_pg` | INSERT diretti su `anagrafiche.soggetti` e `indirizzi_soggetti`, accanto alle madri `fn_crea_soggetto_pg` e `fn_crea_indirizzi_soggetto`; divergono già su dati societari e indirizzi | Chiamare le madri; il ripiego «almeno un indirizzo» da ridecidere |
| D64 | `fn_pgtap_crea_indirizzo_dettaglio` | `ON CONFLICT DO UPDATE` (`:43-45`) al posto di `anagrafiche.fn_get_or_create_indirizzo_dettaglio`: su una riga disattivata restituisce un indirizzo spento e salta i controlli sulla via | Chiamare il BB; presidio in `test-indirizzi-dettaglio-unicita-v1.sql` |
| D65 | `fn_pgtap_crea_mondo_cliente` | Ricopia la verifica del legame di `fn_pgtap_cliente_ba_del_mondo` (`:104-112` contro `:31-39`) | Chiamare la seconda |
| D66 | `script.fn_pgtap_emittente_operatore` / `dbops.fn_pgtap_azienda_di_chi_agisce` | Senza azienda per chi agisce, dbops solleva, script ripiega sul primo emittente (`script/funzioni/fn_pgtap_emittente_operatore.md:48-60`): un'azienda su cui chi agisce non può né leggere né scrivere | L'helper di script solleva, o delega (§4) |
| D67 | `fn_pgtap_crea_lotto` | L'esito del gruppo trattenuto è un INSERT su `vendite.fatturazione_lotti_esiti`, accanto a `vendite.fn_segna_esito_gruppo_lotto`: un `ERRORE` senza `errore_quando` | Chiamare la porta; test 8 di `test-fn-pgtap-crea-lotto-v1.sql` |
| D68 | `fn_pgtap_crea_commessa_attivita` | Senza sorgente la chiave è `PGT-SEG-<md5>`, fuori dalla grammatica di `script.fn_segment_key`: i lettori vedono un documento che non esiste | Chiave composta dal dominio (forma: §4) |
| D69 | `fn_pgtap_crea_listino`, `fn_pgtap_listino_aggiungi_articoli` | Righe senza periodicità anche su versione ATTIVA; tipologia di default che può essere quota fissa: dal 2026-10-31 il motivo 3 di `script.fn_check_versione_listino_attivabile` ferma l'attivazione | Periodicità facoltativa; quota fissa esclusa dal default |
| D70 | `fn_pgtap_porta_a_stato` | Verso `CHIUSA` chiama `vendite.fn_chiudi_versioni_listino_scadute()`, globale e muta: restituisce `ATTIVA` senza errore (verde per sottrazione) | Sollevare se lo stato raggiunto ≠ `p_stato`, per ogni testata |
| D71 | `fn_pgtap_crea_ddt_da_ordine` | «La prima riga» per `riga_nr` può essere l'onere (dal `20261103-36` la madre porta l'onere nella prima bolla); il conteggio di `p_qta_da_evadere` conta gli oneri | Filtro `script.fn_natura_e_merce` — censito «lieve» in `brief-db-addebito-trasporto-ordine` §8.1, corretto lì solo per il reso |
| D72 | `fn_pgtap_crea_preventivo_con_righe` | `nv.destinazione_tipo = 'ORDINE_VENDITA'` in linea, mentre `script.fn_natura_e_merce` è la sede del predicato (copia non censita in §8.1 di quel brief; un'altra in `vendite.vw_preventivi_smistamento`) | Usare il BB |
| D73 | Builder di documento | Lo stato si cerca in tre forme: senza `attivo` (`_crea_ordine`, `_crea_preventivo`), in linea con `attivo IS TRUE`, con `script.fn_doc_stato_id`. Uno stato disattivato non solleva prima di costruire | Tutti con `script.fn_doc_stato_id` |
| D74 | Builder di fixture | «La prima valuta del catalogo» in sette copie (`_crea_ddt`, `_crea_ordine`, `_crea_preventivo`, `_crea_fattura`, `_crea_cliente_ba`, `_crea_emittente`, `_crea_gestore`) | Un BB di fixture, copie ritirate nello stesso giro |

## 3. I metadati

Nessuno cambia il comportamento, ma ognuno dice una cosa falsa a chi legge. ⚠️ Quelli in changeSet già
applicati si correggono con un changeSet nuovo.

### 3.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `dbops.automation_scope` | «Scope opzionale per rollout filtrato»: è l'allow-list che decide l'ambito di ogni automazione; colonne senza COMMENT |
| M2 | COMMENT `storico_scope_policy`, colonne `modo`/`colonna` (`00_schema/dbops/20260911-21…:137-142`), COMMENT `fn_storico_risolvi_scope` | «Cinque modi»: manca `COPPIA` |
| M3 | COMMENT `fn_storico_arma_scope` | Comincia con un marcatore di revisione e poi cita l'adapter `script.fn_scope_ef_whitelist`: si contraddice |
| M4 | COMMENT `fn_grant_storico_shadows` (e corpo) | Cita il test 19 di `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` e il ruolo batch, ritirati il 2026-10-15; «audit SKIP», ma scrive `WARN`; «le shadow ereditano il proprietario da chi esegue», superato dalla cessione al proprietario della madre |
| M5 | COMMENT `fn_run_automations_storico_provision` (e corpo) | Apici raddoppiati (`''STORICO_PROVISION''`); «crea/aggiorna», ma crea soltanto; `MANUAL` come `exec_mode`. Idem COMMENT `maintenance.proc_automations_storico_provision_job` |
| M6 | COMMENT `fn_storico_backfill_scope`; intestazione `90_end/20260911-31…:28-29` | «Il pgTAP le conta come debito»: nessun pgTAP conta le versioni senza origine delle shadow vere |
| M7 | Commento nel corpo di `fn_run_automations_storico` | «duplicate_object: logga SKIP_EXISTS»: lo status è `WARN` |
| M8 | COMMENT `audit_sources.storico_table` (`00_schema/dbops/20260429-05…:19,69`) | «Non esposto dalla vista»: lo è dal 2026-09-02 |
| M9 | COMMENT `ai_query_log`; remark di `user_id` (`00_schema/dbops/20260331-21…:47`) | «Retention via cleanup_at» (D36); «FK auth_user.id» senza vincolo |
| M10 | COMMENT `fn_get_or_create_session_tx_id` e commento nel corpo | «Rispetta myapp.log_with_dblink … non blocca mai»: falso (D1, D26) |
| M11 | COMMENT `trgfn_tx_id_managed` | «Assegna script.uuid_nil()»: nel ramo dell'id non registrato vince il GUC (`:169-173`) e la riga `:163` è irraggiungibile. Il comportamento l'ha giudicato innocuo `brief-db-coerenza-tx-id-non-registrato` (2026-07-22): si corregge il COMMENT, non il corpo |
| M12 | COMMENT `fn_set_gucs_conn` | «Per audit, RLS e override»: nessuno la chiama |
| M13 | COMMENT `script.fn_ensure_logconn` | Dice di leggere `dblink.log_connection`, il corpo legge `myapp.dblink_log_connection` |
| M14 | COMMENT `vw_processi_che_bypassano` e nota in `presidi.csv` | «Fase 6-bis: a regime vuota», «ritiro alla fase 6-bis»: avvenuto (D43) |
| M15 | COMMENT `vw_processi_roster` | «Roster_processo può diventare un SELECT su questa vista»: il repository la legge già (`backend/apps/core/db/processi_repository.py:152-176`) |
| M16 | COMMENT `vw_processi_dominio_su_pgagent` | «DEVE arrivare a VUOTA … oggi fallirebbe il migrate»: vuota dal 2026-09-05 |
| M17 | COMMENT `vw_processi_programmazione_da_guardare`, `vw_processi_programmazione` | Elenco degli esclusi incompleto (anche OK, IN_ATTESA, SPENTO); conteggi usati come argomento; cronaca |
| M18 | COMMENT colonna `processi_bersagli.emittente_via` (`00_schema/dbops/20260904-08…:99`) | «Stesso vocabolario del guard»: falso (D21) |
| M19 | `db/pgtap/anagrafiche/test-identita-tecnica.sql:28-30` | «Il presidio guarda nei DUE sensi»: sono tre, e il secondo non lo costruisce nessun file |
| M20 | `presidi.csv` — `vw_riferimenti_morti_da_sanare` (`:15`), `vw_bersagli_non_dichiarati` (`:25`), `vw_codici_errore_forme_condizione` (`:23`) | Nota stantia (CHECK-KO → REALE, superata da `NON_MISURATO`); `presidiato_da` «ci-validate.yaml», ma la build la ferma `test-vw-bersagli-non-dichiarati.sql`; «lente da rilanciare a mano», ma la legge lo scatto B-7 |
| M21 | `presidi.csv` — `vw_af_senza_giro`; `test-catalogo-presidi-v1.sql:52-61` | «`attivita_fatturabili` non ha la RLS (debito)»: armata dal 2026-09-10, non è nel debito; «tre viste DEFINER, ne copre due»: superato |
| M22 | `presidi.csv` — `vw_ddt_emessi_senza_scarico`, `vw_resi_confermati_senza_carico`; COMMENT `vendite.fn_ddt_muove_merce`, `vendite.fn_reso_muove_merce` | Citano la Regola 3 di `trgfn_ddt_guard_transizione` e la Regola 2 di `trgfn_resi_guard_transizione`, ritirate il 2026-10-25: la porta è `script.trgfn_doc_stato_solo_dal_verbo` |
| M23 | `presidi.csv` — `vw_magazzino_valore_giacenza_divergente`; COMMENT e nota di `vw_magazzino_movimenti_senza_costo` | Scrittori incompleti (anche `fn_posta_trasferimento`, `fn_storna_movimenti_sorgente`, `vendite.fn_posta_ddt`, `vendite.fn_posta_reso`); manca il carico da reso senza costo |
| M24 | `presidi.csv:21` e COMMENT `vw_run_senza_attore` | «Dodici job», «quando è vuota → NOT NULL»: superati dal CHECK (D42); cita `script.fn_run_and_log` (è `maintenance.`) |
| M25 | COMMENT `fn_guardiano_digest` | «Finché NOTIFICA_DIGEST_MUTO è attivo = false»: acceso dal 2026-09-11 |
| M26 | COMMENT `fn_conta_presidio_per_variante`; `codici_errore.csv:856`, `messaggi_errore.csv:853` | «Stessa ragione di fn_conta_presidio» (INVOKER dal 2026-10-10); `E_PRESIDIO_NON_A_CATALOGO` lo solleva `fn_conta_presidio_per_variante` |
| M27 | COMMENT `fn_check_funzioni_riferimenti_morti`; `codici_errore_senza_policy` | Consumatori incompleti, «test 7» è il 6; «voce in error_policies.py», la mappa è `error_policies_generated.py` |
| M28 | COMMENT `fn_apply_chiusura_scadenze` (e del filtro), `automazione_chiusura_scadenze`; riga `CHIUSURA_SCADENZE` di `coda_lavori_tipi.csv`; intestazione e test 4-6 di `test-chiusura-scadenze-classe.sql` | «Il job pgAgent chiama senza argomenti», «chiamata dal job notturno», «quando migreranno sulla coda»: la chiama l'handler della coda dal 2026-09-05; manca il preventivo fra i bersagli; «due bersagli» (tre) |
| M29 | COMMENT `fn_sessione_del_migratore`, `fn_idempotency_prenota`, `sessioni_utente` | Manca il chiamante `script.fn_blocca_credenziale`; «committa da sola» (è il backend in autocommit); manca `TOTP_DISABILITATO`, `SCADENZA` non ha scrittori |
| M30 | COMMENT `fn_admin_merge_comune`, `fn_admin_merge_stradario` | «Ripunta chi riferiva l'origine» (D3, D4); il commento su `fn_get_vie_discendenti` è falso |
| M31 | COMMENT `fn_get_lookup_codici`, `trgfn_child_requires_non_obsolete_parent`; `messaggi_errore.csv:292` | «obsoleto_dal <= CURRENT_DATE»: dal 2026-10-09 è `fn_data_operativa()` |
| M32 | COMMENT `vw_emittenti_regime_non_confermato` | «O di un cambio senza conferma»: stantio dal 2026-10-02 |
| M33 | COMMENT `fn_find_function_usage`, `fn_get_override_col`, `fn_get_child_fk_col` | Copiato da `fn_find_file_usage`; rimanda a `dbops._col_exists` (è `fn_col_exists`); «di fatto STABLE» (è VOLATILE) e «utility delle automazioni» senza chiamanti |
| M34 | COMMENT `lock_columns_conditional`, `fn_cleanup_at_params`, `trgfn_cleanup_at_alla_nascita`, `fn_apply_delete_block_trigger`, `fn_seed_automazione_guard_utility_tipo_ruolo`, `fn_seed_automazione_overlap`, `automazione_overlap`, `automazione_attivo_eccezioni`, `fn_trigger_exists_block_by_args`/`…_require_by_args`, tabella `automation_delete_block` | «Colonne immutabili» (segnala al form); «stesso criterio» (D16); «event_log e i quattro registri» (dieci tabelle); non dice `AFTER DELETE` né il controllo per nome; «Popola» (non scrive); non dice che sovrascrive né che non ha chiamanti; manca `range_col`; «prima riga» (sono due); «la signature a 5 args» (non riconoscono niente, D6); «tabelle sensibili (ruoli)» (generico) |
| M35 | `automation_rules_tbl.csv:12`, nota della regola di `vendite.event_log`; `codici_errore.csv:64`; intestazioni `80_data/changelog/20260602-10…:16-19`, `20260626-04…:21` | «Trigger a10 all'INSERT» (è `trgfn_cleanup_at_alla_nascita` in m50); «meno di 4 argomenti» (copre ogni rifiuto, D46); «oggi NON è schedulato» (ha job e convergenza) |
| M36 | COMMENT di fixture | `fn_pgtap_piva_libera()` «due chiamate danno valori diversi» (falso senza scrittura fra le due); `_crea_operatore_umano` «lo stesso UPDATE di identita_digitali.attivo» (è `fn_accendi_veste`); `_cliente_ba_del_mondo` «BB di fattura, contratto, ordine» (solo `_cliente_del_builder`); `_cliente_del_builder` cinque builder (sei); `_crea_mondo_cliente` `uq_emittenti_fiscali_ba` (stantio); `_crea_commessa`, `_contratto`, `_fattura`, `_ordine` «il cliente da `_crea_mondo_cliente`» (da `_cliente_del_builder` dal 2026-10-24); `_crea_commessa_attivita` (D68); `_crea_reso` si contraddice; `_porta_a_stato` «testate senza la porta» (oggi tutte l'hanno) |
| M37 | Intestazioni pgTAP | `test-fn-pgtap-crea-fattura-v1.sql` («coppia», «quattro anelli»); `test-fn-pgtap-crea-preventivo-v1.sql` («stato alla nascita»); `test-audit-sources-seed.sql:16,54,168` («3 colonne», «almeno 9»); `test-cleanup-framework.sql:31` («tre tabelle», sono sei); `test-storico-scope-congelato-v1.sql:4-8,20-23` («titodb non può fare SET ROLE», superato dai ruoli di sistema); `test-automazione-attivo-eccezioni-v1.sql` (presidia solo la prima eccezione) |
| M38 | `scripts/sql/provision_storico_scope.sql:6` | Rimanda a `work-in-progress/brief-db-rls-storico-scope-congelato.md`, oggi in `work-done/` |
| M39 | `script.fn_check_versione_listino_attivabile`; `script.fn_crea_utente_tecnico` | COMMENT con i motivi 1 e 2, il corpo ha anche il 3; commento del Guard 1 «canale CODA no», la condizione ammette `CODA_AUTOMATICA` |

### 3.2 Senza COMMENT

`dbops.audit_log`; `fn_audit_begin`, `fn_audit_end`, `fn_audit_log_once`; `fn_schema_match`,
`fn_schema_in_scope`, `fn_table_in_scope`, `fn_resolve_scope` (il doppio significato di `*all` —
«qualunque schema» qui, «usa il default» in `fn_resolve_scope` — non è scritto nel database);
`fn_find_file_usage`, `fn_foreign_keys_info`, `fn_search_column_usage`, `fn_list_indices`;
`fn_drop_triggers_by_function_args`; `fn_normalize_indirizzo`, `fn_migrate_add_indirizzo_normalizzato`
e le utility di D61 (si chiudono col ritiro).

### 3.3 Marcatori di revisione, nomi di brief, id di changeSet e conteggi nei COMMENT

Lo stesso residuo che lo standard toglie dalle pagine `manual/` sta nei COMMENT di quasi tutti gli
oggetti rivisti: `Rev …`, `⭐ rev …`, «Brief: …», sigle di cantiere, id di changeSet, un hash di commit
(`28d9beeb6` in `fn_storico_risolvi_scope`), misure usate come argomento («168 su 349» in
`trgfn_prevent_deactivate_if_children`, «12 righe OK», «su 102 dei 185 file»). Il COMMENT è il primo
paragrafo della scheda auto-generata, quindi chi legge lo trova come descrizione. Oggetti più colpiti:
`fn_storico_*`, `fn_ensure_storico_table`, `fn_run_automations_*`, `trgfn_tx_id_managed`,
`fn_get_or_create_session_tx_id`, `fn_generate_tx_id`, tutte le `vw_processi_*`, `processi*`,
`installazione`, `vw_codici_errore_*`, `vw_funzioni_check_codici`, `fn_regexp_occorrenze`,
`messaggi_errore_codici_legacy`, `coda_lavori*`, `fn_accoda_*`, `fn_idempotency_*`,
`fn_sync_functions_owner`, `vw_stati_check_*`, `vw_trigger_functions`, le viste delle FK, quasi tutte
le `fn_pgtap_*` e le etichette di prova.

Proposta: una regola sul COMMENT uguale a quella del primo paragrafo dello Scopo (il significato
dell'oggetto, al presente, niente provenienza), un changeSet di riscrittura per famiglia quando la
famiglia si tocca per un difetto, e un presidio di testo
(`obj_description` che contiene `brief-`, `rev 20`, un id `20\d{6}-\d\d`). Se vale anche per i COMMENT
la R3 del brief maintenance (nomi di brief fuori dalle note dei CSV) lo decide Tid (§4).

## 4. Le decisioni di Tid

| # | Domanda | Raccomandazione della sessione DB |
| --- | --- | --- |
| Q1 | D3/D4: `fn_admin_merge_*` si riparano (sono la riclassificazione delle vie) o si ritirano? | Riparare lo stradario (la guida riclassificazione-vie ne ha bisogno), restringere o riparare il comune nello stesso giro |
| Q2 | D11: che cosa vuol dire `attivo = false` per un processo? | CHECK: il ritiro si scrive con la data, una sede sola |
| Q3 | §2.3: una regola di convergenza per i registri che aggiungono e non tolgono | Sì, una volta per tutti e tre: riconoscimento per funzione, rimozione con `enabled = false` |
| Q4 | D35-D37: `shop` nell'ambito? `ai_query_log`: che termine? `audit_sources`: ambito o colonne tolte? | `shop` nell'ambito; `ai_query_log` a 90 giorni come gli altri registri, o meno per il testo sensibile; `audit_sources` nell'ambito |
| Q5 | D38: classe dei bersagli — solo `DOMINIO` o un esecutore `SISTEMA`? | Solo `DOMINIO` finché non c'è un bersaglio di altra natura |
| Q6 | D42: `vw_run_senza_attore` ritirata o filtrata? | Ritirata (`obsoleto_dal`): il debito non può più nascere |
| Q8 | D51: lettura `DEFINER` dei guard ATTIVO, con l'effetto sulle fixture | Sì, con il censimento delle fixture che chiudono i differiti |
| Q9 | D60 e §2.8: ramo dblink di `fn_audit_*`; `fn_audit_begin/end`; i sei strumenti DBA senza chiamanti | Ritirare il ramo dblink e `begin/end`; riparare `fn_find_function_usage` e `fn_search_column_usage` (servono ai censimenti), ritirare gli altri quattro |
| Q10 | `app.session_key` (D61, `fn_set_gucs_conn`): lo imposta il BE all'autenticazione, o il livello sessione esce da `fn_get_parameter_di_sessione`? | Esce: nessuno lo usa |
| Q11 | D66: `script.fn_pgtap_emittente_operatore` senza azienda — solleva o delega? | Delega a quella di dbops (una sede) |
| Q12 | D68: chiave di default del segmento senza sorgente — `COMMESSA:<id>…` o `MAN:`? | `MAN:`, che è la forma di una riga senza documento |
| Q13 | §3.3: la regola sui COMMENT, e se vale per loro la R3 del brief maintenance | Sì, con il presidio di testo |
| Q14 | Altri dubbi dei lotti, da confermare o girare in difetto: `fn_get_pipeline_task_implementation` ripiega in silenzio sul default per una variante inesistente; una FK registrata a `false` sparisce da ogni presidio; `vw_coda_lavori_da_guardare` è definer su tabella senza RLS e catalogata `LIBERO`; `vw_codici_errore_forme_condizione` è catalogata `LAVORAZIONE` ma la usa lo scatto B-7 come cancello; `vw_processi_dominio_senza_difesa` riconosce il guard dal solo `proname`; `obsoleto_dal IS NULL` fa uscire dai presidi un processo a ritiro programmato che gira ancora (sette viste); un lotto congelato con `stato_lotto` IN_ESECUZIONE/ERRORE ed esiti in ERRORE non lo guarda né `vw_lotti_fermi_da_guardare` né `vw_lotti_chiusi_con_errori_da_guardare`; uno storno di un'uscita senza costo entra in `vw_magazzino_movimenti_senza_costo`; `sessioni_utente.evento = 'SCADENZA'` ammesso e mai scritto; `credenziali_di_prova` senza FK verso la credenziale (un'etichetta che sopravvive alla credenziale); il trigger DELETE_BLOCK è `AFTER DELETE` in fase `a10`; un `ADD CONSTRAINT` overlap su dati già sovrapposti (23P01) ferma il giro; il guard utility gira solo in `ci_apply`, senza processo | Da decidere uno per uno; la sessione DB li apre come difetti solo su conferma |

## 5. Ricadute su BE e FE

Si chiedono quando il giro DB corrispondente è applicato.

| # | Che cosa | Dove | Legata a |
| --- | --- | --- | --- |
| BE1 | L'handler della chiusura per scadenza passa `p_classe = 'DOMINIO'` | `backend/apps/core/services/coda_lavori/chiusura_scadenze_handler.py:51-60` | D38 (Q5) |
| BE2 | I `gaps` scritti a mano per `codice_interno` si ritirano | `backend/apps/core/services/non_editable_fields_helper.py` | D25 |
| BE3 | I controlli preventivi «padre non attivo» si ritirano e si mappa il codice nuovo | `backend/apps/vendite/services/commesse_service.py:552`, `backend/apps/anagrafiche/db/anagrafiche_repository.py:98` | D46 |
| BE4 | La ricerca dei lookup passa alla funzione DB (o cade il tetto `LOOKUP_MAX_SOURCE_ROWS`); la paginazione resta com'è | `backend/apps/core/db/dbops_repository.py:55, 415-470` | D57 |
| BE5 | Docstring stantie: «tre viste … SECURITY DEFINER» (`fn_conta_presidio` è INVOKER) e «registro non vuoto» (il corpo ammette vuoto) | `backend/apps/core/db/presidi_repository.py:16-22`, `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py:66-67` | — |
| BE6 | Codici nuovi di D44-D47, D12 → rigenerare `error_policies_generated.py` | — | §2.5 |

Nessuna ricaduta FE diretta: D25 si vede nel form quando BE2 è fatto.

## 6. Difetti fuori schema trovati leggendo i chiamanti

* `vendite.trgfn_listini_righe_guard_periodicita_quota_fissa` scatta solo su `UPDATE OF periodicita`:
  l'INSERT di una riga a quota fissa senza periodicità su una versione già ATTIVA passa, e la regola del
  dominio è chiusa a metà. Da portare al cantiere dei listini.
* `vendite.vw_preventivi_smistamento`: copia in linea del predicato «natura è merce» (vedi D72).
* `db/changelog/migrations/50_dbops/20250922-05…` e `-06…`: stessi id di changeSet; il primo albero è
  congelato, solo annotazione.

## 7. La documentazione già corretta (2026-11-03/04)

* Le 239 pagine `docs/it/dbzero/dbops/manual/`: 201 riscritte allo standard, 38 create per gli oggetti
  che non l'avevano. Tutte passano la verifica di `standard-guide.md` §«Verifica di una pagina
  `manual/`». Le correzioni di contenuto (codici errore mancanti, colonne inesistenti, chiamanti,
  comportamenti cambiati) sono nella pagina di ciascun oggetto.
* Il blocco comune `dbops/_fixture-pgtap.md`, le guide e le pagine fuori schema che dicevano il falso
  su oggetti `dbops`, e i link da guide, tutorial e `dev/` verso `/dbzero/dbops/manual/` ripuntati alle
  schede. L'elenco è in §7.1.

### 7.1 Doc fuori schema

Tutte con la data al 2026-11-04.

| File | Correzione |
| --- | --- |
| `guide/storicizzazione-tabelle.md` | Sei modi (con `COPPIA`); `p_exec_mode` è `CI` o `SCHEDULED`, valgono le regole `AUTO` o uguali |
| `linee-guida-sql.md` §9 | Il trigger generato è `trg_{table}_gen_tx_id_ins_upd` |
| `guide/tx_id_implementation_guide.md` | Un canale irraggiungibile blocca la scrittura (D1); l'interruttore lo rispetta solo `fn_ensure_logconn` (D26); senza parametro il bypass di sessione è ignorato (D12) |
| `guide/Messaggi-di-Errore-e-Generazione-Log.md` | `error_log` non è immutabile (scade a 90 giorni); senza canale la riga non nasce |
| `guide/messaggi-audit.md` | Tolto il consiglio di accendere `log_with_dblink` per l'audit (D60) |
| `guide/automazione-db.md` | §4.2 (azione FK, require differito, figli attivi, due eccezioni, nomi uguali per due FK — D10), §4.3 (seed overlap senza chiamanti), §4.6 (forma `<prefisso>_soggetto_ruolo_id`, il seed è una diagnosi), §5.4 (hash solo oltre 63 caratteri) |
| `guide/processi-pgagent-funzionali.md` | Chiusura per scadenza: sveglia oraria, `DOMINIO` su `CODA_AUTOMATICA`, audit, verbo e `fn_data_operativa()`, job e link |
| `guide/riclassificazione-vie.md` | Esiste `fn_admin_merge_stradario`, che oggi fallisce (D3) |
| `guide/pgtap-come-si-scrive-un-test.md` | Riga d'onere da `crea_ddt_da_ordine`, `conferma_reso` da `porta_a_stato`, «solo dal verbo» per tutte le testate, fattura a tre anelli, motivo dell'ordine obbligato |
| `dbzero/dbops/_fixture-pgtap.md` | Data, eccezione `pgtap-runner: owner`, link a guida e template |
| `dbzero/vendite/manual/contratti.md`, `dbzero/maintenance/manual/proc_automations_overlap_job.md` | Il chiamante della chiusura è il lavoro di coda; il seed overlap non gira |
| `dev/work-in-progress/sviluppo-multi-face-da-completare.md` | Nota: `zeroerp_batch_fatturazione` è ritirato |
| 19 file in `guide/`, `tutorial/`, `dev/` | 79 link da `/dbzero/{dbops,maintenance,script}/manual/` ripuntati alle schede; in `dev/manual/modello-componenti-bom.md` la riga di data ridotta alla data (la cronaca sta già in `changelog-decisioni-componenti.md`) |

Restano fuori, non richiesti: un link morto preesistente in `guide/gestione-ddt.md`
(`/dbzero/vendite/funzioni/fn_ddt_legami`); marcatori di revisione rimasti nelle guide toccate; i link
`/dbzero/*/manual/` dentro le pagine `manual/` degli **altri** schemi, che si ripuntano quando quegli
schemi vengono rivisti.

## 8. I giri proposti

L'ordine lo decide Tid (§4). Ogni giro: changeSet, pgTAP del presidio, pagine `manual/` riallineate.

Prima la classe A, poi la B, infine la C (§2.0). Dentro una classe i difetti che toccano gli stessi
oggetti vanno insieme; un B o un C entra in un giro A quando tocca lo stesso oggetto, per non riaprirlo
due volte.

| Giro | Classe | Contenuto | Perché insieme |
| --- | --- | --- | --- |
| 1 | A | D1 (+ D26, B), D14 + D15, D40, D41, D43, D54, D56 (+ D7, B) | Giornali e presidi che oggi dicono il falso o tacciono; il BB «sorgente senza commenti» serve a più presidi |
| 2 | A | D3, D4 (+ D45, B) se Q1 = riparare; D44, D46, D47 (+ D49, B) | Porte che falliscono appena usate e rifiuti col codice sbagliato; i codici nuovi in un giro solo, con la rigenerazione BE (BE6) |
| 3 | A | D25, D30, D35, D36, D37, D57 | Promesse senza esecutore e ricerche che non vedono tutto; ricadute BE2, BE4 |
| 4 | A | D6, D21, D51, D53, D58, D59 | Riconoscimento dei trigger, vocabolario delle vie, letture dei guard, strumenti sbagliati |
| 5 | A | D63, D64, D66, D67, D68, D70 | Fixture che producono una forma che l'applicazione non produce |
| 6 | B | D13, D16, D17, D18, D19, D20, D22, D23, D24, D27, D28, D29, D32, D33, D34 (Q3) | Le copie del framework delle automazioni, e la convergenza dei registri |
| 7 | B | D2, D5, D8, D9, D10, D11, D12, D38, D39, D52, D60, D69, D71, D73 | Casi del modello oggi non prodotti, correzioni locali |
| 8 | C | D61 (+ D42, D55) | Un changeSet di ritiro, con le pagine `manual/` cancellate |
| 9 | C | D17-bis, D48, D50, D62, D65, D72, D74 | Pulizia, quando l'oggetto è già aperto in un giro precedente |
| 10 | — | M1-M39, §3.2, §3.3 | I COMMENT, per famiglia, quando la famiglia è già aperta in un giro precedente |

## 9. Alla chiusura

* Ogni difetto chiuso aggiorna la pagina `manual/` dell'oggetto, che oggi descrive il difetto.
* Il brief va in `work-done/` quando tutti i giri sono applicati e verdi, con le richieste BE ancora
  aperte dichiarate nel blocco in testa.

## 10. Giro C1 — la pulizia, 2026-11-04

**Decisioni di Tid (2026-11-04):** si parte dalla classe C. I ritiri si fanno solo per gli oggetti di cui
è certo che nessuno li usa: i quattro strumenti DBA di Q9 restano. `vw_run_senza_attore` si ritira (Q6).
D17-bis e D74 si rimandano.

### 10.1 Che cosa è stato scritto

| ChangeSet | Difetto | Che cosa |
| --- | --- | --- |
| `00_schema/dbops/20261104-09` | D48 | `automation_lock_columns.error_code` senza DEFAULT (era un codice ritirato); COMMENT di colonna |
| `20_code/dbops/20261104-10` | D61 | DROP di undici funzioni senza chiamanti: le cinque utility dei trigger, `fn_trigger_exists_cascade_by_args`, `fn_normalize_indirizzo`, `fn_migrate_add_indirizzo_normalizzato`, `fn_set_gucs_conn`, `fn_seed_automazione_overlap`, `fn_run_automations` |
| `20_code/dbops/20261104-11` | D42 | DROP di `dbops.vw_run_senza_attore` |
| `20_code/dbops/20261104-12` | D50 | `fn_run_automations_tx_id`: il dry run scrive `rule_type = TX_ID` e si firma col proprio nome (l'orchestratore che firmava è ritirato); COMMENT riscritto |
| `20_code/dbops/20261104-13` | D55 | `vw_function_list`: `num_args` da `pronargs`, `comment` da `obj_description` |
| `20_code/dbops/20261104-14` | D62 | `fn_pgtap_piva_libera()` delega a `fn_pgtap_piva_libera(0)`; COMMENT corretto (M36) |
| `20_code/dbops/20261104-15` | D65 | `fn_pgtap_crea_mondo_cliente` verifica il legame con `fn_pgtap_cliente_ba_del_mondo`; COMMENT dei due (M36) |
| `20_code/dbops/20261104-16` | D72 | `fn_pgtap_crea_preventivo_con_righe` sceglie la natura con `script.fn_natura_e_merce`; COMMENT riscritto |
| `80_data/changelog/20261104-17` | D42 | DELETE delle righe di `vw_run_senza_attore` da `dbops.presidi_testi` e `dbops.presidi`, già tolte dai due CSV (i mirror non cancellano) |
| `90_end/20261104-18` | D61 | DROP di `fn_audit_begin`, `fn_audit_end`: in `90_end` perché il REVOKE di `20260911-09` le pretende con una preCondition HALT |
| `00_schema/dbops/20261104-19` | D61 | `chk_audit_status` senza `START`: lo scriveva solo `fn_audit_begin`, e una corsa «aperta» non è più uno stato del modello. Senza, il presidio C1 è rosso (`dbops/test-stati-check-scrittori-v1` test 2, `audit_log.status = START` NON_DICHIARATO: visto da Tid dopo l'apply). Nessun lettore del valore; zero righe `START` su dbdev; una riga `START` farebbe fallire l'`ADD CONSTRAINT`, e va bene così |

pgTAP riallineati: `dbops/test-registri-append-only-postura-v1.sql` (plan 22: i test 14-15 provano che le
due porte non esistono più, i 22-23 escono) e `maintenance/test-job-run-attore.sql` (plan 11: esce il test
della vista).

**Il censimento dei ritiri** (prima di scrivere i DROP): nessun chiamante nel repository (tutti gli alberi
dei changelog, pgTAP, backend, frontend, scripts) fuori dai changeSet che li creano; sul database di
sviluppo nessun riferimento nei corpi delle funzioni (comprese le `BEGIN ATOMIC`), nelle viste, negli step
pgAgent, nei trigger. Tutte di `zeroerp_owner`, `INVOKER`. Chi li nomina ancora come testo, e regge
l'assenza: la lista dei grant di `ci_apply/20260205-41` (scorre solo le funzioni che esistono),
l'elenco delle porte di `vw_audit_log_scrittori_fuori_perimetro`, un filtro di
`scripts/sql/provision_zeroerp.sql`, il GRANT di `90_end/20260904-20` (protetto da `to_regclass`).

### 10.2 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML, `BEGIN … ROLLBACK`)

* L'estratto dei dieci changeSet gira intero (`ON_ERROR_STOP`); `fn_fix_triggers_event_tokens` sullo scratch
  non esiste e l'`IF EXISTS` la salta, come previsto.
* Quindici pgTAP senza e con l'estratto in testa: nessun rosso nuovo. `test-catalogo-presidi-v1` (test 3,
  ogni riga punta a una vista viva) e `test-presidi-testi-v1` verdi senza la vista; `test-lock-columns-convergenza`,
  le fixture del mondo e del preventivo, `test-riferimenti-morti-v1`, `test-audit-log-perimetro-scrittori-v1`
  verdi. Da owner restano rossi per costruzione i test 16-19 della postura (UPDATE/DELETE sul registro:
  da owner riescono) e un rosso preesistente di `test-soggetti-titoli-iva-tipo-soggetto-v1`, uguali senza e con.
* D50 su un caso costruito (tabella di `vendite` con `tx_id` e senza trigger): la riga DRYRUN è
  `dbops.fn_run_automations_tx_id` / `TX_ID`. D55: `num_args` 0 e 1 sulle due firme di
  `fn_pgtap_piva_libera`, nessuna riga doppia. D62: le due firme danno la stessa partita IVA.
  `plpgsql_check` pulito sulle quattro funzioni riscritte.
* Lo scratch dopo le prove è intatto (impronta delle funzioni di `dbops`, righe di `dbops.presidi`, vista,
  default della colonna).

* `20261104-19`, provato dopo l'apply del C1 sullo scratch: `dbops/test-stati-check-scrittori-v1` passa da
  14/15 a 15/15; `test-chiusura-scadenze-audit-v1`, `test-storico-salto-trigger-presente-v1` e la postura
  invariati senza e con.

**✅ Applicato da Tid il 2026-11-04** su dbdev e sullo scratch, `20261104-09` … `-19`. Verdi come app
`dbops/test-registri-append-only-postura-v1.sql`, `maintenance/test-job-run-attore.sql`,
`dbops/test-catalogo-presidi-v1.sql`, `dbops/test-presidi-testi-v1.sql`; verde da owner
`dbops/test-stati-check-scrittori-v1.sql` (era rosso al test 2 dopo il `-18`, chiuso dal `-19`).

### 10.3 Doc

Cancellate le pagine `manual/` dei quattordici oggetti ritirati; riallineate le pagine che li nominavano e
quelle degli oggetti cambiati (§7.1 resta per la revisione).

### 10.4 Residuo della classe C

| # | Che cosa | Perché resta |
| --- | --- | --- |
| R1 | I dry run di `fn_run_automations_lock_columns`, `_audit_update`, `_date_validita` firmano ancora `dbops.fn_run_automations`, ritirata | Tre funzioni grandi: si chiude quando ciascuna si riapre (giro 6) |
| R2 | Il `COALESCE` morto in `fn_lock_columns_divergenze` | Con D32 |
| R3 | I nomi `fn_audit_begin`/`fn_audit_end` nella lista di `ci_apply/20260205-41` e nelle porte di `vw_audit_log_scrittori_fuori_perimetro` | Testo senza effetto; si toglie quando quei file si riaprono |
| R4 | D17-bis, D74 | Rimandati da Tid |
| R5 | I quattro strumenti DBA (`fn_find_file_usage`, `fn_foreign_keys_info`, `fn_get_child_fk_col`, `fn_list_indices`) | Non ritirati: decisione Q9 aperta |
| R6 | `dbops.audit_log.duration_ms` non la scrive più nessuno: la scriveva solo `fn_audit_end`, e `fn_audit_log_once` non ha un parametro per la durata (i runner la mettono in `result`). ✅ La metà su `START` è chiusa da `00_schema/dbops/20261104-19` (vedi §10.1) | **`duration_ms`** da decidere: colonna ritirata, o un parametro della durata in `fn_audit_log_once` |
| R7 | `docs/it/postgresql/dblink.md` dice ancora che `fn_audit_log_once` scrive fuori transazione con `myapp.log_with_dblink = on`: oggi quel ramo non scrive (D60) | Con D60 |
| R8 | ✅ `dbops/manual/fn_run_automations_codice_maiuscolo.md` (cantiere parallelo) diceva «non è una parte di `dbops.fn_run_automations`, che non ha chiamanti» | Corretto dal suo cantiere il 2026-11-04, con il commento di testata di `20_code/dbops/20261104-04` |

## 11. Il cantiere parallelo CODICE_MAIUSCOLO (2026-11-04, applicato)

Nota per i giri 1 e 6, non un difetto. Il cantiere CODICE_MAIUSCOLO (`20261104-01` … `-08`, nessun
brief: il perché sta nelle intestazioni e nelle pagine `manual/`) ha aggiunto un runner nuovo,
`dbops.fn_run_automations_codice_maiuscolo`, applicato da Tid su dbdev con i pgTAP verdi. È nato già
allineato ai difetti che qui si segnalano sugli altri runner, e può servire da forma quando si riaprono:

| Difetto | Come lo evita |
| --- | --- |
| D17 | Il trigger vivo si riconosce dalla funzione (`tgfoid`); la `existence_strategy` della regola non si legge |
| D32-D34 | Stato atteso e vivo in una funzione sola, `dbops.fn_codice_maiuscolo_perimetro`, che converge nei due sensi (`CREA`, `RIGENERA`, `TOGLIE`); la convergenza in `90_end` (`20261104-08`, `runAlways`) ferma il migrate se resta un'azione |
| D41 | Audit `OK` anche nel giro vero, `DRYRUN` nel dry run, `WARN NO_RULE` quando manca la regola |
| R1 | Il dry run si firma col proprio nome |
| D61 | Nessun aggancio all'orchestratore ritirato: la chiamano la convergenza e `maintenance.proc_automations_lock_columns_job` (`20261104-05`) |

⚠️ `20261104-05` ha riscritto `proc_automations_lock_columns_job`: chi la riapre parte da quel corpo.

