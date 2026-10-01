# Brief DB — Il registro degli owner e la sync riservati al migratore (D6, il pezzo che resta)

> **Da leggere per primo: §8 — il giro del 26-09 (cosa è scritto, come è
> stato provato, l'esito dell'apply).** Poi §2 — la forma, e le due trappole che la cambiano.
> Origine: [brief-db-fixture-che-costruiscono-d7-d6-d4.md](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md)
> §3 e §6.4 (chiuso e archiviato il 2026-09-19), a sua volta figlio di
> [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md) §D6.
> Stima scritta lì: **≈ mezza giornata**. ⚠️ D6-bis (la forma canonica del
> `search_path` sulle 38 DEFINER) **non** è qui: resta in `migliorie-generali`.
>
> ~~🔵 Stato 2026-09-19: brief scritto, nessun changeSet.~~
> ✅ **CHIUSO il 2026-09-26.** D-1/D-2/D-3 decise da Tid come raccomandato
> (§6). ChangeSet `20_code/dbops/20260926-11` e `90_end/20260926-12`, loop
> `20260205-41` e provisioning ritoccati, due pgTAP nuovi, doc aggiornata.
> SQL estratto provato su un cluster PostgreSQL 18 usa-e-getta (§8.2), poi
> **applicato da Tid: pgTAP verdi, nessuna regressione** (§8.3). D6 chiusa in
> `migliorie-generali`; D6-bis resta lì.

---

## 1. Il difetto, sul modello

`dbops.sec_functions_owner` dichiara **chi deve possedere** le funzioni
sensibili (cinque righe: i due `tx_id`, `fn_ensure_logconn`,
`fn_log_error_only`, `fn_job_run_log_failure` — tutte a `postgres`), e
`dbops.fn_sync_functions_owner()` — `SECURITY DEFINER` di `postgres` —
**applica** quella dichiarazione con `ALTER FUNCTION … OWNER TO`. Il runAlways
`90_end/20251123-04` la chiama a ogni `liquibase update`, la provision-post
`20251123-12` la porta a `postgres`.

⛔ **Chi può scrivere il registro ed eseguire la sync decide chi possiede le
DEFINER di `postgres`.** Il giro del `20260912-41` l'ha mostrato dal verso
buono — il migratore si presta la proprietà per un `CREATE OR REPLACE` — ma la
leva è la stessa per chiunque abbia le due porte. E le ha `zeroerp_app`, per
costruzione: il loop dei grant (`90_end/ci_apply/20260205-41`) dà
`SELECT, INSERT, UPDATE, DELETE` su **tutte** le tabelle di `dbops` e
`EXECUTE` su **tutte** le funzioni.

Cosa può fare l'app con le due porte (già scritto nel brief madre §3, vale
riportarlo perché è la ragione del cantiere): `UPDATE dbops.sec_functions_owner
SET required_owner = 'zeroerp_app'` + `SELECT dbops.fn_sync_functions_owner()`
⇒ le sei DEFINER indurite passano all'app. Non arriva al superuser (nessun
`CREATE` su schemi, funzioni non risolte da `pg_temp`), ma **spegne il canale
di log** (`fn_ensure_logconn`, `fn_log_error_only` non hanno più i privilegi
per il `dblink`) e può mettere un `ALTER FUNCTION … SET` su una DEFINER che poi
**torna a `postgres`** con quel `SET` dentro.

⚠️ Fatti letti dal vivo su dbdev il 2026-09-19 (fotografia, non motivo — il
motivo è il capoverso sopra):

| Cosa | Valore |
| --- | --- |
| `has_table_privilege('zeroerp_app', 'dbops.sec_functions_owner', …)` | INSERT, UPDATE, DELETE, SELECT **tutti `true`** (`zeroerp_app=arwd/titodb`) |
| `proacl` di `fn_sync_functions_owner()` | `{=X/postgres, postgres=X/postgres, zeroerp_app=X/postgres, zeroerp_batch_fatturazione=X/postgres}` |
| owner di `dbops`, del registro, della sync | `titodb`, `titodb`, `postgres` |
| `pg_has_role('zeroerp_app', owner di dbops, 'MEMBER')` | `false` |

