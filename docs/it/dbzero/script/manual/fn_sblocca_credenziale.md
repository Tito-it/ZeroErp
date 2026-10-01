## 📘 Documentazione Concettuale – Funzione `script.fn_sblocca_credenziale()`

> 👀 **Vedi anche**
>
> **Il modello:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **Il contrario:** [fn_blocca_credenziale](/dbzero/script/funzioni/fn_blocca_credenziale)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

**Toglie il blocco dell'amministratore** da una credenziale. È l'unica strada:
il blocco non scade da solo e il reset della password non lo toglie.

* Solo un **SUPER_ADMIN** (prima riga: `fn_guard_super_admin`).
* **Non tocca i tentativi sbagliati**: chi viene sbloccato ritrova il freno sulle
  macchine così com'era. Li azzera un accesso riuscito o un reset.
* Sbloccare una credenziale che non è bloccata non fa niente.

---

### Storia

* 2026-09-25 — nasce (`20260925-15`). Brief: brief-db-blocco-login-per-credenziale.

{% include-markdown "signature-core.md" %}
