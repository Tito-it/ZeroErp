{% include-markdown "it/dbzero/config/manual/fn_get_aliquota_iva.md" %}
# ⚙️ Funzione `fn_get_aliquota_iva`

```sql
CREATE FUNCTION fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_aliquota config.iva.aliquota_iva%TYPE;
BEGIN
    -- Guard: p_iva_id obbligatorio
    IF p_iva_id IS NULL OR p_iva_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'fn_get_aliquota_iva',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_iva_id',
                'valore', p_iva_id
            ),
            NULL::uuid,
            'p_iva_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera aliquota con override per stato
    SELECT COALESCE(s.aliquota_override, i.aliquota_iva)
      INTO v_aliquota
      FROM config.iva i
      LEFT JOIN config.iva_stati s
        ON s.iva_id = i.id
       AND s.stato_id = p_stato_id
     WHERE i.id = p_iva_id;

    IF v_aliquota IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'fn_get_aliquota_iva',
            'E_CODICE',
            jsonb_build_object('iva_id', p_iva_id),
            NULL::uuid,
            p_iva_id::text, 'config.iva'
        );
    END IF;

    RETURN v_aliquota;
END;
$function$

COMMENT ON FUNCTION config.fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
IS 'Aliquota IVA con override per stato (config.iva_stati). Errori: E_PARAMETRO_INVALIDO, E_CODICE. ⭐ STABLE dal 2026-08-29 (§R-4 del cantiere IVA): e'' sempre stata in sola lettura, e la dichiarazione VOLATILE diceva il falso. Non e'' cosmesi — la funzione gira DENTRO vw_ddt_righe_iva_base, vw_ordini_righe_iva_base e vw_preventivi_righe_dettaglio, cioe'' dove il planner la valuta per riga: con VOLATILE non puo'' riusare il risultato per lo stesso (iva_id, stato_id) ne'' spostare la chiamata fuori da un ciclo. ⛔ Non IMMUTABLE, e la differenza conta: il valore dipende da config.iva e config.iva_stati, quindi «stesso input, stesso output per sempre» sarebbe falso il giorno che qualcuno corregge un''aliquota. ⚠️ Residuo NON toccato qui: la funzione SOLLEVA su p_iva_id nullo invece di ritornare NULL, ed e'' cio'' che sui preventivi impediva perfino di salvare una riga senza aliquota — sanato il 2026-08-29 con una guardia nella funzione chiamante. La gemella sulle fatture ha ancora lo stesso difetto e si chiude dentro I4, perche'' togliere il raise senza il cancello all''emissione scambierebbe un errore rumoroso con un numero sbagliato silenzioso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
