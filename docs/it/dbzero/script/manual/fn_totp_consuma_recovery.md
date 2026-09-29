## 📘 Documentazione Concettuale – Funzione `script.fn_totp_consuma_recovery()`

> 👀 **Vedi anche**
>
> **La tabella:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)
>
> **Codici nuovi:** [fn_totp_rigenera_recovery](/dbzero/script/funzioni/fn_totp_rigenera_recovery)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Entrare **senza telefono** con un codice di recupero. Il codice, dopo, non vale
più; la funzione dice **quanti ne restano**, così il backend può avvisare quando
stanno finendo.

---

### Regole

* Un codice che non c'è, o già usato: `E_TOTP_RECOVERY_NON_VALIDO`.
* Due accessi simultanei con lo stesso codice: ne passa uno solo.
* Si chiama **prima del login**, dopo la password. Il database riceve l'hash del codice, mai il codice in chiaro.

---

### Storia

* 2026-09-29 — nasce (`20260929-20`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
