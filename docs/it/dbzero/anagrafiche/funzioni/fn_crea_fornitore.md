{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_fornitore.md" %}
# ⚙️ Funzione `fn_crea_fornitore`

```sql
CREATE FUNCTION fn_crea_fornitore(p_soggetto_id uuid, p_campi jsonb, p_contatto jsonb, p_indirizzi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_fornitore(p_soggetto_id uuid, p_campi jsonb DEFAULT '{}'::jsonb, p_contatto jsonb DEFAULT NULL::jsonb, p_indirizzi jsonb DEFAULT '[]'::jsonb)
 RETURNS TABLE(fornitore_id bigint, soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi    jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_sr_id    anagrafiche.fornitori.soggetto_ruolo_id%TYPE;
    v_fo_id    anagrafiche.fornitori.id%TYPE;
    -- Le chiavi opzionali: quelle del backend (_CREATE_ALLOWED),
    -- meno il ruolo e lo stato, che decide la madre.
    c_ammesse  CONSTANT text[] := ARRAY[
        'codice', 'valuta_id', 'modalita_pagamento_id', 'termine_pagamento_id',
        'ritenuta_acconto', 'ritenuta_aliquota', 'regime_fiscale_rf',
        'rating', 'qualifica_scadenza', 'note'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Fare di un soggetto un fornitore: il ruolo FO
    --   (get_or_create), la riga di fornitori nello stato
    --   iniziale VE con le chiavi di p_campi (le assenti, e le
    --   null, al DEFAULT), il contatto del ruolo (se c'e') e gli
    --   indirizzi del ruolo. Ritorna (fornitore_id,
    --   soggetto_ruolo_id).
    --
    -- Regole:
    --   - una chiave fuori elenco si rifiuta: E_CAMPO_NON_AMMESSO. Fuori
    --     elenco anche split payment e instradamento FE, che sono del
    --     soggetto, e le condizioni di pagamento, che sono del termine;
    --   - contatto e indirizzi: le regole sono dei loro BB;
    --   - duplicati e FK escono dai vincoli.
    -- =========================================================
    IF p_soggetto_id IS NULL OR jsonb_typeof(v_campi) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_fornitore', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_id', p_soggetto_id,
                               'tipo_campi',  jsonb_typeof(v_campi)),
            NULL::uuid,
            'anagrafiche.fn_crea_fornitore',
            'soggetto mancante o campi che non sono un oggetto');
    END IF;

    PERFORM script.fn_guard_campi_ammessi(
        v_campi, c_ammesse,
        'anagrafiche', 'anagrafiche.fn_crea_fornitore',
        jsonb_build_object('soggetto_id', p_soggetto_id));

    v_sr_id := script.fn_get_or_create_soggetto_ruolo(
                   p_soggetto_id  := p_soggetto_id,
                   p_cd_int_ruolo := 'FO');

    -- Lo stato iniziale: VE, «in verifica» (la regola del backend).
    v_fo_id := (script.fn_scrivi_riga_da_jsonb(
                    'anagrafiche.fornitori'::regclass,
                    jsonb_strip_nulls(v_campi)
                    || jsonb_build_object(
                           'soggetto_ruolo_id',  v_sr_id,
                           'stato_fornitore_id', (SELECT sf.id
                                                    FROM config.stati_fornitore sf
                                                   WHERE sf.codice_interno = 'VE')))
                ->> 'id')::bigint;

    IF p_contatto IS NOT NULL THEN
        PERFORM anagrafiche.fn_crea_contatto(p_soggetto_id, v_sr_id, p_contatto);
    END IF;

    PERFORM anagrafiche.fn_crea_indirizzi_ruolo(v_sr_id, p_indirizzi);

    RETURN QUERY SELECT v_fo_id, v_sr_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_fornitore(p_soggetto_id uuid, p_campi jsonb, p_contatto jsonb, p_indirizzi jsonb)
IS 'Madre: fa di un soggetto un fornitore in una sola istruzione: il ruolo FO (script.fn_get_or_create_soggetto_ruolo), la riga di anagrafiche.fornitori nello stato iniziale VE, il contatto del ruolo (anagrafiche.fn_crea_contatto, se p_contatto non e'' NULL) e gli indirizzi del ruolo (anagrafiche.fn_crea_indirizzi_ruolo, con l''auto-clone dei tipi obbligatori). p_campi: le chiavi opzionali codice, valuta_id, modalita_pagamento_id, termine_pagamento_id, ritenuta_acconto, ritenuta_aliquota, regime_fiscale_rf, rating, qualifica_scadenza, note; le assenti e le null al DEFAULT (il codice lo genera il trigger); una chiave estranea: E_CAMPO_NON_AMMESSO, col campo. Split payment e instradamento FE non sono chiavi: sono del soggetto (anagrafiche.soggetti, anagrafiche.dati_societari); le condizioni di pagamento sono del termine. Lo stato non e'' un campo: un altro stato e'' un UPDATE dopo. Soggetto mancante o campi non oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA. Contatto e indirizzi rifiutano con i codici dei loro BB; i tipi obbligatori li pretende il guard differito al commit. Duplicati (uq_fornitori_soggetto_ruolo_id, uq_fornitori_codice) e FK (fk_fornitori_regimi_fiscali compresa) escono dai vincoli, che il backend traduce per nome. Non controlla il permesso (dominio anagrafiche). INVOKER. Ritorna (fornitore_id, soggetto_ruolo_id).';
```

</div>

---
{% include-markdown "signature-core.md" %}
