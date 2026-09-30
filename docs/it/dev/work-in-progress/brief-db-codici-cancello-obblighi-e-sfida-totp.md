# Brief DB — Tre codici a catalogo: il cancello degli obblighi e la sfida del login TOTP

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-30. **A chi:** team DB (`dev/db-tid`).
> **Origine:** §3.4 di [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md),
> lotti T-0 e T-2 (decisioni di Tid del 2026-09-30).
> **Stato:** 🟢 consegnato a file il 2026-09-30 (`dev/db-tid`), **da applicare**: le righe sono
> nei due CSV (§4), le carica il loader `runOnChange` `20260614-08` al prossimo migrate. Il
> backend lavora in parallelo (decisione di Tid del 2026-09-30) e rigenera
> `error_policies_generated.py` all'arrivo dei codici; il **merge** del BE aspetta questo apply.
>
> **In una riga:** solo righe di `80_data` (`codici_errore.csv` + `messaggi_errore.csv`),
> nessun oggetto nuovo. Tre codici che il **backend** solleva e che oggi non hanno una sede a
> catalogo.

---

## 1. Perché servono

* **Il cancello degli obblighi** (lotto T-0, chiude A-8 del
  [piano accessi](piano-be-fe-accessi-credenziale-e-vesti.md) §4.4): il controllo «questa
  credenziale deve prima fare qualcosa» si sposta dopo l'autenticazione DRF, dove l'utente del
  JWT è noto. Oggi `PasswordChangeRequiredMiddleware` è inerte col JWT e scrive a mano un
  envelope con `E_CAMBIO_PASSWORD_RICHIESTO`, un codice **mai registrato a catalogo**: nessuna
  policy, nessuna frase, nessuna classe. Il cancello nuovo solleva `ServiceError` come ogni altro
  punto, quindi il codice deve esistere. Gli obblighi sono due, con due frasi e due soluzioni
  diverse: il cambio password e la configurazione del secondo fattore.
* **La sfida del login a due passi** (lotto T-2): dopo la password giusta, a chi ha un device
  attivo il backend dà una sfida firmata che vale 5 minuti, non un JWT. Una sfida scaduta,
  manomessa o presentata da un'altra provenienza è un **401**: chi la presenta non è
  autenticato, e deve ripartire dalla password.

⚠️ Il secondo codice scritto a mano dal middleware, `E_CAMBIO_PASSWORD_CHECK_FALLITO` (503 se il
DB non risponde), **non** si registra: dentro l'autenticazione DRF un DB che non risponde è già
un errore della richiesta (fail-closed, `E_DATABASE`). Il codice sparisce col middleware.

## 2. I codici

| Codice | Classe | Quando | Frase proposta (`it`, senza segnaposto) |
| --- | --- | --- | --- |
| `E_CAMBIO_PASSWORD_RICHIESTO` | `NON_PERMESSO` | la credenziale ha `deve_cambiare_password` e la richiesta non è fra quelle ammesse (cambio password, logout, profilo) | «Prima di continuare è necessario cambiare la password.» |
| `E_TOTP_CONFIGURAZIONE_RICHIESTA` | `NON_PERMESSO` | `script.fn_totp_obbligatorio` risponde `obbligatorio` e il device non è `ATTIVO` (`fn_get_totp_device`); la richiesta non è fra quelle ammesse (configurazione del secondo fattore, logout, profilo) | «Prima di continuare è necessario configurare il secondo fattore di autenticazione.» |
| `E_TOTP_SFIDA_NON_VALIDA` | `NON_AUTENTICATO` | il secondo passo del login riceve una sfida scaduta, con la firma sbagliata, di un'altra porta o di un'altra provenienza | «La verifica è scaduta: accedere di nuovo con la password.» |

Proposte di `causa` / `soluzione`:

* `E_CAMBIO_PASSWORD_RICHIESTO` — causa: «L'amministratore ha chiesto il cambio della password,
  o la password è provvisoria.»; soluzione: «Impostare una password nuova dalla pagina di cambio
  password.»
* `E_TOTP_CONFIGURAZIONE_RICHIESTA` — causa: «Per questo accesso il secondo fattore è
  obbligatorio (lo ha deciso l'amministratore, o lo richiede un profilo assegnato) e non è ancora
  configurato.»; soluzione: «Configurare il secondo fattore dalla pagina Sicurezza con un'app di
  autenticazione.»
* `E_TOTP_SFIDA_NON_VALIDA` — causa: «Fra la password e il codice sono passati più di cinque
  minuti, o la richiesta non viene dalla stessa postazione.»; soluzione: «Ripetere l'accesso
  dall'inizio.»

Nelle `note` di `codici_errore.csv`: tutti e tre li solleva il **backend** (come
`E_TOTP_CODICE_NON_VALIDO`), a catalogo per frase e classe.

## 3. Cosa fa il backend dopo

* `./manage-env.sh genera_error_policies`, poi i ripieghi senza `%s` in
  `error_messages_fallback.py`;
* ritira i due codici scritti a mano dal middleware insieme al middleware stesso.

Nessuna ricaduta su pgTAP oltre ai presidi del catalogo (`catalogo-messaggi-errore-completo`,
`vw-codici-errore-*`).

## 4. Fatto (DB, 2026-09-30)

Tre righe in `80_data/sql/config/codici_errore.csv` e tre in `messaggi_errore.csv` (id
**1182 → 1184**), nessun changeSet nuovo: le carica `20260614-08-upsert-messaggi-errore-…`
(`runOnChange`), classi prima, codici poi, messaggi per ultimi.

| Codice | Classe | id |
| --- | --- | --- |
| `E_CAMBIO_PASSWORD_RICHIESTO` | `NON_PERMESSO` | 1182 |
| `E_TOTP_CONFIGURAZIONE_RICHIESTA` | `NON_PERMESSO` | 1183 |
| `E_TOTP_SFIDA_NON_VALIDA` | `NON_AUTENTICATO` | 1184 |

Frasi, cause e soluzioni sono quelle di §2 (con gli accenti in apostrofo, come il resto del
catalogo), tutte **chiuse**: nessuna funzione PL/pgSQL le solleva, quindi nessuno riempirebbe un
`%s`. Le `note` dicono chi solleva (il backend), perché la classe, e **perché non si riusa** il
fratello più vicino:

* `E_TOTP_CONFIGURAZIONE_RICHIESTA` ≠ `E_TOTP_DEVICE_ASSENTE`: quello è il verbo DB che non trova
  il device (409), questo è l'accesso fermato finché il device non c'è (403);
* `E_TOTP_SFIDA_NON_VALIDA` ≠ `E_TOTP_CODICE_NON_VALIDO`: quello è il codice sbagliato su una
  sfida buona (400, si riprova e conta come tentativo), questo è la sfida da rifare (401). Una
  frase sola per i quattro casi, di proposito: non si dice a chi prova quale controllo è fallito.

`E_CAMBIO_PASSWORD_CHECK_FALLITO` **non** è stato registrato, come chiesto in §1.

**Verifica:** i due CSV rilevati col parser `csv` (colonne coerenti, nessun `codice`/`id`
doppio); le classi esistono in `classi_errore.csv`; i presidi del catalogo
(`test-catalogo-messaggi-errore-completo`, `test-vw-codici-errore-*`) non pinnano conteggi.
pgTAP da lanciare da Tid dopo l'apply.

➡️ **Al backend:** `./manage-env.sh genera_error_policies` dopo l'apply, i ripieghi in
`error_messages_fallback.py`, e il ritiro di `PasswordChangeRequiredMiddleware` coi suoi due
codici scritti a mano (§3).
