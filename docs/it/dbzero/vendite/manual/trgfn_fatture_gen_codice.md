## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_gen_codice`

### 🎯 Scopo Principale

Assegna automaticamente il numero fattura quando il campo `numero`
non e` valorizzato.

---

### Regole principali

* se `NEW.numero` e` `NULL` o `0`, viene impostato:
  * `script.fn_generate_codice('fatture')`
* se `NEW.numero` e` gia` valorizzato, non viene modificato.

---

### Effetto trigger

* trigger `BEFORE` su `vendite.fatture`;
* ritorna `NEW` con eventuale numerazione assegnata.

---

{% include-markdown "signature-core.md" %}

