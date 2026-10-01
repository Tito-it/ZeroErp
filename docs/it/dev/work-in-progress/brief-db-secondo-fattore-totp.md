# Brief DB — Secondo fattore (TOTP): obbligo, verbi del device, manuali

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-28. **A chi:** team DB (`dev/db-tid`);
> Tid per le decisioni di §7.
> **Origine:** §3.3 di [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md).
> Le decisioni di Tid già prese sono in quel brief (§6): l'obbligo del secondo fattore vale
> **per credenziale e per ruolo** (decisione 3), il backend usa **librerie esistenti** per TOTP
> e QR (decisione 4).
> **Stato:** ✅ **Lato DB CHIUSO il 2026-09-29**: `20260929-05 → -24` applicati da Tid alle
> 19:30, `-25`/`-26` (D-T5) alle 23:19; **pgTAP verdi col runner** (Tid). Verificato dopo
> l'apply: il 9100 ha il segno dal CSV, la porta è chiusa, la sync chiede al BB ed è di
> `postgres`, il `CHECK` di `sessioni_utente` ammette `TOTP_DISABILITATO`; doc auto-gen
> rigenerata. ✅ D-T1 → D-T3 decise da Tid il 2026-09-28 (§7); ✅ D-T4 e D-T5 il 2026-09-29.
> ⏳ **Resta il BE/FE** (`dev/backend-tid`): le richieste di §9.5. Il brief si archivia quando
> il backend le ha chiuse.
>
> **In una riga:** oggi `config.auth_totp_device` esiste ma nessuno la usa, l'obbligo del
> secondo fattore non ha una sede, e i manuali descrivono un disegno mai costruito. Servono
> la sede dell'obbligo (credenziale + profilo), i verbi che scrivono il device sul modello
> di `config.credenziali`, e i manuali riscritti sullo stato vero.

---

## 1. Cosa c'è oggi — letto dalla struttura (doc auto-gen, 2026-09-28)

* **`config.auth_totp_device`**: 1:1 con `auth_user` (`uq_auth_totp_device_auth_user`),
  `secret_encrypted`, `abilitato`, `confermato`, `recovery_codes_hash jsonb`,
  `ultimo_codice_usato varchar`, `ultimo_uso_at`, `meta`. Solo i trigger di audit: nessun
  guard, nessuna funzione che la scriva. Nessun riferimento in `backend/apps`.
* **`config.credenziali`**: tiene tentativi, blocco e cambio password obbligato. Letta e
  scritta solo dalle funzioni di `script`, all'app solo `SELECT`, niente RLS (si legge prima
  del login). La riga assente vale «nessun obbligo». Il vecchio `totp_obbligatorio` è uscito
  da `identita_digitali` con `20260925-25` (D-10), ma **non è arrivato** sulla credenziale.
* **Super admin**: binding attivo verso un profilo di tipo `SUPER_ADMIN`
  (`script.fn_is_super_admin`, `fn_guard_super_admin`). I profili si risolvono con
  `script.fn_get_profili_accesso_applicabili` (AD_HOC → REPARTO → PORTALE).
* **Cifratura**: il segreto lo cifra il backend (`crypto_service`, `MultiFernet` su
  `DJANGO_FIELD_ENCRYPTION_KEYS`, dal 2026-09-28). Il DB non vede mai il segreto in chiaro e
  non può verificare un codice: **la verifica del codice è del backend**, il DB custodisce
  lo stato e fa rispettare le regole (monouso, anti-replay, chi può cosa).

---

## 2. L'obbligo del secondo fattore

**Decisione di Tid (2026-09-28): entrambi.** Obbligo effettivo = **flag sulla credenziale
OPPURE account privilegiato.**

### 2.1 Sulla credenziale

* `config.credenziali.totp_obbligatorio boolean NOT NULL DEFAULT false`. La riga assente vale
  `false`, come le altre colonne.
* Verbo `script.fn_imposta_totp_obbligatorio(p_auth_user_id integer, p_valore boolean)`, sul
  modello di `fn_imposta_deve_cambiare_password`; chi agisce dev'essere `SUPER_ADMIN`
  (`fn_guard_super_admin`, come `fn_blocca_credenziale`).

### 2.2 Per l'account privilegiato

