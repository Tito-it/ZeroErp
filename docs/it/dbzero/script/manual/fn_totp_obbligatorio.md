## 📘 Documentazione Concettuale – Funzione `script.fn_totp_obbligatorio()`

> 👀 **Vedi anche**
>
> **Le due fonti:** [config.credenziali](/dbzero/config/tabelle/credenziali) · [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
> **Il dispositivo:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Risponde a una domanda sola: **questa persona deve usare il secondo fattore, e
perché?** Il backend la chiede al login e quando decide se portare la persona
alla configurazione del telefono; il perché serve al frontend per spiegarlo.

Le ragioni sono due, e basta una:

* `CREDENZIALE` — un amministratore l'ha imposto a questa persona;
* `PROFILO` — la persona ha un profilo segnato come privilegiato, o è
  `SUPER_ADMIN` (che il segno l'ha sempre).

Nessuna delle due: la risposta è «no» (`false`, motivo vuoto).

---

### Regole

* Vale **per tutte le porte**: la persona ha una password sola. Per questo guarda i profili di tutte le vesti, e il `SUPER_ADMIN` anche quando entra dal portale — a differenza di [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin), che fuori dal gestionale si spegne.
* Il `SUPER_ADMIN` non è fra i profili che [fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) restituisce (è un bypass, non un profilo di permessi): lo chiede a [fn_is_super_admin_account](/dbzero/script/funzioni/fn_is_super_admin_account).
* Se valgono entrambe le ragioni, il motivo è `CREDENZIALE`.
* Una persona che non esiste riceve «no»: è una lettura.
* Gira con i diritti del proprietario: la risposta non deve dipendere da che cosa vede chi la chiede (al login non c'è ancora un contesto).

---

### Storia

* 2026-09-29 — nasce (`20260929-13`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
