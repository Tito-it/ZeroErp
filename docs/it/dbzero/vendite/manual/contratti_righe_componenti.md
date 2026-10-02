## 📘 Documentazione Concettuale – Tabella `vendite.contratti_righe_componenti`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — riga padre composita (FK ON DELETE CASCADE)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — riga BoM (`articolo_componente_id`)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — articolo componente (`componente_id`)
> • [config.iva](/dbzero/config/tabelle/iva) — aliquota IVA del componente
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — UoM operativa del componente
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica approvazione prezzo L3
>
> **Funzioni/trigger correlati:**
>
> • [vendite.fn_contratto_riga_componenti_init](/dbzero/vendite/funzioni/fn_contratto_riga_componenti_init) — popola i componenti dopo INSERT riga padre
> • [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_componenti_guard_coerenza_bom) — guard BoM
> • [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — aggiorna prezzo padre
> • [script.trgfn_componenti_calcola_quantita](/dbzero/script/funzioni/trgfn_componenti_calcola_quantita) — calcola quantita componente
> • [script.trgfn_componenti_propaga_qta](/dbzero/script/funzioni/trgfn_componenti_propaga_qta) — propaga cambio quantita padre
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

`vendite.contratti_righe_componenti` modella il **prezzo negoziabile per singolo componente** di un articolo composito CASO A nell'ambito di un contratto. Stesso pattern delle altre 3 tabelle (preventivi, ordini, ddt).

---

### Prerequisito: rename `quantita_fissa` → `quantita`

La migration `20260511-31` ha rinominato la colonna `quantita_fissa` → `quantita` su `vendite.contratti_righe` per allinearla al pattern delle helper generiche `script.*`. Le migration di adeguamento correlate:

| Migration | Oggetto | Modifica |
|---|---|---|
| `20260511-31` | `contratti_righe` | RENAME `quantita_fissa` → `quantita` |
| `20260511-32` | trigger `qta_from_operativa` | TG_ARGV `'quantita_fissa'` → `'quantita'` |
| `20260511-33` | `fn_list_contratti_da_pushare` | `cr.quantita_fissa` → `cr.quantita` |

**Impatto backend** (aggiornamento manuale richiesto): `contratti_repository.py`, `contratti_service.py`, `views_contratti.py`, `vendite_tools.py`.

---

### Particolarità rispetto alle altre sorgenti

| Aspetto | Valore |
|---|---|
| `billing_account_id` | NOT NULL su `contratti` |
| `utility_id` | NOT NULL su `contratti` (integer, castato a bigint nel resolver) |
| `istanza_utility_id` | NOT NULL su `contratti` — incluso nel `prezzo_resolver_context` JSONB |
| `quantita` nullable | Sì — le righe a consumo hanno `quantita IS NULL`. `fn_contratto_riga_componenti_init` ritorna 0 senza init se NULL |

---

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `riga_contratto_id` | FK alla riga padre (`contratti_righe.id`) con ON DELETE CASCADE |
| `articolo_componente_id` | FK alla riga BoM (`articoli_componenti.id`) |
| `componente_id` | FK all'articolo componente (`articoli.id`) — denormalizzato |
| `coeff_qta_snapshot` | Snapshot `articoli_componenti.coeff_qta` al momento della creazione |
| `quantita` | Calcolata dal trigger `_m50_calcola_quantita` come `coeff_qta_snapshot × quantita_padre` |
| `uom_operativa_id` | UoM **del componente** (non del kit), `NOT NULL` dal 2026-10-02 (`20261002-66`): la valorizza la funzione `_init` dalla UoM dell'articolo componente. Un kit può essere fatto di unità diverse (pezzi, metri, ore); il ripiego sulla UoM del padre è ritirato |
| `prezzo_unitario` | Prezzo del componente (suggerito dal resolver, modificabile L1/L2/L3) |
| `origine_prezzo` | `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE` |
| `prezzo_resolver_context` | JSONB con emittente, BA, data, utility_id, istanza_utility_id |
| `stato_approvazione_prezzo` | Workflow L3: `PENDING`/`APPROVED`/`REJECTED` |

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

Sulla riga padre `contratti_righe` è registrato anche `_z90_propaga_qta_componenti_upd` (AFTER UPDATE OF quantita).

---

### Note operative

- **FK ON DELETE CASCADE**: l'eliminazione di una `contratti_righe` elimina automaticamente tutti i suoi componenti.
- **UNIQUE (riga_contratto_id, articolo_componente_id)**: un componente BoM al massimo una volta per riga padre.
- **Righe a consumo**: `contratti_righe.quantita` nullable — se NULL la fn_init ritorna 0 senza inserire componenti. Il BE deve aggiornare la quantita prima di poter inizializzare.
