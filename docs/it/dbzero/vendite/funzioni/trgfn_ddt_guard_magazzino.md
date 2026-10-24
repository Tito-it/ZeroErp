# ⚙️ Funzione `trgfn_ddt_guard_magazzino`

```sql
CREATE FUNCTION trgfn_ddt_guard_magazzino()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: le regole del magazzino della bolla che un CHECK non vede
--   (D-L3-a): arrivo solo per la bolla di trasferimento e diverso
--   dalla partenza, magazzini dell'emittente della bolla. Un solo
--   codice per le regole di coerenza: la frase la compone il
--   VARIADIC, che dice quale.
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, regola del 2):
--   «immutabili fuori bozza» non e' piu' qui. Lo dice il BB
--   vendite.trgfn_doc_testata_lock_fuori_bozza
--   (trg_ddt_a05_lock_fuori_bozza_upd), con lo stesso codice
--   E_DDT_MAGAZZINO_IMMUTABILE e la stessa frase, e parla prima.
DECLARE
    v_causale   config.causali_trasporto.causale_magazzino%TYPE;
    v_mag_id    magazzino.magazzini.id%TYPE;
BEGIN
    -- 1. L'arrivo: solo la bolla di trasferimento, e un ALTRO magazzino.
    IF NEW.magazzino_arrivo_id IS NOT NULL THEN
        v_causale := vendite.fn_ddt_causale_magazzino(NEW);
        IF v_causale IS DISTINCT FROM 'TRASF_OUT' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_ddt_guard_magazzino',
                'E_DDT_MAGAZZINO_INCOERENTE',
                jsonb_build_object('ddt_id', NEW.id, 'regola', 'ARRIVO_SOLO_TRASFERIMENTO',
                                   'causale_magazzino', v_causale),
                NEW.tx_id,
                'il magazzino di arrivo lo indica solo una bolla di trasferimento fra depositi');
        END IF;
        IF NEW.magazzino_arrivo_id = NEW.magazzino_id THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_ddt_guard_magazzino',
                'E_DDT_MAGAZZINO_INCOERENTE',
                jsonb_build_object('ddt_id', NEW.id, 'regola', 'ARRIVO_UGUALE_PARTENZA',
                                   'magazzino_id', NEW.magazzino_id),
                NEW.tx_id,
                'il magazzino di arrivo coincide con quello di partenza');
        END IF;
    END IF;

    -- 2. Dell'emittente della bolla (M-6). La regola sta nel BB
    --    script.fn_magazzino_dell_emittente (rev 2026-09-28, regola del 2:
    --    il reso e' la seconda occorrenza): letta sotto RLS, un magazzino di
    --    un altro emittente non si vede, e la frase e' la stessa.
    FOREACH v_mag_id IN ARRAY ARRAY[NEW.magazzino_id, NEW.magazzino_arrivo_id] LOOP
        CONTINUE WHEN v_mag_id IS NULL;
        IF NOT script.fn_magazzino_dell_emittente(v_mag_id, NEW.emittente_fiscale_id) THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_ddt_guard_magazzino',
                'E_DDT_MAGAZZINO_INCOERENTE',
                jsonb_build_object('ddt_id', NEW.id, 'regola', 'EMITTENTE',
                                   'magazzino_id', v_mag_id,
                                   'emittente_ddt', NEW.emittente_fiscale_id),
                NEW.tx_id,
                'il magazzino indicato non appartiene all''azienda che emette la bolla');
        END IF;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_magazzino()
IS 'Guard BEFORE INSERT OR UPDATE OF magazzino_id, magazzino_arrivo_id, causale_trasporto_id, emittente_fiscale_id su vendite.ddt (D-L3-a). E_DDT_MAGAZZINO_INCOERENTE, con la regola nel VARIADIC: arrivo su una bolla che non e'' di trasferimento (causale di magazzino diversa da TRASF_OUT), arrivo uguale alla partenza, magazzino di un altro emittente (letto sotto RLS: invisibile e inesistente rispondono uguale). L''arrivo mancante NON e'' qui: e'' un motivo dell''emissione (script.fn_check_ddt_merce). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt. rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, regola del 2): la regola «magazzino dell''emittente» passa al BB script.fn_magazzino_dell_emittente, che il guard del reso (vendite.trgfn_resi_guard_magazzino) usa uguale. rev 2026-10-09 (brief-db-esecutivi-ba-coppia, regola del 2): «immutabili fuori bozza» (E_DDT_MAGAZZINO_IMMUTABILE) passa al BB vendite.trgfn_doc_testata_lock_fuori_bozza, trigger trg_ddt_a05_lock_fuori_bozza_upd: stesso codice, stessa frase, e parla prima di questo guard.';
```

</div>

---
{% include-markdown "signature-core.md" %}
