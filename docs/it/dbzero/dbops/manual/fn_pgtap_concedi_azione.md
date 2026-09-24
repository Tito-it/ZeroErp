## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_concedi_azione`

> 👀 **Vedi anche**
>
> • [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il guard che rende necessario concedere l'azione
> • [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'operatore di fixture, che nasce senza azioni
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-magazzino-verbi-con-permesso` (§3.2)

---
### 🎯 Scopo Principale

(scritta il 2026-09-24)

**Fixture pgTAP: concede a un utente un'azione di processo**, con un'eccezione
utente (`config.user_override_azioni`) abilitata, valida da oggi e senza
scadenza: la stessa forma che scrive il pannello di amministrazione. Restituisce
l'id dell'eccezione.

Serve ai test dei verbi che applicano un'azione con `script.fn_guard_azione`:
l'operatore di `fn_pgtap_crea_emittente_operatore` è tecnico, non super admin, e
non ha azioni. Il permesso si **costruisce** nel test, non si cerca nei dati.

```sql
PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino');
```

* **Idempotente**: se l'eccezione esiste già, la riabilita e la riapre da oggi.
* **Azione inesistente**: `RAISE`, perché è la fixture a sbagliare.
* **Azione disattivata**: la rifiuta il trigger della tabella, ed è giusto che il
  test lo veda.
* Scrive come l'applicazione (`SECURITY INVOKER`), che su quella tabella ha
  `INSERT`.

---

### Storia

* 2026-09-24 — nasce con il brief dei verbi di magazzino (`20260924-39`).

---

{% include-markdown "signature-core.md" %}
