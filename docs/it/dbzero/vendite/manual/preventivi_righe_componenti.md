## 📘 Documentazione Concettuale – Tabella `vendite.preventivi_righe_componenti`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — riga padre composita (FK ON DELETE CASCADE)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — riga BoM (`articolo_componente_id`)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — articolo componente (`componente_id`)
> • [config.iva](/dbzero/config/tabelle/iva) — aliquota IVA del componente
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — UoM operativa del componente
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica approvazione prezzo L3
>
> **Funzioni/trigger correlati:**
>
> • [vendite.fn_preventivo_riga_componenti_init](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_init) — popola i componenti dopo INSERT riga padre
> • [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_componenti_guard_coerenza_bom) — guard BoM (5 check)
> • [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — aggiorna prezzo padre dopo ogni modifica
> • [script.trgfn_componenti_calcola_quantita](/dbzero/script/funzioni/trgfn_componenti_calcola_quantita) — calcola quantita componente da coeff × qta padre
> • [script.trgfn_componenti_propaga_qta](/dbzero/script/funzioni/trgfn_componenti_propaga_qta) — propaga cambio quantita padre ai figli
> • [vendite.trgfn_preventivi_righe_componenti_guard_pending](/dbzero/vendite/funzioni/trgfn_preventivi_righe_componenti_guard_pending) — guard workflow L3 su componente
> • [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — blocca EMESSO e ACCETTATO se un componente attivo è PENDING o REJECTED (dal 2026-09-24)
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

`vendite.preventivi_righe_componenti` modella il **prezzo negoziabile per singolo componente** di un articolo composito CASO A: almeno un componente della BoM ha `esposto_in_fattura = TRUE`.

Per ogni riga padre composita CASO A in `preventivi_righe`, questa tabella contiene **N righe figlie** (una per componente esposto), ciascuna con prezzo proprio soggetto ai meccanismi di approvazione L1/L2/L3. Il prezzo della riga padre viene aggiornato automaticamente come `SUM(prezzo_unitario_comp × coeff_qta_snapshot)` tramite trigger.

Il modello risolve il problema dello *snapshot pricing*: al push su commessa i prezzi vengono propagati direttamente da questa tabella, **senza ri-invocare il resolver di listino**, garantendo che l'operatore e il cliente vedano prezzi coerenti tra preventivo e fattura.

---

### Modello BoM CASO A

La distinzione CASO A / CASO B è determinata da `vendite.fn_resolve_prezzo_composito`:

| Caso | Condizione | Modello |
|---|---|---|
| **CASO A** | ≥ 1 componente con `esposto_in_fattura = TRUE` | N righe in `preventivi_righe_componenti`, prezzo padre calcolato |
| **CASO B** | Nessun componente esposto | Riga padre con prezzo unico, nessuna riga componente |

Questa tabella è **solo CASO A**. Per CASO B la riga padre ha il prezzo direttamente e non genera figli.

---

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `riga_preventivo_id` | FK alla riga padre (`preventivi_righe.id`) con ON DELETE CASCADE |
| `articolo_componente_id` | FK alla riga BoM (`articoli_componenti.id`) — identifica il componente nella distinta base |
| `componente_id` | FK all'articolo componente (`articoli.id`) — denormalizzato per query dirette, coerenza garantita da guard |
| `coeff_qta_snapshot` | Snapshot di `articoli_componenti.coeff_qta` al momento della creazione — isolato da evoluzioni BoM future |
| `quantita` | Calcolata dal trigger `_m50_calcola_quantita` come `coeff_qta_snapshot × quantita_padre` |
| `prezzo_unitario` | Prezzo del componente (suggerito dal resolver, modificabile dall'operatore L1/L2/L3) |
| `origine_prezzo` | Traccia l'origine: `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE` |
| `prezzo_resolver_context` | JSONB con contesto chiamata resolver (emittente, BA, data, utility); in fallback contiene `error`/`sqlstate` |
| `stato_approvazione_prezzo` | ENUM `config.stato_approvazione_prezzo` per workflow L3: `PENDING`/`APPROVED`/`REJECTED` |

---

### Relazione con la riga padre

Il prezzo sulla riga padre (`preventivi_righe.prezzo_unitario`) è **calcolato automaticamente** come SUM pesata dei componenti, tramite il trigger `z90_ricalcola_padre`:

```
preventivi_righe.prezzo_unitario = SUM(
    preventivi_righe_componenti.prezzo_unitario
    × preventivi_righe_componenti.coeff_qta_snapshot
) WHERE attivo = TRUE
```

La riga padre composita CASO A **non deve ricevere un prezzo manuale** — il suo `prezzo_unitario` è sempre il risultato di questo calcolo. Il totale del preventivo agisce sul prezzo padre × quantita padre.

---

### Workflow L1/L2/L3

I meccanismi di approvazione prezzo si applicano al **singolo componente**, non alla riga padre composita:

- **L1 (override manuale)**: l'operatore modifica `prezzo_unitario` del componente con autorizzazione `prezzo_override_manuale`.
- **L2 (limite sconto)**: parametri `VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT` applicati al componente.
- **L3 (approvazione out-of-policy)**: se il prezzo viola L2, si crea una pratica `APPROVAZIONE_PREZZO` e il componente passa a `stato_approvazione_prezzo = 'PENDING'`. Il trigger `trgfn_preventivi_righe_componenti_guard_pending` congela i campi struttura del componente fino all'esito.

Lato testata, il guard di transizione del preventivo ([`vendite.trgfn_preventivi_guard_transizione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione), attraverso [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati)) blocca le transizioni verso EMESSO e ACCETTATO se un componente **attivo**, di una riga attiva, è PENDING o REJECTED (`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`). Un componente spento non conta: resterebbe `REJECTED` per sempre e bloccherebbe il documento senza rimedio.

(Fino al 2026-09-24 lo faceva il trigger ritirato `trgfn_preventivi_guard_transizione_approvazione`, solo verso ACCETTATO e solo sul PENDING.)

---

### Snapshot pricing al push

Al push del preventivo su commessa (`BoMComponentExpander`), i prezzi dei componenti vengono propagati direttamente su `commesse_attivita` **senza ri-invocare `fn_resolve_prezzo_composito`**. Questo garantisce che:

1. Il prezzo che il cliente ha approvato (nel preventivo) sia identico a quello fatturato.
2. Le variazioni di listino successive all'accettazione non interferiscano.
3. I prezzi approvati L3 siano rispettati integralmente.

---

### Trigger registrati

| Trigger | Timing | Fase | Funzione |
|---|---|---|---|
| `_a10_guard_bom_coerenza_ins_upd` | BEFORE INS/UPD | `_a10_` | `script.trgfn_componenti_guard_coerenza_bom` |
| `_a10_guard_pending_upd` | BEFORE UPD | `_a10_` | `vendite.trgfn_preventivi_righe_componenti_guard_pending` |
| `_m50_calcola_quantita_ins_upd` | BEFORE INS/UPD | `_m50_` | `script.trgfn_componenti_calcola_quantita` |
| `_audit_data_user_ins_upd` | BEFORE INS/UPD | — | `script.trgfn_audit_data_user_generic` |
| `_gen_tx_id_ins_upd` | BEFORE INS/UPD | — | `dbops.trgfn_tx_id_managed` |
| `_a10_articoli_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_a10_iva_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_z90_ricalcola_padre_ins_upd_dlt` | AFTER INS/UPD/DLT | `_z90_` | `script.trgfn_componenti_ricalcola_padre` |

Sulla riga padre `preventivi_righe` è registrato anche `_z90_propaga_qta_componenti_upd` (AFTER UPDATE OF quantita) per mantenere allineate le quantita dei componenti.

---

### Note operative

- **FK ON DELETE CASCADE**: l'eliminazione di una `preventivi_righe` elimina automaticamente tutti i suoi componenti.
- **UNIQUE (riga_preventivo_id, articolo_componente_id)**: un componente BoM può comparire al massimo una volta per riga padre.
- **`componente_id` denormalizzato**: è uguale ad `articoli_componenti.componente_id` per la BoM entry referenziata. La coerenza è garantita dal guard `E_DOC_COMPONENTE_ID_INCOERENTE`; la ridondanza permette JOIN diretti a `catalogo.articoli` senza passare per `articoli_componenti`.
- **`meta`**: campo JSONB NOT NULL (default `{}`), riservato per estensioni future senza migrazioni.
- **Indice parziale su `stato_approvazione_prezzo`**: filtra i NULL per contenere l'indice alle sole righe in workflow.
