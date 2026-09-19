# Brief DB — Il registro degli owner e la sync riservati al migratore (D6, il pezzo che resta)

> **Da leggere per primo: §2 — la forma, e le due trappole che la cambiano.**
> Origine: [brief-db-fixture-che-costruiscono-d7-d6-d4.md](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md)
> §3 e §6.4 (chiuso e archiviato il 2026-09-19), a sua volta figlio di
> [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md) §D6.
> Stima scritta lì: **≈ mezza giornata**. ⚠️ D6-bis (la forma canonica del
> `search_path` sulle 38 DEFINER) **non** è qui: resta in `migliorie-generali`.
>
> 🔵 **Stato 2026-09-19: brief scritto, nessun changeSet.** Decisioni aperte
> per Tid in §6 (tre, con la raccomandazione scritta accanto).

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

## 6. Decisioni aperte per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D-1** | Il rifiuto della sync: `42501` nudo (deroga a «errori via `fn_log_and_raise_error`») o un codice a catalogo di classe `NON_PERMESSO`? | **`42501`** — §2.1 trappola 2: stessa forma della postura gemella, e il canale di log è fra le funzioni protette. Un codice a catalogo servirebbe a un operatore che non esiste |
| **D-2** | `SELECT` sul registro all'app: resta o si toglie? | **resta** — §2.2: nessuna leva senza scrittura+sync, e la lista «sola lettura» esiste già; togliere = quarta forma in tre sedi |
| **D-3** | La sync in `v_fn_riservate` (REVOKE EXECUTE da PUBLIC/app nelle tre sedi) **in aggiunta** alla guardia? | **no** — §2.1 punto 2: doppia sede per la stessa regola, e in CI serve un GRANT esplicito al migratore che oggi non c'è. Se un giorno si farà, il presidio (test 8) va girato da `true` a `false` |

## 7. Cosa resta

1. 🔵 D-1/D-2/D-3 decise da Tid → changeSet `20_code/dbops` (la sync, §2.3),
   `90_end` forward (§2.2), ritocco in place di `20260205-41`, blocco in
   `provision_db_roles.sql`, pgTAP + gemello owner (§3), doc (§4);
2. numerazione **al momento di scrivere** (NN globale per data: il numero
   «libero» scade subito);
3. apply e pgTAP: Tid; poi la CI (baseline CI: nessun file nuovo atteso in
   rosso — il presidio nasce verde su un DB da zero, dove la provision-post
   gira dopo `ci_apply` e lo script è l'ultima parola).

*Scritto il 2026-09-19. Fatti dal vivo letti come `titodb` su dbdev, sola
lettura.*
