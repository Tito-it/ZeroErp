{% include-markdown "it/dbzero/vendite/manual/fn_get_limite_emissione_default.md" %}
# ⚙️ Funzione `fn_get_limite_emissione_default`

```sql
CREATE FUNCTION fn_get_limite_emissione_default(p_code character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_limite_emissione_default(p_code character varying)
 RETURNS smallint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_valore config.parameters.default_value%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il valore di un limite di emissione dal catalogo dei
    --   parametri, come numero.
    --
    -- Regole:
    --   - si legge il default NUDO, mai la cascata di override;
    --   - fail-loud su tutte e tre le forme di guasto: assente,
    --     vuoto, non numerico.
    -- =========================================================

    -- Guard di parametro: un codice vuoto lo produce solo un
    -- chiamante rotto, ed e' per questo che il codice e' TECNICO.
    IF p_code IS NULL OR btrim(p_code) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_limite_emissione_default',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'codice del parametro obbligatorio'),
            NULL::uuid,
            'vendite.fn_get_limite_emissione_default',
            'p_code (obbligatorio)');
    END IF;

    -- ⛔ default_value NUDO, non script.fn_get_parameter_full: la
    --    cascata di override (utente/gruppo/sessione/emittente)
    --    darebbe ALLO STESSO documento limiti diversi a seconda
    --    di chi lo genera. L'unico asse di override e' il
    --    registro, ed e' un fatto del sezionale. Vedi il COMMENT.
    SELECT p.default_value
      INTO v_valore
      FROM config.parameters p
     WHERE p.code = p_code;

    -- 1) Assente, oppure presente e vuoto. ⚠️ Il secondo caso e'
    --    raggiungibile davvero: default_value e' NOT NULL ma non
    --    ha nessun CHECK di non-vuoto, e a catalogo ci sono gia'
    --    parametri a stringa vuota.
    IF v_valore IS NULL OR btrim(v_valore) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_limite_emissione_default',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('code', p_code, 'valore', v_valore),
            NULL::uuid,
            -- ⭐ Nel VARIADIC va la CHIAVE DI CONFIGURAZIONE, che
            --    un amministratore riconosce e sa dove mettere.
            p_code);
    END IF;

    -- 2) C'e' ed e' pieno, ma non e' un numero.
    --    ⛔ Senza questo controllo il cast alza un 22P02 grezzo:
    --       il contratto «P0001 + CONSTRAINT = errore di dominio»
    --       salta e il guasto arriva al backend come 500 non
    --       tradotto.
    --    ⚠️ Il quantificatore {1,4} non e' estetica: limita a
    --       0..9999 e quindi al dominio di smallint, cosi' un
    --       valore assurdo non alza un 22003 al posto della frase.
    IF btrim(v_valore) !~ '^[0-9]{1,4}$' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_limite_emissione_default',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('code', p_code, 'valore', v_valore),
            NULL::uuid,
            -- ⭐ Qui la frase nomina anche IL VALORE: e' l'unica
            --    cosa che dice dove sta l'errore di battitura.
            concat(p_code, ' = ', quote_literal(btrim(v_valore)),
                   ' (non e'' un numero intero fra 0 e 9999)'));
    END IF;

    RETURN btrim(v_valore)::smallint;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_limite_emissione_default(p_code character varying)
IS 'Il valore di un limite di emissione dal catalogo dei parametri, come numero. Serve i due codici VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI e VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE, letti da vendite.fn_get_pavimento_emissione quando il registro non dichiara un override suo. ⛔ LEGGE IL default_value NUDO e NON script.fn_get_parameter_full, che pure e'' il lettore canonico: la sua cascata di override (utente/gruppo/sessione/emittente) darebbe ALLO STESSO documento limiti diversi a seconda di chi lo genera, cioe'' il difetto che il limite di emissione chiude. L''unico asse di override e'' il REGISTRO, che e'' un fatto del sezionale e non di chi ci lavora — stessa scelta, e stessa ragione, di script.fn_data_operativa(). ⛔ FAIL-LOUD su tre condizioni, tutte con E_CONFIG_MANCANTE perche'' a rimediare e'' sempre chi amministra la configurazione: parametro assente, valore vuoto (raggiungibile: default_value e'' NOT NULL ma senza CHECK di non-vuoto, e a catalogo ci sono gia'' stringhe vuote), valore non numerico. ⚠️ La regex ammette 1..4 cifre e non un numero qualunque: limita al dominio di smallint, cosi'' un valore assurdo produce la frase invece di un 22003 grezzo che farebbe saltare il contratto P0001. ⛔ NON e'' un lettore generico di parametri e non va usata come tale: e'' narrow per dominio e per famiglia, apposta. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