⭐ La seconda riga cambia una frase del brief madre: l'`EXECUTE` dell'app sulla
sync **non è «solo via PUBLIC»** — c'è una voce esplicita, rimappata a
`postgres` come concedente dal cambio di proprietario. Un `REVOKE … FROM
PUBLIC` da solo non toglierebbe niente all'app, e il loop la ridarebbe alla
passata dopo. È il fatto che chiude la strada dell'ACL (§2.1).

## 2. La forma — decisa dal vincolo tecnico, con due trappole

### 2.1 La sync si difende da sola, nel corpo — non con GRANT/REVOKE

⛔ **Non** con l'ACL della sync, per tre ragioni che si sommano:

1. la funzione è di `postgres`: un privilegio dato al migratore **mentre la
   possiede in prestito** non sopravvive alla restituzione — `ALTER … OWNER`
   rimappa le voci ACL del vecchio proprietario sul nuovo (brief madre §6.4);
2. il loop `20260205-41` e `provision_db_roles.sql` rifanno `GRANT EXECUTE ON
   ALL FUNCTIONS` a ogni passata: servirebbe la sync in `v_fn_riservate` in
   **tre** sedi, più un `GRANT` esplicito al migratore o la CI muore
   (il runAlways `20251123-04` gira come migratore, che in CI è `zeroerp`);
3. il ruolo batch ha `=X` dal suo provisioning, che è **fuori** dai changeSet
   (AGENTS §«I privilegi dei ruoli batch stanno nel provisioning»).

⇒ La sync **rifiuta da sola** chi non è il migratore. `EXECUTE` a PUBLIC
**resta** (decisione già presa nel brief madre §3): con la guardia in testa è
un privilegio che non compra niente.

**Chi passa**: chi possiede lo schema `dbops` — cioè il migratore, in ogni
ambiente (`titodb` su dbdev, `zeroerp` in CI: memoria
`reference_security_definer_proprietario_dipende_dal_migratore`) — e un
superuser (la provision-post come `postgres`). ⭐ Il criterio è **la proprietà
dello schema**, non un nome di ruolo: non c'è un ruolo da nominare che sia
uguale nei due ambienti.

#### ⛔ Trappola 1 — `current_user` dentro una DEFINER è il PROPRIETARIO

Il brief madre §6.4 scriveva `pg_has_role(current_user, …)`. **Non funziona**:
dentro una `SECURITY DEFINER` `current_user` vale il proprietario della
funzione, cioè `postgres`, cioè superuser ⇒ la guardia sarebbe **sempre
aperta**, e un pgTAP con `throws_ok` lo direbbe al primo giro — ma è la
forma che si scrive d'istinto. Il chiamante si legge da **`session_user`**:

```plpgsql
IF NOT (
      pg_catalog.pg_has_role(session_user,
          (SELECT nspowner FROM pg_catalog.pg_namespace WHERE nspname = 'dbops'),
          'MEMBER')
   OR (SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = session_user)
) THEN
    RAISE EXCEPTION USING
        ERRCODE = 'insufficient_privilege',
        MESSAGE = format('dbops.fn_sync_functions_owner: riservata a chi possiede lo schema dbops; sessione %s.', session_user);
END IF;
```

⚠️ **Il limite dichiarato di `session_user`**: è il ruolo di **login**. Una
sessione aperta come `titodb` che fa `SET ROLE zeroerp_app` passerebbe. Non
è il caso dell'applicazione (Django si connette **come** `zeroerp_app`, e
`E_DB_ROLE_UNSAFE` rifiuta un percorso web su un ruolo diverso) né del runner
pgTAP (`PGUSER=zeroerp_app`, connessione vera — `scripts/testpgtap.sh`).
Un'alternativa senza questo limite **non esiste**: PostgreSQL non espone
«l'invocante» di una DEFINER, e una facciata `INVOKER` che controlla
`current_user` e chiama un nucleo DEFINER riporta il problema sul nucleo (che
dovrebbe di nuovo difendersi da solo, con `session_user`). Si scrive nel
`COMMENT` e nel presidio, non si nasconde.

