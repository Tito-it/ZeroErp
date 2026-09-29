## 📘 Documentazione Concettuale – Funzione `script.fn_is_super_admin_account()`

> 👀 **Vedi anche**
>
> **Chi la usa:** [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) · [fn_totp_obbligatorio](/dbzero/script/funzioni/fn_totp_obbligatorio)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Dice se una persona ha il profilo `SUPER_ADMIN` **sulla sua credenziale**, senza
guardare da quale porta sta entrando.

---

### Regole

* [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) fa due domande: «la sessione è nel gestionale?» e «la persona è SUPER_ADMIN?». Per i permessi servono tutte e due; per l'obbligo del secondo fattore solo la seconda, perché la password è una sola e vale anche nel portale. Questa funzione è la seconda domanda, da sola.
* Non è la domanda dell'anti-lockout ([fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo)), che conta tutti gli amministratori raggiungibili.

---

### Storia

* 2026-09-29 — estratta dal corpo di `fn_is_super_admin` (`20260929-10`, `-11`), alla seconda occorrenza. Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
