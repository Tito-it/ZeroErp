{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_evento_stato_corrente_cliente.md" %}
# ⚙️ Funzione `fn_get_evento_stato_corrente_cliente`

```sql
CREATE FUNCTION fn_get_evento_stato_corrente_cliente(p_cliente_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id bigint)
 RETURNS TABLE(data_evento_stato date, tipo_evento text)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
-- Scopo: ricavare l'ultimo evento sosp/riatt del cliente
-- per la detail page. Output a 2 colonne (data + codice
-- evento), niente label di stato (gia' in stato_cliente_id).
DECLARE
    v_data_sosp anagrafiche.clienti.data_sospensione%TYPE;
    v_data_riat anagrafiche.clienti.data_riattivazione%TYPE;
BEGIN
    -- Guard: parametro obbligatorio.
    IF p_cliente_id IS NULL OR p_cliente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_get_evento_stato_corrente_cliente',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_cliente_id',
                'valore',    p_cliente_id
            ),
            NULL::uuid,
            'p_cliente_id obbligatorio e > 0'
        );
    END IF;

    -- Lookup date evento. Se cliente non esiste ->
    -- E_VALORE_MANCANTE (pattern coerente con
    -- vendite.fn_get_commessa_stato).
    SELECT c.data_sospensione, c.data_riattivazione
      INTO v_data_sosp, v_data_riat
      FROM anagrafiche.clienti c
     WHERE c.id = p_cliente_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_get_evento_stato_corrente_cliente',
            'E_VALORE_MANCANTE',
            jsonb_build_object('cliente_id', p_cliente_id),
            NULL::uuid,
            concat('cliente_id ', p_cliente_id)
        );
    END IF;

    -- Dispatch sui 4 casi date NOT NULL combinations.
    -- Pareggio: vince RIATTIVAZIONE (operazione successiva
    -- nel flow normale). Caso anomalo (riatt senza sosp):
    -- ritorna comunque RIATTIVAZIONE — la fn legge, non
    -- valida consistenza.
    IF v_data_sosp IS NULL AND v_data_riat IS NULL THEN
        RETURN QUERY SELECT NULL::date, NULL::text;
    ELSIF v_data_sosp IS NOT NULL AND v_data_riat IS NULL THEN
        RETURN QUERY SELECT v_data_sosp, 'SOSPENSIONE'::text;
    ELSIF v_data_sosp IS NULL AND v_data_riat IS NOT NULL THEN
        RETURN QUERY SELECT v_data_riat, 'RIATTIVAZIONE'::text;
    ELSIF v_data_sosp > v_data_riat THEN
        RETURN QUERY SELECT v_data_sosp, 'SOSPENSIONE'::text;
    ELSE
        -- v_data_sosp <= v_data_riat: vince RIATTIVAZIONE
        RETURN QUERY SELECT v_data_riat, 'RIATTIVAZIONE'::text;
    END IF;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id bigint)
IS 'Restituisce (data_evento_stato, tipo_evento) confrontando data_sospensione vs data_riattivazione del cliente. tipo_evento: SOSPENSIONE | RIATTIVAZIONE | NULL. Pareggio = RIATTIVAZIONE. Caso anomalo (riatt senza sosp) ritorna RIATTIVAZIONE (no validation).';
```

</div>

---
{% include-markdown "signature-core.md" %}
