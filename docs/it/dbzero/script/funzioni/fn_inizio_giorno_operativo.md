# ⚙️ Funzione `fn_inizio_giorno_operativo`

```sql
CREATE FUNCTION fn_inizio_giorno_operativo(p_giorno date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_inizio_giorno_operativo(p_giorno date)
 RETURNS timestamp with time zone
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'ISTANTE in cui comincia il giorno p_giorno nel fuso
    --   dell'azienda. Confine dei filtri per giorno su colonne
    --   timestamptz: [inizio(D), inizio(D + 1)).
    --
    -- Regole:
    --   - p_giorno::timestamp non dipende dalla sessione; AT TIME
    --     ZONE lo legge come ora locale del fuso dell'azienda;
    --   - il fuso lo legge e lo valida fn_fuso_operativo (sede
    --     unica, fail-loud): qui non si rilegge il parametro;
    --   - NULL -> NULL: un confine assente non e' un errore, i
    --     filtri sono opzionali. Il fuso non si legge nemmeno.
    -- =========================================================
    IF p_giorno IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN p_giorno::timestamp AT TIME ZONE script.fn_fuso_operativo();
END;
$function$

COMMENT ON FUNCTION script.fn_inizio_giorno_operativo(p_giorno date)
IS 'L''ISTANTE in cui comincia il giorno p_giorno nel fuso dell''azienda (script.fn_fuso_operativo). ⭐ Confine dei filtri per giorno su colonne timestamptz: col >= fn_inizio_giorno_operativo(da) AND col < fn_inizio_giorno_operativo(a + 1), con la funzione sui confini e non sulla colonna, cosi'' il predicato resta servito dall''indice. ⛔ Sostituisce `%s::date` confrontato con un timestamptz, che da'' la mezzanotte nel fuso della SESSIONE (dal backend: UTC) e mette nel giorno sbagliato cio'' che succede fra la mezzanotte dell''azienda e quella della sessione. Ai cambi d''ora il giorno ha 23 o 25 ore e il confine li segue. NULL -> NULL (filtri opzionali). Fail-loud sul fuso ereditato da fn_fuso_operativo. Brief: brief-be-db-fe-un-solo-fuso-aziendale D-2 (20261009-42).';
```

</div>

---
{% include-markdown "signature-core.md" %}
