# ⚙️ Funzione `fn_scope_ef_whitelist_via_reso_riga`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (reso riga)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('reso_riga', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('reso_riga', p_riga_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_reso_riga(p_auth_user_id integer, p_riga_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Come fn_scope_ef_whitelist_via_reso ma a partire da una riga di reso: e'' la chiave che portano resi_righe_accrediti, resi_righe_riconsegne e resi_righe_rinunce. ⚠️ Risale dal RESO e non dal DDT: vendite.resi_righe ha due genitori NOT NULL (reso_id e ddt_riga_id) e la riga appartiene al documento di reso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
