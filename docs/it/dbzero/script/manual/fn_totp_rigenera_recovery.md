## 📘 Documentazione Concettuale – Funzione `script.fn_totp_rigenera_recovery()`

> 👀 **Vedi anche**
>
> **La tabella:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

**Codici di recupero nuovi**: i vecchi, usati o no, non valgono più. Il backend
chiede prima un codice del telefono, e mostra i nuovi una volta sola.

---

### Regole

* Solo la persona stessa ([fn_guard_utente_stesso](/dbzero/script/funzioni/fn_guard_utente_stesso)).
* Solo su un dispositivo **attivo** (durante la configurazione i codici li dà [fn_totp_registra_device](/dbzero/script/funzioni/fn_totp_registra_device)).

---

### Storia

* 2026-09-29 — nasce (`20260929-21`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
