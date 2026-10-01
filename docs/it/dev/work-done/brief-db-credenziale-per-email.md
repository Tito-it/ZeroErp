# Brief DB — La credenziale di un'email: i dati del dialog del consenso al riuso

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`), con la
> ricaduta sul backend e sul frontend al §3.
>
> **Data**: 2026-09-27 · **Stato**: ✅ **CHIUSO il 2026-09-27.** Lato DB
> `20260927-40`, `-41` applicati (§2.1); B-20 e F-4 scritti (§3.1), test verdi.
> ➜ Il controllo a video di F-4 (e di F-3, ereditato dal brief di origine) è il
> [collaudo in-app](../work-in-progress/collaudo-in-app-consenso-riuso-credenziale.md),
> da eseguire: quando è verde va in `work-done/` accanto a questo brief.
>
> **Origine**: §17 di
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md),
> scorporato il 2026-09-27 alla chiusura di quel brief, perché era l'unico lavoro
> aperto. Il resto del cantiere (P-1, P-2, R-3, R-7, R-8, R-9, §16) è applicato e
> committato. Il contesto del consenso sta in quel brief, §12.7 (la domanda e la
> decisione) e §12.4 (B-6).

## 1. Il problema, sul modello

Il `20260925-51` (brief di origine §12.7) fa rifiutare ad
`anagrafiche.fn_crea_operatore_v2` il riuso di una credenziale trovata per email,
finché il chiamante non **dichiara l'id** della credenziale che accetta
(`p_riusa_auth_user_id`). Il rifiuto è `E_CREDENZIALE_DA_CONFERMARE`. Mette
`auth_user_id`, `username` e `vesti` della credenziale trovata nel **contesto**,
«per il dialog» (manual della madre, descrizione in `codici_errore.csv`).

Ma il contesto **non è un canale verso il client**. `script.fn_log_and_raise_error`
lo scrive in `dbops.error_log`, e l'eccezione porta solo messaggio, `DETAIL`,
`HINT` e i tre canali strutturati: codice (`CONSTRAINT`), campo (`COLUMN`) e
bersaglio (`DATATYPE`). Verificato sul corpo della funzione (doc auto-gen,
`RAISE … USING`).

Quindi al backend arrivano l'email e lo username (nel messaggio), ma **non l'id
da dichiarare** né le vesti da mostrare: il dialog di B-6, così com'è scritto, non
si può fare. E non esiste una lettura a DB «la credenziale di questa email, con
le sue vesti»: l'unico posto dove si costruisce la lista delle vesti è la
`jsonb_agg` dentro la madre.

Le strade scartate (decisione di Tid, 2026-09-27):

- un canale generico di dati nell'eccezione: tocca `fn_log_and_raise_error` e i
  cinque punti di traduzione, ed è un cantiere a sé;
- la rilettura in Python di id e vesti: sarebbe una seconda copia della lettura
  delle vesti, e un campo nuovo nell'envelope.

## 2. Cosa si chiede al team DB

- Una funzione di **lettura** `script.fn_get_credenziale_per_email(p_email text)`
  (nome a scelta del team DB) → `TABLE(auth_user_id integer, username text,
  vesti jsonb)`:
  - zero righe se l'email non ha credenziale;
  - la credenziale la trova `script.fn_get_auth_user_id_for_email`, quindi senza
    distinguere maiuscole e minuscole, e con `E_CREDENZIALE_EMAIL_AMBIGUA` dove
    serve;
  - `vesti` nella forma che la madre già costruisce (`ruolo_applicativo`,
    `attivo`, `soggetto`, in ordine di id).
- ⭐ **Regola del 2**: nel passo 2-bis la madre legge username e vesti **da
  questa funzione**, al posto della sua `jsonb_agg`. Così il dialog e il rifiuto
  leggono la stessa cosa, e non possono divergere.
- **Chi può chiamarla.** La funzione dice se un'email ha un accesso e con
  quali vesti: è un'informazione da amministratore. Lato backend l'unico
  chiamante sarà un endpoint `AdminAPIView` (SUPER_ADMIN). La domanda era se
  mettere anche a DB il guard `script.fn_guard_super_admin`, come ai verbi di
  blocco e sblocco (D-B1 del brief di origine). ✅ *Decisa da Tid il
  2026-09-27: **nessun guard a DB**, il cancello è l'`AdminAPIView` (motivi al
  §2.1).*
- Manual della madre (`docs/it/dbzero/anagrafiche/manual/fn_crea_operatore_v2.md`)
  e descrizione di `E_CREDENZIALE_DA_CONFERMARE`: togliere «il contesto porta …
  per il dialog», che promette un trasporto che non c'è. Il contesto resta, ma
  serve al log.
- pgTAP:
  - la funzione sui tre casi: email nuova → zero righe; credenziale senza vesti
    → `vesti = []`; credenziale con vesti;
  - la madre invariata (`test-crea-operatore-riusa-credenziale-v1`).

### 2.1 Esecuzione (2026-09-27)

**Decisione di Tid (2026-09-27), sulla domanda del §2: nessun guard di
permesso a DB.** Il cancello resta la porta del backend (`AdminAPIView`, solo
SUPER_ADMIN). Un `fn_guard_super_admin` nella funzione:

- romperebbe la madre, che la chiama nel ramo del rifiuto. La madre è
  `INVOKER` e non ha un guard SUPER_ADMIN suo, quindi chi non è SUPER_ADMIN
  leggerebbe `E_PERMESSO_NEGATO` invece di `E_CREDENZIALE_DA_CONFERMARE`: un
  permesso nato dentro un ramo d'errore;
- non chiuderebbe niente: l'app legge già `django.auth_user` (contratto del
  `-40` del 25-09, `provision_db_roles.sql`) e `anagrafiche.identita_digitali`
  (la madre `INVOKER` la legge come app). Il modello del verbo chiude le
  scritture, non le letture; D-B1 riguardava due verbi di scrittura.

| Fase | ChangeSet | Cosa |
| --- | --- | --- |
| `20_code/script` | `20260927-40` | ⭐ `script.fn_get_credenziale_per_email(p_email)` → `TABLE(auth_user_id, username, vesti)`: zero righe se l'email non ha credenziale; una riga anche senza vesti (`vesti = []`); la credenziale la trova `fn_get_auth_user_id_for_email`; `vesti` nella forma della madre (`ruolo_applicativo`, `attivo`, `soggetto`, in ordine di id). `plpgsql`, tipi espliciti (nomina `django.*`), `STABLE`, `INVOKER` |
| `20_code/anagrafiche` | `20260927-41` | la madre, passo 2-bis: username e vesti dalla funzione nuova, al posto della sua aggregazione (regola del 2). Firma invariata: `CREATE OR REPLACE`. Corpo di partenza `-51`, verificato uguale al vivo (corpo e `COMMENT`) |
| `80_data` (CSV esistente) | — | `codici_errore.csv`, descrizione di `E_CREDENZIALE_DA_CONFERMARE`: il contesto porta i dati «per il log (al client non arriva)», e il dialog li legge dalla funzione. Messaggio (`messaggi_errore.csv`) invariato |
| pgTAP | `script/test-fn-get-credenziale-per-email-v1` | 9 casi: firma; email di nessuno, `NULL`, vuota, di soli spazi → zero righe; credenziale senza vesti, cercata in maiuscolo con spazi → una riga, `vesti = []`; credenziale di un operatore → la veste letta dalle tabelle; il rifiuto della madre nomina lo username della funzione; presidio sul testo: la madre chiama la funzione e non ha un `jsonb_agg` suo |
| manual | — | `script/manual/fn_get_credenziale_per_email` (nuovo), `fn_crea_operatore_v2` (regola 4, passo 2-bis, esempio, chiamanti, Storia), `fn_get_auth_user_id_for_email` (consumatore nuovo) |

⚠️ **Email nuova con consenso dichiarato** (`v_trovata` `NULL`,
`p_riusa_auth_user_id` valorizzato): la funzione dà zero righe, `SELECT INTO`
azzera username e vesti, e il `COALESCE` rimette `vesti = []`. È lo stesso
contesto di prima.

⚠️ **Non cambiato, da sapere**: le vesti si leggono con `JOIN` interni su
`soggetti_ruoli` e `soggetti`, sotto la RLS di chi chiama, come faceva la madre.
Una veste il cui soggetto non è visibile al chiamante non compare. Per un
SUPER_ADMIN non è un caso reale; lo si scrive per chi un giorno delegasse la
porta.

**Come è stato provato (2026-09-27).** Su **dbdev**, da owner, in una
transazione ritirata con l'SQL **estratto** dai due changeSet: sullo scratch
`zeroerp_ci` l'utente dell'env non ha i diritti di owner su `script` («permesso
negato per lo schema script»). Dopo la prova, verificato che su dbdev non è
rimasto niente (la funzione non esiste, la madre è quella del `-51`).

| Prova | Esito |
| --- | --- |
| `plpgsql_check` sulle due funzioni | 0 errori; sulla madre resta l'avviso preesistente `v_ru_id` mai letto |
| `test-fn-get-credenziale-per-email-v1` | 9/9 |
| **Controprova**: la funzione senza il `-41` (madre del `-51`) | rosso **solo** il 9: il presidio vede l'aggregazione propria della madre |
| `test-crea-operatore-riusa-credenziale-v1` con la madre nuova | 20/20, senza modifiche |
| cancelli statici (runOnChange, letterali, preCondition, trigger, grant batch, timestamp, preambolo pgTAP) | verdi |

⚠️ La prova gira da owner, non da `zeroerp_app`. La corsa col runner, che usa
l'app, resta di Tid ([il runner](/guide/pgtap-come-si-scrive-un-test)).
Presidi trasversali: `test-riferimenti-morti-v1` è coperto dal `plpgsql_check`
qui sopra; `test-rubinetto-primo-motivo-v1` non è toccato, perché nessuna
chiamata a `fn_raise_primo_motivo_se_presente`.

✅ **Applicati da Tid il 2026-09-27** (`-40` e `-41` insieme): pgTAP verdi,
nessuna regressione.

⏳ **Ora tocca a B-20 e F-4** (§3): il backend chiama
`SELECT * FROM script.fn_get_credenziale_per_email(%s)` dall'endpoint
`AdminAPIView`; sul 409 `E_CREDENZIALE_DA_CONFERMARE` il drawer apre il dialog
e rimanda con `riusa_auth_user_id`.

## 3. Cosa faranno il backend e il frontend, dopo il changeSet

| # | Dove | Cosa |
| --- | --- | --- |
| B-20 | `amm_software` | lettura nel repository e `GET …/operatori/credenziale-per-email/?email=` (`AdminAPIView`) |
| F-4 | `OperatoreDrawer` | sul 409 `E_CREDENZIALE_DA_CONFERMARE` (senza toast: `azioniGestite`) legge la credenziale e apre un `AppDialog` con username e vesti; se l'operatore conferma, ripete la creazione con `riusa_auth_user_id` = l'id letto. Se nel frattempo la credenziale è cambiata, la madre rifiuta di nuovo e il dialog si ripropone: per questo si dichiara un id e non un sì. `E_CREDENZIALE_ALTRA_PERSONA` non apre il dialog: si corregge l'email |
| F-3 | `OperatoreDrawer` | ⏳ ereditato dal brief di origine (§16.4): **controllare a video** che il motivo dei pulsanti spenti (invito, disattivazione, retrocessione da super admin) compaia davvero, perché nessun presidio lo vede. Il codice è committato (`854ca3c2b`). Si fa insieme a F-4, sullo stesso drawer |

### 3.1 Esecuzione BE/FE (2026-09-27)

- **B-20**: `GET /api/v1/amm-software/operatori/credenziale-per-email/?email=`
  (`CredenzialePerEmailView`, `AdminAPIView`) → `data.credenziale` =
  `{auth_user_id, username, vesti}` o `null`. Repository
  `get_credenziale_per_email` (una `SELECT` sulla funzione; `vesti` decodificato
  con il BB `jsonb_out`), tipi `CredenzialePerEmailRow`/`VesteCredenzialeRow`.
  L'email vuota o assente la gestisce il DB (zero righe): nessuna seconda
  copia della regola nella view.
- ⭐ **`ui_action` di `E_CREDENZIALE_DA_CONFERMARE` = `confirm_and_retry`**
  (`error_ui_overrides.py`, con la ragione): è un rifiuto confermabile come la
  capienza dei pagamenti. Col default della classe (banner) il pannello avrebbe
  mostrato un errore su una domanda.
- **Il BB `useForzaturaConfermata` generalizzato** (regola del 2, ok Tid):
  `conferma(dichiarazione)` ripete con la dichiarazione del dominio, invece di
  comporre lei `{forzata, motivo_forzatura}`; se il DB chiede di nuovo, la
  domanda si ripropone. I due consumatori dei pagamenti passano
  `forzaturaConMotivo(motivo)` (helper nuovo in `pagamenti/api/pagamenti.js`),
  comportamento invariato. Spec nuova del BB (6 casi). Nel catalogo BB FE tolta
  una copia della riga, finita per errore fra i BB spostati nei pagamenti.
- **F-4**: `OperatoreDrawer` crea con `esegui()`; sulla domanda legge la
  credenziale (B-20) e apre un `AppDialog` con la frase del DB, username e vesti
  (ruolo, soggetto, attiva/spenta). «Usa questo accesso» ripete con
  `riusa_auth_user_id` = l'id letto; se il DB chiede di nuovo, il dialog si
  riapre coi dati nuovi; se la credenziale non c'è più, avvisa e chiude la
  domanda. `E_CREDENZIALE_ALTRA_PERSONA` resta un errore normale. Nove chiavi
  `amministrazione.riuso_*` in `it.json`/`en.json`.
- **Prove**:
  - `test_login_credenziale_db` (DB vero, `ZEROERP_TEST_DB_E2E=1`): il consenso
    in due tempi ora passa dall'endpoint vero e conferma **con l'id letto**; dopo
    la creazione il dialog vede la veste `OPERATORE` spenta. ⚠️ Ha trovato un
    difetto che il mock non vedeva: `vesti` arrivava come stringa (fuori
    dall'ORM il `jsonb` non si decodifica), corretto con `jsonb_out`;
  - 3 test della view (`test_operatori_views`); spec FE del BB; vitest 414/414,
    eslint, `npm run guards`, `check_i18n_keys`, build verdi.
- Manuale `api_amm_software.md`: §1.2 riallineata al P-2 (madre `_v2`, niente
  password, veste spenta, consenso in due tempi) e §1.2-bis nuova.

➜ **Da vedere a video** (nessun presidio lo vede): il copione è il
[collaudo in-app](../work-in-progress/collaudo-in-app-consenso-riuso-credenziale.md)
(dialog, conferma, rinuncia, rifiuto sull'email di un'altra persona, e la
non-regressione della forzatura dei pagamenti).

✅ Già fatto (2026-09-27), e non dipende da questo brief:
`riusa_auth_user_id` passa dalla view al repository (`p_riusa_auth_user_id`);
assente vale `NULL`, cioè la prima chiamata chiede sempre la conferma. Test:
`test_amm_software_service` (il trasporto) e `test_login_credenziale_db` (i due
tempi sul DB vero, compresa la dichiarazione di un'altra credenziale, che viene
rifiutata).

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-27 | BE | Scorporato dal §17 di `brief-db-blocco-login-per-credenziale` alla sua chiusura: la richiesta al DB, B-20, F-4 e il controllo a video di F-3 |
| 2026-09-27 | Tid → DB | Nessun guard a DB sulla lettura della credenziale (il cancello è l'`AdminAPIView`). Scritti e provati `20260927-40` (`script.fn_get_credenziale_per_email`) e `-41` (la madre la legge, regola del 2), pgTAP `test-fn-get-credenziale-per-email-v1` (9), descrizione di `E_CREDENZIALE_DA_CONFERMARE`, manual (§2.1). Scritto sul brief di origine, ancora in `work-in-progress/` sul ramo DB |
| 2026-09-27 | Tid | `20260927-40`, `-41` applicati; pgTAP verdi, nessuna regressione. Lavoro DB chiuso. Resta a BE/FE: B-20, F-4 (§3) |
| 2026-09-27 | BE | Merge con `Tito-dev`: il §17.4 del brief di origine portato qui come §2.1 (riferimenti rinumerati) |
| 2026-09-27 | BE/FE | **B-20** e **F-4** (§3.1): endpoint di lettura, `confirm_and_retry` sul codice, BB `useForzaturaConfermata` generalizzato (ok Tid), dialog nel drawer. Resta il controllo a video |
| 2026-09-27 | BE | **Chiuso** (Tid). Il controllo a video passa al `collaudo-in-app-consenso-riuso-credenziale.md`, in `work-in-progress/` finché non è eseguito. Brief spostato in `work-done/` |

---
{% include-markdown "signature-core.md" %}
