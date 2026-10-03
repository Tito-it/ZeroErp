## 📘 Documentazione Concettuale – Funzione `script.fn_imposta_totp_obbligatorio()`

> 👀 **Vedi anche**
>
> **La domanda:** [fn_totp_obbligatorio](/dbzero/script/funzioni/fn_totp_obbligatorio)
>
> **La sede:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **Chi può farlo:** [fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Accende o spegne l'obbligo del secondo fattore **per una persona**, per
decisione di un amministratore.

---

### Regole

* Solo un **SUPER_ADMIN** (prima riga: `fn_guard_super_admin`).
* Togliere l'obbligo **non toglie il dispositivo** già configurato, e non toglie l'obbligo che viene da un profilo privilegiato.
* La riga della credenziale nasce qui se non c'era.
* ⛔ Su una **credenziale di sistema** (l'utente di un processo automatico o
  un sistema esterno) l'obbligo **non si accende** (`E_CREDENZIALE_DI_SISTEMA`):
  una macchina non ha un telefono, e l'obbligo la fermerebbe. **Spegnerlo
  invece si può**: è il rimedio a un obbligo acceso per sbaglio.

---

### Storia

* 2026-09-29 — nasce (`20260929-12`). Brief: brief-db-secondo-fattore-totp.
* 2026-10-03 — rifiuta l'accensione su una credenziale di sistema (`20261003-03`). Brief: brief-db-credenziale-verbi-amministratore.

{% include-markdown "signature-core.md" %}
