## 🧾 Tabella `vendite.ordini_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle: 
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)  
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)    
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)     
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)    

---
### 🎯 Scopo Principale
Righe dell’**ordine cliente** con snapshot di descrizione/UoM/IVA e idempotenza della sorgente. Supporta **doppia rappresentazione delle quantità**:

* **Operativa**: `qta_operativa` + `uom_operativa_id` → *sorgente principale* di inserimento.
* **Base**: `quantita` (derivata) per calcoli, residui e reporting normalizzato.

`factor_to_base` memorizza il **fattore di conversione snapshot** (operativa → base) applicato alla riga.

---

### Regole di dominio (quantità/UoM)

* **Sorgente**: `qta_operativa` + `uom_operativa_id`.
* **Derivazione**: `quantita = qta_operativa * factor_to_base` (scala 6). `factor_to_base` è lo **snapshot** della regola valida al momento dell’inserimento (o update coerente).
* **Co‑presenza**: o **entrambi NULL** o **entrambi valorizzati**; ora garantita sia dalla trigger `script.trgfn_qta_from_operativa(...)` sia dal `CHECK chk_ordini_v_r_uom_qta_operativa_copres` (`20260603-11`).
* **Aggiornamenti**: se cambia `qta_operativa` o `uom_operativa_id`, ricalcola `quantita` e aggiorna `factor_to_base`. Aggiornare direttamente `quantita` non è previsto: eventuali tentativi vanno normalizzati o rifiutati dalla trigger.

---

### Vincoli

