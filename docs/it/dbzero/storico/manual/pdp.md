## 📘 Documentazione concettuale - Tabella  `storico.pdp`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [`anagrafiche.pdp`](/dbzero/anagrafiche/tabelle/pdp)   
>
**Approfondimento funzioni:**
>
• [`script.trgfn_storico_generic`](/dbzero/script/funzioni/trgfn_storico_generic)   
> • [`dbops.trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   


---
### 🎯 Scopo Principale
`storico.pdp` conserva la **timeline** dei Punti di Prelievo: per ogni modifica allo stato corrente (`anagrafiche.pdp`) registra uno **snapshot JSONB**, la **tipologia di operazione** (`I`,`U`,`D`), il **tx_id** e la **finestra di validità** (`valid_from`, `valid_to`).
È di fatto una **SCD Type 2** (Slowly Changing Dimension) specializzata per i PDP.

---

### 2. Struttura e colonne

* **PK**: `id BIGINT IDENTITY`
* **FK**: `pdp_id BIGINT NOT NULL` → `anagrafiche.pdp(id)` (**ON DELETE CASCADE**)
* **`tipo_operazione CHAR(1) NOT NULL`** ∈ {`I`,`U`,`D`}
* **`snapshot JSONB NOT NULL`** → cattura lo stato completo della riga base al momento dell’evento
* **`tx_id UUID NOT NULL`** → correlazione transazionale con la base
* **`valid_from TIMESTAMPTZ NOT NULL DEFAULT now()`**
* **`valid_to TIMESTAMPTZ NULL`** (NULL = **record “aperto”/corrente**)
* **`data_insert TIMESTAMPTZ NOT NULL DEFAULT now()`**, **`user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER`**

**Indici**

* `idx_storico_pdp_pdp_id (pdp_id)`
* `idx_storico_pdp_open (pdp_id) WHERE valid_to IS NULL`

---

### 3. Popolamento e trigger

* **UPDATE/DELETE**: `anagrafiche.pdp` aggancia `script.trgfn_storico_generic('pdp_id')` per creare le righe di storico su variazione/cancellazione.
* **INSERT**: dal DDL sorgente non risulta un trigger specifico. Per una timeline completa si consiglia un **trigger `AFTER INSERT`** alla creazione del PDP che inserisca una riga con `tipo_operazione='I'`, `valid_from=now()`, `valid_to=NULL` e `snapshot=to_jsonb(NEW)`.

**Regola temporale**

* Ad ogni **UPDATE**: chiudere la riga “aperta” precedente (`valid_to = now()`) e aprire una nuova riga `U` con `valid_from = now()`.
* Ad ogni **DELETE**: chiudere l’eventuale riga “aperta” e inserire una riga `D` con `valid_from = valid_to = now()`.

---

### 4. Esempi d’uso

* **Timeline intera di un PDP**

```sql
SELECT *
FROM storico.pdp
WHERE pdp_id = :id
ORDER BY valid_from;
```

* **Stato corrente (record aperti)**

```sql
SELECT *
FROM storico.pdp
WHERE valid_to IS NULL;
```

* **Ricostruzione stato al tempo T**

```sql
SELECT *
FROM storico.pdp
WHERE pdp_id = :id
  AND valid_from <= :timestamp
  AND (valid_to  >  :timestamp OR valid_to IS NULL)
ORDER BY valid_from DESC
LIMIT 1;
```

---

### 5. Best practice

* **Allineare tx_id** tra base e storico (usa `dbops.trgfn_tx_id_managed()` in base).
* Mantenere **un solo record “aperto”** per PDP (`valid_to IS NULL`).
* Aggiungere il trigger **AFTER INSERT** per completezza della timeline.
* Verificare periodicamente che non esistano **sovrapposizioni** di periodi per lo stesso `pdp_id`.

---

### 6. Errori frequenti

* Timeline incompleta (manca l’evento `I`).
* Più righe “aperte” per lo stesso PDP (dimenticato `valid_to` in un update storico).
* `tx_id` NULL → trigger di gestione non attivo/assente.

---

{% include-markdown "signature-core.md" %}
