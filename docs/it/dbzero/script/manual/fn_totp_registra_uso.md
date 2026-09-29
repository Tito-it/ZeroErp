## 📘 Documentazione Concettuale – Funzione `script.fn_totp_registra_uso()`

> 👀 **Vedi anche**
>
> **Perché l'intervallo e non il codice:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

**Un codice vale una volta sola.** All'accesso il backend verifica il codice e
passa il numero del suo intervallo di trenta secondi; il database lo accetta solo
se è **successivo** all'ultimo usato, e lo registra.

---

### Regole

* Lo stesso codice due volte, o un codice di un intervallo già superato: `E_TOTP_PASSO_GIA_USATO`.
* Due accessi simultanei con lo stesso codice: ne passa uno solo (confronto e scrittura sono una cosa sola).
* Si chiama **prima del login**, dopo la password: non c'è ancora un utente in sessione.
* Un codice **sbagliato** non arriva qui: lo rifiuta il backend, che lo conta come una password sbagliata.

---

### Storia

* 2026-09-29 — nasce (`20260929-19`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