#### ⛔ Trappola 2 — il rifiuto NON passa dal canale di log

La guardia solleva con `RAISE … ERRCODE = 'insufficient_privilege'` (**42501**),
**non** con `script.fn_log_and_raise_error`. Due ragioni:

- è lo **stesso** esito che l'app riceve su una funzione revocata
  (`test-registri-append-only-postura-v1`, test 22-23: `fn_audit_begin` →
  `42501`): la postura si legge uguale, con o senza ACL;
- il canale di log (`script.fn_log_error_only`, fuori transazione via
  `dblink`) è **una delle funzioni che il registro protegge**: una guardia sul
  meccanismo di hardening non deve dipendere da ciò che indurisce.

Nessun operatore lo vedrà mai: nell'applicazione nessuno chiama la sync
(zero riferimenti in `backend/`, zero nei pgTAP fuori dal presidio del
`search_path`). Niente codice a catalogo, quindi. → **D-1** in §6, perché è
una deroga alla regola «errori via `fn_log_and_raise_error`» e va detta.

### 2.2 Il registro: SOLA LETTURA per l'app, nelle tre sedi

> ⚠️ **Invecchiato fra il 19 e il 26-09.** Il 25-09 nella lista sono entrate
> `config.credenziali*`, `config.nomi_tentati*`, `magazzino.causali` e
> `config.tabelle_gestibili`: non è più «cosa di magazzino». Il 26-09 il
> commento in testa alla lista è stato allargato alla forma generale («scrive
> una porta del proprietario»), e il modello del forward è diventato
> `90_end/20260925-62` (il più recente della stessa forma), non il `20260918-15`.

La lista giusta **esiste già** dal 18-09: `v_tabelle_sola_lettura_app` nel
loop `20260205-41` (nata per il ledger di magazzino, «l'applicazione legge,
scrive solo la primitiva»). Il brief madre proponeva «una lista nuova»: non
serve più — si aggiunge `'dbops.sec_functions_owner'` a quella, e si
**allarga il commento** in testa, che oggi la descrive come cosa di
magazzino.

Le tre sedi, nella forma già pagata due volte (`audit_log` l'11-09, ledger il
18-09 — AGENTS §«Un `REVOKE` a `zeroerp_app` in un changeSet normale NON tiene»):

| Sede | Cosa |
| --- | --- |
| `90_end/ci_apply/20260205-41` (runOnChange, si ritocca in place) | `'dbops.sec_functions_owner'` in `v_tabelle_sola_lettura_app` |
| `scripts/sql/provision_db_roles.sql`, blocco «POSTURA DICHIARATA» | `REVOKE INSERT, UPDATE, DELETE ON TABLE dbops.sec_functions_owner FROM :'app_role'` — è l'**ultima parola** in CI |
| `90_end/<data>-NN-revoke-app-scrittura-sec-functions-owner` (forward, `runOnChange: false`) | applica **subito** su dev, dove `ci_apply` non gira da solo. Modello: `90_end/20260918-15` (guard sul ruolo assente, `preConditions` solo `tableExists`, `rollback` che riapre) |

**`SELECT` resta** all'app (→ **D-2**): è un registro di configurazione, non
un segreto, e una quarta forma di lista («invisibile») costerebbe una riga in
tre sedi per non comprare niente — chi legge il registro senza poterlo
scrivere né eseguire la sync non ha nessuna leva.

**Chi scrive legittimamente il registro, e resta libero**: il mirror CSV
`80_data/20251123-51` (come migratore, proprietario della tabella) e i
changeSet «a prestito» (`UPDATE … SET required_owner = current_user` come
migratore). Zero scrittori in `backend/`, zero nei pgTAP (censiti il 19-09).

