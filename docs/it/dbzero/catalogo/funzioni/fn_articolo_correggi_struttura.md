{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_correggi_struttura.md" %}
# ⚙️ Funzione `fn_articolo_correggi_struttura`

```sql
CREATE FUNCTION fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    c_ammessi CONSTANT text[] := ARRAY[
        'is_composito', 'is_solo_componente', 'natura_vendita_id',
        'causale_onere_id', 'listino_tipologia_id',
        'gestito_a_magazzino', 'requires_lotto', 'requires_serial'];
    v_codice   catalogo.articoli.codice%TYPE;
    v_estranee text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Correggere i flag strutturali di un articolo anche se
    --   usato. Solo SUPER_ADMIN. Ordine: permesso, parametri,
    --   articolo, scrittura con la porta aperta.
    -- =========================================================
    PERFORM script.fn_guard_super_admin(
        NULLIF(current_setting('app.current_user_id', true), '')::integer);

    IF p_campi IS NULL OR jsonb_typeof(p_campi) <> 'object' OR p_campi = '{}'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_campi', 'valore', p_campi),
            NULL::uuid,
            'p_campi: un oggetto con almeno una colonna');
    END IF;

    SELECT string_agg(k, ', ' ORDER BY k)
      INTO v_estranee
      FROM jsonb_object_keys(p_campi) k
     WHERE k <> ALL (c_ammessi);
    IF p_campi IS NULL OR v_estranee IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_campi', 'non_ammesse', v_estranee),
            NULL::uuid,
            'p_campi: colonne non correggibili da qui: ' || v_estranee);
    END IF;

    SELECT a.codice INTO v_codice
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id
       FOR UPDATE;
    IF p_articolo_id IS NULL OR v_codice IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_ARTICOLO_NOT_FOUND',
            jsonb_build_object('articolo_id', p_articolo_id),
            NULL::uuid,
            COALESCE(p_articolo_id::text, '<null>'));
    END IF;

    PERFORM set_config('zeroerp.articolo_correggi_struttura', p_articolo_id::text, true);

    UPDATE catalogo.articoli a
       SET is_composito         = CASE WHEN p_campi ? 'is_composito'
                                       THEN (p_campi ->> 'is_composito')::boolean
                                       ELSE a.is_composito END,
           is_solo_componente   = CASE WHEN p_campi ? 'is_solo_componente'
                                       THEN (p_campi ->> 'is_solo_componente')::boolean
                                       ELSE a.is_solo_componente END,
           natura_vendita_id    = CASE WHEN p_campi ? 'natura_vendita_id'
                                       THEN (p_campi ->> 'natura_vendita_id')::bigint
                                       ELSE a.natura_vendita_id END,
           causale_onere_id     = CASE WHEN p_campi ? 'causale_onere_id'
                                       THEN (p_campi ->> 'causale_onere_id')::bigint
                                       ELSE a.causale_onere_id END,
           listino_tipologia_id = CASE WHEN p_campi ? 'listino_tipologia_id'
                                       THEN (p_campi ->> 'listino_tipologia_id')::smallint
                                       ELSE a.listino_tipologia_id END,
           gestito_a_magazzino  = CASE WHEN p_campi ? 'gestito_a_magazzino'
                                       THEN (p_campi ->> 'gestito_a_magazzino')::boolean
                                       ELSE a.gestito_a_magazzino END,
           requires_lotto       = CASE WHEN p_campi ? 'requires_lotto'
                                       THEN (p_campi ->> 'requires_lotto')::boolean
                                       ELSE a.requires_lotto END,
           requires_serial      = CASE WHEN p_campi ? 'requires_serial'
                                       THEN (p_campi ->> 'requires_serial')::boolean
                                       ELSE a.requires_serial END
     WHERE a.id = p_articolo_id;

    PERFORM set_config('zeroerp.articolo_correggi_struttura', '', true);
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
IS 'VERBO (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): la porta amministratore della regola «un articolo usato non cambia i flag strutturali» (catalogo.trgfn_articoli_guard_struttura_se_usato). Solo SUPER_ADMIN (script.fn_guard_super_admin su app.current_user_id; altrimenti E_PERMESSO_NEGATO). p_campi: oggetto jsonb con le sole colonne da cambiare fra is_composito, is_solo_componente, natura_vendita_id, causale_onere_id, listino_tipologia_id, gestito_a_magazzino, requires_lotto, requires_serial (vuoto, non oggetto o chiavi estranee -> E_PARAMETRO_INVALIDO); articolo assente -> E_ARTICOLO_NOT_FOUND. Scrive con la GUC transazionale zeroerp.articolo_correggi_struttura = id dell''articolo, che il guard onora solo insieme al proprietario della tabella (questo verbo e'' SECURITY DEFINER), e la richiude. Gli altri guard dell''articolo parlano lo stesso. Le righe gia'' scritte non si toccano. La via normale resta un articolo nuovo. search_path bloccato; EXECUTE solo all''app.';
```

---
{% include-markdown "signature-core.md" %}
