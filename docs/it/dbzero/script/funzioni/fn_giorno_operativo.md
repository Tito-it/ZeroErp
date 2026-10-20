# ⚙️ Funzione `fn_giorno_operativo`

```sql
CREATE FUNCTION fn_giorno_operativo(p_istante timestamp with time zone)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_giorno_operativo(p_istante timestamp with time zone)
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il GIORNO, nel fuso dell'azienda, in cui cade p_istante.
    --   Sostituisce `istante::date` e `date_trunc(.., istante)`,
    --   che calcolano nel fuso della sessione.
    --
    -- Regole:
    --   - il fuso lo legge e lo valida fn_fuso_operativo (sede
    --     unica, fail-loud): qui non si rilegge il parametro;
    --   - NULL -> NULL. Il fuso non si legge nemmeno.
    --   - ⚠️ per FILTRARE per giorno non si applica alla colonna
    --     (niente indice): si usano i confini di
    --     fn_inizio_giorno_operativo. Questa serve a PROIETTARE.
    -- =========================================================
    IF p_istante IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN (p_istante AT TIME ZONE script.fn_fuso_operativo())::date;
END;
$function$

COMMENT ON FUNCTION script.fn_giorno_operativo(p_istante timestamp with time zone)
IS 'Il GIORNO, nel fuso dell''azienda (script.fn_fuso_operativo), in cui cade p_istante. ⛔ Sostituisce istante::date e date_trunc(''month'', istante), che calcolano nel fuso della SESSIONE: lo stesso istante cadeva in due giorni secondo chi lo legge (backend in UTC, psql e pgAgent nel fuso del server). Il mese si ricava dal giorno restituito, non dal timestamptz. ⚠️ Serve a PROIETTARE il giorno: per FILTRARE per giorno una colonna timestamptz si usano i confini di fn_inizio_giorno_operativo, che lasciano lavorare l''indice. NULL -> NULL. Fail-loud sul fuso ereditato da fn_fuso_operativo. Brief: brief-be-db-fe-un-solo-fuso-aziendale D-2 (20261009-43).';
```

</div>

---
{% include-markdown "signature-core.md" %}
