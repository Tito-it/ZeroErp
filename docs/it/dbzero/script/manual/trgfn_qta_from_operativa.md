
## Funzione `script.trgfn_qta_from_operativa()`

```sql
CREATE OR REPLACE FUNCTION script.trgfn_qta_from_operativa()
RETURNS trigger
LANGUAGE plpgsql
```
### 🎯 Scopo Principale
Calcolare e garantire la **coerenza della quantità in UoM base (`NEW.qta`)** a partire dalla **sorgente operativa** (`NEW.uom_operativa_id`, `NEW.qta_operativa`) sulle righe documentali (es. `vendite.ddt_righe`). La funzione:

* usa la **UoM operativa** e la **quantità operativa** come fonte verità;
* ricava il **fattore di conversione → base** dalla mappatura `catalogo.articoli_uom_operativa` (con validità e stato `attivo`);
* produce `NEW.qta = NEW.qta_operativa * factor_to_base` (con arrotondamento);
* opzionalmente **snapshotta** `NEW.factor_to_base` e **copia** la UoM base in `NEW.uom_id`.

> Nei DDT di vendita si raccomanda di mantenere `qta` **positiva**; il segno del movimento è demandato alla **causale** di testata.

### Contesto di utilizzo

* **Trigger**: `trg_a10_ins_upd_ddt_righe_qta_from_operativa` (BEFORE INSERT/UPDATE su `vendite.ddt_righe`).
* **Tabelle/oggetti letti**:

  * `catalogo.articoli` (fallback UoM base se `uom_operativa_id` assente);
  * `catalogo.articoli_uom_operativa` (campi: `factor_to_base`, `qty_step`, `max_decimals`, `forbid_fraction`, `valido_dal`, `valido_al`, `attivo`).
* **Funzioni di supporto**: `script.fn_log_and_raise_error(...)` per logging + eccezioni applicative.

### Parametri (`TG_ARGV`)

| Pos | Nome                  | Tipo    | Default | Significato                                                                                                 |
| --: | --------------------- | ------- | ------- | ----------------------------------------------------------------------------------------------------------- |
|   0 | `fill_factor_to_base` | boolean | `false` | Se `TRUE` e `NEW.factor_to_base` è `NULL`, **salva lo snapshot** del fattore usato in `NEW.factor_to_base`. |
|   1 | `fill_uom_id_base`    | boolean | `false` | Se `TRUE`, copia la UoM operativa in `NEW.uom_id` (da usare solo su tabelle che hanno la colonna).          |

### 🧾 Precondizioni & Postcondizioni

**Precondizioni**

* `NEW.articolo_id` non `NULL`.
* `NEW.qta_operativa` **deve** essere valorizzata (se assente → errore `E_QTA_MISSING`).
* `NEW.uom_operativa_id` può essere `NULL`: in tal caso viene **derivata** dalla UoM base dell’articolo (`catalogo.articoli.uom_id`). Se resta `NULL` → errore `E_UOM_MISSING`.

**Postcondizioni**

* `NEW.qta` è valorizzata in **UoM base** con **arrotondamento** (attuale: 6 decimali fissi).
* Se `TG_ARGV[0]=TRUE` e `NEW.factor_to_base` è `NULL` → popolata con il fattore usato.
* Se `TG_ARGV[1]=TRUE` → `NEW.uom_id := NEW.uom_operativa_id` (tipicamente coincide con la UoM base quando l’operativa = base).

### Algoritmo (passi rilevanti)

1. **Short‑circuit**: se **entrambi** `NEW.qta_operativa` **e** `NEW.uom_operativa_id` sono già presenti ⇒ **NON ricalcola** (ritorna `NEW` così com’è).
2. **Lettura parametri** da `TG_ARGV` (`fill_factor_to_base`, `fill_uom_id_base`).
3. **Validazione quantità operativa**: se `NEW.qta_operativa IS NULL` ⇒ `fn_log_and_raise_error(..., 'E_QTA_MISSING', ...)`.
4. **Fallback UoM operativa**: se `NEW.uom_operativa_id IS NULL` ⇒ `SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = NEW.articolo_id`.

   * Se ancora `NULL` ⇒ `fn_log_and_raise_error(..., 'E_UOM_MISSING', ...)`.
5. **Lettura mapping** `catalogo.articoli_uom_operativa` per `(articolo_id, uom_operativa_id)` **attivo** e **valido alla data**: ottiene `v_factor_map`, `v_qty_step`, `v_max_dec`, `v_forbid_frac` (default `factor=1`, `max_dec=6`).
6. **Fattore effettivo**: `v_factor_used := COALESCE(NEW.factor_to_base, v_factor_map, 1)`; se `fill_factor_to_base=TRUE` e `NEW.factor_to_base IS NULL` ⇒ salva lo snapshot.
7. **Policy sull’operativa** (se presente):

   * Se `v_forbid_frac = TRUE` e `NEW.qta_operativa` non è intera ⇒ `E_QTA_OPERATIVA_NON_INTERA`.
   * Se `v_qty_step > 0` e `NEW.qta_operativa` non è multiplo di `v_qty_step` ⇒ `E_QTA_OPER_STEP_INVALIDO`.
