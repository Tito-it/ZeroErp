## 📘 Documentazione Concettuale – Funzione `script.fn_totp_conferma_device()`

> 👀 **Vedi anche**
>
> **Il ciclo di vita:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)
>
> **Il passo prima:** [fn_totp_registra_device](/dbzero/script/funzioni/fn_totp_registra_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

**Chiude la configurazione**: il backend ha verificato il primo codice, e il
dispositivo diventa **attivo**. L'intervallo di quel codice è il primo registrato:
da lì parte la regola «un codice vale una volta sola».

---

### Regole

* Solo la persona stessa ([fn_guard_utente_stesso](/dbzero/script/funzioni/fn_guard_utente_stesso)).
* Su un dispositivo già attivo: `E_TOTP_DEVICE_GIA_ATTIVO`; senza dispositivo: `E_TOTP_DEVICE_ASSENTE`.

---

### Storia

* 2026-09-29 — nasce (`20260929-18`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
