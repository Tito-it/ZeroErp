{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_commessa.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_commessa`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (commessa)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('commessa', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('commessa', p_commessa_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_commessa(p_auth_user_id integer, p_commessa_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adapter via-commessa dello scope EF_WHITELIST: risolve l''emittente attraverso vendite.commesse e delega a fn_scope_ef_whitelist_via_sr (-> canonica). Per tabelle figlie senza colonna emittente propria (es. vendite.commesse_attivita). STABLE, inlineable. Mirror di fn_scope_ef_whitelist_via_fattura. Brief: brief-db-rls-commesse.';
```

---
{% include-markdown "signature-core.md" %}
