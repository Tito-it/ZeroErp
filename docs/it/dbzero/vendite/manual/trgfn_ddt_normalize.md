## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_normalize()`

> 👀 **Vedi anche**
>
• [vendite.ddt](/dbzero/vendite/tabelle/ddt)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_ddt_normalize()` normalizza la testata del DDT
su `INSERT`: completa i campi temporali minimi ed **eredita billing/utility/valuta/
emittente dall'ordine sorgente**.

---

### Regole principali (in ordine)

1. **Anno/data**: se `numero` e` valorizzato e `anno`/`data` mancano → anno corrente / `CURRENT_DATE`.
2. **Eredita` da ordine sorgente** (DDT da ordine): se `sorgente_tipo_id`/`sorgente_uid`
   sono valorizzati e la sorgente e` **`ORDINE_VENDITA`** (lookup per `codice_interno`,
   immutabile), eredita dall'ordine i campi mancanti — `billing_account_id`, `utility_id`,
   `valuta_id`, **`emittente_fiscale_id`**.
3. **Fallback emittente** (standalone): se dopo il punto 2 `emittente_fiscale_id` e` ancora
   `NULL` ed esiste un `billing_account_id`, lo risolve via
   `anagrafiche.fn_get_emittente_fiscale_pk` (convenzione PK).

Non altera mai campi gia` valorizzati (`COALESCE`).

---

### Note

* La sorgente si risolve per **`codice_interno`** (immutabile), non per `codice` (mutabile) —
  coerente con `fn_list_ddt_da_pushare`. E` la condizione per cui `fn_genera_ddt_da_ordine`
  deve scrivere `sorgente_tipo_id = ORDINE_VENDITA` (con `DDT_VENDITA` l'eredita` non scatta).
* L'`emittente_fiscale_id` ereditato e` la chiave di **scope RLS** (§15): `NOT NULL`, garantito
  su ogni DDT; guard di scrittura `trgfn_guard_emittente_scope`; policy `rls_ddt_ef_whitelist`.

---

### Utilizzo

Trigger `trg_ddt_normalize_ins_upd` (`BEFORE INSERT/UPDATE`) su `vendite.ddt`.

---

{% include-markdown "signature-core.md" %}
