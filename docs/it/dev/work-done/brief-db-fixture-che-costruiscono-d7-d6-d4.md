# Brief DB — Le fixture costruiscono il mondo (D7), il pin delle DEFINER (D6), shop.ricevute (D4)

> **Da leggere per primo: §6 — cosa resta**, che al 19-09 è **una voce sola**,
> e ha un brief suo.
> Origine: [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md),
> decisione di Tid del 2026-09-12: *«fai 1 e 2, poi D4»*.
>
> ✅ **CHIUSO e archiviato il 2026-09-19.** Applicato e committato da Tid il
> 12-09 (`35cadf9bb`): changeSet 38-43, i 21 pgTAP riscritti, baseline di
> sviluppo senza regressioni, doc auto-gen rigenerate. **La CI ha detto la
> sua** (§6.2): i 21 file di §1.1 sono usciti da `baseline-rossi-ci.tsv`
> (commit `f8c1c2707`, `47f9712c2`, `8454f7cbd`) e
> `test-role-batch-fatturazione-postura` non è in nessuna delle due baseline.
> ✅ D13 (§4) chiuso il 13-09 nel suo brief
> (`work-done/brief-db-ba-riserva-emittente-operatore-d13.md`, verificato
> contro CI il 14-09). 🔵 **Il pezzo nuovo di D6** (§3, §6.4) è l'unico
> lavoro vivo e dal 19-09 sta in
> [brief-db-registro-owner-e-sync-riservati-al-migratore.md](../work-in-progress/brief-db-registro-owner-e-sync-riservati-al-migratore.md),
> con due fatti in più letti dal vivo che cambiano la forma (l'`EXECUTE`
> esplicito dell'app sulla sync; `session_user`, non `current_user`).
> 🔴 §3: due stesure dei pin erano sbagliate di sede, corrette dopo due apply
> falliti.

---

## 1. Il perimetro non era collaudato dove serve (D7, dentro D7)

Nel registro dei rossi della CI (`db/pgtap/baseline-rossi-ci.tsv`) stavano
**21 file** del perimetro emittente: 12 in `script/` (tutte le `fn_scope_*`,
il fail-closed, l'impersonazione, la ricerca universale) e 9 in `rls/`. Causa
unica, verificata file per file sullo scratch: la fixture **cercava** i soggetti
fra i dati esistenti (`… FROM anagrafiche.emittenti_fiscali ORDER BY id LIMIT 1`,
«un operatore con whitelist», «un cliente libero», «una fattura del mio
emittente»), e su un database ricostruito dai changelog `anagrafiche` è a zero.
Il file moriva nel fixture (copertura **zero**) oppure — peggio — rispondeva
`true` nei rami `skip se no fixture` (verde per sottrazione: la parity a sei
asserzioni, nessuna eseguita).

⇒ Dopo D2 e D3 «production-ready» era tornato difendibile, ma la prova girava
su una macchina sola.

### 1.1 Cosa si è fatto — 20 file riscritti nella fixture, 1 nuovo

Regola applicata ovunque: **il mondo si costruisce, prima del contesto** —
`dbops.fn_pgtap_crea_emittente_operatore()` per le aziende (una per «lato»),
`fn_pgtap_crea_cliente_ba` per i clienti, `fn_pgtap_crea_soggetto_pg` +
`fn_pgtap_crea_soggetto_ruolo` dove basta un ruolo, un binding al profilo
`SUPER_ADMIN` per i super admin, `fn_pgtap_crea_roster_processo` per le identità
tecniche. **Tutti i rami `skip` tolti**: la precondizione ora c'è sempre.

| File | Runner | Note |
| --- | --- | --- |
| `script/test-scope-emittenti-fail-closed-v1` | owner (era app) | tre aziende + BA legato all'operatore da spogliare; test 0 ora prova che PRIMA lo vede |
| `script/test-fn-scope-ef-whitelist` | app | riapre i vincoli DEFERRED dopo l'helper (file `pgtap-differiti`) |
| `script/test-fn-get-user-emittenti-scope` | app | **due** super admin costruiti: senza il secondo il caso «multi» non esiste |
| `script/test-fn-change-user-emittenti-scope` | app | |
| `script/test-emittente-attivo-impersonazione-scope` | app | |
| `script/test-fn-get-emittenti-scope-pk-ids-and-parity` | app | era «verde» con 6 skip: ora le 6 asserzioni girano |
| `script/test-fn-scope-ba-ownership` | owner (era app) | due clienti costruiti |
| `script/test-fn-scope-cliente-ownership` | app | tre SR CL, niente BA |
| `script/test-fn-scope-fornitore-ownership` | app | due FO + un CL |
| `script/test-permessi-fn-check-emittente-scope` | app | un secondo SA perché il DELETE del binding non sia l'ultimo |
| `script/test-search-scope-interno-v1` | owner (era app) | cliente con riga in `anagrafiche.clienti` (la ricerca CL passa da lì) e utility BASE (niente PDP) |
| `script/test-fn-scope-identita-processo` | owner | roster costruito per `send_pending_emails` e `chiusura_scadenze_daily` |
| `rls/test-fn-scope-ba-ownership-ruolo-aware` | owner (era app) | |
| `rls/test-rls-email-log-ambito` | app | |
| `rls/test-rls-event-log-ef-whitelist-write` | owner + FORCE (era app) | commessa costruita |
| `rls/test-rls-listini-ef-whitelist-write` | app | listino proprio costruito per il test 6 |
| `rls/test-rls-fatture-stampa-coda` | owner + FORCE dopo i test di struttura (era app) | fattura costruita |
| `rls/test-rls-fatture-stampa-coda-write-guard` | owner + FORCE (era app) | due fatture costruite |
| `rls/test-rls-fondi-fattura-source-functional` | owner | `_refs` dalle aziende costruite |
| `rls/test-rls-pagamenti-perimetro` | app | banca + filiale costruite, cliente **nel contesto** (→ §2), fattura scritta da A |
| `dbops/test-security-definer-search-path-v1` | app, nuovo | §3 |

Il ventunesimo, `rls/test-role-batch-fatturazione-postura`, è un'altra classe: §1.3.

**Esito** (psql, file per file, `BEGIN … ROLLBACK`, come `zeroerp_app` o owner
secondo il marcatore): **20/20 verdi su dbdev E su `zeroerp_ci`**, con la sola
eccezione di `test-rls-pagamenti-perimetro` su dbdev, che aspetta il changeSet
`20260912-38` (§2) — sullo scratch è 18/18.

### 1.2 Perché sette file sono passati a `pgtap-runner: owner`

Non per far passare un permesso: perché **come `zeroerp_app` un billing account
non si crea** se l'emittente di chi agisce non è quello di default (§4). I file
che devono costruire un cliente o una fattura seguono la pratica dei sei
`*-satelliti.sql`: mondo costruito da owner prima del contesto, BA legato con il
terzo parametro, e dove la policy è il soggetto `FORCE ROW LEVEL SECURITY`
locale alla transazione — acceso **dopo** i test di struttura, così un test
come «RLS attiva e senza FORCE» continua a misurare la postura di esercizio.
Ogni marcatore porta la ragione scritta.

`test-rls-pagamenti-perimetro` **non può** usare il FORCE (il predicato è una
DEFINER che con il FORCE rientrerebbe sotto la propria policy: ricorsione) e
resta `app`: è il motivo del §2.

### 1.3 `test-role-batch-fatturazione-postura`: non era una fixture

Tests 8, 12-15, 17, 19 rossi in CI perché in `ci-validate.yaml` **il ruolo batch
non veniva provisionato affatto** — lo fa `ci.yaml`, che però non lancia la
suite — e sullo scratch di `scripts/ci-local.sh` riceve *apposta* il DML su tutto
(dichiarato nello script: «questo database serve a trovare i changeSet che
rompono un migrate, NON a collaudare la postura»). Il file misurava il nulla o
il contrario di ciò che voleva.

⇒ Aggiunto a `.github/workflows/ci-validate.yaml` il passo **«Provision ruolo
batch fatturazione»**, copia di quello di `ci.yaml`, subito dopo
`provision_db_roles`. In CI il ruolo avrà il perimetro vero e il file misurerà
quello. ⚠️ Non provabile qui: lo dirà la prima corsa, e potrebbe cambiare lo
stato anche di altri file che guardano i ruoli batch (`fn_grant_storico_shadows`,
`test-registri-append-only-postura`).

---

## 2. L'helper `fn_pgtap_crea_cliente_ba` usabile come `zeroerp_app` — `20260912-38`

`20_code/dbops/20260912-38-update-fn-pgtap-crea-cliente-ba-senza-returning`:

1. l'`INSERT` del BA non fa più `RETURNING`: la riga si rilegge dal `codice`
   (UNIQUE) a istruzione finita, quando il trigger `z90` l'ha già legata
   all'emittente di chi agisce;
2. il terzo parametro **rispetta** un legame già scritto dal trigger e **solleva**
   se non coincide con quello chiesto (un BA legato per silenzio a un'altra
   azienda è la fixture sbagliata contro cui il parametro esiste);
3. firma e `RETURNS TABLE` riscritte con `%TYPE` (la doc auto-gen li scioglie —
   corretto su richiesta di Tid).

**Provato** su dbdev e scratch con la definizione iniettata in transazione e la
RLS simulata con `FORCE`: (0) la funzione VIVA con contesto di un emittente non
di default muore su dbdev — è il §4; (2) nuova, contesto A, senza parametro →
BA legato ad A, visibile; (3) parametro = A → ok; (4) parametro = B → solleva
con il messaggio; (5) da owner senza contesto con parametro → legame come
prima. I sei `*-satelliti.sql` (owner, costruiscono prima del contesto) non
cambiano di una riga.

---

## 3. D6 — il pin del `search_path` sulle tre DEFINER di `postgres`

`20260912-39/40/41` (`20_code/dbops/`): `dbops.fn_generate_tx_id`,
`fn_get_or_create_session_tx_id`, `fn_sync_functions_owner` ricreate **con**
`SET search_path TO 'pg_catalog', 'public', 'pg_temp'` nella definizione (non
`ALTER FUNCTION`: un `CREATE OR REPLACE` successivo azzererebbe un pin fatto
con l'ALTER), `%TYPE` in firma, RETURNS e DECLARE, corpo byte per byte dalla doc
auto-gen. `public` **deve** esserci: la catena tocca `dblink`, che vive lì, e il
path di una DEFINER vale per tutto ciò che chiama. `pg_temp` ultimo ed esplicito.

🔴 **Due stesure sbagliate (sera del 12-09), corrette.** Avevo messo tutte e
tre in `changelog-provision-post.yaml` con `context: provision`, e i primi
due apply di Tid sono morti su «bisogna essere proprietari della funzione».
⭐ La lezione è più larga del precedente `20260722-10`: **in sviluppo si migra
con `../scripts/liquibase5.sh update` da `db/`, cioè `liquibase.properties`
(`titodb`) e NESSUN contesto** — `context: provision` non salta niente, e
chiede solo un'utenza che quel comando non ha. Un changeSet deve poter
girare **da `titodb`**, sempre; il makefile con `!provision` non è il flusso
di Tid.

- **39 e 40 — prestito di proprietà, timeline normale** (precedente
  `20260722-10`): nel changeSet si dichiara in `dbops.sec_functions_owner` che
  l'owner richiesto è `current_user`, `fn_sync_functions_owner()` (DEFINER di
  postgres) passa la funzione al migratore, `CREATE OR REPLACE`, poi il registro
  torna a `postgres` e si risincronizza. Una transazione sola; nessuna
  preCondition sulla riga del registro (è un seed di `80_data`). **Provati con
  l'SQL estratto come `titodb` su dbdev e come `zeroerp` sullo scratch**:
  prestito e restituzione nei NOTICE, `proconfig` corretto, owner di nuovo
  `postgres`, e le due funzioni **eseguono** — compreso il percorso vero via
  `dblink`, che è la prova che `public` nel pin serve e basta.
- **41 — la copia di servizio, timeline normale.** La sync non può prestarsi a
  sé stessa: una volta del migratore non è più DEFINER di postgres e la
  restituzione fallirebbe. Ma il registro fa cambiare owner a *qualunque*
  funzione da un DEFINER di postgres, e ne basta uno vivo per volta: (1) si
  crea `fn_sync_functions_owner_boot`, copia della definizione **viva**
  (`pg_get_functiondef`, nessun corpo duplicato); (2) la sync viva la dà a
  postgres (riga temporanea nel registro); (3) la **copia** presta l'originale
  al migratore; (4) `CREATE OR REPLACE` con il pin; (5) la copia restituisce
  l'originale a postgres; (6) l'originale — di nuovo postgres, e pinnato —
  riprende la copia al migratore, che la droppa; via le righe temporanee. Una
  transazione. Da zero (CI) ogni passaggio è un no-op con WARNING e la
  provision-post indurisce dopo. **Provato con l'SQL estratto come `titodb` su
  dbdev e come `zeroerp` sullo scratch** (la sync è di `postgres` in entrambi):
  quattro NOTICE di passaggio, owner finale `postgres`, `proconfig` pinnato,
  copia sparita, registro come prima, e la sync pinnata esegue.
  🔴 **Il giro dice una cosa sul prodotto**: chi può scrivere il registro ed
  eseguire la sync può rendersi proprietario delle sei funzioni indurite —
  e `zeroerp_app` **può** (INSERT/UPDATE su `sec_functions_owner`, `=X` a
  PUBLIC sulla sync). Non arriva al superuser (nessun CREATE su schemi,
  funzioni non risolte da `pg_temp`), ma spegne il canale di log e può
  mettere un `SET` su una DEFINER che poi torna a postgres. È la faccia
  concreta del punto sotto.

**Presidio**: `db/pgtap/dbops/test-security-definer-search-path-v1.sql` — il
terzo criterio di D5 come **invariante generale sul catalogo** (nessuna DEFINER
del progetto senza `search_path`, estensioni escluse per `pg_depend`), la forma
esatta sulle tre, e **due rubinetti** per D6-bis (18 senza `pg_temp`, 5 con
`public` prima di `pg_catalog`: possono solo calare). Oggi è rosso sui test 1 e 3
con i tre nomi in diagnostica: diventa verde con l'apply.

**EXECUTE a PUBLIC su `fn_sync_functions_owner` — valutato, NON fatto, e ora
con un motivo in più per farlo.** La chiamano la provision-post, il runAlways
`20251123-04` e i changeSet «a prestito» (39/-40/-41 e i precedenti), sempre
come migratore — che in CI è `zeroerp` e ha l'EXECUTE **solo via PUBLIC**.
Ritirarlo vuol dire: `v_fn_riservate` nel loop dei grant (`20260205-41`), il
`REVOKE` nel provisioning, il pgTAP che tiene le tre sedi allineate, **e** un
`GRANT` esplicito al migratore o la CI muore. E va nello stesso cantiere il
**registro**: `dbops.sec_functions_owner` è scrivibile da `zeroerp_app`
(INSERT/UPDATE dal loop dei grant), e registro + sync sono la leva con cui
il 41 si è fatto (§3). Chi la tiene decide chi possiede le DEFINER di
postgres: deve essere solo il migratore. È un cantiere suo, non una riga —
**ma è il prossimo di D6**.

---

## 4. 🔴 Trovato strada facendo — un difetto di PRODOTTO multi-emittente

**Come `zeroerp_app`, l'operatore di un emittente che NON è quello di default
non riesce a creare un billing account.** `INSERT INTO anagrafiche.billing_account
… RETURNING id` muore con «la nuova riga viola la regola di sicurezza per riga»:
la policy di lettura (`rls_billing_account_ef_whitelist`) risolve il BA da
`emittenti_fiscali_billing_account`, il legame lo scrive il trigger **AFTER**
`z90_link_ef`, cioè *dopo* che il `RETURNING` ha chiesto di vedere la riga, e nel
frattempo `fn_get_ba_emittente_sr_id` ricade sul **default** — un'altra azienda.

- **Riprodotto il 2026-09-12 su dbdev** con un operatore vero dell'emittente
  44 (`EMITEST`, non default): `auth_user 8`, un `fn_pgtap_crea_cliente_ba`
  nel suo contesto → 42501. Sull'emittente di default passa; sullo scratch
  passa perché il primo emittente creato è il default.
- **Il backend fa la stessa cosa**:
  `backend/apps/anagrafiche/db/clienti_repository.py` `create_billing_account`
  → `RETURNING id`. ⇒ Con due emittenti in esercizio, gli operatori del secondo
  non possono aprire clienti.
- Non è un difetto della fixture e **non l'ho toccato**: il §2 toglie l'ostacolo
  dall'helper, non dal prodotto. Le tre risposte alla domanda «un BA appena
  scritto, ancora senza collegamento, di chi è?»:
  1. **di chi lo sta creando** — `script.fn_get_ba_emittente_sr_id` ricade
     sull'emittente dell'operatore in sessione invece che sul default (è ciò
     che il trigger z90 sta per scrivere); default solo senza sessione;
  2. il BE scrive e rilegge dopo, senza `RETURNING` — non cambia il DB, ma la
     trappola resta per ogni altro scrittore (import, shop, cantieri futuri);
  3. l'emittente diventa **colonna** del BA, scritta all'INSERT — la forma più
     solida (e coerente con «un BA ha esattamente un emittente»), ma un cambio
     di modello: la tabella dei legami diventa derivata; giorni, non ore.

  ✅ **Decisione di Tid, 2026-09-12: la 1**, subito; la 3 resta in coda come
  decisione di modello, non come lavoro. **Nessuna bonifica dei dati**: sono
  dati di test — e comunque sulla macchina i 42 BA sono tutti collegati, la
  riserva serve solo a quell'istante. Il cantiere: un changeSet sul resolver
  (corpo dalla doc auto-gen), il pgTAP che costruisce l'operatore del secondo
  emittente e inserisce un BA **con** `RETURNING` come `zeroerp_app`
  (`throws_ok` oggi, `lives_ok` domani), e il gemello che prova che senza
  sessione la riserva è ancora il default. Brief suo quando si apre.

---

## 5. D4 — `shop.ricevute` armata: `20260912-42` + `-43`

- `00_schema/shop/20260912-42-enable-rls-shop-ricevute`: `ENABLE ROW LEVEL
  SECURITY` (NO FORCE, come la famiglia). Letto dalla struttura il 12-09:
  `zeroerp_app`, `zeroerp_batch_fatturazione` e `zeroerp` **non hanno nessun
  privilegio** sulla tabella (`has_table_privilege`), l'unico scrittore è
  l'owner; nel backend nessun lettore. Nessun percorso cambia.
- `80_data/changelog/20260912-43-delete-debito-rls-shop-ricevute`: `DELETE`
  delle righe **75** e **92** del registro (`loadUpdateData` non cancella) +
  righe tolte da `80_data/sql/dbops/rls_perimetro_debito.csv` (10 → 8).
  ⚠️ Numero datato al 12-09: al 19-09 il CSV ha **7** righe — un cantiere
  successivo ne ha estinta un'altra. Il registro si legge dal CSV, non da qui.
- `acquisti.ddt` / `acquisti.ordini` **restano a registro**: policy di sola
  veste `FORNITORE_PORTALE` e nessuna colonna emittente — è D8, non D4.

**Provato** su dbdev e scratch: SQL estratto in `BEGIN … ROLLBACK` → RLS accesa,
registro a 8, `vw_rls_perimetro_scoperto` con soli `DEBITO_DICHIARATO=8`
(nessun `NON_DICHIARATO`, nessun `DEBITO_ESTINTO`); e
`rls/test-rls-perimetro-scoperto.sql` con i due changeSet iniettati: **8/8**.

---

## 6. Cosa resta

1. ✅ **Apply e pgTAP — fatti da Tid il 12-09**: changeSet 38-43 applicati con
   `../scripts/liquibase5.sh update`, baseline di sviluppo senza regressioni,
   doc auto-gen rigenerate, commit `35cadf9bb`.
2. ✅ **CI — fatto, verificato il 19-09** (fino a quel giorno questa riga lo
   dava aperto: era già chiuso e nessuno l'aveva scritto). I 21 file di §1.1
   sono usciti da `baseline-rossi-ci.tsv` in tre commit (`f8c1c2707`,
   `47f9712c2`, `8454f7cbd`), e non «a mano»: dal 14-09 i rientrati li toglie
   `scripts/pgtap-baseline-ci-rientrati.sh` leggendo il log della corsa.
   `test-role-batch-fatturazione-postura` (§1.3) non è in nessuna delle due
   baseline: il passo «Provision ruolo batch fatturazione» in
   `ci-validate.yaml` ha fatto quello che doveva.
3. **D13** (§4): ✅ deciso — opzione 1, nessuna bonifica dati — e ✅ **chiuso
   il 13-09** nel brief suo, `brief-db-ba-riserva-emittente-operatore-d13.md`:
   tre changeSet (`20260913-01/02/03`) applicati, baseline senza regressioni.
   ⚠️ Il §4 qui sotto diceva «un changeSet sul resolver»: sono diventati tre,
   perché leggendo i chiamanti è emersa una seconda copia della regola
   (`fn_get_emittente_fiscale_pk`) e il `PARALLEL SAFE` andava tolto anche
   alla chiamante — il perché sta nel brief, §4.
4. 🔵 **Il pezzo nuovo di D6** (§3) — dal 19-09 ha un brief suo:
   [brief-db-registro-owner-e-sync-riservati-al-migratore.md](../work-in-progress/brief-db-registro-owner-e-sync-riservati-al-migratore.md).
   ⚠️ Le righe qui sotto sono la forma pensata il 12-09 e **due punti sono
   superati** da lì: `pg_has_role(current_user, …)` non funziona dentro una
   DEFINER (`current_user` è il proprietario — si usa `session_user`), e la
   «lista nuova sola lettura» esiste già (`v_tabelle_sola_lettura_app`, nata
   il 18-09 per il ledger). Restano qui come storia della decisione.
   Registro `dbops.sec_functions_owner` e `fn_sync_functions_owner` riservati
   al migratore. Stima ≈ **mezza giornata**, con la forma già decisa dal
   vincolo tecnico:
   - ⛔ **non** con GRANT/REVOKE sulla sync: la funzione è di `postgres`, e un
     privilegio dato al migratore mentre la possiede in prestito **non
     sopravvive** alla restituzione (`ALTER … OWNER` rimappa le voci ACL del
     vecchio proprietario sul nuovo). ⇒ la sync si difende **da sola**: in
     testa, `IF NOT (pg_has_role(current_user, nspowner di dbops, 'MEMBER')
     OR superuser) THEN RAISE insufficient_privilege` — sostituita con la
     copia di servizio, come il 41. Il migratore possiede `dbops` in ogni
     ambiente (`titodb` / `zeroerp`), `postgres` passa, `zeroerp_app` no;
   - il registro: REVOKE INSERT/UPDATE/DELETE all'app nelle **tre sedi** del
     pattern già usato per `audit_log` l'11-09 — l'elenco nel loop dei grant
     (`20260205-41`, una lista nuova «sola lettura», accanto a
     `v_registri_append_only`), il `REVOKE` in `provision_db_roles.sql`, e
     `test-registri-append-only-postura-v1.sql` che tiene le sedi allineate —
     più un `90_end` forward per applicare subito su dev;
   - pgTAP nuovo, come `zeroerp_app`: `throws_ok(SELECT dbops.fn_sync_functions_owner(), '42501')`
     e `throws_ok` sull'INSERT/UPDATE del registro; e il gemello «il migratore
     e la provision-post passano ancora» (il runAlways `20251123-04` la chiama
     a ogni update).

*Scritto il 2026-09-12. Nessun test eseguito col runner ufficiale; ogni prova è
un `psql -f` in transazione ritirata, un file alla volta.*
