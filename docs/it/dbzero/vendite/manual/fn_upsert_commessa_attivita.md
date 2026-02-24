## 📘 Documentazione Concettuale – Funzione `vendite.fn_upsert_commessa_attivita`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Inserisce o aggiorna una riga `commesse_attivita` con idempotenza su `(commessa_id, segment_key)`.

---

### 🔧 Regole applicate

* `segment_key` obbligatoria (chiave tecnica idempotente).
* Upsert consentito solo su commesse non finali (`CHIUSA`/`ANNULLATA` bloccano).
* Se la riga esiste ed e` gia` emessa (`stato_emissione <> NON_EMESSA`) l'update e` bloccato.
* Normalizza `competenza_mese` al primo giorno del mese.
* Accetta quantita/prezzi negativi; blocca solo `quantita = 0` e `prezzo_snapshot` nullo.
* Traccia classificazione operativa con:
  `tipo_movimento` (`NORMALE`/`RETTIFICA`) e `tipo_consumo` (`ACCONTO`/`CONGUAGLIO`/`STORNO`) in `meta`.
* Mantiene i campi snapshot prezzo/stato per il passaggio successivo verso `attivita_fatturabili`.

---

### ✅ Output

Ritorna `id` della riga in `vendite.commesse_attivita`.

---

{% include-markdown "signature-core.md" %}
