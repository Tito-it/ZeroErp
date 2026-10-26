{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_fattura.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_fattura`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (fattura)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('fattura', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('fattura', p_fattura_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id integer, p_fattura_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adapter via-fattura dello scope EF_WHITELIST: risolve l''emittente attraverso vendite.fatture e delega a fn_scope_ef_whitelist_via_sr (-> canonica). Per tabelle figlie senza colonna emittente propria (es. vendite.fatture_scadenze). STABLE, inlineable.';
```

</div>

---
{% include-markdown "signature-core.md" %}
