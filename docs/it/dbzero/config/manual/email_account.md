## Documentazione Concettuale -- Tabella `config.email_account`

> **Ultimo aggiornamento**: 12 novembre 2026

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_template](/dbzero/config/tabelle/email_template)
> [config.email_log](/dbzero/config/tabelle/email_log)
> [config.email_outbox](/dbzero/config/tabelle/email_outbox)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)

---

### 🎯 Scopo Principale

La tabella `config.email_account` definisce gli **account SMTP** utilizzati dal sistema per l'invio di email. Ogni unita' organizzativa (reparto) puo' avere il proprio account mittente; un account con `unita_organizzativa_id = NULL` funge da **fallback di sistema**.

---

### Ruolo nel processo

Il servizio `EmailDispatchService` risolve l'account da usare per ogni invio con questa logica:

1. Cerca un account attivo associato al reparto dell'operatore
2. Se non trovato, usa l'account con codice `SISTEMA` (fallback)

L'account determina il mittente (`email_from`), il reply-to e tutti i parametri di connessione SMTP.

---

### Sicurezza

* La password SMTP e' salvata **crittografata** con Fernet (chiavi `DJANGO_FIELD_ENCRYPTION_KEYS` del backend, separate dalla `SECRET_KEY`). Non viene mai esposta in chiaro nelle API ne' nei log.
* I campi `smtp_use_tls` e `smtp_use_ssl` sono mutuamente esclusivi (CHECK constraint). TLS (STARTTLS, porta 587) e' il default; SSL diretto e' per porta 465.

---

### Vincoli e regole

* `codice` e' UNIQUE -- identifica l'account in modo leggibile (es. `SISTEMA`, `ACQ_01`, `COMM_01`).
* `smtp_port` deve essere tra 1 e 65535.
* Un solo account con `unita_organizzativa_id IS NULL` e codice `SISTEMA` deve esistere come fallback.
* La FK su `unita_organizzative` e' NO ACTION: non si cancella un reparto se ha un account email associato.
* Senza indirizzo di risposta `email_reply_to` e' `NULL`, e il servizio di invio non mette il
  `Reply-To`. Nel CSV del seed la cella vuota porta il token `NULL` (il mirror dichiara
  `nullValue: "NULL"`). ⚠️ La stringa vuota non e' ancora vietata da un vincolo: la modifica
  dal pannello scrive `''` quando si svuota il campo, e il `CHECK` arriva quando il backend la
  porta a `NULL`.

---

### Esempio di configurazione

| codice    | unita_organizzativa_id | email_from               | Uso                                          |
| --------- | ---------------------- | ------------------------ | -------------------------------------------- |
| `SISTEMA` | NULL                   | `noreply@azienda.it`     | Inviti, reset password, notifiche di sistema |
| `ACQ_01`  | 3 (Ufficio Acquisti)   | `acquisti@azienda.it`    | Comunicazioni a fornitori                    |
| `COMM_01` | 5 (Commerciale)        | `commerciale@azienda.it` | Comunicazioni a clienti                      |

---

### Estensibilita'

Nuovi account possono essere aggiunti senza modifiche al codice. La risoluzione per reparto e' automatica tramite `fn_resolve_email_account`.
