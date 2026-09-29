## 📘 Documentazione Concettuale – Funzione `script.fn_totp_registra_device()`

> 👀 **Vedi anche**
>
> **Il ciclo di vita:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)
>
> **Il passo dopo:** [fn_totp_conferma_device](/dbzero/script/funzioni/fn_totp_conferma_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

**Comincia la configurazione** del secondo fattore: registra il segreto (cifrato
dal backend) e i codici di recupero (come hash), con il dispositivo **da
confermare**.

---

### Regole

* Solo la persona stessa ([fn_guard_utente_stesso](/dbzero/script/funzioni/fn_guard_utente_stesso)).
* Se c'era già una configurazione non confermata, la **sostituisce**: si ricomincia con un QR e codici nuovi.
* ⛔ Su un dispositivo **attivo** rifiuta (`E_TOTP_DEVICE_GIA_ATTIVO`): va prima disattivato.
* I codici di recupero devono essere almeno uno, tutti diversi ([fn_check_totp_recovery_hash](/dbzero/script/funzioni/fn_check_totp_recovery_hash)).

---

### Storia

* 2026-09-29 — nasce (`20260929-17`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
