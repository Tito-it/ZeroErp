# Brief DB — Sei codici d'errore da mettere a catalogo e la lista dei parametri di livello puro

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-07. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** §7 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](../work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)
> (voci E-1, E-2, E-5, F-5). Fino a oggi quelle richieste stavano solo nell'analisi:
> questo brief le porta al team (ok di Tid, 2026-10-07).
> **Stato (2026-10-07 sera):** ✅ giro DB applicato su dbdev (`-70`…`-73` e seed,
> verificato dal BE sul database), ✅ giro BE fatto (§8). ✅ **Chiuso il 2026-10-07.**
> **Da leggere per primo:** §7, poi §7.7, poi §8.

## 1. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-1 | Sei codici nel catalogo (`codici_errore.csv` + `messaggi_errore.csv`) | seed `80_data` | sì: rigenerazione delle policy e ripieghi |
| R-2 | `script.fn_list_parameters_for_user` mostra solo override **di livello puro** | `20_code` | no |
| D-1 | `E_USER_DISABILITATO`: ritirarlo, o dargli un significato nuovo | **domanda a Tid**, poi seed | no |

## 2. R-1 — Sei codici usati dal backend e assenti dal catalogo

Il backend li solleva, ma non sono nel catalogo. Effetto, oggi:

* i due `*_NOT_FOUND` non hanno classe: il traduttore li tratta come «codice
  `E_*` sconosciuto» e risponde **400** «Errore di validazione.» invece di 404;
* gli altri quattro non hanno una riga a catalogo: chi legge `dbops.error_log` o la
  colonna `ultimo_errore` di una coda trova un codice che il catalogo non conosce
  (né frase, né causa, né soluzione).

Li ha trovati il guardrail `test_error_codes_declared_guardrail`, esteso il
2026-10-07 a ogni literal `E_*` del backend (E-2). Oggi stanno nel suo registro del
debito `_DEBITO`, che deve calare.

| Codice | Classe proposta | Frase (quella che il BE scrive già) | Chi lo solleva |
| --- | --- | --- | --- |
| `E_ANAG_CONTO_NOT_FOUND` | `NON_TROVATO` | Conto bancario non trovato nel registro. | `anagrafiche/services/conti_bancari_service.py` (`conto_bancario_id` inesistente) |
| `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` | `NON_TROVATO` | Associazione conto bancario non trovata. | idem (DELETE di un legame inesistente o di un altro proprietario) |
| `E_GUC_RESET_FAILED` | `TECNICO` | Errore interno di sicurezza sessione. | `core/middleware/jwt_audit_middleware.py` (reset delle GUC a inizio richiesta fallito: fail-closed) |
| `E_DB_ROLE_UNSAFE` | `TECNICO` | Errore interno di sicurezza sessione. | idem (la connessione web gira su un ruolo `BYPASSRLS`: richiesta rifiutata) |
| `E_CODA_JOB_STANTIO` | `TECNICO` | Esecuzione interrotta (worker morto o kill): recuperata dal reaper. | `core/services/coda_lavori/repository.py` (`reap_stale`, in `ultimo_errore`) |
| `E_STAMPA_JOB_STANTIO` | `TECNICO` | Render interrotto (worker morto o kill): recuperato dal reaper. | `vendite/db/pipeline_repository.py` (`reset_stale_stampe_in_corso`, in `ultimo_errore`) |

Motivo delle classi, sul modello:

* `NON_TROVATO` — la cosa indicata non esiste: è la definizione della classe (api.md
  §Tassonomia), ed è la classe di `E_ANAG_NOT_FOUND`, il gemello che lo stesso
  service usa per il soggetto;
* `TECNICO` — guasto o pezzo configurato male: l'operatore non può rimediare. I due
  del middleware sono configurazione della macchina; i due dei reaper sono un worker
  morto, e il lavoro è già stato rimesso in coda o chiuso dal reaper stesso.

⚠️ Causa e soluzione le scrive il team DB, come per ogni codice. Due suggerimenti
dal lato BE, per i due del middleware: la soluzione è per chi gestisce la macchina
(GUC: verificare la connessione e il log `jwt_audit_middleware.guc_reset_at_start_failed`;
ruolo: `DB_USER` del web non deve essere il ruolo batch), non per l'operatore.