### 2.3 Sostituire la sync: il giro della copia di servizio, di nuovo

La sync è di `postgres` e **non si presta a sé stessa**: si rifà il giro del
`20260912-41`, in **un** changeSet `20_code/dbops/`, timeline normale, senza
contesto, eseguibile da `titodb` (memoria: due stesure «per postgres» sono
morte il 12-09):

1. `fn_sync_functions_owner_boot` = copia della definizione **viva**
   (`pg_get_functiondef`, nessun corpo duplicato);
2. la sync viva dà la copia a `postgres` (riga temporanea nel registro);
3. la copia presta l'originale al migratore;
4. `CREATE OR REPLACE` con la guardia in testa — corpo **dalla doc auto-gen**
   (`docs/it/dbzero/dbops/funzioni/fn_sync_functions_owner.md`), `SET
   search_path TO 'pg_catalog', 'public', 'pg_temp'` **identico** (il test 3 di
   `test-security-definer-search-path-v1` pretende esattamente quella forma),
   `COMMENT` riscritto (dice anche il limite di `session_user`);
5. la copia restituisce l'originale a `postgres`;
6. l'originale — pinnato, con la guardia, di nuovo di `postgres` — riprende la
   copia al migratore, che la droppa; via le righe temporanee.

⭐ La guardia **non rompe il giro**: ai passi 2 e 6 chi chiama è il migratore,
che possiede `dbops`. E non rompe il runAlways `20251123-04` (migratore) né
la provision-post (`postgres`).
⚠️ Da zero (CI) ogni passo è un no-op con `WARNING` finché la provision-post
non ha dato la sync a `postgres`: identico al 41, che in CI è passato così.

## 3. Il presidio — `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql`

> ⚠️ **Come è stato scritto il 26-09 (plan 13, non 11)**: al 9 (`42501`) si è
> aggiunto il **10**, `throws_like` sulla frase della guardia — stesso codice
> dell'ACL, frase diversa: senza, un `REVOKE` futuro terrebbe verde il 9 anche
> con la guardia tolta. Il vecchio 10 (registro con righe) è l'**11**, il vecchio
> 11 (struttura, commenti `--` tolti prima di cercare) è il **12**, e il **13**
> pinna che la copia `_boot` del giro non è rimasta (`hasnt_function`). Il
> gemello da owner è un file suo,
> `db/pgtap/dbops/test-sec-functions-owner-migratore-passa-v1.sql` (plan 2): il
> test 1 dice se il runner owner **è** il migratore (membro del proprietario di
> `dbops`, o superuser) — se è rosso, il 2 non prova niente e il problema è la
> macchina, non la guardia.

Come `zeroerp_app` (runner di default), sul modello di
`test-registri-append-only-postura-v1`:

| # | Cosa |
| --- | --- |
| 1-3 | `has_table_privilege(app, registro, INSERT/UPDATE/DELETE)` = `false` |
| 4 | `has_table_privilege(app, registro, SELECT)` = `true` (D-2, pinnato) |
| 5-7 | comportamento: INSERT / UPDATE / DELETE sul registro → `42501`, anche a zero righe |
| 8 | ⭐ `has_function_privilege(app, sync, EXECUTE)` = **`true`** — **dichiarato**: la difesa non è nell'ACL, e questo test lo dice a chi si aspettasse un `false` come per `fn_audit_begin` |
| 9 | `throws_ok('SELECT dbops.fn_sync_functions_owner()', '42501')` — la guardia |
| 10 | gemello «esiste»: il registro ha righe (> 0) — il rifiuto del 9 non è un rifiuto su un registro vuoto |
| 11 | struttura: `prosrc` della sync contiene `session_user` e **non** contiene `pg_has_role(current_user` — pinna la trappola 1 |

