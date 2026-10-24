## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_evento_asset`

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

Il perimetro di un **evento asset**, via l'asset: un evento può non avere magazzino,
l'asset ha sempre un emittente.

### Catena di risoluzione

`eventi_assets.id` → `eventi_assets.asset_id` → `via_asset`.

### Chi la usa

La policy di `note_evento_asset` e lo smistatore per `EVENTO_ASSET`. (La policy di
`eventi_assets` usa `via_asset` direttamente, sulla colonna `asset_id`.)

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

ChangeSet `20261018-49`: l'emittente dal risolutore (modo `evento_asset`). Le policy non la chiamano più (`20261018-50`):
calcolano il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Resta per la domanda su **un**
emittente. Brief `brief-db-plancache-funzioni-con-query-incorporate` §5quinquies
(ondata 2).

{% include-markdown "signature-core.md" %}
