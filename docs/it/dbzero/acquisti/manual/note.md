## 📘 Documentazione Concettuale – Tabella `acquisti.note` (partizionata)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [acquisti.ordini](/dbzero/acquisti/tabelle/ordini)   
> • [acquisti.ddt](/dbzero/acquisti/tabelle/ddt)    

---
### 🎯 Scopo Principale
`acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.

---

### Il tipo della nota (`target_tipo`)

> Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3).

`target_tipo` nomina la cosa a cui la nota è ancorata col **codice di `config.tipi_entita`**, che per un
documento è il `codice_interno` della sua sorgente. È `varchar(50)` e ha la **FK** `fk_acq_note_target_tipo` verso
`config.tipi_entita(codice)`: non c'è più un CHECK con l'elenco. Ogni valore ha la sua partizione; un codice
senza partizione è rifiutato dal routing.

| Partizione | `target_tipo` | Fino al 2026-10-25 |
| --- | --- | --- |
| `acquisti.note_ordini` | `ORDINE_ACQUISTO` | `ORDINE` |
| `acquisti.note_ddt` | `DDT_ACQUISTO` | `DDT` |

Un tipo nuovo di nota è una riga di `tipi_entita.csv` più la sua partizione.

---

⛔ `FATTURA` e `CONTRATTO`, che il CHECK di prima ammetteva, sono usciti: non avevano partizione, tabella né
entità. In `vendite.note` gli stessi `DDT` e `ORDINE` nominavano i documenti di **vendita**: con i codici
della grammatica lo stesso nome per due documenti diversi non c'è più.

---

### Struttura (padre)

* **Partizionamento**: `PARTITION BY LIST (target_tipo)`.
* **PK composita**: `(target_tipo, id)` → necessaria per le partizioni (l’`id` non è univoco globalmente).
* **Ancora**: `anchor_tipo ∈ {DOCUMENTO, RIGA}`.
* **Posizione**: `posizione ∈ {HEADER, FOOTER, SEZIONE, BEFORE, AFTER}` (le ammissibilità effettive sono raffinate nelle partizioni).
* **Ordinamento**: `seq ≥ 0` (default 10) per controllare l’ordine di resa all’interno della stessa area di ancoraggio/posizione.
* **Contenuti**: `testo` (plain) e/o `testo_md` (Markdown); `stile` per resa (es. NORMALE, AVVISO…).
* **Localizzazione**: `lingua` (char(5), es. `it-IT`).
* **Visibilità**: `visibile` e `solo_stampa`.
* **Meta**: JSONB estendibile.

Indici globali utili:

* `ix_note_render_order(target_tipo, target_id, anchor_tipo, posizione, seq)`
* `ix_acquisti_note_by_riga(… WHERE target_riga_id IS NOT NULL)`

---

### Partizioni e regole

Ogni partizione applica **FK** coerenti con il dominio e un **CHECK combinato** che allinea `anchor_tipo`/`posizione`/`target_riga_id`:


1. **`acquisti.note_ddt`** – `FOR VALUES IN ('DDT_ACQUISTO')`

   * FK: `target_id → acquisti.ddt(id)`, `target_riga_id → acquisti.ddt_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ddt_note_render`.


2. **`acquisti.note_ordini`** – `FOR VALUES IN ('ORDINE_ACQUISTO')`

   * FK: `target_id → acquisti.ordini(id)`, `target_riga_id → acquisti.ordini_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ordini_note_render`.


> **Perché partizionare?**
>
query/cleanup **target-specifiche** (es. rebuild di tutte le note fatture) sono più veloci;
> si possono impostare policy di **retention** e **permessi** differenti per dominio;
> manutenzione più semplice (vacuum, reindex, backup parziali).

---

### Esempi d’uso

* **Nota di piede FATTURA** (documento): `anchor_tipo='DOCUMENTO'`, `posizione='FOOTER'`, `target_riga_id=NULL`, `seq=10`.
* **Nota “prima della riga” ORDINE_ACQUISTO**: `anchor_tipo='RIGA'`, `posizione='BEFORE'`, `target_riga_id=<id_riga>`, `seq=5`.
* **Condizioni generali** su **HEADER PREVENTIVO** in `testo_md`.


---

### Ruolo nel sistema

`acquisti.note` fornisce un **layer di annotazioni** uniforme e riusabile per tutto il dominio acquisti. Il partizionamento per `target_tipo` consente crescita ordinata, performance prevedibili e governance per dominio, mantenendo al contempo un’unica API di scrittura/lettura.
