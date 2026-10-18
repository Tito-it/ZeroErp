# ⚙️ Funzione `fn_scope_ef_whitelist_via_fattura_sdi`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (fattura sdi)? La domanda
    --   su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('fattura_sdi', ...), DEFINER, invece
    --   di leggerlo qui sotto la RLS del padre: la strada documento ->
    --   emittente e' scritta UNA volta (il modo del risolutore), e una
    --   chiamata non riesegue piu' la policy del padre. Stesse risposte: per
    --   l'operatore il padre e' invisibile esattamente quando il suo
    --   emittente e' fuori perimetro, e la canonica lo dice comunque.
    --   Le policy non passano piu' di qui (20261018-33): calcolano il
    --   perimetro una volta per istruzione.
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('fattura_sdi', p_sdi_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
IS '⭐ rev 2026-10-18 (20261018-32, D-3b-2 giro 1b): l''emittente lo chiede a script.fn_resolve_emittente_fiscale_id (DEFINER), non lo legge sotto la RLS del padre: una strada sola, e nessuna policy del padre rieseguita a ogni chiamata. Stesse risposte. Adattatore di scope a due livelli per vendite.fatture_sdi_eventi, veste OPERATORE: risale da fatture_sdi alla fattura e delega a script.fn_scope_ef_whitelist_via_fattura. STABLE e NON security definer, come gli altri fn_scope_*. Trasmissione inesistente -> fattura NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
