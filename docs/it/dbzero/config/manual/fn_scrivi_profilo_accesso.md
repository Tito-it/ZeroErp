## 📘 Documentazione Concettuale – Funzione `config.fn_scrivi_profilo_accesso()`

> **Ultimo aggiornamento**: 26 novembre 2026

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 8)

**Scrivere un profilo di accesso con i suoi permessi**: il profilo (per
codice), le aree con il loro livello e le azioni abilitate. Se il profilo
esiste lo aggiorna; aree e azioni, se indicate, le sostituisce.

È il verbo del SUPER_ADMIN: la usa il backend per il profilo di un reparto. Il provisioning dei dati di
sviluppo (i profili di prova `DEV_LETTURA` e `DEV_OPERATIVO`) chiama direttamente la sua primitiva,
[fn_applica_scrivi_profilo_accesso](/dbzero/config/manual/fn_applica_scrivi_profilo_accesso), perché gira senza
un utente in sessione.

### Regole

* Il profilo si cerca col codice **normalizzato**
  ([script.fn_codice_normalizzato](/dbzero/script/manual/fn_codice_normalizzato)): il codice si
  salva in maiuscolo, quindi `reparto_x` e `REPARTO_X` sono lo stesso profilo, e una seconda
  chiamata col codice in minuscolo aggiorna quello che c'è invece di provare a crearne un altro
  (correzione del 4 novembre 2026, su segnalazione del backend).
* Un codice ha un tipo solo: un profilo non cambia tipo.
* Attivo e «richiede il secondo fattore»: alla nascita attivo e senza
  secondo fattore, se non si dice altro; dopo, restano come sono se non si
  indicano.
* Aree e azioni: se non si passano restano come sono; un elenco (anche
  vuoto) le sostituisce.

### Che cosa non fa

Non lega il profilo a nessuno: per un'identità c'è
[fn_lega_profilo_identita](/dbzero/config/manual/fn_lega_profilo_identita).

### ⛔ Il permesso

È `SECURITY DEFINER` col `search_path` fissato, e nella prima riga chiede il SUPER_ADMIN all'utente di sessione
(`script.fn_guard_super_admin`): un altro operatore, o nessun utente, riceve `E_PERMESSO_NEGATO`. È lo stesso
controllo dell'endpoint. Le regole del profilo stanno nella primitiva, che l'applicazione non esegue; le tabelle
dei profili sono in sola lettura per l'applicazione.

### Test

`db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
