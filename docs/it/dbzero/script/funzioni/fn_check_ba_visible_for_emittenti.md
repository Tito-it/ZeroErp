# ⚙️ Funzione `fn_check_ba_visible_for_emittenti`

```sql
CREATE FUNCTION fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ba_visible_for_emittenti(p_billing_account_id bigint, p_emittente_ids bigint[])
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
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
IS 'Pure check (fn_check_*, boolean, no raise): un billing_account e'' visibile per un set di emittenti autorizzati? Rev 2026-08-18 (R-5, brief perimetro-emittente Fase E): la regola a due livelli — mapping specifico BA->emittente, altrimenti fallback sull''emittente is_default — NON e'' piu'' scritta qui. Vive in script.fn_get_ba_emittente_sr_id, e questa funzione si limita a chiedere «l''emittente risolto sta fra quelli autorizzati?». Risposta identica alla versione precedente: l''equivalenza e'' garantita dai due indici UNIVOCI (uq_emittenti_fiscali_ba, uq_emittenti_fiscali_ba_default), che rendono sia il mapping sia il default al massimo uno. ⭐ Il motivo dell''estrazione: R-5 deve MOSTRARE il nome dell''emittente nella riga di ricerca, non filtrarci sopra. Senza estrarre, la stessa regola sarebbe finita in due copie — il filtro e l''etichetta — che alla prima modifica avrebbero iniziato a raccontare cose diverse sullo stesso billing account, in silenzio. ⚠️ p_emittente_ids NULL o vuoto = «nessun emittente autorizzato» = false, e la risposta arriva prima di risolvere: e'' il ramo fail-closed. Usata da fn_search_soggetti_universale e fn_get_search_detail (ramo CL).';
```

---
{% include-markdown "signature-core.md" %}
