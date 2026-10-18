## 📘 Documentazione Concettuale – Funzione `config.fn_imposta_emittente_attivo()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 9)

**Impostare l'azienda su cui lavora un utente** (l'emittente attivo). Ogni
conferma, anche della stessa azienda, resta nella storia.

⚠️ Che l'utente possa lavorare su quell'azienda lo controlla oggi solo il
backend, prima di chiamare: è una regola senza un controllo sulla tabella
(debito dichiarato nel brief).

La usano il backend e il provisioning dei dati di sviluppo.

### Test

`db/pgtap/config/test-fn-imposta-override-emittente-attivo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
