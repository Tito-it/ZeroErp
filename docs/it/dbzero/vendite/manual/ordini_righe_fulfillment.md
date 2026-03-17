## 📘 Documentazione Concettuale – Tabella `vendite.ordini_righe_fulfillment`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)  
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
>
**Approfondimento funzioni:**
> 
• [vendite.trgfn_a10_ins_upd_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_a10_ins_upd_ordini_ful_guard_consistenza)   

---

### 🎯 Scopo Principale

Rappresenta l’**evasione (parziale o totale)** delle **righe d’ordine** verso le **righe di DDT**. Ogni record è una **mappatura puntuale riga↔riga** con la **quantità evasa** in **UoM base** (`qta_evasa`).

Obiettivi principali:

* Tracciare con precisione **quale riga DDT** evada **quale riga Ordine**.
* Consentire **evasioni parziali** e **multi‑DDT** per la stessa riga d’ordine.
* Abilitare il calcolo del **residuo** ordine in base: `qta_ordine - Σ qta_evasa`.

> La tabella è il **fulcro operativo** per avanzamento ordini, KPI di servizio e coerenza logistica tra vendite e magazzino.

---

### Flussi tipici

1. **Spedizione da ordine**: l’operatore seleziona righe ordine → genera DDT → per ogni riga DDT si crea **1..n** record di fulfillment verso le righe d’ordine pertinenti (in genere 1:1).
2. **Parziale / Backorder**: se si spedisce una parte, si registra `qta_evasa` < `qta_ordine`; la riga ordine rimane **aperta** con residuo > 0.
3. **Completa**: quando `Σ qta_evasa = qta_ordine`, la riga ordine è **evasa** (lo stato a livello testata viene aggiornato dai meccanismi di aggregazione).

---

### Regole di dominio

* **Unicità coppia**: una coppia `(ordine_riga_id, ddt_riga_id)` è **unica** (indice `uq_ordini_r_ful_v_pair`).

  * Permette più records per la **stessa riga ordine** verso **DDT diversi** e viceversa.
* **Quantità**: `qta_evasa > 0` (check `chk_ordini_r_ful_v_qta_pos`).
* **Coerenza articolo/UoM**: demandata alla **trigger guard** (vedi sotto): la riga DDT deve riferire lo **stesso articolo** (e UoM coerente) della riga ordine.
* **Integrità referenziale**: `ON DELETE RESTRICT` su entrambe le FK per **impedire** cancellazioni che romperebbero la tracciabilità storica.

---

### Trigger di coerenza

**`trg_ordini_a10_ins_upd_ful_guard_consistenza`** → `vendite.trgfn_a10_ins_upd_ordini_ful_guard_consistenza()` (BEFORE INSERT/UPDATE)

Funzioni principali (riassunto):

* Verifica **matching articolo** tra `vendite.ordini_righe.id = NEW.ordine_riga_id` e `vendite.ddt_righe.id = NEW.ddt_riga_id`.
* Calcola **residuo** riga ordine e **impedisce** che `Σ qta_evasa` superi `qta_ordine`.
* Facoltativamente controlla **compatibilità UoM** (operativa→base) come da policy del progetto.
* In caso di violazioni, invoca `script.fn_log_and_raise_error(...)` con codice specifico e contesto (ordine_riga_id, ddt_riga_id, quantità, residuo, ecc.).

> La guardia di consistenza è la **cintura di sicurezza** per evitare over‑shipping o incoerenze di item.

---

### Query utili

* **Residuo per riga d’ordine**

```sql
SELECT r.id AS ordine_riga_id,
       r.qta                              AS qta_ordine,
       COALESCE(SUM(f.qta_evasa),0)       AS qta_evasa,
       r.qta - COALESCE(SUM(f.qta_evasa),0) AS qta_residua
FROM vendite.ordini_righe r
LEFT JOIN vendite.ordini_righe_fulfillment f
       ON f.ordine_riga_id = r.id
WHERE r.ordine_id = :ordine_id
GROUP BY r.id, r.qta;
```

* **DDT che evadono un ordine**

```sql
SELECT f.ddt_riga_id, d.ddt_id, f.qta_evasa
FROM vendite.ordini_righe_fulfillment f
JOIN vendite.ddt_righe d ON d.id = f.ddt_riga_id
WHERE f.ordine_riga_id = :ordine_riga_id
ORDER BY d.ddt_id;
```

---

### Checklist di conformità

* [ ] `uq_ordini_r_ful_v_pair` presente e attivo.
* [ ] Check `qta_evasa > 0` presente.
* [ ] Trigger **guard_consistenza** attiva su INSERT/UPDATE.
* [ ] FK con `RESTRICT` (policy anti‑cancellazione) confermate.
* [ ] `storicizza = true` e trigger di storico collegato allo standard di progetto.

---

### Migliorie puntuali (opzionali)

1. **Indice su `ordine_riga_id`**: per le pagine residuo/report; oggi l’unicità è sulla coppia, ma un indice singolo `ix_fulv_ordine_riga` velocizza molte query.
2. **Meta JSON**: valutare **GIN** se si filtrano spesso campi di `meta`.
3. **Error codes**: documentare i codici emessi dalla guard (es. `E_QTA_SUPERA_RESIDUO`, `E_ARTICOLO_MISMATCH`) per facilitarne la gestione in UI/API.

---

### Ruolo nel sistema

È la **fonte di verità** per:

* **Stato riga ordine** (aperta/parziale/evasa).
* **Ricostruzione logistica** (chi ha evaso cosa).
* **Fatturazione differita** (quantità base già spedite).
* **KPI** (OTD, lead time evasione, % fill rate, backorder).
