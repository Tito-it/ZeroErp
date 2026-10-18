{% include-markdown "it/dbzero/script/manual/fn_stato_id_da_iso2.md" %}
# ⚙️ Funzione `fn_stato_id_da_iso2`

```sql
CREATE FUNCTION fn_stato_id_da_iso2(p_iso2 text, p_chi text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_id_da_iso2(p_iso2 text, p_chi text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_iso2  text := upper(btrim(p_iso2));
    v_id    config.stati.id%TYPE;
    v_n     integer;   -- un conteggio: niente da ancorare
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'id dell'UNICO stato con questo codice ISO2.
    --   NULL se il codice e' vuoto o nessuno stato lo porta:
    --   quel caso lo giudica il chiamante, col suo codice.
    --
    -- Regole:
    --   - codice_iso2 non e' univoco (righe storiche del
    --     catalogo ISTAT): piu' righe = E_STATO_ISO2_AMBIGUO,
    --     mai una riga a caso.
    -- =========================================================
    IF v_iso2 IS NULL OR v_iso2 = '' THEN
        RETURN NULL;
    END IF;

    SELECT count(*), min(s.id)
      INTO v_n, v_id
      FROM config.stati s
     WHERE s.codice_iso2 = v_iso2;

    IF v_n > 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_stato_id_da_iso2', 'E_STATO_ISO2_AMBIGUO',
            jsonb_build_object('codice_iso2', v_iso2,
                               'stati', v_n,
                               'chi', p_chi),
            NULL::uuid,
            v_iso2, v_n::text);
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_id_da_iso2(p_iso2 text, p_chi text)
IS 'BB (2026-10-18): l''id dell''UNICO stato di config.stati con questo codice ISO2 (maiuscole, spazi tolti). NULL se il codice e'' vuoto o nessuno stato lo porta: il «non trovato» lo giudica il chiamante, perche'' non e'' lo stesso errore (un codice scelto dall''operatore, E_CODICE, non e'' un parametro configurato male, E_DEFAULT_ERRATO). Piu'' righe: E_STATO_ISO2_AMBIGUO, mai una riga a caso: codice_iso2 non e'' univoco, il catalogo ISTAT tiene righe storiche dello stesso paese con codici catastali diversi. Chiamanti: script.fn_stato_proposto_id, anagrafiche.fn_crea_soggetto_pf e _pg. D-1 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11.';
```

---
{% include-markdown "signature-core.md" %}
