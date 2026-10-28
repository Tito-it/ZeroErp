{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_guard_stato_date.md" %}
# ⚙️ Funzione `trgfn_clienti_guard_stato_date`

```sql
CREATE FUNCTION trgfn_clienti_guard_stato_date()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_guard_stato_date()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_a          config.stati_cliente.codice_interno%TYPE;
    v_a_descr    config.stati_cliente.descrizione%TYPE;
    v_da         config.stati_cliente.codice_interno%TYPE;
    v_da_descr   config.stati_cliente.descrizione%TYPE;
    v_cliente    text;
    v_campo      text;
    v_data_nome  text;
BEGIN
    SELECT sc.codice_interno, sc.descrizione
      INTO v_a, v_a_descr
      FROM config.stati_cliente sc
     WHERE sc.id = NEW.stato_cliente_id;

    IF TG_OP = 'UPDATE' THEN
        SELECT sc.codice_interno, sc.descrizione
          INTO v_da, v_da_descr
          FROM config.stati_cliente sc
         WHERE sc.id = OLD.stato_cliente_id;
    END IF;

    -- Come l'operatore riconosce il cliente: il codice del
    -- suo BA (C-3). NEW.id c'e' gia' anche su INSERT (default
    -- della identity, calcolato prima dei BEFORE).
    SELECT ba.codice
      INTO v_cliente
      FROM anagrafiche.billing_account ba
     WHERE ba.id = NEW.billing_account_id;
    v_cliente := COALESCE(v_cliente, '#' || NEW.id::text);

    -- 1. Il grafo, sul cambio di stato.
    IF TG_OP = 'UPDATE'
       AND NEW.stato_cliente_id IS DISTINCT FROM OLD.stato_cliente_id
       AND NOT EXISTS (
               SELECT 1
                 FROM config.transizioni_stati_cliente t
                WHERE t.stato_da_id = OLD.stato_cliente_id
                  AND t.stato_a_id  = NEW.stato_cliente_id
                  AND t.attivo) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_clienti_guard_stato_date',
            'E_CLIENTE_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'campo',      'stato_cliente_id',
                'cliente_id', NEW.id,
                'stato_da',   v_da,
                'stato_a',    v_a),
            NEW.tx_id,
            v_cliente, v_da_descr::text, v_a_descr::text);
    END IF;

    -- 2. Da chiuso la data di chiusura non cambia.
    IF TG_OP = 'UPDATE'
       AND v_da IN ('CH', 'CM', 'CW', 'CF')
       AND NEW.data_chiusura IS DISTINCT FROM OLD.data_chiusura THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_clienti_guard_stato_date',
            'E_CLIENTE_DATA_CHIUSURA_IMMUTABILE',
            jsonb_build_object(
                'campo',      'data_chiusura',
                'cliente_id', NEW.id),
            NEW.tx_id,
            v_cliente, OLD.data_chiusura::text);
    END IF;

    -- 3. La data che lo stato pretende. Una per volta, nell'ordine
    --    in cui la vita del cliente le scrive.
    IF v_a IN ('AT', 'RS', 'SF', 'SC', 'CH', 'CM', 'CW', 'CF')
       AND NEW.data_attivazione IS NULL THEN
        v_campo := 'data_attivazione';
        v_data_nome := 'attivazione';
    ELSIF v_a IN ('SF', 'SC')
       AND NEW.data_sospensione IS NULL THEN
        v_campo := 'data_sospensione';
        v_data_nome := 'sospensione';
    ELSIF v_a IN ('CH', 'CM', 'CW', 'CF')
       AND NEW.data_chiusura IS NULL THEN
        v_campo := 'data_chiusura';
        v_data_nome := 'chiusura';
    ELSIF TG_OP = 'UPDATE'
       AND v_a = 'AT' AND v_da IN ('SF', 'SC')
       AND NEW.data_riattivazione IS NULL THEN
        v_campo := 'data_riattivazione';
        v_data_nome := 'riattivazione';
    END IF;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_clienti_guard_stato_date',
            'E_CLIENTE_STATO_SENZA_DATA',
            jsonb_build_object(
                'campo',      v_campo,
                'cliente_id', NEW.id,
                'stato',      v_a),
            NEW.tx_id,
            v_cliente, v_a_descr::text, v_data_nome);
    END IF;

    -- La chiusura non precede l'attivazione (AN escluso: il
    -- periodo gli azzera le date).
    IF v_a IS DISTINCT FROM 'AN'
       AND NEW.data_chiusura < NEW.data_attivazione THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_clienti_guard_stato_date',
            'E_DATA_CHIUSURA',
            jsonb_build_object(
                'campo',      'data_chiusura',
                'cliente_id', NEW.id),
            NEW.tx_id,
            v_cliente, NEW.data_chiusura::text, NEW.data_attivazione::text);
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_guard_stato_date()
IS 'Guard BEFORE INSERT OR UPDATE su anagrafiche.clienti (C-5, C-6 di Tid del 2026-10-13/14): (1) il cambio di stato segue config.transizioni_stati_cliente (E_CLIENTE_STATO_TRANSIZIONE_INVALIDA; l''INSERT non passa dal grafo); (2) da chiuso (CH, CM, CW, CF) la data di chiusura non cambia (E_CLIENTE_DATA_CHIUSURA_IMMUTABILE); (3) ogni stato pretende la sua data: AT/RS l''attivazione, SF/SC anche la sospensione, i chiusi anche la chiusura, AT da un sospeso la riattivazione (E_CLIENTE_STATO_SENZA_DATA); la chiusura non precede l''attivazione (E_DATA_CHIUSURA). PR, AN, AG senza date pretese. La frase porta il codice del billing account. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
