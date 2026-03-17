## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_documento_canale_stato`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Gestisce in modo uniforme la transizione stato dei canali fatturabili per documento sorgente.

---

### Regole applicate

* chiave sorgente obbligatoria: `sorgente_tipo_id` + `sorgente_uid`;
* `canale_codice` deve essere:
  un codice attivo di `config.sorgenti.codice` oppure `DIRETTO`;
* stati ammessi: `APERTO`, `CONSUMATO`, `BLOCCATO`;
* se `stato_canale='BLOCCATO'` richiede `motivo_blocco`;
* `target_sorgente_tipo_id` e `target_sorgente_uid` devono essere valorizzati a coppia;
* quando imposta `APERTO` blocca automaticamente eventuali altri canali `APERTO`
  sulla stessa sorgente documento.

---

### Output

Ritorna `id` della riga canale inserita/aggiornata.

---

{% include-markdown "signature-core.md" %}
