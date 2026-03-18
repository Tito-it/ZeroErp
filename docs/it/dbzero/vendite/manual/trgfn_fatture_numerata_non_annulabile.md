## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_fatture_numerata_non_annulabile`
### 🎯 Scopo Principale
Blocca il passaggio a stato `ANNULLATA` per una fattura gia` numerata.

---

### Regole principali

* il controllo scatta solo se cambia `stato_doc_fiscale_id`;
* risolve se il nuovo stato e` `ANNULLATA` (`config.stati_doc_fiscale.codice_interno`);
* considera fattura numerata quando `numero` e` valorizzato;
* se `ANNULLATA` + numerata -> errore `E_FATTURA_NON_ANNULLABILE`.

---

### Effetto trigger

* trigger `BEFORE UPDATE` su `vendite.fatture`;
* impedisce la modifica non consentita con errore applicativo.

---

{% include-markdown "signature-core.md" %}

