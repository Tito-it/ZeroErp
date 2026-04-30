## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_uom_operativa_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa)
> [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>
Approfondimento viste correlate:
> [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio)
> [catalogo.vw_articoli_componenti_dettaglio](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio)

### 🎯 Scopo Principale

(latest review 28-04-2026)

`catalogo.vw_articoli_uom_operativa_dettaglio` denormalizza le righe di
[`catalogo.articoli_uom_operativa`](/dbzero/catalogo/tabelle/articoli_uom_operativa)
con codici e descrizioni di **UoM** e **articolo**, ed espone 2 **capability di
riga** usate dal frontend per abilitare/disabilitare l'azione "Elimina UoM"
nel pannello configurazione UoM operativa di un articolo.

E' la vista gemella di
[`vw_articoli_componenti_dettaglio`](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio)
(BoM, Fase 2 28-04-2026): stesso pattern naming italiano, stesso schema
"capability + motivo" coerente per il consumo FE.

---

### Schema esposto

| Sezione | Colonne |
|---|---|
| **Tabella sorgente** `articoli_uom_operativa` | `id`, `articolo_id`, `uom_id`, `is_base`, `factor_to_base`, `is_sell_uom`, `is_purchase_uom`, `is_logistic_uom`, `qty_step`, `rounding_mode`, `max_decimals`, `forbid_fraction`, `require_lot`, `gtin`, `valido_dal`, `valido_al`, `validita`, `attivo`, `meta`, `user_insert`, `user_update`, `data_insert`, `data_update`, `tx_id`, `storicizza` |
| **Denormalizzazione UoM** | `uom_codice`, `uom_descrizione` (da `unita_misura`) |
| **Denormalizzazione articolo** | `articolo_codice`, `articolo_descrizione` (da `articoli`) |
| **Capability di riga** (Fase 6, 28-04-2026) | `puo_eliminarsi`, `motivo_non_eliminabile` |

### Logica capability

| Campo | Tipo | Definizione |
|---|---|---|
| `puo_eliminarsi` | `BOOLEAN` | `NOT is_base` |
| `motivo_non_eliminabile` | `TEXT` | `'UOM_BASE_NON_ELIMINABILE'` se `is_base = true`, altrimenti `NULL` |

**Pattern simmetrico a Fase 2 BoM**: `motivo_non_*` valorizzato solo quando
la riga **non** e' eliminabile; `NULL` quando l'azione e' permessa.

### Perche' solo `is_base`

Il brief BE Fase 6 prevedeva originariamente anche un guard `NOT EXISTS (figli...)`,
ma:

* Nel modello DB attuale **non esistono FK reverse** verso `articoli_uom_operativa.id`
  (le tabelle che usano UoM -- `vendite.listini_righe`, `magazzino.movimenti`, righe
  documentali -- referenziano `unita_misura.id`, non `articoli_uom_operativa.id`).
* Le guard cross-dominio (es. "esiste almeno un movimento di magazzino con
  questa coppia (articolo, uom)") sono **estensioni potenziali future**, da
  introdurre solo a fronte di un caso d'uso concreto.
* Tenere la vista semplice oggi evita complessita' inutile e mantiene la
  capability **deterministica e veloce** (un solo CASE su una colonna locale).

Il backend, se in futuro avra' bisogno di verifiche cross-dominio aggiuntive,
puo' applicarle a livello service (Python) **prima** di delegare al DB l'eliminazione,
oppure la vista verra' estesa con nuovi rami `motivo_non_eliminabile`.

---

### Esempi

**1) Riga UoM base (non eliminabile):**

```sql
SELECT id, uom_codice, is_base, puo_eliminarsi, motivo_non_eliminabile
  FROM catalogo.vw_articoli_uom_operativa_dettaglio
 WHERE articolo_id = '00000000-0000-0000-0000-000000000101'
   AND is_base = true;
-- id: ...,  uom_codice: PZ,  is_base: t,
-- puo_eliminarsi: f,  motivo_non_eliminabile: UOM_BASE_NON_ELIMINABILE
```

**2) Riga UoM secondaria (eliminabile):**

```sql
SELECT id, uom_codice, is_base, factor_to_base, puo_eliminarsi, motivo_non_eliminabile
  FROM catalogo.vw_articoli_uom_operativa_dettaglio
 WHERE articolo_id = '00000000-0000-0000-0000-000000000101'
   AND is_base = false;
-- id: ...,  uom_codice: KG,  is_base: f,  factor_to_base: 6,
-- puo_eliminarsi: t,  motivo_non_eliminabile: NULL
```

**3) Lookup BE per costruire DTO con flag:**

```python
# apps/catalogo/db/catalogo_repository.py
def list_uom_operativa(articolo_id: UUID) -> list[dict]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, uom_codice, is_base, factor_to_base,
                   qty_step, rounding_mode, max_decimals, forbid_fraction,
                   puo_eliminarsi, motivo_non_eliminabile
              FROM catalogo.vw_articoli_uom_operativa_dettaglio
             WHERE articolo_id = %s
             ORDER BY is_base DESC, uom_codice ASC
            """,
            [articolo_id],
        )
        ...
```

Il FE riceve la lista UoM con il flag `puo_eliminarsi`: il pulsante "Elimina"
e' disabilitato sulle righe `false`, con tooltip mappato dal codice
`motivo_non_eliminabile` (i18n FE).

---

### Note operative

* **Capability deterministiche**: i 2 campi sono pure proiezioni di
  `is_base`. Nessun side-effect, nessuna query annidata: la vista resta
  inline-friendly per il planner e ammette filtri WHERE su qualunque
  colonna senza penalita' di performance.
* **Naming italiano**: scelto per coerenza con
  [`vw_articoli_componenti_dettaglio`](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio)
  e con la convenzione progetto (campi tabella `valido_dal`/`valido_al`,
  `prodotto_codice`, ecc.).
* **NULL su `motivo_non_eliminabile`** quando `puo_eliminarsi = true`:
  pattern autodocumentante che evita ambiguita' (la stringa motivo esiste
  solo quando il blocco e' attivo).
* **`articolo_descrizione` / `uom_descrizione` denormalizzati**:
  riducono il numero di JOIN richiesti dal BE per il rendering UI.
  La vista NON denormalizza la lista delle righe BoM (che richiederebbe
  aggregazione): per quella usare
  [`vw_articoli_componenti_dettaglio`](/dbzero/catalogo/views/vw_articoli_componenti_dettaglio).
* **Estensione futura**: se servisse un secondo motivo di "non eliminabile"
  (es. `UOM_USATA_IN_DOCUMENTI`), basta estendere il `CASE` esistente
  aggiungendo il ramo prima del NULL. Nessuna modifica alla firma colonne
  -> safe per il consumer FE.

---

### Verifica e test

- pgTAP: `db/pgtap/catalogo/test-vw-articoli-uom-operativa-dettaglio-capability-v1.sql`
  (`plan(6)`): presenza vista + scenario UoM base (puo_eliminarsi=false +
  motivo='UOM_BASE_NON_ELIMINABILE') + scenario UoM secondaria
  (puo_eliminarsi=true + motivo=NULL) + denormalizzazione `articolo_codice`
  / `uom_codice`.

---

{% include-markdown "signature-core.md" %}

---
