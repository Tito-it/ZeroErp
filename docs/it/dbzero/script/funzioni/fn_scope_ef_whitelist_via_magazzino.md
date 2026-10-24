{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_magazzino.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_magazzino`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (magazzino)? La
    --   domanda su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('magazzino', ...), DEFINER, invece di
    --   leggerlo sotto la RLS del padre: una strada sola, e nessuna policy del
    --   padre rieseguita a ogni chiamata. Stesse risposte. Le policy non passano
    --   piu' di qui (20261018-50).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('magazzino', p_magazzino_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adattatore di scope della famiglia magazzino, L''ANCORA: risale da magazzini.id a emittente_fiscale_id e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer come le sorelle via_*. Magazzino inesistente o fuori perimetro (sotto RLS non si vede) -> emittente NULL -> false a whitelist valorizzata (fail-closed). Lo usano le policy di ubicazioni, movimenti, movimenti_attesi, valore_giacenza, inventari, rettifiche, trasferimenti e, per delega, le derivate. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
