## 📘 Documentazione Concettuale – Funzione `script.fn_scope_note_magazzino_ef_perimetro`

> 👀 **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_perimetro](/dbzero/script/manual/fn_scope_ef_perimetro) (la funzione di scope col perimetro, a cui ogni ramo chiede)
> [script.fn_resolve_emittente_fiscale_id](/dbzero/script/manual/fn_resolve_emittente_fiscale_id) (l'emittente della testata, per riga)
> [script.fn_scope_note_ef_perimetro](/dbzero/script/funzioni/fn_scope_note_ef_perimetro) (lo stampo, per vendite)
>
**Tabelle correlate:**
>
[magazzino.note](/dbzero/magazzino/tabelle/note)
>
Brief: `brief-db-perimetro-una-volta-famiglie-residue` §4 (P-1); origine
`brief-db-magazzino-lotto-1-terreno-vuoto` (§4.10)

---
### 🎯 Scopo Principale

(rev 2026-10-21, `20261021-25`)

**Lo smistatore delle note di magazzino.** `magazzino.note` è partizionata per
`target_tipo`, e le policy delle **partizioni non risalgono al padre** (provato il 09-09 in
vendite): letto dal padre, senza una policy propria, ogni policy sulle partizioni sarebbe
aggirabile. Questa funzione serve alla policy del padre: dalla famiglia della nota sceglie il
modo con cui risolvere l'emittente della testata, lo stesso che usa la policy della partizione.

| `target_tipo` | Modo del risolutore |
|---|---|
| `ASSET` | `asset` |
| `EVENTO_ASSET` | `evento_asset` |
| `INVENTARIO`, `INVENTARIO_RIGA` | `inventario` |
| `MOVIMENTO` | `movimento` |
| `RETTIFICA`, `RETTIFICA_RIGA` | `rettifica` |
| `TRASFERIMENTO`, `TRASFERIMENTO_RIGA` | `trasferimento` |
| altro | `false` |

⭐ Nelle partizioni `_riga` il `target_id` è la **testata** (la riga sta in
`target_riga_id`): lo scope passa dalla testata anche lì.

### Il perimetro arriva già calcolato

Il perimetro dell'operatore (super admin, veste, whitelist, emittente attivo) non dipende dalla
nota. La policy lo calcola **una volta per istruzione**, in una sottoquery su
`script.fn_get_emittenti_scope_pk_ids`, e lo passa come primo argomento. Per ogni nota resta
solo la risoluzione dell'emittente.

Fino al 2026-10-20 la policy chiamava `script.fn_scope_note_magazzino_ef_whitelist`, che
smistava sugli adattatori `fn_scope_ef_whitelist_via_*`: ognuno ricalcolava il perimetro a ogni
nota letta. Ritirata dal `20261021-27`. Gli adattatori restano per la domanda su un emittente
(verbi, guard, backend).

### L'`ELSE false` è la riga che conta

Un `target_tipo` nuovo e non gestito rende quelle note **invisibili** dal padre, non visibili
a tutti, nemmeno al super admin. Il pgTAP confronta i rami con i confini delle partizioni del padre: quando si
aggiunge un tipo (una partizione), si aggiunge il ramo, e il test lo ricorda.
(Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3): il CHECK `chk_note_target_tipo`, con cui si confrontava prima, è ritirato; al suo posto la FK
verso `config.tipi_entita`.)

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_perimetro` | `bigint[]` | Il perimetro dell'operatore, dalla policy: `NULL` = tutti, `'{}'` = nessuno. |
| `p_target_tipo` | `magazzino.note.target_tipo%TYPE` | La famiglia della nota. |
| `p_target_id` | `magazzino.note.target_id%TYPE` | La testata a cui la nota è appesa. |

Output: `boolean`. Stampo: `fn_scope_note_ef_perimetro` (vendite). Presidi:
`db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql` (test 5, 6 e 12) e
`db/pgtap/script/test-scope-ef-perimetro-una-volta-per-istruzione-v1.sql` (forma e piano).

---

{% include-markdown "signature-core.md" %}
