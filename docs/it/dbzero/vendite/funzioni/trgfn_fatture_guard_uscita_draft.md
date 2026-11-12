{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_uscita_draft.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_uscita_draft`

```sql
CREATE FUNCTION trgfn_fatture_guard_uscita_draft()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_uscita_draft()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una fattura non lascia lo stato iniziale (la bozza:
--        config.stati_doc_fiscale.iniziale) se non e' completa
--        di cio' che il documento stampa — gli indirizzi marcati
--        obbligatori per l'ambito FATTURE e l'intestazione
--        fiscale congelata delle due parti.
-- Uso:   BEFORE UPDATE OF stato_doc_fiscale_id FOR EACH ROW
DECLARE
    v_old_codice   config.stati_doc_fiscale.codice_interno%TYPE;
    v_old_iniziale config.stati_doc_fiscale.iniziale%TYPE;
    v_new_codice   config.stati_doc_fiscale.codice_interno%TYPE;
    v_new_abortito config.stati_doc_fiscale.is_abortito%TYPE;
    v_presenti     integer[];
    v_ind_mancanti text[];
    v_int_mancanti text[] := ARRAY[]::text[];
    -- tipo esplicito: le parti mancanti DENTRO un'intestazione congelata
    v_int_incomplete text[] := ARRAY[]::text[];
    v_riassunto    text[] := ARRAY[]::text[];
BEGIN
    -- Solo il cambio di stato interessa. Il trigger e' gia' su
    -- UPDATE OF, ma quella clausola scatta anche quando la colonna
    -- viene riscritta con lo stesso valore.
    IF NEW.stato_doc_fiscale_id IS NOT DISTINCT FROM OLD.stato_doc_fiscale_id THEN
        RETURN NEW;
    END IF;

    SELECT s.codice_interno, s.iniziale
      INTO v_old_codice, v_old_iniziale
      FROM config.stati_doc_fiscale s
     WHERE s.id = OLD.stato_doc_fiscale_id;

    -- Si presidia l'USCITA dalla bozza, non ogni avanzamento:
    -- oltre la bozza il documento e' gia' passato di qui, e a
    -- proteggerlo c'e' il guard di congelamento dei satelliti.
    -- La bozza e' lo stato iniziale del vocabolario, non un codice.
    IF v_old_iniziale IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    SELECT s.codice_interno, s.is_abortito
      INTO v_new_codice, v_new_abortito
      FROM config.stati_doc_fiscale s
     WHERE s.id = NEW.stato_doc_fiscale_id;

    -- Abbandono: una bozza incompleta deve restare chiudibile.
    -- Questo guard presidia l'emissione, non l'abbandono.
    IF COALESCE(v_new_abortito, FALSE) THEN
        RETURN NEW;
    END IF;

    -- 1. INDIRIZZI — dalla matrice config.tipi_indirizzi_allowed,
    --    non da un codice cablato: stesso building block di
    --    script.fn_check_ddt_emittibile.
    SELECT array_agg(fi.tipo_indirizzo_id)
      INTO v_presenti
      FROM vendite.fatture_indirizzi fi
     WHERE fi.fattura_id = NEW.id;

    v_ind_mancanti := script.fn_indirizzi_obbligatori_mancanti('FATTURA', v_presenti);

    IF array_length(v_ind_mancanti, 1) IS NOT NULL THEN
        v_riassunto := v_riassunto
            || format('indirizzi obbligatori mancanti: %s',
                      array_to_string(v_ind_mancanti, ', '));
    END IF;

    -- 2. INTESTAZIONE — le due colonne di testata scritte da
    --    vendite.fn_snapshot_intestazione_fattura. Si controlla il
    --    TIPO e non il solo NULL: jsonb_strip_nulls e' applicato a
    --    monte, quindi uno snapshot senza dati arriva qui come
    --    '{}' e passerebbe un test sul solo IS NULL.
    IF COALESCE(jsonb_typeof(NEW.emittente_snapshot), 'null') <> 'object'
       OR NEW.emittente_snapshot = '{}'::jsonb THEN
        v_int_mancanti := v_int_mancanti || 'emittente_snapshot'::text;
    -- 2-bis. La SEDE LEGALE del cedente, dentro l'intestazione
    --    congelata. La scrive lo snapshot dalla
    --    catena RUOLO -> SOGGETTO (script.fn_resolve_indirizzo_documento,
    --    SEDELEG); senza indirizzo la chiave non c'e' (jsonb_strip_nulls).
    --    Stesso criterio del tipo: '{}' non vale.
    ELSIF COALESCE(jsonb_typeof(NEW.emittente_snapshot -> 'sede'), 'null') <> 'object'
          OR NEW.emittente_snapshot -> 'sede' = '{}'::jsonb THEN
        v_int_incomplete := v_int_incomplete || 'sede legale dell''emittente'::text;
    END IF;

    IF COALESCE(jsonb_typeof(NEW.cliente_snapshot), 'null') <> 'object'
       OR NEW.cliente_snapshot = '{}'::jsonb THEN
        v_int_mancanti := v_int_mancanti || 'cliente_snapshot'::text;
    END IF;

    IF array_length(v_int_mancanti, 1) IS NOT NULL THEN
        v_riassunto := v_riassunto
            || format('intestazione non congelata: %s',
                      array_to_string(v_int_mancanti, ', '));
    END IF;

    IF array_length(v_int_incomplete, 1) IS NOT NULL THEN
        v_riassunto := v_riassunto
            || format('intestazione incompleta: manca la %s',
                      array_to_string(v_int_incomplete, ', '));
    END IF;

    IF array_length(v_riassunto, 1) IS NULL THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        'trgfn_fatture_guard_uscita_draft',
        'E_FATTURA_NON_EMETTIBILE_INCOMPLETA',
        jsonb_build_object(
            'fattura_id',            NEW.id,
            'numero',                NEW.numero,
            'stato_da',              v_old_codice,
            'stato_a',               v_new_codice,
            'indirizzi_mancanti',    to_jsonb(v_ind_mancanti),
            'intestazione_mancante', to_jsonb(v_int_mancanti),
            'intestazione_incompleta', to_jsonb(v_int_incomplete)),
        NEW.tx_id,
        NEW.id::text,
        array_to_string(v_riassunto, '; ')
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_uscita_draft()
IS 'Guard (BEFORE UPDATE OF stato_doc_fiscale_id) di completezza sull''uscita dalla bozza: una fattura non lascia lo stato iniziale del vocabolario (config.stati_doc_fiscale.iniziale) senza gli indirizzi marcati obbligatori per l''ambito FATTURA (matrice config.tipi_indirizzi_allowed via script.fn_indirizzi_obbligatori_mancanti) e senza l''intestazione fiscale congelata delle due parti (emittente_snapshot, con la sede legale del cedente, e cliente_snapshot, scritte da vendite.fn_snapshot_intestazione_fattura). Sono i due lati della stessa garanzia di ristampa conforme. Esce in testa se lo stato di partenza non e'' quello iniziale (oltre, presidia il guard di congelamento dei satelliti) e se lo stato d''arrivo e'' abortito (una bozza incompleta resta chiudibile). Nessun bypass GUC: il reset del lotto rientra nella bozza, non ne esce. L''intestazione si verifica per jsonb_typeof e non per IS NULL, perche'' jsonb_strip_nulls fa arrivare uno snapshot vuoto come ''{}''. Errore: E_FATTURA_NON_EMETTIBILE_INCOMPLETA, con la mancanza nel messaggio e nel contesto. Il rimedio della sede mancante e'' anagrafico: inserire la sede legale dell''azienda e rieseguire lo step della bozza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
