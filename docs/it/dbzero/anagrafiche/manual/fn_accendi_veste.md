## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_accendi_veste()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**Accendere un accesso** (una veste) di un utente: dopo che ha accettato un
invito, quando attiva lo shop, o quando il provisioning dei dati di sviluppo
prepara i suoi utenti.

* Accende solo una veste di **quell'utente**, ed eventualmente solo fra le
  vesti indicate.
* Una veste già accesa resta com'è.
* Risponde se la veste c'era.

### Test

`db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
