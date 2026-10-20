# ⚙️ Funzione `trgfn_soggetti_guard_regime_pa`

```sql
CREATE FUNCTION trgfn_soggetti_guard_regime_pa()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_regime_pa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: cliente_pa e split_payment a 'S' solo se la natura li ammette.
--   config.tipi_soggetto_dettaglio.cliente_pa_ammesso /
--   split_payment_ammesso: false -> il flag resta 'N'.
--   Il VALORE (S/N) lo presidiano i CHECK chk_soggetti_cliente_pa e
--   chk_soggetti_split_payment; qui si decide solo PER CHI, cioe' la
--   parte che sta in un'altra tabella e che un CHECK non puo' leggere.
-- Aggancio: BEFORE INSERT OR UPDATE OF cliente_pa, split_payment,
--   tipo_soggetto_dettaglio_id. Il ramo sulla natura copre il cambio di
--   natura. Nessun altro trigger BEFORE di soggetti scrive queste tre
--   colonne (linee-guida-trigger, «UPDATE OF»).
-- ⭐ Senza natura RIFIUTA un flag a 'S' (A-5): diverge apposta dai
--   guard del sesso e di CF/P.IVA, che li' tacciono.
-- Brief: brief-db-dati-fiscali-e-societari-del-soggetto (A-3, A-5).
-- =========================================================
DECLARE
    v_cliente_pa_ammesso    config.tipi_soggetto_dettaglio.cliente_pa_ammesso%TYPE;
    v_split_payment_ammesso config.tipi_soggetto_dettaglio.split_payment_ammesso%TYPE;
    v_descrizione           config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_codice                config.tipi_soggetto_dettaglio.codice_interno%TYPE;
BEGIN
    -- Due flag a 'N': nessuna natura ha niente da dire.
    IF NEW.cliente_pa IS DISTINCT FROM 'S' AND NEW.split_payment IS DISTINCT FROM 'S' THEN
        RETURN NEW;
    END IF;

    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_regime_pa',
            'E_DATO_FISCALE_SENZA_TIPO_SOGGETTO',
            jsonb_build_object('campo',         'tipo_soggetto_dettaglio_id',
                               'soggetto_id',   NEW.id,
                               'cliente_pa',    NEW.cliente_pa,
                               'split_payment', NEW.split_payment),
            NEW.tx_id,
            -- frase chiusa: il VARIADIC si passa vuoto ma ESPLICITO,
            -- o la firma variadica non si risolve
            VARIADIC ARRAY[]::text[]);
    END IF;

    SELECT tsd.cliente_pa_ammesso, tsd.split_payment_ammesso,
           tsd.descrizione, tsd.codice_interno
      INTO v_cliente_pa_ammesso, v_split_payment_ammesso,
           v_descrizione, v_codice
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    IF NOT FOUND THEN
        RETURN NEW;   -- la FK fk_soggetti_tipo_soggetto_dettaglio parla dopo
    END IF;

    IF NEW.cliente_pa = 'S' AND NOT v_cliente_pa_ammesso THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_regime_pa',
            'E_CLIENTE_PA_NON_AMMESSO',
            jsonb_build_object('campo',                      'cliente_pa',
                               'soggetto_id',                NEW.id,
                               'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                               'codice_interno',             v_codice),
            NEW.tx_id,
            COALESCE(v_descrizione, v_codice));
    END IF;

    IF NEW.split_payment = 'S' AND NOT v_split_payment_ammesso THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.trgfn_soggetti_guard_regime_pa',
            'E_SPLIT_PAYMENT_NON_AMMESSO',
            jsonb_build_object('campo',                      'split_payment',
                               'soggetto_id',                NEW.id,
                               'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                               'codice_interno',             v_codice),
            NEW.tx_id,
            COALESCE(v_descrizione, v_codice));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_regime_pa()
IS 'Guard BEFORE INSERT OR UPDATE OF cliente_pa, split_payment, tipo_soggetto_dettaglio_id su anagrafiche.soggetti: un flag a S deve essere ammesso dalla natura (config.tipi_soggetto_dettaglio.cliente_pa_ammesso / split_payment_ammesso), altrimenti E_CLIENTE_PA_NON_AMMESSO o E_SPLIT_PAYMENT_NON_AMMESSO col flag nel campo. Senza natura un flag a S e'' rifiutato con E_DATO_FISCALE_SENZA_TIPO_SOGGETTO (A-5): diverge apposta dai guard del sesso e di CF/P.IVA, che li'' tacciono. Due flag a N passano sempre. Il cambio di natura e'' coperto: chi cambia natura porta il flag a N nella stessa scrittura, il DB non lo azzera. Brief: brief-db-dati-fiscali-e-societari-del-soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