8. **Calcolo base**: `NEW.qta := ROUND(NEW.qta_operativa * v_factor_used, 6)` e `RETURN NEW`.

> **Nota**: la variabile `v_max_dec` è già letta ma attualmente **non usata** nell’arrotondamento; vedi migliorìe.

### 🚨 Codici errore (via `fn_log_and_raise_error`)

| Codice                       | Significato                           | Suggerimento operativo                                                                       |
| ---------------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------- |
| `E_QTA_MISSING`              | `qta_operativa` mancante              | Valorizzare la quantità operativa o impostare regole di ricomposizione.                      |
| `E_UOM_MISSING`              | UoM operativa non determinabile       | Verificare `articolo_id` e mapping UoM; controllare UoM base su `catalogo.articoli`.         |
| `E_QTA_OPERATIVA_NON_INTERA` | Qtà operativa deve essere intera      | Correggere la quantità o aggiornare la policy `forbid_fraction` nelle UoM operative ammesse. |
| `E_QTA_OPER_STEP_INVALIDO`   | Qtà operativa non rispetta `qty_step` | Adeguare la quantità al passo consentito o aggiornare `qty_step`.                            |

### Esempi d’uso

**A) Inserimento con operativa completa (no ricalcolo)**

```sql
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id,
  descrizione,
  uom_operativa_id, qta_operativa,
  uom_id, qta
) VALUES (
  1001, 1, '3b9b6a2a-...-9f3c',
  'Viti autofilettanti 3x16 – scatole',
  20, 2,
  NULL, NULL
);
-- Il trigger NON ricalcola (entrambi presenti) e userà il mapping solo per validazioni opzionali.
```

**B) Inserimento con sola operativa → calcolo base**

```sql
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  uom_operativa_id, qta_operativa,
  qta
) VALUES (
  1001, 2, '3b9b6a2a-...-9f3c', 'Viti 3x16',
  20, 2,
  NULL
);
-- Calcola qta = 2 * factor_to_base (snapshot opzionale se TG_ARGV[0]=TRUE)
```

**C) Inserimento con operativa mancante → fallback UoM base**

```sql
INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, qta
) VALUES (
  1001, 3, '3b9b6a2a-...-9f3c', 'Viti 3x16',
  50, NULL
);
-- Deriva uom_operativa_id := UoM base articolo; calcola qta = 50 * factor(base→base=1)
```

**D) Update** – cambio UoM operativa o qtà operativa

```sql
UPDATE vendite.ddt_righe
   SET uom_operativa_id = 21, qta_operativa = 1.5
 WHERE id = :riga_id;
-- Verifica forbid_fraction/qty_step, ricalcola qta = ROUND(1.5 * factor(21→base), 6)
```

### Binding del trigger (esempio YAML Liquibase)

> Se vuoi applicarlo a `vendite.ddt_righe` con gli argomenti `(true, false)`:

```yaml
databaseChangeLog:
  - changeSet:
      id: 20251107-01-trg-ddt-righe-qta-from-oper
      author: mctit
      changes:
        - createTrigger:
            catalogName: null
            schemaName: vendite
            tableName: ddt_righe
            triggerName: trg_a10_ins_upd_ddt_righe_qta_from_operativa
            before: true
            insert: true
            update: true
            forEachRow: true
            referencedTableCatalogName: null
            referencedTableSchemaName: null
            referencedTableName: null
            disabled: false
            procedure: "script.trgfn_qta_from_operativa('true','false')"
```

### Migliorìe proposte (aderenza linee guida ZeroERP)

1. **Arrotondamento parametrico**: usare `v_max_dec` al posto del fisso `6`, es.: `ROUND(..., v_max_dec)`.
2. **Guard su `qta`**: se `uom_operativa_id` e `qta_operativa` sono presenti, **impedire** l’override manuale di `NEW.qta` (o ricalcolarla sempre) per evitare incoerenze.
3. **Coerenza UoM base**: se esiste `NEW.uom_id`, validare `NEW.uom_id = uom_base_articolo` (errore dedicato `E_UOM_BASE_MISMATCH`).
4. **Epsilon configurabile** per il controllo `qty_step` (attuale `1e-9` hardcoded) → legarlo a parametro `config.parameters` (es. `uom_step_epsilon`).
5. **Gestione fattori time‑bounded**: se più mapping validi nel periodo, scegliere quello con `valido_dal` più recente ≤ `CURRENT_DATE`.
6. **Test pgTAP**: coprire casi positivi/negativi (mancanze, step non rispettato, frazioni vietate, snapshot factor, fallback UoM, max_dec).

### Note di implementazione

* La funzione è **idempotente** sul caso “operativa completa” (non ricalcola).
* L’errore viene sempre **loggato** in `dbops.error_log` tramite `fn_log_and_raise_error`, con `context` e chiavi (`table`, `column`, ecc.).
* Progettata per essere **riusabile** su più tabelle (DDT, Ordini, ecc.) tramite `TG_ARGV` e presenza condizionale delle colonne (`uom_id`, `factor_to_base`).
