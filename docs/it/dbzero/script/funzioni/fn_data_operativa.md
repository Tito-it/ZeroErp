{% include-markdown "it/dbzero/script/manual/fn_data_operativa.md" %}
# ⚙️ Funzione `fn_data_operativa`

```sql
CREATE FUNCTION fn_data_operativa()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_data_operativa()
 RETURNS date
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   La data di oggi NEL FUSO DELL'AZIENDA, non in quello
    --   della sessione. Sostituisce current_date.
    --
    -- ⭐ Il fuso lo legge e lo valida script.fn_fuso_operativo
    --   (20261009-40), sede unica: assente, vuoto, non
    --   riconosciuto -> E_CONFIG_MANCANTE, mai un ripiego a UTC.
    --   Qui resta solo la domanda «che giorno e' oggi».
    --
    -- ℹ️ now() e' l'istante di inizio transazione: dentro la
    --    stessa transazione la risposta e' per costruzione
    --    identica, ed e' il motivo per cui la funzione e' STABLE.
    -- =========================================================
    RETURN (now() AT TIME ZONE script.fn_fuso_operativo())::date;
END;
$function$

COMMENT ON FUNCTION script.fn_data_operativa()
IS 'La data di oggi NEL FUSO DELL''AZIENDA (config.parameters.SYSTEM_FUSO_ORARIO), non in quello della sessione. ⛔ Sostituisce current_date: current_date segue il fuso della SESSIONE, e le sessioni non hanno tutte lo stesso fuso (Django in UTC, psql e pgAgent nel fuso del server) — lo stesso oggetto dava due date diverse secondo il canale, e ogni documento nato fra mezzanotte e le 02:00 locali portava la data del giorno prima (misurato 2026-08-25: 7 fatture su 18 sfasate). ⭐ Rev 2026-10-09 (20261009-41, brief-be-db-fe-un-solo-fuso-aziendale D-1): il fuso non lo legge piu'' da se'': lo chiede a script.fn_fuso_operativo, sede unica della lettura (default NUDO, mai fn_get_parameter_full) e del fail-loud (assente, vuoto, non riconosciuto -> E_CONFIG_MANCANTE; la validita'' del nome la decide il registro config.parameter_fk_surrogate alla scrittura). Nessun ripiego a UTC o a current_date. ℹ️ STABLE perche'' now() e'' l''istante di inizio transazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
