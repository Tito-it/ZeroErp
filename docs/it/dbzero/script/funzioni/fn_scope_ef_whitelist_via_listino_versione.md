# ⚙️ Funzione `fn_scope_ef_whitelist_via_listino_versione`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (listino versione)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('listino_versione', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('listino_versione', p_versione_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adattatore di scope per i satelliti di vendite.listini_versioni (listini_righe, listini_righe_componenti): risale da listino_versione_id al listino e delega a script.fn_scope_ef_whitelist_via_listino — la stessa che protegge listini_versioni, cosi'' la riga e la sua versione non possono divergere. STABLE e NON security definer, come gli altri fn_scope_*. Versione inesistente -> listino NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.11';
```

---
{% include-markdown "signature-core.md" %}
