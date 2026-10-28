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
-- Scopo: le transizioni di stato della fattura (matrice
--   config.stati_doc_fiscale_transizioni) e, entrando in EMESSA, i motivi
--   di script.fn_check_fattura_emettibile.
-- Rev 2026-10-22 (20261022-07, D-3 di Tid; §9.9 di
--   brief-be-utenti-di-sviluppo): il cancello IVA all'emissione.
-- Rev 2026-10-27 (20261027-16, brief-modello-documento-vendita §15): via il
--   «blocco retrocessione GIORNALIERO», che decideva «indietro» confrontando
--   la colonna ordine (R-1 vuole avanti/indietro dal vocabolario, non da un
--   ordine) ed era gia' coperto dalla matrice: nessuna riga della fattura
--   (solo_lotto = false) torna indietro, per nessun tipo di lotto. Un
--   passaggio all'indietro lo rifiuta la matrice, qui sotto, con lo stesso
--   codice (parametro transizione_stato).
DECLARE
    v_ok BOOLEAN;
    v_codice_a   config.stati_doc_fiscale.codice_interno%TYPE;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.stato_doc_fiscale_id IS NOT NULL
       AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id
    THEN
        IF OLD.stato_doc_fiscale_id IS NULL THEN
            -- Prima assegnazione
            SELECT s.applica_fattura INTO v_ok FROM config.stati_doc_fiscale s WHERE s.id = NEW.stato_doc_fiscale_id AND s.attivo;
            IF COALESCE(v_ok, FALSE) = FALSE THEN
                PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'stato_doc_fiscale_id', 'atteso', 'applica_fattura=true', 'ricevuto', NEW.stato_doc_fiscale_id),
                    NULL::uuid, 'stato non applicabile a fattura', NEW.stato_doc_fiscale_id::text);
            END IF;
        ELSE
            -- Transizione ammessa
            SELECT EXISTS (
                SELECT 1 FROM config.stati_doc_fiscale_transizioni t
                 WHERE t.ammesso AND t.stato_from_id = OLD.stato_doc_fiscale_id AND t.stato_to_id = NEW.stato_doc_fiscale_id AND t.solo_lotto = FALSE
            ) INTO v_ok;
            IF NOT v_ok THEN
                PERFORM script.fn_log_and_raise_error(TG_TABLE_SCHEMA, TG_NAME, 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'transizione_stato', 'atteso', concat(OLD.stato_doc_fiscale_id, '→ammessa'), 'ricevuto', NEW.stato_doc_fiscale_id),
                    NULL::uuid, concat('transizione ', OLD.stato_doc_fiscale_id, '→', NEW.stato_doc_fiscale_id), 'fattura');
            END IF;
        END IF;
    END IF;

    -- ⭐ IL CANCELLO ALL'EMISSIONE (rev 2026-10-22, 20261022-07).
    --   Entrando in EMESSA, da qualunque stato (anche da uno stato vuoto:
    --   vendite.fn_numera_fattura_opz_emessa lo scrive cosi'), la fattura
    --   non deve avere motivi: oggi una riga senza aliquota IVA
    --   (E_FATTURA_RIGA_IVA_MANCANTE). Il predicato sta nella check;
    --   l'helper solleva il codice del primo motivo e tace su [].
    -- ⚠️ Sulla DESTINAZIONE, non su una coppia DRAFT -> EMESSA: una strada
    --   nuova verso EMESSA nasce gia' coperta (stessa forma del preventivo).
    -- ⛔ La bozza resta libera: il vincolo e' all'emissione, non al
    --   salvataggio della riga (decisione di Tid del 2026-08-29).
    IF TG_OP = 'UPDATE'
       AND NEW.stato_doc_fiscale_id IS DISTINCT FROM OLD.stato_doc_fiscale_id THEN
        SELECT s.codice_interno INTO v_codice_a
          FROM config.stati_doc_fiscale s
         WHERE s.id = NEW.stato_doc_fiscale_id;

        IF v_codice_a = 'EMESSA' THEN
            PERFORM script.fn_raise_primo_motivo_se_presente(
                'vendite', TG_NAME::text,
                script.fn_check_fattura_emettibile(NEW.id),
                NULL,
                NEW.tx_id,
                jsonb_build_object('fattura_id', NEW.id,
                                   'stato_a',    v_codice_a));
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_stato()
IS 'Guard transizioni stato fatture via config.stati_doc_fiscale_transizioni (righe solo_lotto = false). Rev 2026-10-22 (20261022-07, D-3 di Tid; §9.9 di brief-be-utenti-di-sviluppo): entrando in EMESSA, da qualunque stato, solleva il primo motivo di script.fn_check_fattura_emettibile (E_FATTURA_RIGA_IVA_MANCANTE: una riga senza aliquota IVA) con script.fn_raise_primo_motivo_se_presente. La bozza resta libera; la guardia del riepilogo e'' in vendite.fn_ricalcola_riepilogo_iva_fattura. Rev 2026-10-27 (20261027-16, brief-modello-documento-vendita §15, R-1): via il blocco della retrocessione di un GIORNALIERO, che decideva «indietro» dalla colonna ordine ed era gia'' coperto dalla matrice (nessuna riga della fattura torna indietro). Lo stato lo scrivono i verbi (porta script.trgfn_doc_stato_solo_dal_verbo): vendite.fn_fattura_proietta_stato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
