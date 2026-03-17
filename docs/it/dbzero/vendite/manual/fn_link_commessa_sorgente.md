## 📘 Documentazione Concettuale – Funzione `vendite.fn_link_commessa_sorgente`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Collega la ROOT source a una commessa in modo idempotente e coerente.

---

### Regole applicate

* Una commessa puo` avere una sola ROOT (`ruolo_link='ROOT'`).
* Se ROOT gia` presente, deve coincidere con la sorgente in ingresso.
* `sorgente_uid` obbligatoria e non vuota.
* In caso di mismatch sulla ROOT esistente, la funzione alza errore bloccante.

---

### Output

Ritorna `id` del record in `vendite.commesse_sorgenti`.

---

{% include-markdown "signature-core.md" %}