**Test DB:** quelli che il catalogo ha già (ogni codice ha classe e messaggio,
convenzione `E_`). Nessun pgTAP nuovo: nessuna funzione DB solleva questi codici.

## 3. R-2 — La lista dei parametri mostra solo override di livello puro

`config.parameter_overrides` ha sei dimensioni (`django_user_id`, `django_group_id`,
`emittente_fiscale_id`, `categoria_cliente_id`, `session_key`, `function_name`).
L'unicità è sull'insieme e nessun `CHECK` vieta una riga che ne valorizza più d'una:
**il modello ammette le righe miste**.

Dal 2026-09-28 (F-5) il backend **scrive e cancella** solo override di livello puro
(tutte le altre dimensioni `NULL`, `parameter_repository._altre_dimensioni_nulle`).
`script.fn_list_parameters_for_user` invece li **legge** così (doc auto-gen, oggi):

| Join | Filtra | Manca |
| --- | --- | --- |
| `po_us` (utente) | solo `django_user_id` | gruppo, emittente, categoria, sessione, funzione |
| `po_em` (emittente) | utente e gruppo `NULL` | categoria, sessione, funzione |
| `po_cat` (categoria) | tutte le altre `NULL` | — (è il modello da seguire) |

Effetti: una riga mista compare in lista come «override personale» (o d'emittente)
con un `id` che la DELETE del backend (pura) rifiuta con 404; con più righe miste
dello stesso utente il `LEFT JOIN po_us` può **duplicare** la riga del parametro.

**Si chiede:** `po_us` e `po_em` escludono tutte le altre dimensioni, come `po_cat`.
Lo stesso vale per la `COALESCE` di `resolved_value` che riusa `po_us`.

⚠️ **Fuori da questa richiesta**, e da decidere con Tid prima: la cascata di
risoluzione (`fn_get_parameter_full`) — se le righe miste debbano esistere e come
pesino. Qui si allinea solo la **lista** a ciò che il backend scrive.

**Test DB:** un pgTAP che **costruisce** una riga mista (utente + categoria) e una
pura per lo stesso parametro e utente, e prova che la lista mostra la pura, una riga
sola per parametro, con l'`id` della pura. Il caso si costruisce: sul DB di oggi
potrebbe non esserci nessuna riga mista, e il test non deve dipenderne.

## 4. D-1 — `E_USER_DISABILITATO` (domanda a Tid)

Il codice è a catalogo (`NON_PERMESSO`), ma dal 2026-10-02 nessuno lo solleva: col
ritiro di `DISABILITATO` (R-DB-1 del brief area Accessi) una veste spenta è
`attivo = false` col suo tipo, e chi ha solo vesti spente lo nega il livello d'area.
Due strade:

* **ritirarlo** (`obsoleto_dal`), come ogni codice che nessuno nomina più;
* **riusarlo** come codice di «nessuna veste accesa», se si vuole che quel diniego
  abbia una frase sua invece del 403 generico. ⚠️ Sarebbe un riuso per una
  condizione nuova: api.md §«Il rubinetto degli accumulatori» chiede un codice
  nuovo, non uno vecchio con un significato diverso.

Raccomandazione del BE: **ritirarlo**. Se serve un messaggio per «nessuna veste
accesa», nasce un codice suo.

## 5. Cosa fa il backend dopo l'apply

* R-1: `./manage-env.sh genera_error_policies`; frasi di ripiego in
  `error_messages_fallback.py` per i sei; via le sei voci da `_DEBITO` del guardrail
  (fallisce finché restano); per i due `*_NOT_FOUND` i test di
  `test_conti_bancari_service` controllano anche lo status 404; doc
  `api_conti_bancari_ruolo.md`, `api_conti_bancari_soggetto.md`,
  `jwt_audit_middleware.md`, api.md §codici middleware-level. Chiude **E-1**.
* R-2: nessuna modifica BE; si toglie la riga «lato DB» di F-5 dall'analisi.
* D-1: se ritirato, nessuna modifica BE (nessun punto di chiamata lo nomina).

## 6. Nota per il team DB

> ✅ **Superata il 2026-10-07**: `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`
> è nel repo (`codici_errore.csv`, `messaggi_errore.csv` id 1201), mergiato con
> `brief-db-offerta-emissione-ed-erogazione` (commit `6d0a138ef`). Il DB non è più
> avanti rispetto a git sul catalogo.

Il 2026-10-07 il cancello `test_error_codes_db_policy_guardrail` (DB vero) è rosso
su `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`, nominato da
`script.fn_check_listino_congelabile` sul DB di sviluppo e **assente dal repo**
(né CSV né changeSet). Sembra un giro DB applicato e non ancora mergiato: non è di
questo brief, ma il BE non può rigenerare le policy (R-1) finché il DB è avanti
rispetto a git sul catalogo.

## 7. Consegne

*(team DB, 2026-10-07)*

### 7.1 R-1 — i sei codici a catalogo

Righe in coda a `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv`
(mirror `loadUpdateData`, nessun changeSet nuovo). Classi come proposte dal BE;
frase quella che il BE scrive già; `causa` e `soluzione` scritte per chi legge,
e per i due del middleware e i due dei reaper la soluzione è per **chi gestisce
il sistema**, non per l'operatore.

| Codice | Classe | id messaggio |
| --- | --- | --- |
| `E_ANAG_CONTO_NOT_FOUND` | `NON_TROVATO` | 1204 |
| `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` | `NON_TROVATO` | 1205 |
| `E_GUC_RESET_FAILED` | `TECNICO` | 1206 |
| `E_DB_ROLE_UNSAFE` | `TECNICO` | 1207 |
| `E_CODA_JOB_STANTIO` | `TECNICO` | 1208 |
| `E_STAMPA_JOB_STANTIO` | `TECNICO` | 1209 |

Nessun pgTAP nuovo, come chiesto: nessuna funzione DB li solleva, e i presidi
del catalogo (`test-codici-errore-identita`, `test-catalogo-messaggi-errore-completo`)
valgono anche per loro. Verificato prima di scrivere: nessuno dei sei era già a
catalogo; id e codici senza doppioni nei due file.

### 7.2 D-1 — `E_USER_DISABILITATO` ritirato

Decisione di Tid del 2026-10-07: **ritirarlo**. `obsoleto_dal = 2026-10-07` nel
CSV, con la nota del perché. Verificato per nome: nessuna funzione DB, nessun
punto del backend o del frontend lo solleva; lo nominano solo le copie del
catalogo nel backend (`error_policies_generated.py`, `error_messages_fallback.py`).
Il messaggio resta: un codice ritirato continua a risolversi
(`test-codici-errore-obsoleto-dal`). Se servirà una frase per «nessuna veste
accesa», nasce un codice suo.

### 7.3 R-2 — la lista, e il vincolo che la rende vera

⭐ **Trovato mentre si scriveva R-2, e cambia la premessa del §3.** Il brief dice
*«l'unicità è sull'insieme»*. Sulla carta sì, nei fatti no:
`uq_overrides_full_scope_v4` è `NULLS DISTINCT` (il default di PostgreSQL),
quindi non scatta su nessuna riga che abbia una dimensione `NULL` — cioè su
nessun override reale. Il modello ammetteva **due override personali puri** per
lo stesso parametro e utente (basta una doppia richiesta concorrente sull'upsert
CTE del BE). Effetti: la cascata ne sceglieva uno a caso (`LIMIT 1` senza
`ORDER BY`), e la lista duplicava la riga **anche con i JOIN puri**. Allineare i
JOIN non bastava a garantire «una riga per parametro».

Decisione di Tid del 2026-10-07: chiuderlo nello stesso giro.

| changeSet | Cosa |
| --- | --- |
| `00_schema/config/20261007-70-alter-parameter-overrides-unique-nulls-not-distinct` | `uq_overrides_full_scope_v4` → `uq_overrides_full_scope_v5` **`NULLS NOT DISTINCT`**, stesse colonne. `attivo` resta fuori (una riga spenta occupa il suo ambito: l'upsert del BE la riattiva). Cancello `HALT` su zero doppioni (`expectedResult: 0`, lecito per §11.4); la query per trovarli è nell'intestazione. Nome nuovo apposta: il significato cambia |
| `20_code/script/20261007-71-update-fn-list-parameters-for-user-livelli-puri` | i **quattro** livelli mostrati leggono solo override puri — anche il **gruppo**, che il brief non nominava: non ha id, ma un valore misto mostrato «del gruppo» è lo stesso falso. `resolved_value` **chiama** `script.fn_get_parameter_full` invece di ricopiarne la cascata (regola del 2: la copia esce nello stesso giro). Firma e `RETURNS TABLE` invariati, `CREATE OR REPLACE`; `%TYPE` su parametri e colonne di uscita |

⚠️ **Sulla `COALESCE`, una lettura diversa dalla richiesta.** Il §3 chiede che
«lo stesso valga per la `COALESCE` di `resolved_value` che riusa `po_us`». Resa
pura, la `COALESCE` avrebbe smesso di dire ciò che il runtime applica (la cascata
legge anche le righe miste): è proprio la domanda che il §3 tiene fuori. Quindi
`resolved_value` segue il runtime, per costruzione. Conseguenza dichiarata: con
una riga mista in vigore la lista può mostrare un `resolved_value` che non
coincide con nessun livello esposto. È vero, e la lista non lo nasconde.

**Fatto datato** (dbdev, 2026-10-07, come `zeroerp_app`): 4 override, zero righe
miste, zero doppioni. Non motiva niente: dice solo che il cancello del `-70` su
dev non si chiude.

### 7.4 pgTAP

| File | Cosa |
| --- | --- |
| `script/test-fn-list-parameters-for-user.sql` | ⚠️ *superata dal §7.7: oggi 18 test, senza righe miste.* 14 → **20**. I test 15-20 **costruiscono** le righe miste accanto alle pure: una riga per parametro (15), utente ed emittente col valore e l'id della pura (16-17), gruppo e categoria con sole miste a `NULL` (18), sola mista utente+categoria → nessun override personale (19), `resolved_value` = `fn_get_parameter_full` sugli stessi ambiti (20, confronto col runtime e non con un valore: deve seguire la risposta di Tid sulle miste) |
| `config/test-parameter-overrides-categoria-cliente-v1.sql` | ⚠️ *oggi 15 test, §7.7.* 12 → **13**. Test 7 sul v5 **e** su `indnullsnotdistinct` (il nome da solo non prova la clausola), 8 su v3 e v4 assenti, 13 nuovo: secondo override sullo stesso ambito → `23505`. Il parametro della fixture ora è costruito: il test 11 scrive un override con tutte le dimensioni `NULL` sul primo parametro reale, e col vincolo che vale davvero avrebbe rifiutato il giorno in cui quell'ambito esiste |
| `config/test-parameters-vendite-limiti-prezzi.sql`, `config/test-parameters-uom-defaults-cascade-v1.sql`, `config/test-parameters-emittente-defaults-cascade.sql` | scrivono override puri su parametri e ambiti **reali** (primo utente, un emittente): `ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE`. Prima un override già presente produceva un doppione e la cascata sceglieva a caso, quindi il test era fragile senza saperlo; ora riscrive e il `ROLLBACK` ripristina. ⚠️ Nominano il vincolo: rossi finché il `-70` non è applicato |

**Prova** (scratch `zeroerp_ci`, come `zeroerp`, SQL **estratto** dai due YAML
in una transazione annullata, `ON_ERROR_STOP=1`): i sette file che toccano gli
override — i cinque sopra più `script/test-fn-get-parameter-full-emittente` e
`config/test-fn-get-parameter-full-categoria-cliente-v1` — **tutti verdi**
(20, 13, 7, 13, 10, 9, 9). Sul corpo vecchio, senza l'SQL estratto, i test 15-19
della lista sono **rossi** e il 20 muore su «più di una riga restituita da una
sottoquery» (vedono il difetto); 7, 8 e 13 del vincolo rossi. `plpgsql_check`
pulito, firma identica (`pg_get_function_identity_arguments`). La `preCondition`
del `-70` dà 0 su dbdev e sullo scratch. Guardrail statici verdi
(`precondition_seed`, `run_on_change`, `sql_letterali`, `timestamp_senza_fuso`,
`ddl_su_trigger_automazione`). ⚠️ Prova da owner: la RLS non entra; la corsa
come app è quella di Tid dopo l'apply.

### 7.5 Ricadute fuori dal DB (richieste, non fatte)

* **BE — `parameter_repository._upsert_override_cte`**: il commento dice che
  «una seconda riga attiva accanto a quella spenta non si inserisce». Fino a
  oggi era falso (il v4 non scattava); col v5 è vero. In più due upsert
  concorrenti sullo stesso ambito ora rispondono **`23505`** invece di creare un
  doppione: da decidere come lo traduce il BE (oggi probabilmente come errore
  generico). Il BE potrebbe anche passare a `ON CONFLICT ON CONSTRAINT
  uq_overrides_full_scope_v5`, che ora funziona. Scelta del BE.
* **BE — D-1**: le righe di `E_USER_DISABILITATO` nelle copie del catalogo
  (policy generate, frase di ripiego) restano coerenti con un codice ritirato;
  nessuna modifica obbligata.
* **Doc aggiornata**: `dbzero/config/manual/parameter_overrides.md`,
  `dbzero/script/manual/fn_list_parameters_for_user.md`,
  `guide/configurazione-e-gestione-parametri.md`. La doc auto-gen si rigenera
  dopo l'apply.

### 7.6 Le righe miste — ✅ deciso da Tid il 2026-10-07: non esistono

> Decisione: *«commercialmente al massimo si farebbe 15 + 5 separato, mai
> insieme: adesso farei un solo sconto»*. Un override vale per **un** ambito; fra
> due ambiti la cascata sceglie un valore (vince l'utente), non li combina. Il
> vincolo e il resto nel §7.7. Sotto, la domanda com'era posta.

* **Le righe miste** (§3, invariato): devono esistere? come pesano nella
  cascata? Oggi `fn_get_parameter_full` prende una riga utente+categoria al
  livello utente **anche quando la categoria non è quella in gioco**. Il test 20
  della lista è scritto per seguire la risposta, qualunque sia. Se la risposta
  fosse «non devono esistere», la sede è un `CHECK` (al più una dimensione
  valorizzata) dietro un cancello sui dati, e il problema della lista sparisce
  alla radice.

### 7.7 Secondo giro: un ambito per override (§7.6)

| changeSet | Cosa |
| --- | --- |
| `00_schema/config/20261007-72-alter-parameter-overrides-check-un-ambito` | `CHECK chk_parameter_overrides_un_ambito`: `num_nonnulls(` le sei dimensioni `) = 1`. Niente righe miste, e niente righe **senza** ambito (nessun livello della cascata le leggeva: override inerti). CHECK puro, nessun codice d'errore: il backend scrive sempre un ambito solo, quindi il `23514` lo vede solo uno scrittore sbagliato. Cancello `HALT` su zero righe fuori regola (0 su dbdev e scratch, 2026-10-07) |
| `20_code/script/20261007-73-update-fn-list-parameters-for-user-filtri-dai-vincoli` | escono dalla lista i filtri «altre dimensioni `IS NULL`» del `-71`: col vincolo sono una copia del CHECK. `resolved_value` resta delegato a `fn_get_parameter_full`. Firma invariata |

⚠️ **Incidente evitato, da sapere.** Avevo riscritto il `-71` in quel file per
togliere i filtri, mentre Tid lo stava applicando (19:28 dbdev, 19:29 scratch).
Un changeSet applicato non si tocca: il `-71` è stato **ripristinato parola per
parola** (corpo e `COMMENT` confrontati con il database: md5 identici) e la
semplificazione è diventata il `-73`.

**pgTAP** (oggi):

| File | Cosa |
| --- | --- |
| `config/test-parameter-overrides-categoria-cliente-v1.sql` | **15** test. L'11 (riga senza ambito) passa da «accettata» a **rifiutata** `23514`; 14 nuovo: riga utente + categoria → `23514`; 15 nuovo: il CHECK c'è, col suo nome |
| `script/test-fn-list-parameters-for-user.sql` | **18** test. I 15-20 sulle righe miste escono (la riga non nasce più); 15-18: un override per livello su tutti e quattro → una riga per parametro, valore e id di utente ed emittente, `resolved_value` = `fn_get_parameter_full` sugli stessi ambiti |

**Prova** (scratch `zeroerp_ci`, come `zeroerp`, che ha già `-70`/`-71`/`-72`; SQL
del `-73` **estratto**, transazione annullata): dieci file che scrivono o leggono
override verdi — i due sopra (15, 18), `vendite-limiti-prezzi` (7),
`uom-defaults-cascade` (13), `emittente-defaults-cascade` (10),
`fn-get-parameter-full-emittente` (9), `fn-get-parameter-full-categoria-cliente`
(9), `fk-surrogate-dispatch` (7), `vw-parameter-fk-surrogate-dangling` (4),
`elimina-credenziale` (17 su 18: il 18 è un test «come app» rosso da owner, e lo
è identico senza il `-73`). `plpgsql_check` pulito, firma identica. Guardrail
statici verdi.

**Ricadute sul BE** (in aggiunta al §7.5):

* ⛔ `core/tests/db/test_parameter_overrides_db.py`:
  `test_upsert_utente_non_tocca_la_riga_mista` e
  `test_delete_utente_non_cancella_la_riga_mista` **scrivono righe miste**
  (utente + categoria, utente + sessione). Dopo il `-72` quelle `INSERT`
  rifiutano con `23514`: i due test vanno ritirati o trasformati in «una riga
  mista non nasce».
* `parameter_repository._altre_dimensioni_nulle`: col vincolo le condizioni «le
  altre dimensioni `IS NULL`» sono sempre vere. Restano corrette; toglierle è
  una scelta del BE (sarebbe la stessa pulizia del `-73`).

## 8. Giro BE

*(sessione backend, 2026-10-07 sera)*

**Verifica dell'apply su dbdev** (come `zeroerp_app`): `-70`, `-71`, `-72`, `-73`
in `databasechangelog`; `chk_parameter_overrides_un_ambito` e
`uq_overrides_full_scope_v5` con `indnullsnotdistinct = true`;
`fn_list_parameters_for_user` senza filtri `IS NULL`; i sei codici a catalogo
con le classi del §7.1, `E_USER_DISABILITATO` con `obsoleto_dal = 2026-10-07`.
La rigenerazione delle policy porta **solo** i sei codici e il ritiro: il DB non
è avanti rispetto a git sul catalogo.

| Cosa | Dove |
| --- | --- |
| Policy rigenerate (990 voci, 102 ritirate) | `core/services/error_policies_generated.py` |
| Frasi di ripiego per i sei, senza segnaposto | `core/services/error_messages_fallback.py` |
| `_DEBITO` del guardrail vuoto (E-1, E-2 chiuse) | `core/tests/test_error_codes_declared_guardrail.py` |
| I due `*_NOT_FOUND` provati anche sullo status **404** | `anagrafiche/tests/services/test_conti_bancari_service.py` |
| ⭐ §7.5 — l'upsert passa a `INSERT … ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE` (riattiva la riga come prima). Atomico: due upsert concorrenti sullo stesso ambito si serializzano sul vincolo, niente doppione e niente `23505` da tradurre. La CTE SELECT-poi-INSERT esce | `core/db/parameter_repository.py` |
| §7.7 — via i filtri «altre dimensioni `IS NULL`» da upsert e delete, come il `-73` sulla lista: col CHECK sono una copia. La tupla `_DIMENSIONI_OVERRIDE` resta come elenco delle colonne di scope ammesse (`_colonna_di_scope`: il nome finisce nella SQL) | idem |
| §7.7 — i due test che scrivevano righe miste diventano: la riga mista **non nasce** (`23514`), un upsert ripetuto aggiorna la stessa riga (una sola), la delete non tocca l'override di un altro utente | `core/tests/db/test_parameter_overrides_db.py` |
| Il test della SQL per livello riscritto sul vincolo d'ambito | `core/tests/services/test_parameter_repository_dimensioni.py` |
| Doc | `api_conti_bancari_ruolo.md`, `api_conti_bancari_soggetto.md` (404, via il «difetto noto»), `jwt_audit_middleware.md`, api.md §codici middleware-level, `api_parameter_settings.md`, catalogo BB backend (`ParameterRepository`), analisi difetti (E-1, F-5 lato DB, E-5 per `E_USER_DISABILITATO`) |

D-1: nessuna modifica (nessun punto di chiamata nomina `E_USER_DISABILITATO`; le
copie del catalogo lo portano come ritirato).

**Prova:** `ZEROERP_TEST_DB_E2E=1`, suite `apps.core` + `apps.anagrafiche` —
2262 test verdi (1 skip preesistente), i cinque di `test_parameter_overrides_db`
eseguiti sul DB vero, non saltati.
