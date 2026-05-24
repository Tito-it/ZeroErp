## 📘 Documentazione Concettuale – Tabella `vendite.offerte_commerciali_eccezioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.note_offerte_commerciali](/dbzero/vendite/tabelle/note_offerte_commerciali)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

`vendite.offerte_commerciali_eccezioni` contiene le **eccezioni puntuali al listino**
proposte nell'offerta commerciale: ogni riga rappresenta una deviazione tipizzata
rispetto al listino di riferimento dell'offerta.

E' il **mirror fedele di `vendite.contratti_righe`**, con le sole differenze intenzionali:

- `offerta_id` al posto di `contratto_id`
- **escluse** `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` — il
  flusso di approvazione prezzo si applica solo sui contratti, non sull'offerta
  pre-negoziazione.

La simmetria strutturale garantisce che `fn_push_offerta_a_contratto` sia una
copia 1:1 senza conversioni di colonne (§5.1 analisi).

---

### Tipi di eccezione

Ogni riga porta un campo `tipo_eccezione` (enum `vendite.tipo_eccezione_contratto`):

| Valore       | Significato                                          | `prezzo_unitario` |
| ------------ | ---------------------------------------------------- | ----------------- |
| `OVERRIDE`   | Prezzo personalizzato per articolo gia' nel listino  | NOT NULL          |
| `ESCLUSIONE` | Articolo del listino escluso per questo cliente      | NULL              |
| `AGGIUNTA`   | Articolo non presente nel listino, aggiunto          | NOT NULL          |

#### CHECK `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`

```text
ESCLUSIONE  → prezzo_unitario IS NULL
OVERRIDE    → prezzo_unitario IS NOT NULL
AGGIUNTA    → prezzo_unitario IS NOT NULL
```

#### Vincoli di unicita parziale

| Indice                                         | Predicato                               | Semantica |
| ---------------------------------------------- | --------------------------------------- | --------- |
| `uq_offerte_eccezioni_one_eccezione_per_articolo` | `WHERE tipo_eccezione IN ('OVERRIDE','ESCLUSIONE')` | OVERRIDE e ESCLUSIONE sono mutualmente esclusivi per la stessa coppia `(offerta, articolo)` |
| `uq_offerte_eccezioni_one_aggiunta_per_articolo`  | `WHERE tipo_eccezione = 'AGGIUNTA'`    | Al piu' una AGGIUNTA per coppia `(offerta, articolo)` |

Gli stessi indici esistono su `contratti_righe` con gli stessi predicati, confermando
la simmetria strutturale.

---

### Tipo erogazione e fonte quantita attesa

Le colonne `tipo_erogazione` e `fonte_quantita_attesa` replicano la stessa semantica
di `contratti_righe`:

- `tipo_erogazione` — `CANONE | UNA_TANTUM | ORARIO | CONSUMO` (CHECK
  `chk_offerte_eccezioni_tipo_erog`).
- `fonte_quantita_attesa` — `FISSA | MANUALE | TIMESHEET | LETTURE | DERIVATA_COMPONENTI`
  (CHECK `chk_offerte_eccezioni_fonte_qta`), NOT NULL.
- CHECK `chk_offerte_eccezioni_coerenza_canone` — se `tipo_erogazione = 'CANONE'`,
  `generazione_canone` deve essere in `('INIZIO_PERIODO', 'FINE_PERIODO', 'PRORATA')`.
- CHECK `chk_offerte_eccezioni_coerenza_fonte_erogazione` — blocca le 7 combinazioni
  vietate tra `tipo_erogazione` e `fonte_quantita_attesa` (stessa matrice di `contratti_righe`).

Per la matrice completa e la semantica di ogni valore vedi la documentazione di
[`vendite.contratti_righe`](/dbzero/vendite/tabelle/contratti_righe).

---

### Quantita operative e unita di misura

- `uom_operativa_id` — FK → `catalogo.unita_misura(id)`. UoM operativa dichiarata in riga.
- `qta_operativa` — quantita nella UoM operativa.
- `factor_to_base` — snapshot del fattore di conversione verso la UoM base (default 1).
- `quantita` — quantita nella UoM base.

Questi campi replicano la struttura di `contratti_righe` per garantire la copia 1:1 al push.

---

### Relazione con l'offerta e ciclo di vita

- La riga e' **posseduta dall'offerta**: `ON DELETE CASCADE` su `offerta_id`. Se l'offerta
  viene eliminata (solo in BOZZA), le eccezioni scompaiono con essa.
- Le righe sono modificabili finche' l'offerta e' in stato BOZZA. Il trigger guard
  della testata (Step 4) blocca modifiche dopo l'emissione.
- Il campo `attivo` permette di disattivare una riga senza eliminarla; il trigger
  `dbops.trgfn_child_requires_active_parent` blocca la disattivazione dell'articolo
  padre se esiste almeno una riga eccezione attiva che vi fa riferimento.

---

### Note collegate

Le note testuali sulle singole eccezioni risiedono in `vendite.note_offerte_commerciali`
(partizione `'OFFERTA'` di `vendite.note`) con `target_tipo = 'RIGA'` e
`target_riga_id → offerte_commerciali_eccezioni(id)`.

---

{% include-markdown "signature-core.md" %}

---
