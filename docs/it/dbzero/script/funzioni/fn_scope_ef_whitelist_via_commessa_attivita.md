# ⚙️ Funzione `fn_scope_ef_whitelist_via_commessa_attivita`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (commessa attivita)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('commessa_attivita', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('commessa_attivita', p_commessa_attivita_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adattatore di scope per i satelliti di vendite.commesse_attivita (oggi: commesse_attivita_log): risale da commessa_attivita_id alla commessa e delega a script.fn_scope_ef_whitelist_via_commessa — la stessa che protegge commesse_attivita, cosi'' il diario e la riga che racconta non possono divergere. STABLE e NON security definer, come gli altri fn_scope_*. ⛔ Stessa firma di _via_commessa e chiavi entrambe bigint: scambiarle compila e gira, e nel verso negativo sembra pure funzionare — lo presidia il verso POSITIVO del pgTAP. Riga inesistente -> commessa NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.15';
```

</div>

---
{% include-markdown "signature-core.md" %}
