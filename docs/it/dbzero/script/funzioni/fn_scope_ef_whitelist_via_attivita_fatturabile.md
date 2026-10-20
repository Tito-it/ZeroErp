# ⚙️ Funzione `fn_scope_ef_whitelist_via_attivita_fatturabile`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (attivita fatturabile)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('attivita_fatturabile', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('attivita_fatturabile', p_attivita_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id integer, p_attivita_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Perimetro emittente di una vendite.attivita_fatturabili, risalendo a `commessa_id` (NOT NULL) e delegando a script.fn_scope_ef_whitelist_via_commessa. ⛔ Non si usa `billing_account_id`, che e'' nullable: una policy su una chiave nullable ha un buco esatto dove il NULL passa (brief §6.1). ⚠️ Serve a proteggere le NOTE di attivita'' fatturabile: la tabella attivita_fatturabili resta il debito dichiarato del §6.1. Brief: brief-db-perimetro-emittente-righe-documento.md';
```

</div>

---
{% include-markdown "signature-core.md" %}
