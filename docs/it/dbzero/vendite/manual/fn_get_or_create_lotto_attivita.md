## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_lotto_attivita`

> 👀 **Vedi anche**
>
> • [vendite.fn_resolve_lotto_utility_emittente](/dbzero/vendite/funzioni/fn_resolve_lotto_utility_emittente)  
> • [vendite.fn_set_attivita_lotto_stato](/dbzero/vendite/funzioni/fn_set_attivita_lotto_stato)  
>
---

### 🎯 Scopo Principale

(latest review 22-02-2026)
Recupera un lotto `attivita_fatturabili_lotti` esistente (per `id` o `lock_batch_id`) oppure lo crea se assente, applicando le stesse regole di coerenza del dominio fatturazione.

---

### 🔧 Regole applicate

* Valida coerenza tra `billing_account_id` e `utility_id`.
* Valida coerenza tra `billing_account_id` ed `emittente_soggetto_ruolo_id`.
* Risolve fallback emittente tramite helper condiviso `fn_resolve_lotto_utility_emittente`.
* Blocca il riuso lotto solo con combinazione `stato_lotto='IN_ESECUZIONE'` e `stato_operativo='CHIUSO'`.
* In creazione inizializza `stato_lotto='IN_ESECUZIONE'` e `stato_operativo='APERTO'`.

---

### ✅ Output

Ritorna l'`id` del lotto attività esistente o appena creato.

---

{% include-markdown "signature-core.md" %}
