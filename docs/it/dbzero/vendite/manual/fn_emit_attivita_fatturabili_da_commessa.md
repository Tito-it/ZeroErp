## 📘 Documentazione Concettuale – Funzione `vendite.fn_emit_attivita_fatturabili_da_commessa`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Esegue il pull da `commesse_attivita` verso `attivita_fatturabili` (step 0 pipeline attività fatturabili).

---

### Regole applicate

* La ROOT source della commessa e` obbligatoria (`commesse_sorgenti`).
* La sorgente delle righe AF e` sempre `COMMESSA`.
* `segment_key` viene mappata deterministicamente in UUID per `attivita_fatturabili.sorgente_uid`.
* `attivita_fatturabili.sorgente_riga` viene valorizzato con `commesse_attivita.id`
  (coerenza con trigger polimorfo `key_selector='id'`).
* Idempotenza gestita tramite chiave sorgente (`COMMESSA + segment_key-hash`).
* Se trova una riga AF gia` fatturata, blocca l'aggiornamento con errore.
* Propaga `commessa_id`, `commessa_attivita_id` e `prezzo_bloccato`.
* Aggiorna `commesse_attivita.stato_emissione = 'EMESSA'` per le righe emesse.

---

### Output

Ritorna contatori:

* `total_candidate`
* `inserted_rows`
* `updated_rows`
* `skipped_rows`

---

{% include-markdown "signature-core.md" %}
