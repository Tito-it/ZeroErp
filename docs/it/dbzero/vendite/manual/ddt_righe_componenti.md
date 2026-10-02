## 📘 Documentazione Concettuale – Tabella `vendite.ddt_righe_componenti`

> 👀 **Vedi anche**
>
> **Tabelle correlate:**
>
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) — riga padre composita (FK ON DELETE CASCADE)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — riga BoM (`articolo_componente_id`)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — articolo componente (`componente_id`)
> • [config.iva](/dbzero/config/tabelle/iva) — aliquota IVA del componente
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — UoM operativa del componente
> • [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica approvazione prezzo L3
>
> **Funzioni/trigger correlati:**
>
> • [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init) — popola i componenti dopo INSERT riga padre
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

`vendite.ddt_righe_componenti` modella il **prezzo negoziabile per singolo componente** di un articolo composito CASO A nell'ambito di un DDT: una riga per ogni componente attivo e valido della distinta (modello unificato del 2026-05-13). L'esposizione del componente in fattura (`catalogo.articoli_componenti.esposizione_in_fattura`) è una regola di presentazione della fattura, non un filtro su queste righe.

Per ogni riga padre composita CASO A in `ddt_righe`, questa tabella contiene **N righe figlie** (una per componente attivo della distinta), ciascuna con prezzo proprio soggetto ai meccanismi di approvazione L1/L2/L3. Il prezzo della riga padre viene aggiornato automaticamente come `SUM(prezzo_unitario_comp × coeff_qta_snapshot)` tramite trigger.

Il modello garantisce snapshot pricing: al push su commessa i prezzi vengono propagati direttamente da questa tabella, **senza ri-invocare il resolver di listino**.

---

### Modello BoM CASO A

Dal modello unificato del 2026-05-13 la distinzione dipende solo dall'articolo (`catalogo.articoli.is_composito`), e la applica `vendite.fn_ddt_riga_componenti_init`:

| Caso | Condizione | Modello |
|---|---|---|
| **CASO A** | articolo composito (`is_composito = TRUE`) | N righe in `ddt_righe_componenti`, una per componente attivo e valido, prezzo padre calcolato |
| **CASO B** | articolo non composito | Riga padre con prezzo unico, nessuna riga componente |

Fino al 2026-05-13 il CASO A era «≥ 1 componente con `esposto_in_fattura = TRUE`»; quel flag è diventato una regola di presentazione, e dal 2026-10-01 è `esposizione_in_fattura` a tre modi (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`), letto dalla vista di rappresentazione della fattura.

Questa tabella è **solo CASO A**. Per CASO B la riga padre ha il prezzo direttamente e non genera figli.

---

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `riga_ddt_id` | FK alla riga padre (`ddt_righe.id`) con ON DELETE CASCADE |
| `articolo_componente_id` | FK alla riga BoM (`articoli_componenti.id`) — identifica il componente nella distinta base |
| `componente_id` | FK all'articolo componente (`articoli.id`) — denormalizzato per query dirette, coerenza garantita da guard |
| `coeff_qta_snapshot` | Snapshot di `articoli_componenti.coeff_qta` al momento della creazione — isolato da evoluzioni BoM future |
| `quantita` | Calcolata dal trigger `_m50_calcola_quantita` come `coeff_qta_snapshot × quantita_padre` |
| `prezzo_unitario` | Prezzo del componente (suggerito dal resolver, modificabile dall'operatore L1/L2/L3). ⚠️ **Può mancare** dal 2026-08-19, vedi sotto |
| `origine_prezzo` | Traccia l'origine: `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE`, `LISTINO_BUNDLE`. ⚠️ **Può mancare** insieme al prezzo |
| `prezzo_resolver_context` | JSONB con contesto chiamata resolver (emittente, BA, data, utility); in fallback contiene `error`/`sqlstate` |
| `stato_approvazione_prezzo` | ENUM `config.stato_approvazione_prezzo` per workflow L3: `PENDING`/`APPROVED`/`REJECTED` |

---

### Relazione con la riga padre

> ## ⚠️ Rev 2026-08-19 — su QUESTA tabella il prezzo può mancare
>
> `prezzo_unitario` e `origine_prezzo` sono diventati **facoltativi**, e solo
> qui: sulle gemelle di preventivi, ordini, contratti e offerte restano
> obbligatori — lì un prezzo mancante è un difetto vero.
>
> **Perché.** Un kit è merce come il resto, e la merce si muove anche quando non
> si vende: conto visione, campionatura, riparazione, trasferimento. Su quei
> documenti pretendere un prezzo per ogni componente significa chiedere un dato
> che per essi non ha significato. Era l'ultima ragione per cui un kit non
> poteva viaggiare senza vendersi.
>
> **Le due colonne mancano sempre insieme**: nessun prezzo, nessuna origine. Non
> esiste un valore `NON_RISOLTO` — sarebbe entrato nel vocabolario di cinque
> tabelle per dire ciò che l'assenza dice già. Il motivo tecnico della mancata
> risoluzione sta in `prezzo_resolver_context->>'esito_codice'`.
>
> ⛔ **E il prezzo del padre diventa `NULL`, non la somma dei figli rimasti.** Un
> kit a prezzo assente lo ferma il gate all'emissione; un kit a prezzo
> **parziale** il gate lo passa e arriva in fattura. Vedi
> [script.fn_ricalcola_prezzo_padre_da_componenti](/dbzero/script/funzioni/fn_ricalcola_prezzo_padre_da_componenti).
>
> **Cosa resta in piedi**: il divieto del prezzo **zero** sui componenti
> obbligatori vale ancora — ma solo se il DDT ha una causale fatturabile
> (clausola `WHEN` del trigger, su
> [vendite.fn_check_ddt_riga_richiede_prezzo](/dbzero/vendite/funzioni/fn_check_ddt_riga_richiede_prezzo)).
> E il gate all'emissione ferma comunque il DDT che vende con componenti non
> valorizzati.

Il prezzo sulla riga padre (`ddt_righe.prezzo_unitario`) è **calcolato automaticamente** come SUM pesata dei componenti, tramite il trigger `z90_ricalcola_padre`:

```
ddt_righe.prezzo_unitario = SUM(
    ddt_righe_componenti.prezzo_unitario
    × ddt_righe_componenti.coeff_qta_snapshot
) WHERE attivo = TRUE
```

Note: `ddt_righe.prezzo_unitario` è nullable. Il trigger aggiorna comunque la colonna con il valore calcolato; se non ci sono componenti attivi il risultato è 0.

---

### Differenze rispetto a `preventivi_righe_componenti`

| Aspetto | Preventivi | DDT |
|---|---|---|
| Guard L3 PENDING | ✅ implementato | ❌ Non ancora implementato |
| `utility_id` sulla testata | ✅ disponibile | ✅ disponibile (tipo `integer`) |
| Numero trigger | 8 | 7 |

Il guard L3 specifico per DDT verrà aggiunto in una PR separata al completamento del workflow approvazione prezzi su questa sorgente.

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

Sulla riga padre `ddt_righe` è registrato anche `_z90_propaga_qta_componenti_upd` (AFTER UPDATE OF quantita) per mantenere allineate le quantita dei componenti.

---

### Note operative

- **FK ON DELETE CASCADE**: l'eliminazione di una `ddt_righe` elimina automaticamente tutti i suoi componenti.
- **UNIQUE (riga_ddt_id, articolo_componente_id)**: un componente BoM può comparire al massimo una volta per riga padre.
- **`componente_id` denormalizzato**: ridondanza permette JOIN diretti a `catalogo.articoli` senza passare per `articoli_componenti`.
- **`meta`**: campo JSONB NOT NULL (default `{}`), riservato per estensioni future senza migrazioni.
- **Indice parziale su `stato_approvazione_prezzo`**: filtra i NULL per contenere l'indice alle sole righe in workflow.
