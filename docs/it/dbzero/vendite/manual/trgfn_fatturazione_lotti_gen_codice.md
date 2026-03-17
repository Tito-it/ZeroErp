## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatturazione_lotti_gen_codice`

### 🎯 Scopo Principale

Genera automaticamente `codice` su `vendite.fatturazione_lotti`
quando non valorizzato in INSERT/UPDATE.

---

### Regole principali

* se `NEW.codice` e` `NULL` o vuoto (`btrim=''`) viene assegnato:
  * `script.fn_generate_codice('lotti_fatturazione')`
* se `NEW.codice` e` gia` valorizzato, non viene modificato.

---

### Effetto trigger

* trigger `BEFORE` su tabella lotti fatturazione;
* ritorna `NEW` con eventuale codice generato.

---

{% include-markdown "signature-core.md" %}

