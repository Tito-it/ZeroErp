## 📘 Documentazione Concettuale – Tabella `config.credenziali_eliminate`

> 👀 **Vedi anche**
>
> **Chi la scrive:** [fn_elimina_credenziale](/dbzero/script/funzioni/fn_elimina_credenziale)

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

Tiene **la traccia delle credenziali eliminate**. Quando un amministratore elimina
una credenziale la sua riga sparisce: qui resta scritto quale era (il numero e il
nome utente), la sua email, chi l'ha eliminata e quando.

---

### Regole

* La scrive **solo** il verbo dell'eliminazione. L'applicazione la può leggere,
  non modificare né cancellare.
* Non scade: la traccia resta.
* Non ha legami verso le credenziali: quella descritta non esiste più, ed è il
  punto.

---

### Storia

* 2026-10-06 — nasce (`20261006-10`). Brief: brief-db-elimina-credenziale-senza-veste.

{% include-markdown "signature-core.md" %}
