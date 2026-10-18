## 📘 Documentazione Concettuale – Funzione `config.fn_scrivi_profilo_accesso()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 8)

**Scrivere un profilo di accesso con i suoi permessi**: il profilo (per
codice), le aree con il loro livello e le azioni abilitate. Se il profilo
esiste lo aggiorna; aree e azioni, se indicate, le sostituisce.

La usano il backend (il profilo di un reparto) e il provisioning dei dati di
sviluppo (i profili di prova `DEV_LETTURA` e `DEV_OPERATIVO`).

### Regole

* Un codice ha un tipo solo: un profilo non cambia tipo.
* Attivo e «richiede il secondo fattore»: alla nascita attivo e senza
  secondo fattore, se non si dice altro; dopo, restano come sono se non si
  indicano.
* Aree e azioni: se non si passano restano come sono; un elenco (anche
  vuoto) le sostituisce.

### Che cosa non fa

Non lega il profilo a nessuno: per un'identità c'è
[fn_lega_profilo_identita](/dbzero/config/manual/fn_lega_profilo_identita).
Il permesso lo decide il backend.

### Test

`db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
