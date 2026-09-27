# Brief DB — La credenziale di un'email: i dati del dialog del consenso al riuso

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`), con la
> ricaduta sul backend e sul frontend al §3.
>
> **Data**: 2026-09-27 · **Stato**: ⏳ **richiesta al team DB (§2)**, non
> ancora scritta. Il backend e il frontend (§3) **aspettano** il changeSet.
>
> **Origine**: §17 di
> [brief-db-blocco-login-per-credenziale.md](../work-done/brief-db-blocco-login-per-credenziale.md),
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
- ❓ **Da decidere (Tid / team DB): chi può chiamarla.** La funzione dice se
  un'email ha un accesso e con quali vesti: è un'informazione da amministratore.
  Lato backend l'unico chiamante sarà un endpoint `AdminAPIView` (SUPER_ADMIN).
  La domanda è se mettere anche a DB il guard `script.fn_guard_super_admin`,
  come ai verbi di blocco e sblocco (D-B1 del brief di origine).
- Manual della madre (`docs/it/dbzero/anagrafiche/manual/fn_crea_operatore_v2.md`)
  e descrizione di `E_CREDENZIALE_DA_CONFERMARE`: togliere «il contesto porta …
  per il dialog», che promette un trasporto che non c'è. Il contesto resta, ma
  serve al log.
- pgTAP:
  - la funzione sui tre casi: email nuova → zero righe; credenziale senza vesti
    → `vesti = []`; credenziale con vesti;
  - la madre invariata (`test-crea-operatore-riusa-credenziale-v1`).

## 3. Cosa faranno il backend e il frontend, dopo il changeSet

| # | Dove | Cosa |
| --- | --- | --- |
| B-20 | `amm_software` | lettura nel repository e `GET …/operatori/credenziale-per-email/?email=` (`AdminAPIView`) |
| F-4 | `OperatoreDrawer` | sul 409 `E_CREDENZIALE_DA_CONFERMARE` (senza toast: `azioniGestite`) legge la credenziale e apre un `AppDialog` con username e vesti; se l'operatore conferma, ripete la creazione con `riusa_auth_user_id` = l'id letto. Se nel frattempo la credenziale è cambiata, la madre rifiuta di nuovo e il dialog si ripropone: per questo si dichiara un id e non un sì. `E_CREDENZIALE_ALTRA_PERSONA` non apre il dialog: si corregge l'email |
| F-3 | `OperatoreDrawer` | ⏳ ereditato dal brief di origine (§16.4): **controllare a video** che il motivo dei pulsanti spenti (invito, disattivazione, retrocessione da super admin) compaia davvero, perché nessun presidio lo vede. Il codice è committato (`854ca3c2b`). Si fa insieme a F-4, sullo stesso drawer |

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

---
{% include-markdown "signature-core.md" %}