* `chk_ordini_v_r_qta_pos` → **`quantita > 0`** ✅ corretto in `20260603-11` (in precedenza replicava per errore `prezzo_unitario >= 0`, guard sulla quantità mancante).
* `chk_ordini_v_r_uom_qta_operativa_copres` → `(uom_operativa_id IS NULL) = (qta_operativa IS NULL)` ✅ aggiunto in `20260603-11` (co‑presenza operativa).
* `check_ordini_righe_qta_operativa_pos` → `qta_operativa > 0` (consente `NULL`).
* `chk_ordini_v_r_prezzo_pos` → `prezzo_unitario >= 0` (l'omaggio è `quantita > 0` + `prezzo_unitario = 0`).
* `chk_ordini_v_r_sconto` → `sconto_percentuale` tra 0 e 100 (rinominato da `chk_ordini_v_r_sconto_perc`, unificazione 2026-06-05).
* **UQ**: `(ordine_id, riga_nr)`; **UQ idempotenza**: `(sorgente_tipo_id, sorgente_uid)` filtro `WHERE sorgente_tipo_id IS NOT NULL`.

---

### Trigger & funzioni collegate

* **Righe solo in bozza — sul DELETE**: `trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_dlt`
  → su un ordine fuori da DRAFT nessuna riga si toglie (`E_RIGA_DOC_NON_BOZZA`;
  building block [`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
  2026-09-22). ⚠️ INSERT e UPDATE restano **aperti di proposito**:
  `data_consegna_confermata` si decide alla conferma e può cambiare dopo, e il
  verbo che la governa non esiste ancora (`PROJECT_CONTEXT`, «la promessa di
  consegna»). Quando ci sarà, la porta si allarga con un `CREATE OR REPLACE
  TRIGGER`.
* **Delete‑block**: `trg_ordini_righe_a10_block_dlt` → traduce in una frase il
  rifiuto di togliere una riga con legami a valle (fulfillment, resi); a rifiutare
  sono le FK ([`trgfn_dlt_block_ordrig_ddtrig`](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig)).
* **Data confermata ferma su una riga spedita**: `trg_ordini_righe_a10_guard_data_consegna_spedita_upd`
  → la `data_consegna_confermata` di una riga già partita con un DDT uscito dalla
  bozza, anche per una parte, non cambia più (`E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA`):
  la data di consegna si scrive prima di spedire. Il guard solleva il primo motivo di
  [`script.fn_check_ordine_riga_data_consegna_confermata`](/dbzero/script/funzioni/fn_check_ordine_riga_data_consegna_confermata),
  la stessa check della colonna `data_consegna_confermata_blocco` di
  [vw_ordini_righe_dettaglio](/dbzero/vendite/views/vw_ordini_righe_dettaglio)
  (2026-10-11, `brief-db-date-consegna-righe-in-blocco` D-7).
* **Quantità da operativa**: `trg_a10_ins_upd_ordini_righe_qta_from_operativa` → invoca `script.trgfn_qta_from_operativa('true','false')` per calcolare `quantita` e aggiornare `factor_to_base` a ogni INSERT/UPDATE.
* **Natura di vendita** (dal 2026-10-13, brief-db-articoli-ammessi-per-documento A-4):
  `natura_vendita_id` (NOT NULL) è la natura con cui la riga è stata venduta. La scrive
  [`script.trgfn_righe_natura_vendita`](/dbzero/script/manual/trgfn_righe_natura_vendita) (`…_a10_natura_vendita_ins_upd`, modo CHIAMANTE): quella portata dal verbo che
  copia la riga, `fn_push_preventivo_a_ordine` porta quella della riga di preventivo, altrimenti quella dell'articolo; si riscrive solo quando cambia
  l'articolo. A mano non si cambia (`…_a10_lock_columns_upd`, generato da
  `dbops.automation_lock_columns`, `E_RIGA_NATURA_VENDITA_IMMUTABILE`).
* **Sync stato ordine**: gestito a livello testata dal trigger su fulfillment (vedi doc dedicata), senza usare terminologia “ortogonale”.

---

### Interazione con fulfillment / DDT / Fatture

* Il **residuo** ordine si calcola su `quantita` (base) per coerenza con stock e confronti multipli.
* In **fulfillment**, la guardia riga↔riga confronta **articolo** e, se presente, la **UoM** coerente; la quantità evasa non può superare il residuo dell’ordine.
* In fatturazione differita da DDT, conviene propagare **entrambe** le quantità (operativa+base) nelle `attivita_fatturabili` per stampa e calcoli coerenti.

---

### Tabella note migliorie (dal DDL ricevuto)

1. ✅ **RISOLTO (`20260603-11`)** — BUG vincolo quantità: `chk_ordini_v_r_qta_pos` replicava `prezzo_unitario >= 0`; corretto a `quantita > 0`.
2. ✅ **RISOLTO (`20260603-11`)** — Co‑presenza operativa: aggiunto `CHECK ((uom_operativa_id IS NULL) = (qta_operativa IS NULL))` (`chk_ordini_v_r_uom_qta_operativa_copres`) per impedire stati ibridi.
3. **Chiarezza `qta_operativa > 0`** (aperto): il `CHECK` attuale passa con `NULL` (comportamento desiderato). Per leggibilità si può rendere esplicito: `CHECK (qta_operativa IS NULL OR qta_operativa > 0)`.
4. **Deduplicate items** (aperto): uniformare `deduplicate_items=True` → `true` (stile SQL coerente con il resto del progetto).

---

### Query tipiche

* Righe di un ordine, con totale base:

```sql
SELECT r.*, (r.quantita * r.prezzo_unitario) * (1 - COALESCE(r.sconto_percentuale,0)/100.0) AS imponibile_riga
FROM vendite.ordini_righe r
WHERE r.ordine_id = :ordine_id
ORDER BY r.riga_nr;
```

* Residuo riga (base) con fulfillment:

```sql
SELECT r.id,
       r.quantita - COALESCE(SUM(f.qta_evasa),0) AS residuo
FROM vendite.ordini_righe r
LEFT JOIN vendite.ordini_righe_fulfillment f ON f.ordine_riga_id = r.id
WHERE r.ordine_id = :ordine_id
GROUP BY r.id;
```

---

### Checklist di conformità

* [ ] Trigger **delete‑block** attiva.
* [ ] Trigger **qta_from_operativa** attiva e copre INSERT/UPDATE.
* [x] `chk_ordini_v_r_qta_pos` **corretto** a `quantita > 0` (`20260603-11`).
* [ ] `factor_to_base` aggiornato a ogni variazione UoM/quantità.
* [ ] UQ progressivo riga per testata.
* [ ] UQ idempotenza import attiva.
* [x] Co‑presenza operativa garantita (CHECK `chk_ordini_v_r_uom_qta_operativa_copres`, `20260603-11`).

---

### Note

* **Niente hard delete**: i flussi applicativi usano annulli/storni.
* Le **API** dovrebbero accettare entrambe le rappresentazioni ma applicare la **priorità all’operativa**; le GET restituiscono entrambe per trasparenza.
* La stampa documenti può mostrare la UoM operativa, lasciando i calcoli in base per confrontabilità.

### 🔄 rev 2026-09-13 — le date di consegna, sulla riga

Due date nuove (`20260913-06`), entrambe facoltative:
**`data_consegna_richiesta_cliente`** — quando il cliente la vuole — e
**`data_consegna_confermata`** — quando **noi** ci impegniamo a darla. La
differenza fra le due è la promessa. Il suffisso `_cliente` segue la regola dei
documenti: non marcato = nostro, marcato = della controparte (sull'ordine
d'acquisto è il contrario, e i nomi lo dicono).

* **Sulla riga, non sulla testata**: una riga può essere pronta e un'altra no.
  La testata la espone come minimo delle righe attive
  ([vw_ordini_lista](/dbzero/vendite/views/vw_ordini_lista)).
* **Nessun vincolo fra le due**, né con la data del documento: si può
  confermare *prima* di quanto chiesto, e la retrodatazione è un caso d'uso.
* La richiesta arriva dal preventivo al push; la conferma si decide alla
  conferma dell'ordine, e il database **non** la blocca per stato: è il
  backend a limitare oggi la modifica delle righe alla bozza.
* Con il residuo da spedire danno il **ritardo**
  ([vw_situazione_merce_ordine](/dbzero/vendite/views/vw_situazione_merce_ordine)).

Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 2.
