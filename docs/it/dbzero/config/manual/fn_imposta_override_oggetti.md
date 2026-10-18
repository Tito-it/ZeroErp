## 📘 Documentazione Concettuale – Funzione `config.fn_imposta_override_oggetti()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 9)

**Impostare le eccezioni di un utente sui singoli oggetti** (per esempio:
nessun accesso ai contratti). L'elenco dato **sostituisce** tutte le
eccezioni dell'utente; un elenco vuoto le toglie.

### Regole

* Ogni eccezione nomina l'oggetto, il livello e, se serve, il motivo e il
  periodo di validità.
* Senza data di inizio vale da oggi; con l'inizio esplicitamente vuoto vale
  senza inizio.
* Un oggetto fuori catalogo o riservato al sistema dei permessi è rifiutato
  dal catalogo.

La usano il backend e il provisioning dei dati di sviluppo.

### Test

`db/pgtap/config/test-fn-imposta-override-emittente-attivo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