E un **gemello da owner** (`-- pgtap-runner: owner`, motivo scritto): `lives_ok('SELECT dbops.fn_sync_functions_owner()')` — il migratore passa
ancora. In `BEGIN … ROLLBACK` un eventuale `ALTER OWNER` si ritira. ⚠️ Senza
questo gemello il presidio «il migratore passa» esisterebbe solo come «il
prossimo `liquibase update` muore», che è un presidio violento e tardivo.

Presidi trasversali attraversati (memoria «funzione plpgsql nuova = due
presidi»): la `_boot` è temporanea e sparisce nel changeSet; la sync è
**modificata**, non nuova — riferimenti morti la rilegge (usa solo
`pg_catalog.*`, ok), il rubinetto del primo motivo non la conta (nessun
`fn_log_and_raise_error`).

## 4. Documentazione da toccare nello stesso giro

- `docs/it/dbzero/dbops/manual/fn_sync_functions_owner.md` — §«Considerazioni
  di sicurezza»: la guardia, chi passa, il limite di `session_user`, `EXECUTE`
  PUBLIC che resta e perché;
- `docs/it/dbzero/dbops/manual/sec_functions_owner.md` — un capoverso «chi la
  scrive»: il migratore e basta, l'app legge;
- `docs/it/linee-guida-sql.md` §11.8 — la quarta occorrenza del pattern a tre
  sedi (`audit_log`, `storico`, ledger, registro): una riga nell'elenco, non
  una sezione;
  ⚠️ **smentito il 26-09**: in §11.8 un elenco delle occorrenze non c'è, e il
  conto non era più quattro (credenziali, nomi tentati, pannello dal 25-09). Fatto
  invece: la frase «due elenchi» in testa al loop è diventata l'elenco vero delle
  cinque liste, e si è aggiunto il paragrafo **«una `SECURITY DEFINER` di
  `postgres` non si chiude con l'ACL»**, che è la regola nuova di questo cantiere;
- `migliorie-generali-da-test-valutazione.md` §D6 e checklist: `[~]` → `[x]`
  con la data, D6-bis resta `[ ]`;
- memoria `reference_security_definer_proprietario_dipende_dal_migratore`:
  l'ultimo capoverso («registro e sync vanno riservati») diventa «riservati
  dal <data>, con `session_user`».

## 5. Le prove — prima dell'apply, che lo fa Tid

- SQL **estratto** (`updateSQL` offline, render dallo YAML), eseguito in
  `BEGIN … ROLLBACK` **come `titodb` su dbdev** e **come `zeroerp` su
  `zeroerp_ci`**: i NOTICE del giro della copia, `proowner` finale
  `postgres`, `proconfig` invariato, `prosrc` con la guardia;
- nella stessa transazione, `SET ROLE zeroerp_app` **non basta** per provare
  la guardia (è `session_user`, trappola 1 al contrario): la prova negativa è
  il pgTAP come app, cioè il runner — **lo lancia Tid**;
- il forward `90_end` in `BEGIN … ROLLBACK`: `has_table_privilege` prima/dopo;
- ⛔ niente `liquibase update`, niente baseline: cancello e regola.

## 6. Decisioni per Tid — ✅ prese il 2026-09-26

✅ **Tid ha accettato le tre raccomandazioni** così come sono scritte qui sotto:
`42501` nudo, `SELECT` che resta, sync fuori da `v_fn_riservate`.

| # | Domanda | Raccomandazione (= decisione) |
| --- | --- | --- |
| **D-1** | Il rifiuto della sync: `42501` nudo (deroga a «errori via `fn_log_and_raise_error`») o un codice a catalogo di classe `NON_PERMESSO`? | **`42501`** — §2.1 trappola 2: stessa forma della postura gemella, e il canale di log è fra le funzioni protette. Un codice a catalogo servirebbe a un operatore che non esiste |
| **D-2** | `SELECT` sul registro all'app: resta o si toglie? | **resta** — §2.2: nessuna leva senza scrittura+sync, e la lista «sola lettura» esiste già; togliere = quarta forma in tre sedi |
| **D-3** | La sync in `v_fn_riservate` (REVOKE EXECUTE da PUBLIC/app nelle tre sedi) **in aggiunta** alla guardia? | **no** — §2.1 punto 2: doppia sede per la stessa regola, e in CI serve un GRANT esplicito al migratore che oggi non c'è. Se un giorno si farà, il presidio (test 8) va girato da `true` a `false` |

