{% include-markdown "it/dbzero/script/manual/fn_stato_proposto_id.md" %}
# ⚙️ Funzione `fn_stato_proposto_id`

```sql
CREATE FUNCTION fn_stato_proposto_id(p_chi text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_proposto_id(p_chi text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_iso2  config.parameters.default_value%TYPE;
    v_id    config.stati.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'id dello stato che si propone quando chi scrive non
    --   lo dice. p_chi: chi lo chiede (il nome del trigger o
    --   della funzione), per il livello «function» della
    --   cascata e per il log.
    --
    -- Regole:
    --   - lo stato proposto e' un DATO (STATO_PROPOSTO_ISO2),
    --     mai una costante nel codice;
    --   - e' una PROPOSTA: si legge con la cascata degli
    --     override col contesto della SESSIONE (utente, gruppo,
    --     emittente, sessione, funzione, default), da
    --     script.fn_get_parameter_di_sessione: i lettori sono
    --     trigger e madri, che il contesto non lo ricevono;
    --   - fail-loud su tre guasti: assente o vuoto, codice
    --     senza stato, codice che indica piu' stati
    --     (fn_stato_id_da_iso2). Mai un ripiego.
    -- =========================================================
    v_iso2 := script.fn_get_parameter_di_sessione('STATO_PROPOSTO_ISO2', p_chi);

    -- 1) Assente (fn_get_parameter_full ferma gia' la riga
    --    mancante) o vuoto.
    IF v_iso2 IS NULL OR btrim(v_iso2) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_stato_proposto_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('code', 'STATO_PROPOSTO_ISO2',
                               'valore', v_iso2,
                               'chi', p_chi),
            NULL::uuid,
            'STATO_PROPOSTO_ISO2');
    END IF;

    -- 2) Piu' stati: lo ferma il BB (E_STATO_ISO2_AMBIGUO).
    v_id := script.fn_stato_id_da_iso2(v_iso2, p_chi);

    -- 3) Nessuno stato. ⭐ Rete: il registro
    --    config.parameter_fk_surrogate (riga 8) lo rifiuta gia'
    --    alla scrittura; qui arriva un codice scritto col
    --    registro spento, o uno stato tolto dopo.
    IF v_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'script.fn_stato_proposto_id', 'E_DEFAULT_ERRATO',
            jsonb_build_object('tabella', 'config.stati',
                               'parametro', 'STATO_PROPOSTO_ISO2',
                               'valore', v_iso2,
                               'chi', p_chi),
            NULL::uuid,
            'config.stati', 'STATO_PROPOSTO_ISO2', v_iso2);
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_proposto_id(p_chi text)
IS 'BB (2026-10-18): l''id di config.stati che si propone quando chi scrive non dice lo stato. Legge config.parameters.STATO_PROPOSTO_ISO2 (codice ISO2) da script.fn_get_parameter_di_sessione, cioe'' con la cascata degli override e il contesto della SESSIONE: utente (app.current_user_id), gruppi (django.auth_user_groups, se leggibili), emittente attivo (app.current_emittente_id), sessione (app.session_key), funzione (p_chi), default. E'' una PROPOSTA, l''override e'' legittimo. Valida e non ripiega: assente o vuoto E_CONFIG_MANCANTE, codice senza stato E_DEFAULT_ERRATO, codice che indica piu'' stati E_STATO_ISO2_AMBIGUO (da script.fn_stato_id_da_iso2). Lettori: i trigger normalize di indirizzi, indirizzi_soggetti, soggetti, regioni, iva_stati, toponomastica; anagrafiche.fn_crea_soggetto_pf e _pg; script.fn_crea_utente_tecnico. ⛔ Non decide le regole di un paese: CF e P.IVA, sigla di provincia e IVA restano scritte per ''IT'' dove la legge e'' italiana. Prende il posto di state_code_iso3 (script.fn_get_default_by_param, ritirata) e di soggetto_default_stato_iso2 (col ripiego silenzioso a ''IT''). D-1 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11. Rev 2026-10-18 (20261019-06, R-BE-13 §6.12): fino ad allora utente, gruppi ed emittente arrivavano NULL e i loro override non scattavano mai.';
```

</div>

---
{% include-markdown "signature-core.md" %}
