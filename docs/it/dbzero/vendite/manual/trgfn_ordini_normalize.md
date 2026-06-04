## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_normalize()`

> 👀 **Vedi anche**
>
• [vendite.ordini](/dbzero/vendite/tabelle/ordini)  

---
### 🎯 Scopo Principale
La trigger function `vendite.trgfn_ordini_normalize()` normalizza i campi minimi
dell’ordine **in fase di creazione**: completa anno/data quando il `numero` è
presente ed eredita il `fatturazione_trigger` dal billing account.

---

### Regole principali

Tutte le regole operano **solo su `INSERT`**:

* se `numero` è valorizzato:
  * imposta `anno` all’anno corrente se nullo/0;
  * imposta `data` a `CURRENT_DATE` se nulla;
  * non altera i valori se già compilati.
* se `billing_account_id` è valorizzato: eredita `fatturazione_trigger` da
  `anagrafiche.billing_account.fatturazione_ordini` (vedi
  [vendite.ordini](/dbzero/vendite/tabelle/ordini) §"Fatturazione: ordine vs DDT").
  Può essere sovrascritto manualmente per singolo ordine.

---

### Nota — solo INSERT (DB-ORD-LOCK, 2026-06-04)

Fino al 2026-06-04 la funzione ri-ereditava `fatturazione_trigger` anche su
`UPDATE`, quando cambiava `billing_account_id`. Da quando il **cliente è
immutabile post-creazione** (`billing_account_id`/`soggetto_ruolo_id` lockati,
codice `E_ORD_CLIENTE_IMMUTABILE` — vedi [vendite.ordini](/dbzero/vendite/tabelle/ordini)
§"Immutabilità cliente"), quel ramo `UPDATE` è **irraggiungibile** (il lock in
fase `a10` scatta prima di questo trigger) ed è stato **rimosso**: cambiare il BA
non è più possibile su un ordine esistente, quindi non c'è nulla da ri-propagare.

---

### Utilizzo

Usata come trigger `BEFORE INSERT/UPDATE` su `vendite.ordini`
(`trg_ordini_normalize_ins_upd`); la logica è attiva **solo sul ramo INSERT**, su
`UPDATE` è un no-op.

---

{% include-markdown "signature-core.md" %}
