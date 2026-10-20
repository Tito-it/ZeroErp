{% include-markdown "it/dbzero/script/manual/fn_check_ba_visible_for_emittenti.md" %}
# ⚙️ Funzione `fn_check_ba_visible_for_emittenti`

```sql
CREATE FUNCTION fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_emittente_sr_id bigint;
BEGIN
    -- Convenzione fn_check_*: pure boolean, nessun raise.

    -- ⚠️ Questo ramo NON e' assorbito dalla delegata. «Nessun
    --   emittente autorizzato» e' una risposta secca, e va data
    --   prima di risolvere alcunche': senza, si finirebbe su
    --   `x = ANY(NULL)` che vale NULL — e un NULL in un WHERE
    --   non nega, sparisce.
    IF p_emittente_ids IS NULL OR array_length(p_emittente_ids, 1) IS NULL THEN
        RETURN false;
    END IF;

    -- La regola a due livelli (mapping specifico -> fallback
    -- default) vive in UN posto solo: 20260818-58. Qui resta
    -- solo la domanda di questa funzione — «e' fra i miei?».
    -- Il BA NULL lo gestisce la delegata, che risponde NULL.
    v_emittente_sr_id := script.fn_get_ba_emittente_sr_id(p_billing_account_id);

    IF v_emittente_sr_id IS NULL THEN
        RETURN false;
    END IF;

    RETURN v_emittente_sr_id = ANY(p_emittente_ids);
END
$function$

COMMENT ON FUNCTION script.fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
IS 'Pure check (fn_check_*, boolean, no raise): un billing_account e'' visibile per un set di emittenti autorizzati? Rev 2026-08-18 (R-5, brief perimetro-emittente Fase E): la regola «quale emittente fattura questo BA» NON e'' scritta qui. Vive in script.fn_get_ba_emittente_sr_id, e questa funzione si limita a chiedere «l''emittente risolto sta fra quelli autorizzati?». ⭐ Dal 20260913-01 (D13) quella regola ha TRE livelli — mapping specifico; altrimenti, in sessione, l''emittente dell''operatore che sta agendo; altrimenti il default — e questo check li eredita senza una riga di modifica: e'' il motivo per cui la regola sta in un posto solo. ⚠️ p_emittente_ids NULL o vuoto = «nessun emittente autorizzato» = false, e la risposta arriva prima di risolvere: e'' il ramo fail-closed. ⚠️ STABLE e NON PARALLEL SAFE dal 20260913-02: la delegata legge la GUC di sessione e chiama fn_resolve_emittente_for_user, che non e'' SAFE — la marcatura si dichiara onestamente, come gia'' il 18-08 sulla ricerca universale. Usata da fn_search_soggetti_universale e fn_get_search_detail (ramo CL) e dalla policy RLS via_efba del billing account. Brief: brief-db-ba-riserva-emittente-operatore-d13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
