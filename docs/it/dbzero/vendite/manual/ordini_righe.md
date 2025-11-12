## 🧾 Tabella `vendite.ordini_righe`

> 👀 **Vedi anche**
>
>  Approfondimento tabelle: 
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini)  
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)    
> * [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)     
> * [vendite.mv_ddt_ordini](/dbzero/vendite/tabelle/mv_ddt_ordini)      
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)    

---

### 🎯 Scopo Principale

Righe dell’**ordine cliente** con snapshot di descrizione/UoM/IVA e idempotenza della sorgente. Supporta **doppia rappresentazione delle quantità**:

* **Operativa**: `qta_operativa` + `uom_operativa_id` → *sorgente principale* di inserimento.
* **Base**: `qta` (derivata) per calcoli, residui e reporting normalizzato.

`factor_to_base` memorizza il **fattore di conversione snapshot** (operativa → base) applicato alla riga.

---

### 🧠 Regole di dominio (quantità/UoM)

* **Sorgente**: `qta_operativa` + `uom_operativa_id`.
* **Derivazione**: `qta = qta_operativa * factor_to_base` (scala 6). `factor_to_base` è lo **snapshot** della regola valida al momento dell’inserimento (o update coerente).
* **Co‑presenza**: o **entrambi NULL** (non ammesso in produzione) o **entrambi valorizzati**; la validazione è demandata alla trigger `script.trgfn_qta_from_operativa(...)`.
* **Aggiornamenti**: se cambia `qta_operativa` o `uom_operativa_id`, ricalcola `qta` e aggiorna `factor_to_base`. Aggiornare direttamente `qta` non è previsto: eventuali tentativi vanno normalizzati o rifiutati dalla trigger.

---

### 🛡️ Vincoli

* `chk_ordini_v_r_qta_pos` → (da correggere nel DDL: oggi ripete prezzo) **deve validare `qta > 0`**.
* `check_ordini_righe_qta_operativa_pos` → `qta_operativa > 0` (consente `NULL`).
* `chk_ordini_v_r_prezzo_pos` → `prezzo_unitario >= 0`.
* `chk_ordini_v_r_sconto_perc` → tra 0 e 100.
* **UQ**: `(ordine_id, riga_nr)`; **UQ idempotenza**: `(sorgente_tipo_id, sorgente_uid)` filtro `WHERE sorgente_tipo_id IS NOT NULL`.

> 💡 *Suggerimento schema*: aggiungere un `CHECK` di co‑presenza operativa: `(uom_operativa_id IS NULL) = (qta_operativa IS NULL)`.

---

### ⚙️ Trigger & funzioni collegate

* **Delete‑block**: `trg_a10_dlt_block` → vieta hard delete (policy).
* **Quantità da operativa**: `trg_a10_ins_upd_ordini_righe_qta_from_operativa` → invoca `script.trgfn_qta_from_operativa('true','false')` per calcolare `qta` e aggiornare `factor_to_base` a ogni INSERT/UPDATE.
* **Sync stato ordine**: gestito a livello testata dal trigger su fulfillment (vedi doc dedicata), senza usare terminologia “ortogonale”.

---

### 🔄 Interazione con fulfillment / DDT / Fatture

* Il **residuo** ordine si calcola su `qta` (base) per coerenza con stock e confronti multipli.
* In **fulfillment**, la guardia riga↔riga confronta **articolo** e, se presente, la **UoM** coerente; la quantità evasa non può superare il residuo dell’ordine.
* In fatturazione differita da DDT, conviene propagare **entrambe** le quantità (operativa+base) nelle `attivita_fatturabili` per stampa e calcoli coerenti.

---

### 🔍 Tabella note migliorie (dal DDL ricevuto)

1. **BUG vincolo quantità**: `chk_ordini_v_r_qta_pos` oggi replica `prezzo_unitario >= 0` → **correggere** a `qta > 0`.
2. **Co‑presenza operativa**: aggiungere `CHECK ((uom_operativa_id IS NULL) = (qta_operativa IS NULL))` per impedire stati ibridi.
3. **Chiarezza `qta_operativa > 0`**: il `CHECK` attuale passa con `NULL` (comportamento desiderato). Per leggibilità, si può rendere esplicito: `CHECK (qta_operativa IS NULL OR qta_operativa > 0)`.
4. **Deduplicate items**: uniformare `deduplicate_items=True` → `true` (stile SQL coerente con il resto del progetto).

---

### 🔄 Query tipiche

* Righe di un ordine, con totale base:

```sql
SELECT r.*, (r.qta * r.prezzo_unitario) * (1 - COALESCE(r.sconto_perc,0)/100.0) AS imponibile_riga
FROM vendite.ordini_righe r
WHERE r.ordine_id = :ordine_id
ORDER BY r.riga_nr;
```

* Residuo riga (base) con fulfillment:

```sql
SELECT r.id,
       r.qta - COALESCE(SUM(f.qta_evasa),0) AS residuo
FROM vendite.ordini_righe r
LEFT JOIN vendite.ordini_righe_fulfillment f ON f.ordine_riga_id = r.id
WHERE r.ordine_id = :ordine_id
GROUP BY r.id;
```

---

### ✅ Checklist di conformità

* [ ] Trigger **delete‑block** attiva.
* [ ] Trigger **qta_from_operativa** attiva e copre INSERT/UPDATE.
* [ ] `chk_ordini_v_r_qta_pos` **corretto** a `qta > 0`.
* [ ] `factor_to_base` aggiornato a ogni variazione UoM/quantità.
* [ ] UQ progressivo riga per testata.
* [ ] UQ idempotenza import attiva.
* [ ] Co‑presenza operativa garantita.

---

### 📌 Note

* **Niente hard delete**: i flussi applicativi usano annulli/storni.
* Le **API** dovrebbero accettare entrambe le rappresentazioni ma applicare la **priorità all’operativa**; le GET restituiscono entrambe per trasparenza.
* La stampa documenti può mostrare la UoM operativa, lasciando i calcoli in base per confrontabilità.