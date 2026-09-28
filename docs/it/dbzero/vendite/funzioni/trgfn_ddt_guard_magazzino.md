# ⚙️ Funzione `trgfn_ddt_guard_magazzino`

```sql
CREATE FUNCTION trgfn_ddt_guard_magazzino()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: le regole del magazzino della bolla che un CHECK non vede
--   (D-L3-a): immutabile fuori bozza, arrivo solo per la bolla di
--   trasferimento e diverso dalla partenza, magazzini dell'emittente
--   della bolla. Un solo codice per le regole di coerenza: la frase la
--   compone il VARIADIC, che dice quale.
DECLARE
    v_stato_old config.stati_doc_ddt.codice_interno%TYPE;
    v_causale   config.causali_trasporto.causale_magazzino%TYPE;
    v_ef        magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_mag_id    magazzino.magazzini.id%TYPE;
BEGIN
    -- 1. Immutabili fuori bozza: lo stato VECCHIO decide.
    IF TG_OP = 'UPDATE'
       AND (NEW.magazzino_id        IS DISTINCT FROM OLD.magazzino_id
            OR NEW.magazzino_arrivo_id IS DISTINCT FROM OLD.magazzino_arrivo_id) THEN
        SELECT s.codice_interno INTO v_stato_old
          FROM config.stati_doc_ddt s
         WHERE s.id = OLD.stato_doc_ddt_id;
        IF v_stato_old IS DISTINCT FROM 'DRAFT' THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_ddt_guard_magazzino',
                'E_DDT_MAGAZZINO_IMMUTABILE',
                jsonb_build_object('ddt_id', NEW.id, 'stato', v_stato_old,
                                   'magazzino_da', OLD.magazzino_id, 'magazzino_a', NEW.magazzino_id,
                                   'arrivo_da', OLD.magazzino_arrivo_id, 'arrivo_a', NEW.magazzino_arrivo_id),
                -- Niente bersaglio: DDT non e' (ancora) un tipo di
                -- config.tipi_entita, e l'operatore e' gia' sulla bolla.
                NEW.tx_id,
                COALESCE(v_stato_old, 'NULL'));
        END IF;
    END IF;

    -- 2. L'arrivo: solo la bolla di trasferimento, e un ALTRO magazzino.
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

    -- 3. Dell'emittente della bolla (M-6). Sotto RLS: un magazzino di un
    --    altro emittente non si vede, e la frase e' la stessa.
    FOREACH v_mag_id IN ARRAY ARRAY[NEW.magazzino_id, NEW.magazzino_arrivo_id] LOOP
        CONTINUE WHEN v_mag_id IS NULL;
        v_ef := NULL;
        SELECT m.emittente_fiscale_id INTO v_ef
          FROM magazzino.magazzini m
         WHERE m.id = v_mag_id;
        IF v_ef IS DISTINCT FROM NEW.emittente_fiscale_id THEN
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
IS 'Guard BEFORE INSERT OR UPDATE OF magazzino_id, magazzino_arrivo_id, causale_trasporto_id, emittente_fiscale_id su vendite.ddt (D-L3-a). E_DDT_MAGAZZINO_IMMUTABILE: il magazzino (o l''arrivo) cambia su una bolla che non era in bozza — stato VECCHIO, come la causale. E_DDT_MAGAZZINO_INCOERENTE, con la regola nel VARIADIC: arrivo su una bolla che non e'' di trasferimento (causale di magazzino diversa da TRASF_OUT), arrivo uguale alla partenza, magazzino di un altro emittente (letto sotto RLS: invisibile e inesistente rispondono uguale). L''arrivo mancante NON e'' qui: e'' un motivo dell''emissione (script.fn_check_ddt_merce). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

---
{% include-markdown "signature-core.md" %}
