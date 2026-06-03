## 📘 Documentazione Concettuale – Tabella `vendite.offerte_commerciali_eccezioni_componenti`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> • [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) — eccezione padre (FK ON DELETE CASCADE)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — riga BoM (`articolo_componente_id`)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — articolo componente (`componente_id`)
> • [config.iva](/dbzero/config/tabelle/iva) — aliquota IVA del componente
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — UoM operativa del componente
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica approvazione prezzo L3
> • [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — mirror strutturale nel dominio contratti
>
> **Funzioni/trigger correlati:**
>
> • [vendite.fn_offerta_eccezione_componenti_init](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_init) — popola i componenti dopo INSERT eccezione
> • [vendite.fn_offerta_eccezione_componenti_preview](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_preview) — preview read-only per il drawer
> • [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — copia i componenti su contratti_righe_componenti al push
> • [script.trgfn_componenti_guard_pending](/dbzero/script/funzioni/trgfn_componenti_guard_pending) — guard L3 generico (TG_ARGV[0] = `'eccezione_offerta_id'`)
> • [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_componenti_guard_coerenza_bom) — guard BoM
> • [script.trgfn_componenti_ricalcola_padre](/dbzero/script/funzioni/trgfn_componenti_ricalcola_padre) — aggiorna prezzo eccezione padre
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
> • [Analisi offerte commerciali — §A](/dev/work-done/analisi-offerta-commerciale-db)

---

### 🎯 Scopo Principale

(rev 2026-05-26)

`vendite.offerte_commerciali_eccezioni_componenti` modella il **prezzo negoziabile per
singolo componente** di un articolo composito CASO A nell'ambito di un'eccezione offerta
commerciale. È il **mirror strutturale di `contratti_righe_componenti`** per il dominio
offerte, con le differenze intenzionali elencate di seguito.

---

### Differenze rispetto a `contratti_righe_componenti`

| Aspetto | `contratti_righe_componenti` | `offerte_commerciali_eccezioni_componenti` |
|---|---|---|
| FK padre | `riga_contratto_id → contratti_righe(id)` | `eccezione_offerta_id → offerte_commerciali_eccezioni(id)` |
| Colonna `attivo` | Presente (`DEFAULT true`) | **Assente** — in offerta tutti i componenti sono sempre visibili |
| Colonna `ordine` | Presente (`DEFAULT 0`) | **Assente** |
| Colonna `meta` | Presente (`DEFAULT '{}'::jsonb`) | **Assente** |
| `stato_approvazione_prezzo` | Popolato in fase di negoziazione contratto | **Trasportato 1:1 dal push** offerta→contratto (NULL ammesso) |
| `pratica_approvazione_prezzo_id` | Collegato al workflow L3 contratto | **Trasportato 1:1 dal push** (NULL ammesso) |
| Guard pending | `trgfn_componenti_guard_pending('riga_contratto_id')` | `trgfn_componenti_guard_pending('eccezione_offerta_id')` |

La simmetria strutturale garantisce che `fn_push_offerta_a_contratto` (rev3) copi i
componenti con una singola INSERT senza conversioni di colonne.

---

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `eccezione_offerta_id` | FK alla eccezione padre (`offerte_commerciali_eccezioni.id`) con ON DELETE CASCADE |
| `articolo_componente_id` | FK alla riga BoM (`articoli_componenti.id`) — chiave override in `fn_offerta_eccezione_componenti_init` |
| `componente_id` | FK all'articolo componente (`articoli.id`) — denormalizzato |
| `coeff_qta_snapshot` | Snapshot `articoli_componenti.coeff_qta` al momento della creazione |
| `quantita` | Calcolata dal trigger `_m50_calcola_quantita` come `coeff_qta_snapshot × quantita_padre` |
| `prezzo_unitario` | Prezzo del componente (suggerito dal resolver, modificabile L1/L2) |
| `origine_prezzo` | `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE` |
| `prezzo_resolver_context` | JSONB con emittente, BA, data, utility_id, istanza_utility_id |
| `stato_approvazione_prezzo` | NULL ammesso; se presente, trasportato 1:1 al push → contratto |

---

### Trigger registrati

| Trigger | Timing | Fase | Funzione |
|---|---|---|---|
| `_a10_guard_bom_coerenza_ins_upd` | BEFORE INS/UPD | `_a10_` | `script.trgfn_componenti_guard_coerenza_bom` |
| `_a10_guard_obbligatorio_upd` | BEFORE UPD | `_a10_` | `script.trgfn_componenti_guard_obbligatorio` |
| `_a10_guard_pending_upd` | BEFORE UPD | `_a10_` | `script.trgfn_componenti_guard_pending('eccezione_offerta_id')` |
| `_a10_prezzo_obbligatorio_ins_upd` | BEFORE INS/UPD | `_a10_` | `script.trgfn_componenti_check_prezzo_obbligatorio` |
| `_m50_calcola_quantita_ins_upd` | BEFORE INS/UPD | `_m50_` | `script.trgfn_componenti_calcola_quantita` |
| `_audit_data_user_ins_upd` | BEFORE INS/UPD | — | `script.trgfn_audit_data_user_generic` |
| `_gen_tx_id_ins_upd` | BEFORE INS/UPD | — | `dbops.trgfn_tx_id_managed` |
| `_a10_articoli_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_a10_iva_require_attivo_ins_upd` | AFTER INS/UPD | `_a10_` | `dbops.trgfn_child_requires_active_parent` |
| `_z90_ricalcola_padre_ins_upd_dlt` | AFTER INS/UPD/DLT | `_z90_` | `script.trgfn_componenti_ricalcola_padre` |

Sulla eccezione padre `offerte_commerciali_eccezioni` è registrato anche
`_z90_propaga_qta_componenti_upd` (AFTER UPDATE OF quantita) via
`script.trgfn_componenti_propaga_qta`.

---

### Note operative

- **FK ON DELETE CASCADE**: l'eliminazione di una `offerte_commerciali_eccezioni` elimina automaticamente tutti i suoi componenti.
- **UNIQUE (eccezione_offerta_id, articolo_componente_id)**: un componente BoM al massimo una volta per eccezione padre.
- **Solo componenti `esposto_in_fattura = TRUE`**: `fn_offerta_eccezione_componenti_init` filtra la BoM per questo flag (CASO A). Non tutti i componenti della distinta vengono inseriti — solo quelli rilevanti per la fatturazione.
- **`stato_approvazione_prezzo` NULL di default**: il workflow L3 sulle offerte non è attivo; il campo è presente per trasporto 1:1 al momento del push offerta→contratto, preservando eventuali approvazioni pre-negoziazione.
- **Copia 1:1 al push**: `fn_push_offerta_a_contratto` (rev3) copia tutti i componenti in `contratti_righe_componenti` con `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` intatti. Il contratto DRAFT acquisisce i componenti già valutati.
