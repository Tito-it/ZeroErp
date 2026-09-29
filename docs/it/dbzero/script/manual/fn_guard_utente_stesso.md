## 📘 Documentazione Concettuale – Funzione `script.fn_guard_utente_stesso()`

> 👀 **Vedi anche**
>
> **Il gemello:** [fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Il controllo in prima riga dei verbi che toccano **le cose proprie** di una
persona — oggi il dispositivo del secondo fattore: chi agisce dev'essere la
persona su cui si agisce. Altrimenti `E_PERMESSO_NEGATO`, lo stesso codice di
ogni permesso negato.

---

### Regole

* Chi agisce lo passa il chiamante, letto dal contesto della richiesta.
* Nessun utente in sessione vale «no».
* Protegge da un backend che sbaglia l'identità, non da uno manomesso: l'identità la dichiara il backend.

---

### Storia

* 2026-09-29 — nasce (`20260929-14`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