✅ D-T1 (Tid, 2026-09-28): **un segno dichiarato sul profilo**, non una lista di aree scritta in
una funzione.

* `config.profili_accesso.richiede_secondo_fattore boolean NOT NULL DEFAULT false`;
* un `CHECK`: `tipo <> 'SUPER_ADMIN' OR richiede_secondo_fattore` — il super admin l'ha
  **sempre**, non si può spegnere;
* chi amministra i profili lo accende sugli altri profili che considera privilegiati (per
  esempio quello di chi gestisce utenti e permessi). L'obbligo **segue i binding**: chi riceve
  il profilo ha l'obbligo, chi lo perde non l'ha più, senza flag da ricordare;
* la scrittura del campo segue la strada di scrittura di `profili_accesso` di oggi.

### 2.3 Una funzione sola che risponde

`script.fn_totp_obbligatorio(p_auth_user_id integer)` → `(obbligatorio boolean, motivo text)`,
`motivo` ∈ `CREDENZIALE` / `PROFILO` / `NULL`. Legge la credenziale e i profili applicabili
**di tutte le vesti** (`p_ruolo_applicativo` NULL): la credenziale è una sola e vale per tutte
le porte, come il blocco. Il backend la chiama al login e nel middleware che obbliga al setup;
il `motivo` serve al frontend per spiegare perché.

---

## 3. I verbi del device

Stessa postura di `config.credenziali`: **all'app solo `SELECT`** su `auth_totp_device`, ogni
scrittura da una funzione di `script` (`SECURITY DEFINER`, `search_path` fissato), niente RLS.
Da verificare quali GRANT ha oggi `zeroerp_app` sulla tabella, e toglierli.

«Chi agisce» si legge da `app.current_user_id`, come in `fn_blocca_credenziale`.

| Verbo | Chi agisce | Cosa fa |
| --- | --- | --- |
| `fn_totp_registra_device(p_auth_user_id, p_secret_encrypted, p_recovery_codes_hash jsonb)` | l'utente stesso | crea il device **non confermato**; sostituisce un device non confermato che ci fosse già; su un device attivo solleva (va prima disabilitato) |
| `fn_totp_conferma_device(p_auth_user_id, p_passo bigint)` | l'utente stesso | il backend ha verificato il primo codice: `confermato` e `abilitato` a `true`, registra il passo (§4) |
| `fn_totp_registra_uso(p_auth_user_id, p_passo bigint)` | nessuno (prima del login) | anti-replay (§4): accetta solo un passo **successivo** all'ultimo usato, poi lo registra con `ultimo_uso_at`. Device non attivo → solleva |
| `fn_totp_consuma_recovery(p_auth_user_id, p_codice_hash text)` → `integer` | nessuno (prima del login) | toglie l'hash dall'array se c'è e restituisce **quanti codici restano**; hash assente → solleva. Una sola istruzione, con la riga bloccata: due login con lo stesso codice, uno solo passa |
| `fn_totp_rigenera_recovery(p_auth_user_id, p_recovery_codes_hash jsonb)` | l'utente stesso | sostituisce l'array; il backend ha verificato prima un codice corrente |
| `fn_totp_disabilita_device(p_auth_user_id, p_motivo text)` | l'utente stesso **o** un `SUPER_ADMIN` | cancella il device (il segreto e i codici spariscono). Motivo obbligatorio quando agisce un altro. Chi ha l'obbligo viene riportato al setup dal middleware, al prossimo accesso |
| lettura: `fn_get_totp_device(p_auth_user_id)` | — | `attivo`, `secret_encrypted`, `ultimo_passo`, `recovery_rimasti`; conosce il significato della riga assente |

⚠️ **Il caso senza via d'uscita.** Se l'unico super admin perde il telefono e i codici di
recupero, nessuno può disabilitargli il device. `fn_totp_disabilita_device` deve quindi
funzionare anche **in contesto di sistema** (la GUC di `system_process_context`), così un
comando di gestione lanciato sul server lo sblocca. Il comando lo fa il backend.
> ⛔ **Superato il 2026-09-29 (D-T4, §9.2):** il gateway `system_process_context` non esiste
> più dal 2026-09-05 (`backend/apps/core/services/system_context.py`) e il backend ha una
> sola connessione, `zeroerp_app`. Lo sblocco lo fa la **sessione del migratore**, dal server.

