{% include-markdown "it/dbzero/pratiche/manual/fn_valuta_tempo_esecuzione_da_a.md" %}
# ⚙️ Funzione `fn_valuta_tempo_esecuzione_da_a`

```sql
CREATE FUNCTION fn_valuta_tempo_esecuzione_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_valuta_tempo_esecuzione_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
 RETURNS TABLE(giorni_netti integer, giorni_esecuzione integer, giorni_rimanenti integer, stato_tempo text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: confronta il tempo netto tra due flussi con la formula configurata.
-- Output: giorni_netti, giorni_esecuzione, giorni_rimanenti, stato_tempo (OK/WARNING/CRITICO/SFORATO).
-- Se non esiste formula configurata, restituisce NULL (nessuna valutazione).
DECLARE
    v_tipo_prestazione_id pratiche.pratiche.tipo_prestazione_id%TYPE;
    v_template_da_id      pratiche.flussi.template_flusso_id%TYPE;
    v_template_a_id       pratiche.flussi.template_flusso_id%TYPE;
    v_formula             RECORD;
    v_giorni_netti        INTEGER;
    v_giorni_rimanenti    INTEGER;
BEGIN
    -- Recupera tipo_prestazione della pratica
    SELECT p.tipo_prestazione_id INTO v_tipo_prestazione_id
    FROM pratiche.pratiche p WHERE p.id = p_pratica_id;

    -- Recupera template_flusso_id dei due flussi
    SELECT f.template_flusso_id INTO v_template_da_id
    FROM pratiche.flussi f WHERE f.id = p_flusso_da_id;

    SELECT f.template_flusso_id INTO v_template_a_id
    FROM pratiche.flussi f WHERE f.id = p_flusso_a_id;

    -- Se uno dei due flussi non ha template, nessuna valutazione
    IF v_template_da_id IS NULL OR v_template_a_id IS NULL THEN
        RETURN;
    END IF;

    -- Cerca la formula matching
    SELECT ft.giorni_esecuzione, ft.giorni_warning, ft.giorni_critico
    INTO v_formula
    FROM pratiche.formule_tempo ft
    WHERE ft.tipo_prestazione_id = v_tipo_prestazione_id
      AND ft.template_flusso_da_id = v_template_da_id
      AND ft.template_flusso_a_id = v_template_a_id
      AND ft.attivo = true;

    -- Se non esiste formula, nessuna valutazione
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Calcola giorni netti
    v_giorni_netti := pratiche.fn_calcola_tempo_netto_da_a(
        p_pratica_id, p_flusso_da_id, p_flusso_a_id);

    IF v_giorni_netti IS NULL THEN
        RETURN;
    END IF;

    v_giorni_rimanenti := v_formula.giorni_esecuzione - v_giorni_netti;

    -- Determina stato tempo
    giorni_netti      := v_giorni_netti;
    giorni_esecuzione := v_formula.giorni_esecuzione;
    giorni_rimanenti  := v_giorni_rimanenti;

    IF v_giorni_rimanenti <= 0 THEN
        stato_tempo := 'SFORATO';
    ELSIF v_giorni_rimanenti <= v_formula.giorni_critico THEN
        stato_tempo := 'CRITICO';
    ELSIF v_giorni_rimanenti <= v_formula.giorni_warning THEN
        stato_tempo := 'WARNING';
    ELSE
        stato_tempo := 'OK';
    END IF;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_valuta_tempo_esecuzione_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
IS 'Check pura STABLE: valuta tempo netto tra due flussi vs formula configurata. Ritorna OK/WARNING/CRITICO/SFORATO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
