{% include-markdown "it/dbzero/script/manual/fn_scope_coda_lavori_perimetro.md" %}
# ⚙️ Funzione `fn_scope_coda_lavori_perimetro`

```sql
CREATE FUNCTION fn_scope_coda_lavori_perimetro(p_super_admin boolean, p_processo boolean, p_perimetro bigint[], p_run_as text, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_coda_lavori_perimetro(p_super_admin boolean, p_processo boolean, p_perimetro bigint[], p_run_as text, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: chi guarda puo' vedere questo lavoro della coda?
    --   OPERATORE: l'azienda del lavoro e' nel perimetro di chi
    --   guarda. SISTEMA: chi guarda e' il super admin o l'identita'
    --   tecnica del drenatore. Altro: no.
    -- ⚠️ Il drenatore non ha un ramo per i lavori OPERATORE: li
    --   vede col perimetro del suo utente tecnico, un'azienda alla
    --   volta. Un ramo che glieli mostrasse tutti sarebbe una porta
    --   fra le aziende.
    SELECT COALESCE(
        CASE p_run_as
            WHEN 'SISTEMA'   THEN p_super_admin OR p_processo
            WHEN 'OPERATORE' THEN script.fn_scope_ef_perimetro(p_perimetro, p_emittente_fiscale_id)
            ELSE false
        END,
        false)
$function$

COMMENT ON FUNCTION script.fn_scope_coda_lavori_perimetro(p_super_admin boolean, p_processo boolean, p_perimetro bigint[], p_run_as text, p_emittente_fiscale_id bigint)
IS 'La regola di visibilita'' di dbops.coda_lavori, con le tre risposte su chi guarda gia'' calcolate dalla policy una volta per istruzione: super admin (script.fn_is_super_admin), identita'' tecnica viva del drenatore (script.fn_scope_identita_processo con draina_coda_lavori) e perimetro emittenti (script.fn_get_emittenti_scope_pk_ids). OPERATORE: l''azienda del lavoro e'' nel perimetro (script.fn_scope_ef_perimetro; perimetro NULL = tutte). SISTEMA: super admin o drenatore. Altro run_as: false. Il drenatore vede i lavori OPERATORE solo col perimetro del suo utente tecnico, un''azienda alla volta. Pura, non legge tabelle (linee-guida-sql §10.3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
