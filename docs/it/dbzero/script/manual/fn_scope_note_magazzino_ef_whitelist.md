## 📘 Documentazione Concettuale – Funzione `script.fn_scope_note_magazzino_ef_whitelist`

> 👀 **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (la canonica, a cui tutte delegano)
> [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) (l'ancora del dominio)
> [script.fn_scope_ef_whitelist_via_asset](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_asset) (la seconda ancora)
> [script.fn_scope_note_magazzino_ef_whitelist](/dbzero/script/funzioni/fn_scope_note_magazzino_ef_whitelist) (lo smistatore delle note)
>
**Tabelle correlate:**
>
[magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.10)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Lo smistatore delle note di magazzino.** `magazzino.note` è partizionata per
`target_tipo`, e le policy delle **partizioni non risalgono al padre** (provato il 09-09 in
vendite): letto dal padre, senza una policy propria, ogni policy sulle partizioni sarebbe
aggirabile. Questa funzione serve alla policy del padre: sceglie l'adattatore dalla famiglia
della nota e gli passa `target_id`.

| `target_tipo` | Adattatore |
|---|---|
| `ASSET` | `via_asset` |
| `EVENTO_ASSET` | `via_evento_asset` |
| `INVENTARIO`, `INVENTARIO_RIGA` | `via_inventario` |
| `MOVIMENTO` | `via_movimento` |
| `RETTIFICA`, `RETTIFICA_RIGA` | `via_rettifica` |
| `TRASFERIMENTO`, `TRASFERIMENTO_RIGA` | `via_trasferimento` |
| altro | `false` |

⭐ Nelle partizioni `_riga` il `target_id` è la **testata** (la riga sta in
`target_riga_id`): lo scope passa dalla testata anche lì.

### L'`ELSE false` è la riga che conta

Un `target_tipo` nuovo e non gestito rende quelle note **invisibili** dal padre, non visibili
a tutti. Il pgTAP confronta i rami con il CHECK `chk_note_target_tipo` del padre: quando si
aggiunge un tipo, si aggiunge il ramo, e il test lo ricorda.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). |
| `p_target_tipo` | `magazzino.note.target_tipo%TYPE` | La famiglia della nota. |
| `p_target_id` | `magazzino.note.target_id%TYPE` | La testata a cui la nota è appesa. |

Output: `boolean`. Stampo: `fn_scope_note_ef_whitelist` (vendite). Presidio:
`db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql` (test 5, 6 e 12).

---

{% include-markdown "signature-core.md" %}
