{% include-markdown "it/dbzero/ui/manual/fn_check_forma_configurazione.md" %}
# ⚙️ Funzione `fn_check_forma_configurazione`

```sql
CREATE FUNCTION fn_check_forma_configurazione(p_famiglia text, p_contenitore_id integer, p_configurazione jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_check_forma_configurazione(p_famiglia text, p_contenitore_id integer, p_configurazione jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- text[]: le chiavi ammesse della radice e della voce, per famiglia
    v_chiavi      text[];
    v_voce_chiavi text[];
    -- text: la chiave dell'elenco della famiglia ('colonne' o 'widget')
    v_elenco      text;
    -- text, jsonb: chiave e valore della radice, nel ciclo
    v_k           text;
    v_v           jsonb;
    -- jsonb: una voce dell'elenco, nel ciclo
    v_e           jsonb;
    -- text: una chiave fuori posto, o il campo di una voce
    v_fuori       text;
    v_campo       text;
    -- i codici gia' visti nell'elenco
    v_cod         ui.lista_colonna.codice%TYPE;
    v_codici      ui.lista_colonna.codice%TYPE[] := ARRAY[]::varchar[];
BEGIN
    IF p_famiglia IS NULL OR p_famiglia NOT IN ('lista', 'dashboard') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'ui.fn_check_forma_configurazione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_famiglia', 'valore', p_famiglia),
            NULL::uuid,
            'la famiglia della configurazione (lista o dashboard)');
    END IF;
    IF p_contenitore_id IS NULL OR p_contenitore_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'ui.fn_check_forma_configurazione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_contenitore_id', 'valore', p_contenitore_id),
            NULL::uuid,
            'l''id della lista o della dashboard');
    END IF;

    IF p_configurazione IS NULL OR jsonb_typeof(p_configurazione) <> 'object' THEN
        RETURN jsonb_build_object('chiave', 'configurazione', 'motivo', 'non è un oggetto');
    END IF;

    IF p_famiglia = 'lista' THEN
        v_chiavi      := ARRAY['colonne', 'pagina_dimensione'];
        v_elenco      := 'colonne';
        v_voce_chiavi := ARRAY['codice', 'ordine', 'larghezza', 'visibile', 'fissata'];
    ELSE
        v_chiavi      := ARRAY['widget', 'dimensione_max'];
        v_elenco      := 'widget';
        v_voce_chiavi := ARRAY['codice', 'ordine', 'visibile'];
    END IF;

    FOR v_k, v_v IN
        SELECT r.key, r.value FROM jsonb_each(p_configurazione) AS r ORDER BY r.key
    LOOP
        IF NOT (v_k = ANY (v_chiavi)) THEN
            RETURN jsonb_build_object('chiave', v_k, 'motivo', 'non è una chiave ammessa');
        END IF;
        IF jsonb_typeof(v_v) = 'null' THEN
            RETURN jsonb_build_object('chiave', v_k, 'motivo', 'è null');
        END IF;

        IF v_k = v_elenco THEN
            IF jsonb_typeof(v_v) <> 'array' THEN
                RETURN jsonb_build_object('chiave', v_k, 'motivo', 'non è un elenco');
            END IF;

            FOR v_e IN SELECT a.value FROM jsonb_array_elements(v_v) AS a LOOP
                IF jsonb_typeof(v_e) <> 'object' THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo', 'una voce non è un oggetto');
                END IF;
                IF jsonb_typeof(v_e -> 'codice') IS DISTINCT FROM 'string'
                   OR btrim(v_e ->> 'codice') = '' THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo', 'una voce non ha il codice');
                END IF;
                v_cod := v_e ->> 'codice';

                SELECT f.k INTO v_fuori
                  FROM jsonb_object_keys(v_e) AS f(k)
                 WHERE NOT (f.k = ANY (v_voce_chiavi))
                 ORDER BY f.k LIMIT 1;
                IF v_fuori IS NOT NULL THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo',
                        format('la voce %s ha la chiave %s, non ammessa', v_cod, v_fuori));
                END IF;
                SELECT f.key INTO v_campo
                  FROM jsonb_each(v_e) AS f
                 WHERE jsonb_typeof(f.value) = 'null'
                 ORDER BY f.key LIMIT 1;
                IF v_campo IS NOT NULL THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo',
                        format('la voce %s ha %s null', v_cod, v_campo));
                END IF;

                IF v_cod = ANY (v_codici) THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo',
                        format('il codice %s è ripetuto', v_cod));
                END IF;
                v_codici := array_append(v_codici, v_cod);

                IF p_famiglia = 'lista' THEN
                    IF NOT EXISTS (SELECT 1 FROM ui.lista_colonna lc
                                    WHERE lc.lista_id = p_contenitore_id
                                      AND lc.codice   = v_cod) THEN
                        RETURN jsonb_build_object('chiave', v_k, 'motivo',
                            format('%s non è una colonna della lista', v_cod));
                    END IF;
                ELSE
                    IF NOT EXISTS (SELECT 1 FROM ui.dashboard_widget dw
                                     JOIN ui.widget w ON w.id = dw.widget_id
                                    WHERE dw.dashboard_id = p_contenitore_id
                                      AND w.codice        = v_cod) THEN
                        RETURN jsonb_build_object('chiave', v_k, 'motivo',
                            format('%s non è una card della dashboard', v_cod));
                    END IF;
                END IF;

                -- Interi positivi: ordine (le due famiglie), larghezza (liste).
                SELECT f.c INTO v_campo
                  FROM unnest(ARRAY['ordine', 'larghezza']) AS f(c)
                 WHERE jsonb_exists(v_e, f.c)
                   AND COALESCE(ui.fn_intero_da_jsonb(v_e -> f.c), 0) < 1
                 ORDER BY f.c LIMIT 1;
                IF v_campo IS NOT NULL THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo',
                        format('%s della voce %s non è un intero positivo', v_campo, v_cod));
                END IF;
                -- Booleani: visibile (le due famiglie), fissata (liste).
                SELECT f.c INTO v_campo
                  FROM unnest(ARRAY['fissata', 'visibile']) AS f(c)
                 WHERE jsonb_exists(v_e, f.c)
                   AND jsonb_typeof(v_e -> f.c) <> 'boolean'
                 ORDER BY f.c LIMIT 1;
                IF v_campo IS NOT NULL THEN
                    RETURN jsonb_build_object('chiave', v_k, 'motivo',
                        format('%s della voce %s non è vero o falso', v_campo, v_cod));
                END IF;
            END LOOP;

        ELSIF v_k = 'dimensione_max' THEN
            IF NOT ui.fn_dimensione_max_ammessa(ui.fn_intero_da_jsonb(v_v)) THEN
                RETURN jsonb_build_object('chiave', v_k, 'motivo', 'non è un intero da 1 a 100');
            END IF;
        END IF;
        -- pagina_dimensione: la giudica ui.fn_guard_misura_pagina, col suo codice.
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.fn_check_forma_configurazione(p_famiglia text, p_contenitore_id integer, p_configurazione jsonb)
IS 'Il primo motivo per cui la configurazione di una preferenza non ha la forma ammessa, come {chiave, motivo}, o NULL se la forma è buona. p_famiglia ''lista'' (p_contenitore_id = ui.lista_definizione.id) o ''dashboard'' (ui.dashboard_definizione.id). La radice è un oggetto con le sole chiavi della famiglia, nessuna a null: colonne e pagina_dimensione per le liste, widget e dimensione_max per le dashboard; {} è ammesso. colonne/widget è un elenco di oggetti con le sole chiavi della voce (codice, ordine, larghezza, visibile, fissata; per il widget codice, ordine, visibile), nessuna a null, solo codice obbligatorio: codice testo non vuoto, unico nell''elenco, di una colonna della lista o di una card del pool della dashboard in qualsiasi stato; ordine e larghezza interi positivi (ui.fn_intero_da_jsonb); visibile e fissata booleani. dimensione_max da ui.fn_dimensione_max_ammessa. pagina_dimensione non la giudica: lo fa ui.fn_guard_misura_pagina. Non solleva sul dato; solleva E_PARAMETRO_INVALIDO su una famiglia fuori dalle due o un contenitore NULL o non positivo. La chiama il trigger di forma delle due preferenze (ui.trgfn_preferenza_guard_forma), che solleva E_UI_CONFIGURAZIONE_FORMA. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
