## Documentazione – Funzione `script.fn_subentro_cliente()`

> Vedi anche
>
**Guide correlate:**
>
[Guida – Generazione di un Cliente](/guide/generazione-cliente)
> [Guida – Gestione delle Istanze Utility](/guide/gestione-delle-istanze-utility)
> [Glossario termini utility](/guide/glossario/glossario-utility)
>
**Tabelle e funzioni collegate:**
>
[anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)
> [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
> [`anagrafiche.trgfn_clienti_set_parent_istanza`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza)
> [`anagrafiche.trgfn_clienti_sync_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp)
> [`anagrafiche.trgfn_clienti_sync_stato_pdp`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp)
> [`script.fn_disdetta_cliente`](/dbzero/script/funzioni/fn_disdetta_cliente) — cessazione senza subentro

---
### 🎯 Scopo Principale
(latest review 01-03-26)

La funzione `script.fn_subentro_cliente()` **chiude il cliente attualmente attivo su un PDP** prima che venga creato un nuovo cliente sullo stesso punto di prelievo.

In parole semplici: quando un intestatario cambia (subentro/voltura), questa funzione si occupa di "fare spazio" chiudendo il contratto del cliente uscente, in modo che il nuovo possa essere attivato senza violare il vincolo di non sovrapposizione.

### Cosa fa e cosa NON fa

**Fa:**

* Cerca il cliente attivo piu recente sul PDP indicato
* Lo chiude impostando `data_chiusura` e stato `CH` (chiuso)
* Ritorna l'`id` del cliente chiuso (o NULL se non c'era nessuno da chiudere)

**Non fa:**

* Non crea la nuova istanza
* Non crea il nuovo billing account
* Non crea il nuovo cliente

La creazione del nuovo ciclo (istanza → BA → cliente) e a carico del **chiamante** (frontend, API o orchestrator Django). Questa separazione e voluta: la funzione DB si occupa della logica pura (chiusura sicura), mentre l'orchestrazione complessa sta in Django.

---

### Firma

```sql
script.fn_subentro_cliente(
    p_pdp_id           BIGINT,
    p_data_attivazione DATE
) RETURNS BIGINT
```

* **`p_pdp_id`** — il PDP su cui sta avvenendo il subentro
* **`p_data_attivazione`** — la data di attivazione del nuovo cliente. La funzione calcola `data_chiusura = p_data_attivazione - 1 giorno` per il cliente uscente

**Valore di ritorno:** `id` del cliente chiuso, oppure `NULL` se non c'era nessun cliente attivo (prima attivazione sul PDP).

---

### Logica interna

#### 1. Validazione parametri

Se `p_pdp_id` o `p_data_attivazione` sono NULL, la funzione solleva un errore.

#### 2. Recupero stato CH (chiuso)

Cerca in `config.stati_cliente` il record con `codice_interno = 'CH'`. Se non lo trova, errore di configurazione.

#### 3. Ricerca del cliente da chiudere

Cerca il cliente piu recente sul PDP con queste condizioni:

* `pdp_id = p_pdp_id`
* stato diverso da `AN` (annullato)
* `data_attivazione` valorizzata e precedente a `p_data_attivazione`
* `data_chiusura` NULL o >= `p_data_attivazione` (periodo ancora aperto)

La ricerca usa `FOR UPDATE` per bloccare il record e prevenire aggiornamenti concorrenti.

#### 4. Nessun cliente trovato → prima attivazione

Se non c'e nessun cliente da chiudere, la funzione ritorna `NULL`. Il PDP e libero per la prima attivazione.

#### 5. Chiusura del cliente precedente

```sql
UPDATE anagrafiche.clienti
   SET data_chiusura    = p_data_attivazione - INTERVAL '1 day',
       stato_cliente_id = v_stato_chiuso_id
 WHERE id = v_cliente_precedente_id;
```

I trigger in cascata si occupano automaticamente di:

* Ricalcolare `periodo` → `[data_attivazione, data_chiusura)` (tramite `trgfn_clienti_set_periodo`)
* Aggiornare lo stato del PDP → DISPONIBILE (tramite `trgfn_clienti_sync_stato_pdp`)
* Storicizzare il record e aggiornare i campi audit

---

### Utilizzo tipico

La funzione va chiamata come primo passo in una sequenza transazionale:

```sql
BEGIN;

-- 1. Chiudi il cliente precedente (se esiste)
SELECT script.fn_subentro_cliente(123, '2026-04-01');

-- 2. Crea la nuova istanza
INSERT INTO anagrafiche.istanze_utilities (...) VALUES (...) RETURNING id;

-- 3. Crea il billing account
INSERT INTO anagrafiche.billing_account (...) VALUES (...) RETURNING id;

-- 4. Crea il nuovo cliente
INSERT INTO anagrafiche.clienti (...) VALUES (...);

COMMIT;
```

Se un qualsiasi passo fallisce, l'intera transazione viene annullata.

---

### Casi d'uso

#### Caso 1 — Subentro con cliente attivo

* Esiste un cliente ATTIVO sul PDP, attivato il 01-01-2025
* Si chiama `fn_subentro_cliente(pdp_id, '2026-04-01')`
* Il cliente precedente viene chiuso con `data_chiusura = 2026-03-31`, stato `CH`
* Il PDP torna DISPONIBILE (poi tornera ATTIVO quando si inserisce il nuovo cliente)

#### Caso 2 — Prima attivazione

* Nessun cliente attivo sul PDP
* La funzione ritorna `NULL`, nessuna modifica
* Il chiamante procede con la creazione diretta

---

### Errori intercettati

* `p_pdp_id` NULL → errore
* `p_data_attivazione` NULL → errore
* Stato `CH` non trovato in `config.stati_cliente` → errore di configurazione

---

### Relazione con `fn_disdetta_cliente`

|       | `fn_subentro_cliente`                            | `fn_disdetta_cliente`                          |
| ----- | ------------------------------------------------ | ---------------------------------------------- |
| Scopo | Chiudere il cliente uscente prima di un subentro | Cessare il servizio senza subentro             |
| Input | PDP + data attivazione nuovo                     | Cliente + data cessazione                      |
| Dopo  | Si crea un nuovo ciclo (istanza+BA+cliente)      | Il PDP resta DISPONIBILE, nessun nuovo cliente |
| BA    | Il BA del vecchio cliente non viene toccato      | Il BA non viene toccato (policy)               |

---

{% include-markdown "signature-core.md" %}
