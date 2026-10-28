## 📘 Documentazione Concettuale – Tabella `vendite.note` (partizionata)

> 👀 **Vedi anche**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)   
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)   
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)    

---
### 🎯 Scopo Principale
`vendite.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.

---

### Il tipo della nota (`target_tipo`)

> Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3).

`target_tipo` nomina la cosa a cui la nota è ancorata col **codice di `config.tipi_entita`**, che per un
documento è il `codice_interno` della sua sorgente. È `varchar(50)` e ha la **FK** `fk_vendite_note_target_tipo` verso
`config.tipi_entita(codice)`: non c'è più un CHECK con l'elenco. Ogni valore ha la sua partizione; un codice
senza partizione è rifiutato dal routing.

| Partizione | `target_tipo` | Fino al 2026-10-25 |
| --- | --- | --- |
| `vendite.note_preventivo` | `PREVENTIVO` | uguale |
| `vendite.note_contratto` | `CONTRATTO` | uguale |
| `vendite.note_fatture` | `FATTURA` | uguale |
| `vendite.note_ordini` | `ORDINE_VENDITA` | `ORDINE` |
| `vendite.note_ddt` | `DDT_VENDITA` | `DDT` |
| `vendite.note_attivita_fatturabili` | `ATTIVITA` | `ATTIVITAFT` |
| `vendite.note_offerte_commerciali` | `OFFERTA_COMMERCIALE` | `OFFERTA` |

Un tipo nuovo di nota è una riga di `tipi_entita.csv` più la sua partizione.

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
* `ix_vendite_note_by_riga(… WHERE target_riga_id IS NOT NULL)`

---

### Partizioni e regole

Ogni partizione applica **FK** coerenti con il dominio e un **CHECK combinato** che allinea `anchor_tipo`/`posizione`/`target_riga_id`:

1. **`vendite.note_contratto`** – `FOR VALUES IN ('CONTRATTO')`

   * FK: `target_id → vendite.contratti(id)`, `target_riga_id → vendite.contratti_righe(id)`.
   * CHECK: se `anchor_tipo='DOCUMENTO'` → `target_riga_id IS NULL` e `posizione ∈ {HEADER, FOOTER, SEZIONE}`; se `anchor_tipo='RIGA'` → `target_riga_id IS NOT NULL` e `posizione ∈ {BEFORE, AFTER}`.
   * Trigger: `trg_note_contratto_ins_upd_contnote_validate()`.

2. **`vendite.note_ddt`** – `FOR VALUES IN ('DDT_VENDITA')`

   * FK: `target_id → vendite.ddt(id)`, `target_riga_id → vendite.ddt_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ddt_note_render`.

3. **`vendite.note_fatture`** – `FOR VALUES IN ('FATTURA')`

   * FK: `target_id → vendite.fatture(id)`, `target_riga_id → vendite.fatture_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_fatture_note_render`.

4. **`vendite.note_ordini`** – `FOR VALUES IN ('ORDINE_VENDITA')`

   * FK: `target_id → vendite.ordini(id)`, `target_riga_id → vendite.ordini_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ordini_note_render`.

5. **`vendite.note_preventivo`** – `FOR VALUES IN ('PREVENTIVO')`

   * FK: `target_id → vendite.preventivi(id)`, `target_riga_id → vendite.preventivi_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Trigger: `trg_note_preventivo_ins_upd_prevnote_validate()`.

> **Perché partizionare?**
>
query/cleanup **target-specifiche** (es. rebuild di tutte le note fatture) sono più veloci;
> si possono impostare policy di **retention** e **permessi** differenti per dominio;
> manutenzione più semplice (vacuum, reindex, backup parziali).

---

### Esempi d’uso

* **Nota di piede FATTURA** (documento): `anchor_tipo='DOCUMENTO'`, `posizione='FOOTER'`, `target_riga_id=NULL`, `seq=10`.
* **Nota “prima della riga” ORDINE_VENDITA**: `anchor_tipo='RIGA'`, `posizione='BEFORE'`, `target_riga_id=<id_riga>`, `seq=5`.
* **Condizioni generali** su **HEADER PREVENTIVO** in `testo_md`.

---

### Migliorie / anomalie riscontrate


1. **Indici addizionali**
   Selezione frequente per **testata**: aggiungi indice dedicato `(target_tipo, target_id)` (senza altre colonne) per lookup rapidi.

2. **Policy di update**
   Se le note devono essere **immutabili** dopo emissione/numerazione (es. su FATTURA), valuta un trigger *fail‑fast* condizionato allo stato documento.

---

### Ruolo nel sistema

`vendite.note` fornisce un **layer di annotazioni** uniforme e riusabile per tutto il dominio vendite. Il partizionamento per `target_tipo` consente crescita ordinata, performance prevedibili e governance per dominio, mantenendo al contempo un’unica API di scrittura/lettura.