⚠️ **I verbi senza chi agisce** (`fn_totp_registra_uso`, `fn_totp_consuma_recovery`) sono
come `fn_registra_tentativo_login`: si chiamano prima del login. Non danno niente a chi non
ha già superato la password: il backend li chiama solo dopo.

---

## 4. ⭐ Anti-replay sul **passo**, non sul codice

`ultimo_codice_usato varchar` confronta il **testo** del codice. Il TOTP non funziona così: un
codice vale per un **passo** di 30 secondi, e lo stesso numero di 6 cifre può tornare
legittimamente in un passo diverso. Quello che non deve succedere è **riusare lo stesso passo**,
o uno più vecchio (il backend accetta anche il passo precedente, per l'orologio del telefono).

Proposta, sul modello (RFC 6238 §5.2):

* `ultimo_codice_usato varchar` → **`ultimo_passo_usato bigint`** (il contatore
  `floor(unix_time / 30)` del codice accettato). Il sistema non è in produzione e la tabella non
  ha scrittori: si cambia senza migrazione di dati;
* `fn_totp_registra_uso` accetta solo `p_passo > ultimo_passo_usato`, con la riga bloccata:
  anche due richieste simultanee con lo stesso codice ne fanno passare una sola;
* un `CHECK` `ultimo_passo_usato >= 0`.

Questo rende **monouso** anche il token di sfida del login a due passi (lato backend): per
riusarlo serve comunque un codice di un passo non ancora usato.

---

## 5. Codici d'errore

Da registrare nel catalogo, con policy e frase (ripiego senza `%s`). Nomi proposti:

| Codice | Quando |
| --- | --- |
| `E_TOTP_DEVICE_GIA_ATTIVO` | `fn_totp_registra_device` su un device confermato |
| `E_TOTP_DEVICE_ASSENTE` | conferma, uso, recovery o disabilitazione senza device (o, per l'uso, non attivo) |
| `E_TOTP_PASSO_GIA_USATO` | `fn_totp_registra_uso` / `fn_totp_conferma_device` con un passo non successivo |
| `E_TOTP_RECOVERY_NON_VALIDO` | `fn_totp_consuma_recovery` con un hash che non c'è |
| `E_TOTP_CODICE_NON_VALIDO` | lo solleva il **backend** (la verifica del codice è sua): serve solo in catalogo |

Per il chiamante non valido si riusa `E_AUTH_CHIAMATA_NON_VALIDA`, per chi non è super admin
il codice di `fn_guard_super_admin`, per il motivo mancante il gemello di
`E_CREDENZIALE_MOTIVO_OBBLIGATORIO`.

---

## 6. I manuali da riscrivere

Una guida che descrive un disegno mai costruito va riscritta sullo stato vero:

* **`config/manual/auth_totp_device.md`**: descrive un `TotpService` che non esiste, il campo
  `totp_obbligatorio` su `risorse_umane_auth_user` che non esiste più, e un segreto cifrato con
  una «chiave derivata da `Django SECRET_KEY`» (dal 2026-09-28 è `DJANGO_FIELD_ENCRYPTION_KEYS`,
  vedi `sicurezza-e-qualita-statica.md` § «Le chiavi dei dati cifrati»). Da riscrivere col ciclo
  di vita sui verbi di §3 e l'anti-replay di §4;
* **`config/manual/credenziali.md`**: § «Storia» dice che `totp_obbligatorio` esce da
  `identita_digitali` verso la credenziale; con questo lavoro diventa vero, e va aggiunta la
  riga nella tabella «Cosa azzera cosa»: un codice TOTP sbagliato conta come un tentativo
  fallito della credenziale (§7, D-T2);
* il manuale di `profili_accesso` per il campo nuovo.

---

## 7. Decisioni per Tid

✅ **Tutte e tre decise da Tid il 2026-09-28: accettate le proposte.**

| # | Domanda | Decisione |
| --- | --- | --- |
| D-T1 | Come si riconosce un account privilegiato? | **Segno sul profilo** (`richiede_secondo_fattore`, sempre acceso sul `SUPER_ADMIN`). L'alternativa è una regola che deduce il privilegio da aree e livelli: ma quali capacità contano è una scelta di chi amministra, non un fatto del modello, e una lista di aree scritta in una funzione diventa vecchia alla prima area nuova |
| D-T2 | Un codice TOTP sbagliato conta come un tentativo fallito della credenziale? | **Sì**: stesso freno sulla provenienza e stessa attesa crescente della password (`fn_registra_tentativo_login`). Chi sbaglia il codice ha già la password: è proprio il caso da frenare. Sei cifre sono un milione di combinazioni |
| D-T3 | Dove resta traccia di un device disabilitato da un super admin (chi, quando, perché)? | Nell'audit degli eventi di autenticazione che il backend già scrive. La riga del device sparisce, e non deve restare un segreto per tenere uno storico |
| D-T4 | (2026-09-29, nata scrivendo) Chi sblocca il caso senza via d'uscita, visto che `system_process_context` non esiste più? | **La sessione del migratore**, dal server: `fn_totp_disabilita_device` ammette chi possiede lo schema `dbops` (o un superuser), con motivo. L'app non raggiunge quel ramo. Niente comando Django (§9.2) |
| D-T5 | (2026-09-29) Dove resta traccia dello sblocco dal server, dove il backend non c'è? | **Strada B**: il verbo scrive l'evento `TOTP_DISABILITATO` in `dbops.sessioni_utente`, solo in quel ramo (§9.6) |

---

## 8. Cosa fa il backend dopo (per sapere cosa serve)

Il login a due passi (password → sfida breve → codice → JWT), il setup con QR e codici di
recupero mostrati una volta sola, il middleware che porta al setup chi ha l'obbligo e non ha un
device attivo (sul modello di `PasswordChangeRequiredMiddleware`), il comando di gestione per
il caso senza via d'uscita (§3), `auth_totp_device.secret_encrypted` in `CAMPI_CIFRATI`.
Serve dal DB: §2, §3, §4, §5. I manuali (§6) possono seguire.

> ⚠️ **Il comando di gestione non serve più** (D-T4, §9.2): lo sblocco è della sessione del
> migratore. Le richieste al BE aggiornate sono in §9.5.

---

## 9. Consegna DB (`dev/db-tid`, 2026-09-29)

### 9.1 I changeSet — ✅ applicati il 2026-09-29 (19:30; `-25`/`-26` alle 23:19)

| # | Dove | Cosa |
| --- | --- | --- |
| `20260929-05` | `00_schema/config` | `credenziali.totp_obbligatorio` (§2.1) |
| `-06` | `00_schema/config` | `profili_accesso.richiede_secondo_fattore` (§2.2) |
| `-07` | `00_schema/config` | la forma del device: `ultimo_passo_usato bigint` al posto di `ultimo_codice_usato`, via `abilitato`, quattro `CHECK` (§4) |
| `-08` | `20_code/dbops` | ⭐ BB `dbops.fn_sessione_del_migratore()` (regola del 2) |
| `-09` | `20_code/dbops` | `fn_sync_functions_owner` chiede al BB: **ritirata la copia** nello stesso giro (giro della copia di servizio, come `20260926-11`) |
| `-10` | `20_code/script` | ⭐ BB `script.fn_is_super_admin_account(p)` (regola del 2) |
| `-11` | `20_code/script` | `fn_is_super_admin` chiede al BB: **ritirata la copia**, risultato invariato |
| `-12` | `20_code/script` | `fn_imposta_totp_obbligatorio` (SUPER_ADMIN, upsert) |
| `-13` | `20_code/script` | `fn_totp_obbligatorio` → `(obbligatorio, motivo)` (§2.3) |
| `-14` | `20_code/script` | guard `fn_guard_utente_stesso(p_utente, p_auth_user_id)` |
| `-15` | `20_code/script` | `fn_get_totp_device` → `(stato, secret_encrypted, ultimo_passo_usato, recovery_rimasti)` |
| `-16` | `20_code/script` | check `fn_check_totp_recovery_hash(jsonb)` |
| `-17 → -22` | `20_code/script` | i sei verbi del device (§3) |
| — | `80_data` (CSV) | 6 codici in `codici_errore.csv` + `messaggi_errore.csv` (1161-1166); `profili_accesso.csv` colonna nuova (9100 = `t`), tipizzata nei due mirror che caricano quel file (`20260418-43`, `20260806-18`) |
| `-23` | `90_end` | `CHECK` «il `SUPER_ADMIN` ha sempre il segno» |
| `-24` | `90_end` | la porta: all'app solo `SELECT` su `auth_totp_device`; stesse voci nel loop `ci_apply/20260205-41` e in `provision_db_roles.sql` (§11.8, tre sedi) |

Codici (§5): `E_TOTP_DEVICE_GIA_ATTIVO` e `E_TOTP_DEVICE_ASSENTE` (**CONFLITTO_STATO**: la
credenziale c'è, è il suo stato che non ammette l'operazione), `E_TOTP_PASSO_GIA_USATO`,
`E_TOTP_RECOVERY_NON_VALIDO`, `E_TOTP_CODICE_NON_VALIDO` (solo del backend),
`E_TOTP_MOTIVO_OBBLIGATORIO` (**DATO_ERRATO**). Frasi chiuse, senza segnaposto.

### 9.2 Dove la consegna si scosta dal brief, e perché

1. 🔴 **Il `SUPER_ADMIN` non è fra i profili applicabili.** `fn_get_profili_accesso_applicabili`
   risolve solo AD_HOC, REPARTO e PORTALE: il §2.3 contava su lei sola, e il super admin — il
   caso per cui l'obbligo esiste — sarebbe rimasto fuori. E `fn_is_super_admin` non va bene:
   fuori dalla veste OPERATORE risponde `false`, quindi il super admin che entra dal portale
   con la stessa password non avrebbe avuto l'obbligo. ⇒ la seconda domanda di
   `fn_is_super_admin` («binding SUPER_ADMIN attivo?») è estratta nel BB
   `fn_is_super_admin_account`, che `fn_totp_obbligatorio` chiede da sola.
2. 🔴 **`system_process_context` non esiste più** (dal 2026-09-05). ⇒ **D-T4** (Tid,
   2026-09-29): lo sblocco è della sessione del migratore. La domanda «la sessione è del
   migratore?» esisteva già nel corpo di `fn_sync_functions_owner`: estratta nel BB
   `fn_sessione_del_migratore`, copia ritirata.
3. **Via `abilitato`.** I verbi producono due soli stati (da confermare / confermato) e
   disabilitare cancella la riga (D-T3): due booleani che dicono la stessa cosa lasciavano due
   combinazioni che nessun verbo produce. Nessun lettore fuori dal DB (grep del 2026-09-29).
4. **`fn_get_totp_device` restituisce uno `stato`** (`ASSENTE` / `DA_CONFERMARE` / `ATTIVO`)
   invece di `attivo`: un booleano non distingue «nessun device» da «setup a metà», e il
   backend ne ha bisogno (il setup riprende; la sfida del login vale solo su `ATTIVO`).
5. **La conferma non solleva `E_TOTP_PASSO_GIA_USATO`**: un device non confermato non ha un
   passo con cui confrontare (la registrazione lo azzera). Il replay del codice di conferma lo
   ferma il passo registrato dalla conferma stessa.
6. **Il `CHECK` del `SUPER_ADMIN` nasce in `90_end`**, non con la colonna: da zero il profilo
   9100 arriva in `80_data/20260419-04` (già mergiato) senza la colonna, e il segno lo scrive
   il mirror del CSV. In `00_schema` il migrate si sarebbe fermato.
7. **`fn_totp_obbligatorio` è DEFINER**: la chiama il backend prima che esista un contesto;
   oggi le tabelle lette non hanno RLS (struttura, 2026-09-29), ma sotto una policy futura un
   INVOKER senza contesto risponderebbe «nessun obbligo» — fail-open sulla sicurezza.
8. **Due funzioni in più, nate già estratte**: `fn_guard_utente_stesso` (quattro verbi
   chiedono «chi agisce è la credenziale stessa?») e `fn_check_totp_recovery_hash` (registra e
   rigenera validano lo stesso mazzo: array non vuoto di stringhe distinte — i doppioni
   sparirebbero insieme al consumo).
9. **Il motivo della disabilitazione**: dall'applicazione il DB lo pretende ma non lo conserva (D-T3,
   la traccia è del backend); dal server lo scrive lui in `dbops.sessioni_utente` (D-T5, §9.6).

### 9.3 Le prove (2026-09-29, prima dell'apply)

SQL **estratto** dagli YAML (`yaml.safe_load`), in `BEGIN … ROLLBACK` sul DB di sviluppo,
come owner; seed simulato con le sole righe nuove. ⚠️ Il seed simulato **non prova il loader
di Liquibase** (la colonna nuova nei due mirror): lo dice solo l'apply.

| pgTAP | Esito da owner |
| --- | --- |
| `config/test-totp-device-verbi-v1` (28) | 27 verdi; il **25** rosso per costruzione (il runner owner è il migratore, terzo attore ammesso) |
| `config/test-totp-obbligo-v1` (15) | 15 verdi |
| `config/test-totp-porta-v1` (12) | 10 verdi; **2** e **12** rossi per costruzione (provano l'app) |
| `config/test-totp-disabilita-migratore-v1` (4, runner **owner**) | 4 verdi |

**Regressione per asserzione** (stesso file senza e con i changeSet) su 19 presidi:
`catalogo-messaggi-errore-completo`, `riferimenti-morti` (compila ogni plpgsql),
`security-definer-search-path`, i due `sec-functions-owner-*`, `vw-codici-errore-*`, i tre
`fn-is-super-admin` / `ultimo-super-admin`, `rubinetto-primo-motivo`, i quattro della
credenziale, i due guard dei profili, `fk-auth-user-ponte-django`, `codici-errore-identita`,
`costanti-catalogo-citate-dal-codice`: **nessuna asserzione cambia**, salvo il test 12 di
`dbops/test-sec-functions-owner-riservato-v1`, un presidio sul **testo** della sync che
cercava `pg_has_role(session_user…)` nel suo corpo: aggiornato nello stesso giro perché segua
la domanda nel BB (la sync chiama il BB, il BB legge `session_user`).

Oggetti vivi confrontati prima e dopo le prove (corpo di `fn_is_super_admin` e della sync,
proprietario della sync, privilegi dell'app, registro degli owner): **invariati**.
Guardrail: `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
`grant_ruolo_batch`, `sql_letterali`, `timestamp_senza_fuso`, `pgtap_preambolo` verdi.
⚠️ Il `pgtap_preambolo` era **rosso prima di questo giro**, su due pgTAP del brief liste
(`vendite/test-contratto-righe-lista-v1`, `test-listino-versione-in-vigore-v1`): aggiunta la
riga del contesto, entrambi verdi come prima (12/12, 13/13).

✅ **Dopo l'apply (2026-09-29)**: corsa col runner di Tid **verde** — i quattro pgTAP nuovi
(come app; `test-totp-disabilita-migratore-v1` come owner) e i presidi trasversali. I rossi
«da owner per costruzione» della prova pre-apply erano, come dichiarato, verdi come app.

### 9.4 Documentazione (scritta il 2026-09-29)

`config/manual/auth_totp_device.md` **riscritto** sullo stato vero (ciclo di vita sui verbi,
anti-replay sul passo, chi può cosa; via il `TotpService`, `risorse_umane_auth_user` e la
chiave derivata da `SECRET_KEY`); `credenziali.md` (la quarta cosa della credenziale, la riga
«codice del secondo fattore sbagliato» in «Cosa azzera cosa», la storia); `profili_accesso.md`
(il segno e il `SUPER_ADMIN`); 13 schede nuove (le funzioni); storie di `fn_is_super_admin` e
`fn_sync_functions_owner`; la guida `architettura-permessi-e-autorizzazioni` (il quarto guard).
✅ Doc auto-gen rigenerata: le 13 pagine nuove includono la loro scheda.

### 9.5 ⏳ Richieste al BE / FE (`dev/backend-tid`)

1. **Policy HTTP** dei sei codici in `error_policies.py` (o `test_error_codes_db_policy_guardrail`
   è rosso alla rigenerazione della doc auto-gen).
2. **`fn_get_totp_device` dà `stato`**, non `attivo` (§9.2 punto 4): la sfida del login solo
   su `ATTIVO`; su `DA_CONFERMARE` il setup riprende.
3. **D-T2 nel login a due passi**: un codice sbagliato → `script.fn_registra_tentativo_login(…,
   p_successo => false)`; e il **successo** si registra solo dopo il secondo fattore, non dopo
   la sola password (altrimenti la password giusta azzererebbe i tentativi del codice).
4. **Il segno sul profilo**: la scrittura di `profili_accesso` è del backend (amm_software) —
   il campo nel CRUD dei profili e a video; sul `SUPER_ADMIN` il `CHECK` risponde 23514 se
   qualcuno prova a spegnerlo.
5. **I codici di recupero**: al DB arrivano gli **hash**, distinti e non vuoti (se no
   `E_AUTH_CHIAMATA_NON_VALIDA`); `fn_totp_consuma_recovery` restituisce quanti ne restano.
6. **Il passo**: lo calcola il backend (`floor(unix_time / 30)` del codice accettato). ⚠️ Il DB
   non limita il passo verso il futuro (il periodo è del backend: una seconda sede del «30»
   sarebbe una copia): un passo sbagliato per eccesso bloccherebbe il device fino alla
   disabilitazione. Un test lato BE sul valore passato.
7. **Niente comando di gestione per lo sblocco** (D-T4): la procedura è del DBA, sul server —
   `SELECT script.fn_totp_disabilita_device(<auth_user_id>, '<motivo>');` da una sessione del
   migratore, senza `app.current_user_id`. Da scrivere nel runbook di esercizio. La traccia la
   lascia il verbo da solo (D-T5): nel runbook basta dire che il motivo è obbligatorio.
8. **Il pannello che mostra la storia degli accessi** di una persona (se lo mostra, leggendo
   `dbops.sessioni_utente`): un evento nuovo, `TOTP_DISABILITATO`, senza `jti`, col
   `dettaglio` `{via, sessione, chi_agisce, motivo}` — gli serve un'etichetta. Il pannello delle
   sessioni attive non cambia (legge solo `LOGIN`/`REFRESH`).
9. **FE**: le chiavi i18n dei due motivi (`CREDENZIALE`, `PROFILO`) e dei sei codici.

### 9.6 ✅ D-T5 — la traccia dello sblocco dal server (decisa da Tid il 2026-09-29: strada B)

**La domanda.** D-T3 affida chi / quando / perché all'audit del backend; ma nella strada del
migratore (D-T4) il backend non c'è, e il DB pretendeva il motivo senza conservarlo. Due
strade: (a) basta il log del server e la disciplina del DBA; (b) il verbo, **solo in quel
ramo**, scrive la traccia. ✅ **Tid: B.**

**La sede.** L'«audit degli eventi di autenticazione che il backend già scrive» è
`dbops.sessioni_utente` (login, refresh, logout, scadenza, revoca: una riga per evento, per
credenziale, `dettaglio` jsonb). La traccia va **lì**, accanto agli altri eventi della persona:
nessun registro nuovo. `vendite.event_log` non va bene (sa collocare solo lotti, commesse e
fatture), `dbops.audit_log` è il registro tecnico delle esecuzioni.

| # | Dove | Cosa |
| --- | --- | --- |
| `20260929-25` | `00_schema/dbops` | `chk_sessioni_utente_evento` ammette `TOTP_DISABILITATO` |
| `-26` | `20_code/script` | `fn_totp_disabilita_device`: nel ramo del migratore, dopo la cancellazione e **nella stessa istruzione**, la riga con `dettaglio = {via: SERVER, sessione: <ruolo di login>, chi_agisce, motivo}`. Se la riga non si scrive, la disattivazione si annulla. Gli altri rami invariati |

`sessione` e non `user_insert`: dentro una DEFINER `CURRENT_USER` è il proprietario. Retention:
quella della tabella (180 giorni, `CLEANUP_AT`). `jti` NULL: il pannello delle sessioni attive
(solo `LOGIN`/`REFRESH`) non la vede.

✅ **Applicati il 2026-09-29 alle 23:19, pgTAP verdi col runner (Tid).** **Prove pre-apply** (SQL estratto dei soli `-25`/`-26`, gli altri erano applicati): `test-totp-disabilita-
migratore-v1` 5/5 (nuovo il 4: la riga, con via, ruolo di login e motivo);
`test-totp-device-verbi-v1` nuovo **23b** (dal SUPER_ADMIN via applicazione nessuna riga —
rosso da owner per costruzione: il runner owner è il migratore); obbligo 15/15; porta come
prima; regressione per asserzione sui 19 presidi: nessuna asserzione cambia; DB vivo invariato;
guardrail verdi.
