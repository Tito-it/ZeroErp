## 📘 Documentazione Concettuale – Tabella `vendite.ordini_righe_componenti`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — riga padre composita (FK ON DELETE CASCADE)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — riga BoM (`articolo_componente_id`)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — articolo componente (`componente_id`)
> • [config.iva](/dbzero/config/tabelle/iva) — aliquota IVA del componente
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — UoM operativa del componente
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica approvazione prezzo L3
>
> **Funzioni/trigger correlati:**
>
> • [vendite.fn_ordine_riga_componenti_init](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_init) — popola i componenti dopo INSERT riga padre
> • [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_componenti_guard_coerenza_bom) — guard BoM (5 check)
> • [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — aggiorna prezzo padre dopo ogni modifica
> • [script.trgfn_componenti_calcola_quantita](/dbzero/script/funzioni/trgfn_componenti_calcola_quantita) — calcola quantita componente da coeff × qta padre
> • [script.trgfn_componenti_propaga_qta](/dbzero/script/funzioni/trgfn_componenti_propaga_qta) — propaga cambio quantita padre ai figli
>
> **Tipo ENUM:**
>
> • `config.stato_approvazione_prezzo` — PENDING/APPROVED/REJECTED per workflow L3
>
> **Guide:**
>
> • [Gestione Listini v5 §5.2](/guide/gestione-listini) — BoM CASO A vs CASO B

---

### 🎯 Scopo Principale

`vendite.ordini_righe_componenti` modella il **prezzo negoziabile per singolo componente** di un articolo composito CASO A nell'ambito di un ordine: una riga per ogni componente attivo e valido della distinta (modello unificato del 2026-05-13). L'esposizione del componente in fattura (`catalogo.articoli_componenti.esposizione_in_fattura`) è una regola di presentazione della fattura, non un filtro su queste righe.

Per ogni riga padre composita CASO A in `ordini_righe`, questa tabella contiene **N righe figlie** (una per componente attivo della distinta), ciascuna con prezzo proprio soggetto ai meccanismi di approvazione L1/L2/L3. Il prezzo della riga padre viene aggiornato automaticamente come `SUM(prezzo_unitario_comp × coeff_qta_snapshot)` tramite trigger.

Il modello garantisce snapshot pricing: al push su commessa i prezzi vengono propagati direttamente da questa tabella, **senza ri-invocare il resolver di listino**.

---

### Modello BoM CASO A

Dal modello unificato del 2026-05-13 la distinzione dipende solo dall'articolo (`catalogo.articoli.is_composito`), e la applica `vendite.fn_ordine_riga_componenti_init`:

| Caso | Condizione | Modello |
|---|---|---|
| **CASO A** | articolo composito (`is_composito = TRUE`) | N righe in `ordini_righe_componenti`, una per componente attivo e valido, prezzo padre calcolato |
| **CASO B** | articolo non composito | Riga padre con prezzo unico, nessuna riga componente |

Fino al 2026-05-13 il CASO A era «≥ 1 componente con `esposto_in_fattura = TRUE`»; quel flag è diventato una regola di presentazione, e dal 2026-10-01 è `esposizione_in_fattura` a tre modi (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`), letto dalla vista di rappresentazione della fattura.

Questa tabella è **solo CASO A**. Per CASO B la riga padre ha il prezzo direttamente e non genera figli.

---

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `riga_ordine_id` | FK alla riga padre (`ordini_righe.id`) con ON DELETE CASCADE |
| `articolo_componente_id` | FK alla riga BoM (`articoli_componenti.id`) — identifica il componente nella distinta base |
| `componente_id` | FK all'articolo componente (`articoli.id`) — denormalizzato per query dirette, coerenza garantita da guard |
| `coeff_qta_snapshot` | Snapshot di `articoli_componenti.coeff_qta` al momento della creazione — isolato da evoluzioni BoM future |
| `quantita` | Calcolata dal trigger `_m50_calcola_quantita` come `coeff_qta_snapshot × quantita_padre` |
| `uom_operativa_id` | UoM **del componente** (non del kit), `NOT NULL` dal 2026-10-02 (`20261002-66`): la valorizza la funzione `_init` dalla UoM dell'articolo componente. Un kit può essere fatto di unità diverse (pezzi, metri, ore); il ripiego sulla UoM del padre è ritirato |
| `prezzo_unitario` | Prezzo del componente (suggerito dal resolver, modificabile dall'operatore L1/L2/L3) |
| `origine_prezzo` | Traccia l'origine: `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE` |
| `prezzo_resolver_context` | JSONB con contesto chiamata resolver (emittente, BA, data); in fallback contiene `error`/`sqlstate` |
| `stato_approvazione_prezzo` | ENUM `config.stato_approvazione_prezzo` per workflow L3: `PENDING`/`APPROVED`/`REJECTED` |

---

### Relazione con la riga padre

Il prezzo sulla riga padre (`ordini_righe.prezzo_unitario`) è **calcolato automaticamente** come SUM pesata dei componenti, tramite il trigger `z90_ricalcola_padre`:

```
ordini_righe.prezzo_unitario = SUM(
    ordini_righe_componenti.prezzo_unitario
    × ordini_righe_componenti.coeff_qta_snapshot
) WHERE attivo = TRUE
```

La riga padre composita CASO A **non deve ricevere un prezzo manuale** — il suo `prezzo_unitario` è sempre il risultato di questo calcolo.

---

### Differenze rispetto a `preventivi_righe_componenti`

| Aspetto | Preventivi | Ordini |
|---|---|---|
| Guard L3 PENDING | ✅ `trgfn_preventivi_righe_componenti_guard_pending` | ✅ [`trgfn_ordini_righe_componenti_guard_pending`](/dbzero/vendite/funzioni/trgfn_ordini_righe_componenti_guard_pending) (20260511-38) |
| Guard testata sul prezzo non autorizzato (dal 2026-09-24) | ✅ `trgfn_preventivi_guard_transizione` (Regola 3, verso ACCETTATO) e `fn_check_preventivo_emettibile` (verso EMESSO) | ✅ `trgfn_ordini_guard_transizione`, Regola 5 — solo DRAFT → CONFERMATO |
| `utility_id` sulla testata | ✅ disponibile | ❌ Non presente su `ordini` |
| Numero trigger | 8 | 7 |

Il controllo di testata, in entrambi i documenti, è [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati): un componente attivo in attesa (PENDING) o rifiutato (REJECTED) blocca l'avanzamento con `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`. Sull'ordine lo chiede solo la conferma dalla bozza: il rientro automatico da EVASO / PARZIALMENTE_EVASO non conferma niente di nuovo.

---

### Trigger registrati

| Trigger | Timing | Fase | Funzione |
|---|---|---|---|
| `_a10_guard_bom_coerenza_ins_upd` | BEFORE INS/UPD | `_a10_` | `script.trgfn_componenti_guard_coerenza_bom` |
| `_m50_calcola_quantita_ins_upd` | BEFORE INS/UPD | `_m50_` | `script.trgfn_componenti_calcola_quantita` |
| `_audit_data_user_ins_upd` | BEFORE INS/UPD | — | `script.trgfn_audit_data_user_generic` |
| `_gen_tx_id_ins_upd` | BEFORE INS/UPD | — | `dbops.trgfn_tx_id_managed` |
| `_a10_articoli_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_a10_iva_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_z90_ricalcola_padre_ins_upd_dlt` | AFTER INS/UPD/DLT | `_z90_` | `script.trgfn_componenti_ricalcola_padre` |

Sulla riga padre `ordini_righe` è registrato anche `_z90_propaga_qta_componenti_upd` (AFTER UPDATE OF quantita) per mantenere allineate le quantita dei componenti.

---

### Note operative

- **FK ON DELETE CASCADE**: l'eliminazione di una `ordini_righe` elimina automaticamente tutti i suoi componenti.
- **UNIQUE (riga_ordine_id, articolo_componente_id)**: un componente BoM può comparire al massimo una volta per riga padre.
- **`componente_id` denormalizzato**: è uguale ad `articoli_componenti.componente_id` per la BoM entry referenziata. La ridondanza permette JOIN diretti a `catalogo.articoli` senza passare per `articoli_componenti`.
- **`meta`**: campo JSONB NOT NULL (default `{}`), riservato per estensioni future senza migrazioni.
- **Indice parziale su `stato_approvazione_prezzo`**: filtra i NULL per contenere l'indice alle sole righe in workflow.
