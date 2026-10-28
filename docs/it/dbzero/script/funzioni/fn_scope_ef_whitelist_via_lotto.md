# ⚙️ Funzione `fn_scope_ef_whitelist_via_lotto`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (lotto)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('lotto', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('lotto', p_lotto_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_lotto(p_auth_user_id integer, p_lotto_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adattatore di scope per i satelliti di vendite.fatturazione_lotti: risale da lotto_id a `emittente_soggetto_ruolo_id` e delega a script.fn_scope_ef_whitelist_via_sr. ⚠️ Via SR e non la canonica fn_scope_ef_whitelist: la testata dei lotti nomina l''emittente per soggetto-ruolo, come vendite.fatture e a differenza delle sei famiglie di documento — e le due numerazioni non sono confrontabili. STABLE e NON security definer, come gli altri fn_scope_*. Lotto inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.9';
```

</div>

---
{% include-markdown "signature-core.md" %}
