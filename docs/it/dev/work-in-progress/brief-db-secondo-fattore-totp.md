# Brief DB — Secondo fattore (TOTP): obbligo, verbi del device, manuali

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-28. **A chi:** team DB (`dev/db-tid`);
> Tid per le decisioni di §7.
> **Origine:** §3.3 di [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md).
> Le decisioni di Tid già prese sono in quel brief (§6): l'obbligo del secondo fattore vale
> **per credenziale e per ruolo** (decisione 3), il backend usa **librerie esistenti** per TOTP
> e QR (decisione 4).
> **Stato:** 🟡 da fare. ✅ D-T1 → D-T3 decise da Tid il 2026-09-28 (§7): si procede. Il
> backend e il frontend del TOTP **aspettano** questo lavoro.
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

---

## 8. Cosa fa il backend dopo (per sapere cosa serve)

Il login a due passi (password → sfida breve → codice → JWT), il setup con QR e codici di
recupero mostrati una volta sola, il middleware che porta al setup chi ha l'obbligo e non ha un
device attivo (sul modello di `PasswordChangeRequiredMiddleware`), il comando di gestione per
il caso senza via d'uscita (§3), `auth_totp_device.secret_encrypted` in `CAMPI_CIFRATI`.
Serve dal DB: §2, §3, §4, §5. I manuali (§6) possono seguire.
