## 📘 Documentazione Concettuale – Funzione `script.fn_check_totp_recovery_hash()`

> 👀 **Vedi anche**
>
> **Chi la usa:** [fn_totp_registra_device](/dbzero/script/funzioni/fn_totp_registra_device) · [fn_totp_rigenera_recovery](/dbzero/script/funzioni/fn_totp_rigenera_recovery)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Dice se un **mazzo nuovo** di codici di recupero ha la forma giusta: almeno un
codice, tutti testi non vuoti, **nessun doppione**. Risponde sì o no, non
solleva.

---

### Regole

* I doppioni contano: consumare un codice lo toglie dal mazzo, e due codici uguali sparirebbero insieme.
* Un mazzo **vuoto** è uno stato normale del dispositivo (codici finiti), ma non un mazzo nuovo accettabile: per questo è un controllo dei verbi e non un vincolo della tabella.

---

### Storia

* 2026-09-29 — nasce (`20260929-16`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
