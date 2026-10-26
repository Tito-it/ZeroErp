{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_sync_stato_pdp.md" %}
# ⚙️ Funzione `trgfn_clienti_sync_stato_pdp`

```sql
CREATE FUNCTION trgfn_clienti_sync_stato_pdp()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_oggi          anagrafiche.clienti.data_attivazione%TYPE;
    v_stato_att_id  config.stati_pdp.id%TYPE;
    v_stato_disp_id config.stati_pdp.id%TYPE;
    v_pdp_id        anagrafiche.clienti.pdp_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: lo stato tecnico del PDP segue l'occupazione:
    --   occupato (un cliente col periodo che contiene oggi)
    --   -> DISP diventa ATT; libero -> ATT diventa DISP.
    --   DTEC e DISM non si toccano.
    -- rev 2026-10-14 (C-8 di brief-db-cliente-manuale-uno-per-
    --   soggetto-e-utility): prima leggeva lo stato del cliente,
    --   e solo AT/CH.
    -- =========================================================
    IF NEW.pdp_id IS NULL
       AND (TG_OP = 'INSERT' OR OLD.pdp_id IS NULL) THEN
        RETURN NULL;
    END IF;

    SELECT id INTO v_stato_att_id
      FROM config.stati_pdp
     WHERE codice_interno = 'ATT';

    SELECT id INTO v_stato_disp_id
      FROM config.stati_pdp
     WHERE codice_interno = 'DISP';

    IF v_stato_att_id IS NULL OR v_stato_disp_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_stato_pdp',
            'E_CODICE',
            jsonb_build_object('stati_pdp', 'ATT/DISP'),
            NEW.tx_id,
            'ATT/DISP',
            'config.stati_pdp'
        );
    END IF;

    v_oggi := script.fn_data_operativa();

    -- Il PDP del cliente e, se il cliente l'ha lasciato,
    -- quello di prima.
    FOR v_pdp_id IN
        SELECT DISTINCT p.id
          FROM unnest(ARRAY[
                   NEW.pdp_id,
                   CASE WHEN TG_OP = 'UPDATE' THEN OLD.pdp_id END]) AS p(id)
         WHERE p.id IS NOT NULL
    LOOP
        IF anagrafiche.fn_check_pdp_occupato(v_pdp_id, v_oggi) THEN
            UPDATE anagrafiche.pdp p
               SET stato_pdp_id = v_stato_att_id
             WHERE p.id = v_pdp_id
               AND p.stato_pdp_id = v_stato_disp_id;
        ELSE
            UPDATE anagrafiche.pdp p
               SET stato_pdp_id = v_stato_disp_id
             WHERE p.id = v_pdp_id
               AND p.stato_pdp_id = v_stato_att_id;
        END IF;
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()
IS 'Trigger AFTER su anagrafiche.clienti: lo stato tecnico del PDP segue l''occupazione (anagrafiche.fn_check_pdp_occupato, il periodo che contiene il giorno operativo): occupato e DISP -> ATT; libero e ATT -> DISP; DTEC e DISM non si toccano. Se il cliente cambia PDP si ricalcolano entrambi. rev 2026-10-14 (C-8): prima leggeva lo stato del cliente, solo AT/CH, sotto RLS. Limite: una chiusura con data futura libera il PDP alla prossima scrittura, non alla data. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
