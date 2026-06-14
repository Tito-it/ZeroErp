## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_guard_pratica_terminale`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.flussi](flussi.md)
> [pratiche.trgfn_flussi_guard_transizione](trgfn_flussi_guard_transizione.md)
> [pratiche.trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)
> [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche)

---
### 🎯 Scopo Principale

Difesa lato DB contro le operazioni su una **pratica conclusa**. Quando la pratica
padre e' in uno **stato terminale**, i suoi flussi sono **congelati**: non possono
essere creati nuovi flussi ne' modificati quelli esistenti (transizioni di stato,
`esito`, `note_esito` o qualunque altro campo operativo).

La protezione FE (scheda in sola lettura, percorso non cliccabile, drawer senza
azioni) e' la prima linea; questo guard garantisce che una chiamata API diretta o
un batch non aggiri la regola.

---

### Definizione di "stato terminale"

Uno stato pratica e' **terminale** quando **non ha alcuna transizione di stato in
uscita attiva** in `config.transizioni_stati_pratiche`. Oggi corrispondono a
`CHIUSA` e `ANNULLATA`. La definizione e' **derivata dalla matrice transizioni**
(non da una lista di codici/id hardcodati): si auto-mantiene se in futuro si
aggiunge/rimuove uno stato terminale o una transizione.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_a10_guard_pratica_terminale_ins_upd` | BEFORE | INSERT OR UPDATE | `pratiche.flussi` |

Fase `_a10_` (guard). L'evento copre tutte le colonne (non `UPDATE OF`): il
congelamento riguarda l'intera riga, quindi anche le modifiche di soli `esito` /
`note_esito` senza cambio di stato. Convive con gli altri guard `_a10_` del flusso
(`esito_completato`, `prerequisiti`, `ripetibilita`, `transizione`).

---

### Regole

1. Risolve lo stato corrente della pratica padre (`NEW.pratica_id`, sempre presente
   per la FK `fk_flussi_pratica`).
2. Se lo stato ha **almeno una transizione di stato in uscita attiva** → la pratica
   e' ancora operabile → **nessun blocco**.
3. Se lo stato e' **terminale** → solleva errore parlante, con codice distinto per
   operazione (creazione vs modifica).
4. Il guard e' su `pratiche.flussi`: l'**atto di rendere terminale la pratica**
   (UPDATE su `pratiche.pratiche`) **non passa di qui** e resta permesso, anche con
   flussi ancora attivi.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO` (490) | INSERT di un flusso su pratica padre terminale. Placeholder: codice stato terminale |
| `PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE` (491) | UPDATE di un flusso (stato, esito, note_esito, ogni campo) su pratica padre terminale. Placeholder: codice stato terminale |

---

### Note operative

* Nessuna cascata pratica → flussi alla terminazione: annullando/chiudendo una
  pratica i flussi attivi restano nel loro stato (congelati). Se in futuro si
  decidesse di portarli automaticamente a uno stato coerente, quella cascata "di
  sistema" andra' resa esente da questo guard.
* Lato BE: mappare i due codici in `pratiche_service` / `error_policies` per un
  messaggio utente coerente sulle rotte di creazione/cambio stato/modifica flusso.
* Test: `db/pgtap/pratiche/test-guard-pratica-terminale-flussi.sql`.

---
{% include-markdown "signature-core.md" %}
