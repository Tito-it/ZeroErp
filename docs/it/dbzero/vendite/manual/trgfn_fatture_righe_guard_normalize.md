## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_righe_guard_normalize`
### 🎯 Scopo Principale
Normalizza i dati di riga fattura su inserimento/aggiornamento:
* eredita `dest_billing_account_id` dalla testata se assente;
* allinea lo snapshot `iva_natura` in base a `config.iva`.

---

### Regole principali

* se `NEW.dest_billing_account_id` e` `NULL`, usa `fatture.billing_account_id`;
* se `NEW.iva_id` e` valorizzato, copia in `NEW.iva_natura` il codice
  da `config.iva_natura` collegato alla master IVA;
* in UPDATE, se cambia manualmente `iva_natura` a parita` di `iva_id`,
  riallinea comunque lo snapshot dalla master.

---

### Effetto trigger

* trigger `BEFORE INSERT OR UPDATE` su `vendite.fatture_righe`;
* mantiene coerenza tra testata/riga e snapshot natura IVA.

---

{% include-markdown "signature-core.md" %}

