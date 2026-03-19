## 📘 Documentazione Concettuale – Tabella `catalogo.articoli_uom_operativa`

> 👀 **Vedi anche**
>
**Approfondimenti tabelle:**   
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)   
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)   
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)   
---
### 🎯 Scopo Principale
(latest review 13-01-26)
Mappa, per ciascun **articolo**, le **unità di misura operative** ammesse e il **fattore di conversione** verso la **UoM base**. Permette di lavorare con confezioni (es. *cartone 6 bottiglie*, *scatola 50 pz*) mantenendo **coerenza contabile e di stock** in **UoM base**.

* Ogni articolo ha **una sola** UoM **base** (`is_base = TRUE`, `factor_to_base = 1`).
* Può avere **più** UoM operative per finalità diverse (vendita/logistica/acquisto), con regole di **input** e **arrotondamento** dedicate (`qty_step`, `max_decimals`, `forbid_fraction`, `rounding_mode`).

---

### Regole di conversione (di dominio)

* **Direzione**: `qta_base = qta_operativa * factor_to_base`.
* **Snapshot nei documenti**: le righe documento copiano il `factor_to_base` **valido alla data** per garantire riproducibilità (es. campo omonimo nelle righe d’ordine/DDT).
* **Validità temporale**: se presenti `valido_dal`/`valido_al`, si seleziona **la riga attiva** alla data del documento (`attivo = TRUE` + finestra temporale).
* **Arrotondamenti**: rispettare `rounding_mode` e vincoli di input `qty_step`/`max_decimals`; se `forbid_fraction = TRUE` ⇒ quantità **intere** (step=1, decimali=0).

---

### Utilizzo nei documenti

* **Ordini / DDT / Preventivi**: l’utente seleziona `uom_operativa_id` + inserisce `qta_operativa`; il trigger calcola `qta` (base) usando `factor_to_base` e valida gli input secondo `qty_step`/`max_decimals`/`forbid_fraction`.
* **Fatturazione**: si può esporre e totalizzare in UoM operativa, salvando sempre anche `qta` in base.
* **Magazzino**: i movimenti e i saldi sono **sempre in UoM base**; le viste operative derivano al bisogno (`qta_base / factor_to_base`).

---

### Checklist operativa

* [ ] Per **ogni articolo** esiste **esattamente una** riga con `is_ba
se=TRUE` e `factor_to_base=1`.
* [ ] **Una sola riga per (articolo_id, uom_id)**: l’univocità impedisce versioni multiple per la stessa coppia.
* [ ] `rounding_mode` tra {UP, DOWN, HALF_UP, HALF_DOWN, HALF_EVEN}.
* [ ] Se `forbid_fraction=TRUE` ⇒ `max_decimals=0` e `qty_step=1`.
* [ ] Le API/trigger rispettano `qty_step`, `max_decimals` e **copiano** il `factor_to_base` nei documenti.

---

### Migliorie / Anomalie (sul DDL fornito)

1. **Vincolo "base" più stringente (consigliato)**
   Aggiungere un **CHECK** che imponga `factor_to_base = 1` quando `is_base = TRUE` e **vieti** flags commerciali/logistici sulla riga base, es.:

   ```sql
   CHECK (NOT is_base OR factor_to_base = 1)
   ```

   (l’uso di `is_sell_uom`/`is_purchase_uom`/`is_logistic_uom` sulla riga base è opzionale; se vuoi tenerli separati, valuta `CHECK (NOT is_base OR (is_sell_uom OR is_purchase_uom OR is_logistic_uom) IS NOT TRUE)`.)

2. **Integrità temporale**
   Con l’univocità su `(articolo_id, uom_id)` non sono previste versioni multiple per la stessa coppia; se in futuro si vuole versionare nel tempo, sarà necessario rivedere il vincolo e introdurre un range/constraint di esclusione.

3. **Default e stile indici**
   Negli indici è usato `deduplicate_items=True` (maiuscolo). Per coerenza con lo stile del progetto, usare `true` minuscolo.
   `ix_artuomop_meta_gin` usa `fastupdate=True`: OK per GIN; il parametro è supportato e coerente.

4. **Performance query**
   Se le ricerche filtrano spesso per **categoria d’uso**, valutare indici parziali:

   ```sql
   CREATE INDEX IF NOT EXISTS ix_artuomop_sell ON catalogo.articoli_uom_operativa(articolo_id)
     WHERE is_sell_uom IS TRUE AND attivo IS TRUE;
   CREATE INDEX IF NOT EXISTS ix_artuomop_log ON catalogo.articoli_uom_operativa(articolo_id)
     WHERE is_logistic_uom IS TRUE AND attivo IS TRUE;
   ```

5. **Coerenza dati di base**
   Considera un **unique parziale** per evitare più righe base per lo stesso articolo (già presente come indice unico parziale `WHERE is_base IS TRUE` → 👍). Puoi consolidarlo come **constraint** formale via Liquibase se preferisci.

6. **API di selezione mapping attivo**
   Standardizzare una **view/funzione** per scegliere la riga mappatura **attiva alla data** (riduce duplicazione di logica in trigger/servizi):

   ```sql
   CREATE OR REPLACE VIEW catalogo.v_articoli_uom_operativa_attiva AS
   SELECT u.*
   FROM catalogo.articoli_uom_operativa u
   WHERE u.attivo IS TRUE
     AND (u.valido_dal IS NULL OR u.valido_dal <= CURRENT_DATE)
     AND (u.valido_al  IS NULL OR u.valido_al  >= CURRENT_DATE);
   ```

---

### Esempi d’uso

* **Scatola viti 50 pz**: base = **pz** (`is_base=TRUE`, `factor=1`), operativa = **scatola** (`factor_to_base=50`). Inserendo `qta_operativa=3` ⇒ `qta_base=150`.
* **Cartone acqua 6x1.5L**: base = **bottiglia**; operativa = **cartone** (`factor_to_base=6`).

---

### Query utili

**UoM operative di un articolo (base in cima)**

```sql
SELECT u.*
FROM catalogo.articoli_uom_operativa u
WHERE u.articolo_id = :articolo_id
ORDER BY u.is_base DESC, u.is_sell_uom DESC, u.is_logistic_uom DESC, u.uom_id;
```

**Recupero mapping attivo alla data**

```sql
SELECT *
FROM catalogo.articoli_uom_operativa u
WHERE u.articolo_id = :articolo_id
  AND u.uom_id = :uom_id
  AND (u.valido_dal IS NULL OR u.valido_dal <= :data_doc)
  AND (u.valido_al  IS NULL OR u.valido_al  >= :data_doc)
  AND u.attivo IS TRUE
LIMIT 1;
```

---

### Decisioni di design (Zero ERP)

* **UoM base** come unità di coerenza per stock/valorizzazioni/reportistica.
* **UoM operativa** come interfaccia utente (vendita/logistica/acquisto) con regole di input e arrotondamento.
* **Snapshot `factor_to_base`** nei documenti per garantire immutabilità storica.
* **Selettore di mapping "attivo alla data"** per evitare ambiguità.
