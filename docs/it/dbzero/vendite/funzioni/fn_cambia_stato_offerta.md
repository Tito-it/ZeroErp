{% include-markdown "it/dbzero/vendite/manual/fn_cambia_stato_offerta.md" %}
# ⚙️ Funzione `fn_cambia_stato_offerta`

```sql
CREATE FUNCTION fn_cambia_stato_offerta(p_offerta_id bigint, p_stato character varying, p_motivazione text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_offerta(p_offerta_id bigint, p_stato character varying, p_motivazione text)
 RETURNS TABLE(offerta_id bigint, stato_precedente character varying, stato_nuovo character varying)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_codice       vendite.offerte_commerciali.codice%TYPE;
    v_stato_da     config.stati_doc_offerte.codice_interno%TYPE;
    v_stato_da_id  vendite.offerte_commerciali.stato_doc_offerta_id%TYPE;
    v_stato_a_id   config.stati_doc_offerte.id%TYPE;
    v_stato_a_desc config.stati_doc_offerte.descrizione%TYPE;
    v_motivazione  vendite.offerte_commerciali.motivazione_rifiuto%TYPE;
    -- Un flag letto dal meta jsonb della riga del passaggio:
    -- nessuna colonna di cui sia il riflesso.
    v_richiesta    boolean;
BEGIN
    -- ==========================================================
    -- Scopo: il verbo di ogni cambio di stato manuale di
    --   un'offerta (modello del documento: prima riga comune,
    --   motivazione, scrittura comune). Matrice e condizioni dei
    --   passaggi le giudica il guard di transizione, all'UPDATE.
    -- Ritorna: offerta_id, stato_precedente, stato_nuovo
    --   (codice_interno).
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri. La motivazione vuota o di soli spazi manca.
    IF p_offerta_id IS NULL OR p_offerta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_offerta',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_offerta_id', p_offerta_id),
            NULL::uuid, 'vendite.fn_cambia_stato_offerta',
            'p_offerta_id (obbligatorio, maggiore di zero)');
    END IF;
    v_motivazione := NULLIF(btrim(p_motivazione), '');

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT o.codice, o.stato_doc_offerta_id, s.codice_interno
      INTO v_codice, v_stato_da_id, v_stato_da
      FROM vendite.offerte_commerciali o
      JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id
     WHERE o.id = p_offerta_id
       AND script.fn_scope_ef_whitelist_via_offerta(v_utente, o.id)
       FOR UPDATE OF o;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_offerta',
            'E_OFFERTA_NON_TROVATA', jsonb_build_object('id', p_offerta_id), NULL::uuid,
            p_offerta_id::text);
    END IF;

    -- 3. Lo stato chiesto: il codice di uno stato attivo.
    v_stato_a_id := script.fn_doc_stato_id('vendite.offerte_commerciali'::regclass, p_stato);
    IF v_stato_a_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_offerta',
            'E_STATO_WORKFLOW_NON_TROVATO',
            jsonb_build_object('codice', p_stato),
            NULL::uuid,
            COALESCE(p_stato, 'NULL'));
    END IF;

    -- 4. Prima riga comune: lo stato che ha gia', passaggio di
    --    processo, azione.
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.offerte_commerciali'::regclass,
                                      v_stato_da_id, v_stato_a_id);

    -- 5. La motivazione (O-3): obbligatoria dove la riga del
    --    passaggio la chiede. Un passaggio fuori matrice non la
    --    chiede: lo rifiuta il guard di transizione, al punto 6.
    SELECT COALESCE((t.meta ->> 'requires_motivazione')::boolean, false)
      INTO v_richiesta
      FROM config.stati_doc_offerte_transizioni t
     WHERE t.stato_da_id = v_stato_da_id
       AND t.stato_a_id  = v_stato_a_id
       AND t.attivo IS TRUE;

    IF COALESCE(v_richiesta, false) AND v_motivazione IS NULL THEN
        SELECT s.descrizione INTO v_stato_a_desc
          FROM config.stati_doc_offerte s
         WHERE s.id = v_stato_a_id;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_cambia_stato_offerta',
            'E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA',
            jsonb_build_object('campo',      'motivazione_rifiuto',
                               'offerta_id', p_offerta_id,
                               'stato_da',   v_stato_da,
                               'stato_a',    p_stato),
            NULL::uuid,
            COALESCE(v_codice, p_offerta_id::text),
            COALESCE(v_stato_a_desc, p_stato));
    END IF;

    -- La motivazione si scrive prima dello stato, nella stessa
    -- transazione: il lock di testata la ammette negli stati da
    -- cui si rifiuta o si annulla.
    IF v_motivazione IS NOT NULL THEN
        UPDATE vendite.offerte_commerciali o
           SET motivazione_rifiuto = v_motivazione
         WHERE o.id = p_offerta_id;
    END IF;

    -- 6. Lo stato, attraverso la porta. Il guard di transizione
    --    giudica matrice e condizioni; il guard dell'annullo i
    --    legami (la revisione precedente che torna emessa).
    PERFORM script.fn_doc_scrivi_stato('vendite.offerte_commerciali'::regclass,
                                       p_offerta_id, v_stato_a_id);

    RETURN QUERY SELECT p_offerta_id, v_stato_da, p_stato;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_offerta(p_offerta_id bigint, p_stato character varying, p_motivazione text)
IS 'VERBO di ogni cambio di stato manuale di un''offerta (modello del documento, brief-modello-documento-vendita §13). Permesso: dalla riga del passaggio (config.stati_doc_offerte_transizioni.azione_processo_codename: emetti_offerta su BOZZA -> EMESSA e ACCETTATA -> ANNULLATA) con script.fn_guard_passaggio, prima di ogni scrittura (lo stato che l''offerta ha gia'': E_DOC_GIA_NELLO_STATO); accetta, rifiuta e l''annullo della bozza al permesso sul documento, che controlla il backend. Motivazione (O-3): scritta in motivazione_rifiuto prima dello stato quando c''e''; obbligatoria dove la riga del passaggio dichiara requires_motivazione nel meta (rifiuto e annulli): senza, o vuota, E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA (campo motivazione_rifiuto). SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE col predicato della policy nella WHERE (script.fn_scope_ef_whitelist_via_offerta; fuori perimetro E_OFFERTA_NON_TROVATA, no-leak). Lo stato chiesto per codice_interno (script.fn_doc_stato_id; nessuno stato attivo: E_STATO_WORKFLOW_NON_TROVATO). Lo stato lo scrive script.fn_doc_scrivi_stato attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), e il guard di transizione (vendite.trgfn_offerte_commerciali_guard_transizione) giudica matrice (E_OFFERTA_TRANSIZIONE_NON_AMMESSA) e condizioni; l''annullo con legami (la revisione precedente che torna emessa) passa da vendite.fn_annulla_offerta. Ritorna offerta_id, stato_precedente, stato_nuovo (codice_interno). EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §13 (O-1, O-3, Tid 2026-10-26).';
```

</div>

---
{% include-markdown "signature-core.md" %}
