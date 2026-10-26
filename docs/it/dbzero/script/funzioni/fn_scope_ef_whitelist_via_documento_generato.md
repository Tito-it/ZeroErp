# ⚙️ Funzione `fn_scope_ef_whitelist_via_documento_generato`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (documento generato)? La
    --   domanda su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('documento_generato', ...), DEFINER, invece di
    --   leggerlo sotto la RLS del padre: una strada sola, e nessuna policy del
    --   padre rieseguita a ogni chiamata. Stesse risposte. Le policy non passano
    --   piu' di qui (20261018-50).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('documento_generato', p_documento_generato_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adattatore di scope per i satelliti di documenti.documenti_generati (documenti_generati_eventi, documenti_generati_file): risale da documento_generato_id all''emittente_fiscale_id (NOT NULL) e delega a script.fn_scope_ef_whitelist — la CANONICA, la stessa che protegge la testata, cosi'' il satellite e il documento non possono divergere. ⛔ Non _via_sr e non _via_efba: questa testata nomina l''emittente per emittente fiscale, e le tre hanno la stessa firma (integer, bigint) — scambiarle compila, gira e confronta due numerazioni diverse, cioe'' risponde quasi sempre false. STABLE e NON security definer, come gli altri fn_scope_*. Documento inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). ⚠️ documenti_generati_file porta storage_key, file_name e sha256: fuori perimetro non si leggono metadati, si leggono le coordinate del PDF di un''altra azienda. Brief: brief-db-perimetro-emittente-righe-documento.md §11.16';
```

</div>

---
{% include-markdown "signature-core.md" %}
