## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_lotto`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_create_fatturazione_lotto](/dbzero/vendite/funzioni/fn_create_fatturazione_lotto)     
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_get_or_create_lotto()`** recupera un lotto esistente
(o lo crea se assente) garantendo la coerenza dei parametri di richiesta.

---

### 🔧 Regole applicate

* `tipo_lotto` obbligatorio (MASSIVO | GIORNALIERO).
* Se `p_lotto_id` e` valorizzato:
  * verifica l’esistenza del lotto;
  * valida la coerenza di `competenza_mese`, `utility_id`, `tipo_doc_fiscale_id`, `billing_account_id`, `emittente_soggetto_ruolo_id`, `tipo_lotto`.
  * blocca il riuso solo se il lotto e` in `IN_ESECUZIONE` **e** `stato_operativo <> APERTO`.
* Se `p_lock_batch_id` e` valorizzato e non esiste un lotto, ne crea uno nuovo.
* Se non e` presente nessun riferimento, delega a `fn_create_fatturazione_lotto`.
* La risoluzione emittente segue il fallback di `fn_create_fatturazione_lotto` (input esplicito, mapping BA, fallback su emittente unico attivo).

---

### ✅ Output

Ritorna l’`id` del lotto esistente o creato.

---

{% include-markdown "signature-core.md" %}
