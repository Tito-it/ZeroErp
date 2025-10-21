## 📘 Documentazione Concettuale – Tabella `acquisti.note` (partizionata)

> 👀 **Vedi anche**
>
> **Approfondimetno tabelle:**
>
> • [acquisti.ordini](/dbzero/acquisti/tabelle/ordini)   
> • [acquisti.ddt](/dbzero/acquisti/tabelle/ddt)    

---

### 🎯 Scopo Principale

`acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.

---

### 🧱 Struttura (padre)

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

### 🧩 Partizioni e regole

Ogni partizione applica **FK** coerenti con il dominio e un **CHECK combinato** che allinea `anchor_tipo`/`posizione`/`target_riga_id`:


1. **`acquisti.note_ddt`** – `FOR VALUES IN ('DDT')`

   * FK: `target_id → acquisti.ddt(id)`, `target_riga_id → acquisti.ddt_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ddt_note_render`.


2. **`acquisti.note_ordini`** – `FOR VALUES IN ('ORDINE')`

   * FK: `target_id → acquisti.ordini(id)`, `target_riga_id → acquisti.ordini_righe(id)`.
   * CHECK analogo a `CONTRATTO`.
   * Indice dedicato `ix_ordini_note_render`.


> 💡 **Perché partizionare?**
>
> * query/cleanup **target-specifiche** (es. rebuild di tutte le note fatture) sono più veloci;
> * si possono impostare policy di **retention** e **permessi** differenti per dominio;
> * manutenzione più semplice (vacuum, reindex, backup parziali).

---

### 🧪 Esempi d’uso

* **Nota di piede FATTURA** (documento): `anchor_tipo='DOCUMENTO'`, `posizione='FOOTER'`, `target_riga_id=NULL`, `seq=10`.
* **Nota “prima della riga” ORDINE**: `anchor_tipo='RIGA'`, `posizione='BEFORE'`, `target_riga_id=<id_riga>`, `seq=5`.
* **Condizioni generali** su **HEADER PREVENTIVO** in `testo_md`.


---

### 👓 Ruolo nel sistema

`acquisti.note` fornisce un **layer di annotazioni** uniforme e riusabile per tutto il dominio acquisti. Il partizionamento per `target_tipo` consente crescita ordinata, performance prevedibili e governance per dominio, mantenendo al contempo un’unica API di scrittura/lettura.