## 7. Cosa resta

> ⚠️ Superato il 26-09: i punti 1 e 2 sono fatti, il 3 è di Tid. Stato vero in §8.

1. ✅ D-1/D-2/D-3 decise da Tid → changeSet `20_code/dbops` (la sync, §2.3),
   `90_end` forward (§2.2), ritocco in place di `20260205-41`, blocco in
   `provision_db_roles.sql`, pgTAP + gemello owner (§3), doc (§4);
2. numerazione **al momento di scrivere** (NN globale per data: il numero
   «libero» scade subito);
3. apply e pgTAP: Tid; poi la CI (baseline CI: nessun file nuovo atteso in
   rosso — il presidio nasce verde su un DB da zero, dove la provision-post
   gira dopo `ci_apply` e lo script è l'ultima parola).

## 8. Il giro del 2026-09-26

### 8.1 Cosa è scritto

| File | Cosa |
| --- | --- |
| `20_code/dbops/20260926-11-update-fn-sync-functions-owner-riservata-al-migratore` | il giro della copia di servizio (§2.3) con la guardia in testa al corpo; `search_path` identico; `COMMENT` riscritto (chi passa, il limite di `session_user`, `EXECUTE` PUBLIC che resta). ⭐ In più rispetto al `20260912-41`: dopo il passo 3 un controllo che il **prestito sia riuscito** (la sync non solleva mai, degrada a `WARNING`) — altrimenti il fallimento si vedrebbe solo più in là come un generico «bisogna essere proprietari». La guardia è **fail-closed**: `COALESCE(…, false)`, una risposta `NULL` rifiuta |
| `90_end/20260926-12-revoke-app-scrittura-sec-functions-owner` | il forward su dev, sul modello del `20260925-62` |
| `90_end/ci_apply/20260205-41` (in place) | `'dbops.sec_functions_owner'` in `v_tabelle_sola_lettura_app`, commento della lista allargato, blocco di testata «IL REGISTRO DEGLI OWNER» (e perché la sync **non** è in `v_fn_riservate`) |
| `scripts/sql/provision_db_roles.sql` | blocco «IL REGISTRO DEGLI OWNER» in coda alla postura dichiarata |
| `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql` | come app, plan 13 (§3) |
| `db/pgtap/dbops/test-sec-functions-owner-migratore-passa-v1.sql` | come owner (`pgtap-runner: owner`, motivo scritto), plan 2 |
| doc | `manual/fn_sync_functions_owner.md` (§«Riservata al migratore»), `manual/sec_functions_owner.md` (§«Chi la scrive»), linee-guida-sql §11.8, `migliorie-generali` D6 (`[~]`, stato 🟡) |

Numeri: `-11`/`-12` presi dopo i `20260926-01…10` già nel repo.

### 8.2 Cosa è provato, e come

⛔ **In questa sessione il database non era raggiungibile**: la lettura delle
credenziali (`~/.pgpass`, parametri di connessione) è stata bloccata dal
classificatore dei permessi. Quindi **niente prova su dbdev né su `zeroerp_ci`**,
e i fatti del §1 (ACL della sync, privilegi dell'app sul registro) **non sono
stati riletti**: restano fatti del 19-09.

La prova è stata fatta su un **cluster PostgreSQL 18 usa-e-getta** nello
scratchpad (`initdb`, solo loopback, distrutto a fine corsa), con tre ruoli
**veri** di login: `postgres` superuser, `titodb` migratore non superuser e
proprietario degli schemi, `zeroerp_app`. Fixture: il registro con la DDL di
`20251123-01`, una funzione sensibile di prova, la sync **vecchia estratta dallo
YAML `20260912-41`** (= il corpo vivo della doc auto-gen), portata a `postgres`
come fa la provision-post, e la postura di oggi dell'app (SIUD sul registro,
`zeroerp_app=X/postgres` sulla sync). L'SQL dei due changeSet è quello
**reso da `updateSQL` offline**, non riscritto.

| Passo | Esito |
| --- | --- |
| A. pgTAP come app **prima** del giro | 9 rossi su 13 (1-3, 5-7, 9, 10, 12): il file vede il difetto |
| B. `20260926-11` come `titodb`, in una transazione | exit 0; i quattro `NOTICE` del giro nell'ordine giusto (copia → postgres, originale → titodb, originale → postgres, copia → titodb) |
| C. dopo | sync di `postgres`, `proconfig` invariato (`search_path=pg_catalog, public, pg_temp`), ACL invariata, guardia nel `prosrc`, `COMMENT` nuovo, `_boot` sparita, zero righe temporanee |
| B2. `20260926-12` come `titodb` | exit 0; registro `{titodb=arwdDxtm/titodb, zeroerp_app=r/titodb}` |
| D. il loop `20260205-41` estratto, come `titodb` | l'ACL del registro resta `zeroerp_app=r` |
| E. pgTAP come app **dopo** | 13/13 |
| F. gemello come `titodb` e come `postgres` | 2/2 e 2/2 |
| G. limite dichiarato: `titodb` con `SET ROLE zeroerp_app` | **passa** (`current_user=zeroerp_app`, `session_user=titodb`): il limite è reale, ed è quello scritto |
| H. l'app chiama la sync | `ERROR: …riservata a chi possiede lo schema dbops (il migratore) o a un superuser; sessione zeroerp_app.` + HINT |
| I. mutazione: guardia riscritta su `current_user` (la trappola 1) | il pgTAP torna rosso su 9, 10, 12 — il presidio vede la trappola |
| «Da zero» (CI): sync ancora del migratore | exit 0; ogni passaggio di owner è un `WARNING`, la guardia entra, sync del migratore — la provision-post la porta a `postgres` dopo |

Guardrail di CI eseguiti, tutti verdi: `run_on_change`, `precondition_seed`,
`ddl_su_trigger_automazione`, `grant_ruolo_batch`, `sql_letterali`,
`timestamp_senza_fuso`, `pgtap_preambolo` (debito `throws_ok` senza
discriminante invariato a 117: i nuovi hanno `42501`).

⚠️ **Cosa il cluster usa-e-getta NON prova**: il registro vero (cinque righe,
funzioni vere), i proprietari veri di dbdev, `plpgsql_check` e i presidi
trasversali (riferimenti morti, `test-security-definer-search-path-v1`), e il
blocco del provisioning (non eseguito: stessa forma dei blocchi accanto).

### 8.3 Cosa restava a Tid — ✅ fatto il 2026-09-26

✅ Tid: *«migrazione eseguita, test verdi, nessuna regressione»*. I tre punti
qui sotto sono chiusi; il brief va in `work-done/`.

1. **apply** su dbdev (`20260926-11`, `-12`) e, a parte, su `zeroerp_ci`;
2. **pgTAP**: i due file nuovi, più `dbops/test-security-definer-search-path-v1`
   (test 3: la forma del pin) e `dbops/test-riferimenti-morti-v1` (la sync è
   riscritta); ⚠️ il gemello da owner è verde solo se il runner owner di quella
   macchina è il migratore — il suo test 1 lo dice;
3. poi `migliorie-generali` D6 da `[~]` a `[x]`, e il brief in `work-done/`.

*Scritto il 2026-09-19. Fatti dal vivo letti come `titodb` su dbdev, sola
lettura. Giro del 2026-09-26 (§8): changeSet, pgTAP e doc; prova su cluster
usa-e-getta, database del progetto non raggiungibile dalla sessione.*
