{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_guard_stato.md" %}
# ⚙️ Funzione `trgfn_fatture_guard_stato`

```sql
CREATE FUNCTION trgfn_fatture_guard_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: il cambio di stato della fattura (BEFORE UPDATE OF
--   stato_doc_fiscale_id).
--   1. Lo stato d'arrivo si applica alla fattura
--      (config.stati_doc_fiscale.applica_fattura). Sulla
--      DESTINAZIONE, non sulla coppia: copre ogni strada, anche
--      una futura. La nascita non e' un cambio: la copre il CHECK
--      chk_stati_doc_fiscale_iniziale_applica.
--   2. Il passaggio e' una riga ammessa della matrice
--      config.stati_doc_fiscale_transizioni con solo_lotto =
--      false: nessuna riga della fattura torna indietro.
--   3. Entrando in EMESSA, i motivi di
--      script.fn_check_fattura_emettibile.
-- =========================================================
DECLARE
    v_ok         boolean;  -- esito di EXISTS sulla matrice
    v_applica    config.stati_doc_fiscale.applica_fattura%TYPE;
    v_codice_a   config.stati_doc_fiscale.codice_interno%TYPE;
BEGIN
    -- UPDATE OF scatta anche a valore uguale: senza cambio, niente.
    IF NEW.stato_doc_fiscale_id IS NOT DISTINCT FROM OLD.stato_doc_fiscale_id THEN
        RETURN NEW;
    END IF;

    SELECT s.applica_fattura, s.codice_interno
      INTO v_applica, v_codice_a
      FROM config.stati_doc_fiscale s
     WHERE s.id = NEW.stato_doc_fiscale_id;

    -- 1. La destinazione si applica alla fattura.
    IF v_applica IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'stato_doc_fiscale_id', 'atteso', 'applica_fattura=true', 'ricevuto', NEW.stato_doc_fiscale_id),
            NULL::uuid, 'stato non applicabile a fattura', NEW.stato_doc_fiscale_id::text);
    END IF;

    -- 2. Il passaggio e' ammesso dalla matrice.
    SELECT EXISTS (
        SELECT 1 FROM config.stati_doc_fiscale_transizioni t
         WHERE t.ammesso AND t.stato_from_id = OLD.stato_doc_fiscale_id AND t.stato_to_id = NEW.stato_doc_fiscale_id AND t.solo_lotto = FALSE
    ) INTO v_ok;
    IF NOT v_ok THEN
        PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'transizione_stato', 'atteso', concat(OLD.stato_doc_fiscale_id, '→ammessa'), 'ricevuto', NEW.stato_doc_fiscale_id),
            NULL::uuid, concat('transizione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), 'fattura');
    END IF;

    -- 3. IL CANCELLO ALL'EMISSIONE. Entrando in EMESSA, da
    --   qualunque stato, la fattura non deve avere motivi: oggi una
    --   riga senza aliquota IVA (E_FATTURA_RIGA_IVA_MANCANTE). Il
    --   predicato sta nella check; l'helper solleva il codice del
    --   primo motivo e tace su [].
    -- ⚠️ Sulla DESTINAZIONE, non su una coppia DRAFT -> EMESSA.
    -- ⛔ La bozza resta libera: il vincolo e' all'emissione, non al
    --   salvataggio della riga.
    -- ⚠️ EMESSA per codice: il vocabolario fiscale non dichiara
    --   ancora quale stato e' l'emissione.
    IF v_codice_a = 'EMESSA' THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', TG_NAME::text,
            script.fn_check_fattura_emettibile(NEW.id),
            NULL,
            NEW.tx_id,
            jsonb_build_object('fattura_id', NEW.id,
                               'stato_a',    v_codice_a));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_stato()
IS 'Guard (BEFORE UPDATE OF stato_doc_fiscale_id) del cambio di stato della fattura. Lo stato d''arrivo deve applicarsi alla fattura (config.stati_doc_fiscale.applica_fattura): la regola sta sulla destinazione e vale per ogni strada; la nascita la copre il CHECK chk_stati_doc_fiscale_iniziale_applica. Il passaggio deve essere una riga ammessa di config.stati_doc_fiscale_transizioni con solo_lotto = false: nessuna riga della fattura torna indietro. Errore dei due controlli: E_LOTTO_PARAMETRO_NON_COERENTE (parametro stato_doc_fiscale_id o transizione_stato). Entrando in EMESSA, da qualunque stato, solleva il primo motivo di script.fn_check_fattura_emettibile (una riga senza aliquota IVA) con script.fn_raise_primo_motivo_se_presente; la bozza resta libera. Lo stato lo scrivono i verbi (porta script.trgfn_doc_stato_solo_dal_verbo): vendite.fn_fattura_proietta_stato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
