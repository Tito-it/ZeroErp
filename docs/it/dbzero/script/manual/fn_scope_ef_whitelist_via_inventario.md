## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_inventario`

> 👀 **Vedi anche**
>
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Funzioni correlate:**
>
[script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) (la canonica, a cui tutte delegano)
> [script.fn_scope_ef_whitelist_via_magazzino](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_magazzino) (l'ancora del dominio)
> [script.fn_scope_ef_whitelist_via_asset](/dbzero/script/funzioni/fn_scope_ef_whitelist_via_asset) (la seconda ancora)
> [script.fn_scope_note_magazzino_ef_perimetro](/dbzero/script/manual/fn_scope_note_magazzino_ef_perimetro) (lo smistatore delle note)
>
**Tabelle correlate:**
>
[magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.10)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

Il perimetro di un **inventario**, via il suo magazzino.

### Catena di risoluzione

`inventari.id` → `inventari.magazzino_id` → `via_magazzino`.

### Chi la usa

Le policy di `inventari_righe` (`inventario_id`), `note_inventario` e `note_inventario_riga`
(in entrambe `target_id` è la testata), e lo smistatore per `INVENTARIO` e `INVENTARIO_RIGA`.

### La forma, comune a tutta la famiglia

`LANGUAGE sql`, `STABLE`, **non** `SECURITY DEFINER`: una funzione definer dentro una policy
guarderebbe con gli occhi dell'owner, che la RLS non vede. La risalita alla testata vive in
un posto solo (`via_magazzino`) e le derivate **delegano**: se cambia il modo in cui un
magazzino nomina il proprio emittente, si corregge in una riga.

**Fail-closed per costruzione**: chiave inesistente → emittente `NULL` → la canonica risponde
`false` a whitelist valorizzata. E sotto RLS un magazzino fuori perimetro non si vede da
dentro la policy, quindi risolve `NULL`: la stessa cosa.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_auth_user_id` | `integer` | Utente applicativo (dal GUC `app.current_user_id`). Resta `integer` (riferimento a `django.auth_user`: `%TYPE` non ammesso). |
| la chiave | `<tabella>.id%TYPE` | La riga da cui si risale. |

Output: `boolean`, l'esito della canonica.

Presidio: `db/pgtap/rls/test-rls-magazzino-perimetro-v1.sql`.

---

### ⭐ rev 2026-10-18 — non sta più nelle policy

ChangeSet `20261018-49`: l'emittente dal risolutore (modo `inventario`). Le policy non la chiamano più (`20261018-50`):
calcolano il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Resta per la domanda su **un**
emittente. Brief `brief-db-plancache-funzioni-con-query-incorporate` §5quinquies
(ondata 2).

{% include-markdown "signature-core.md" %}
