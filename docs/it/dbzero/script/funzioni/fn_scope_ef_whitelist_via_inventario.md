{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_inventario.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_inventario`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (inventario)? La
    --   domanda su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('inventario', ...), DEFINER, invece di
    --   leggerlo sotto la RLS del padre: una strada sola, e nessuna policy del
    --   padre rieseguita a ogni chiamata. Stesse risposte. Le policy non passano
    --   piu' di qui (20261018-50).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('inventario', p_inventario_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id integer, p_inventario_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adattatore di scope per un inventario via il suo magazzino (delega a via_magazzino). Chiave di inventari_righe e delle note note_inventario e note_inventario_riga (dove target_id e'' la testata).';
```

</div>

---
{% include-markdown "signature-core.md" %}
