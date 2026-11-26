{% include-markdown "it/dbzero/script/manual/fn_tipo_contatto_proposto_id.md" %}
# ⚙️ Funzione `fn_tipo_contatto_proposto_id`

```sql
CREATE FUNCTION fn_tipo_contatto_proposto_id(p_chi text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_tipo_contatto_proposto_id(p_chi text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_codice  config.parameters.default_value%TYPE;
    v_id      config.tipi_contatti.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'id del tipo di contatto che si propone quando chi crea un
    --   soggetto non lo dice. p_chi: chi lo chiede (il nome della
    --   funzione), per il livello «function» della cascata e per il log.
    --
    -- Regole:
    --   - il tipo proposto e' un DATO (TIPO_CONTATTO_PROPOSTO, il
    --     codice_interno del tipo), mai una costante nel codice ne' «il
    --     primo per id»;
    --   - e' una PROPOSTA: si legge con la cascata degli override col
    --     contesto della SESSIONE (utente, gruppo, emittente, sessione,
    --     funzione, default), da script.fn_get_parameter_di_sessione;
    --   - fail-loud su due guasti: assente o vuoto, codice senza tipo.
    --     Mai un ripiego. codice_interno e' unico: il codice indica al
    --     piu' un tipo.
    -- =========================================================
    v_codice := script.fn_get_parameter_di_sessione('TIPO_CONTATTO_PROPOSTO', p_chi);

    -- 1) Assente (fn_get_parameter_full ferma gia' la riga mancante) o vuoto.
    IF v_codice IS NULL OR btrim(v_codice) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_tipo_contatto_proposto_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('code', 'TIPO_CONTATTO_PROPOSTO',
                               'valore', v_codice,
                               'chi', p_chi),
            NULL::uuid,
            'TIPO_CONTATTO_PROPOSTO');
    END IF;

    SELECT t.id INTO v_id
      FROM config.tipi_contatti t
     WHERE t.codice_interno = v_codice;

    -- 2) Nessun tipo. ⭐ Rete: il registro config.parameter_fk_surrogate
    --    (riga 9) lo rifiuta gia' alla scrittura; qui arriva un codice
    --    scritto col registro spento, o un tipo tolto dopo.
    IF v_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_tipo_contatto_proposto_id', 'E_DEFAULT_ERRATO',
            jsonb_build_object('tabella', 'config.tipi_contatti',
                               'parametro', 'TIPO_CONTATTO_PROPOSTO',
                               'valore', v_codice,
                               'chi', p_chi),
            NULL::uuid,
            'config.tipi_contatti', 'TIPO_CONTATTO_PROPOSTO', v_codice);
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_tipo_contatto_proposto_id(p_chi text)
IS 'BB: l''id di config.tipi_contatti che si propone quando chi crea un soggetto non dice il tipo del contatto di default. Legge config.parameters.TIPO_CONTATTO_PROPOSTO (il codice_interno del tipo) da script.fn_get_parameter_di_sessione, cioe'' con la cascata degli override e il contesto della SESSIONE: utente, gruppi, emittente attivo, sessione, funzione (p_chi), default. E'' una PROPOSTA, l''override e'' legittimo. Valida e non ripiega: assente o vuoto E_CONFIG_MANCANTE, codice senza tipo E_DEFAULT_ERRATO; il registro config.parameter_fk_surrogate rifiuta gia'' alla scrittura un codice che non e'' un tipo. Lettori: anagrafiche.fn_crea_soggetto_pf e _pg (col proprio nome come p_chi), script.fn_crea_utente_tecnico. Gemello di script.fn_stato_proposto_id. Decisione D-T5-6 b di Tid (2026-11-24).';
```

</div>

---
{% include-markdown "signature-core.md" %}
