{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_set_periodo.md" %}
# ⚙️ Funzione `trgfn_clienti_set_periodo`

```sql
CREATE FUNCTION trgfn_clienti_set_periodo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_set_periodo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice_stato config.stati_cliente.codice_interno%TYPE;
BEGIN
    -- Scopo: deriva periodo = [data_attivazione, data_chiusura).
    --   La data di chiusura e' l'estremo escluso; senza chiusura
    --   il periodo e' aperto.
    -- ⚠️ rev 2026-10-14 (brief-db-cliente-manuale-uno-per-soggetto-e-utility):
    --   i controlli sulle date (E_DATA_APERTURA per AT,
    --   E_DATA_CHIUSURA per CH) sono passati, per tutti gli
    --   stati, ad anagrafiche.trgfn_clienti_guard_stato_date.
    SELECT sc.codice_interno
      INTO v_codice_stato
      FROM config.stati_cliente sc
     WHERE sc.id = NEW.stato_cliente_id;

    -- Annullato: nessuna data, nessun periodo.
    IF v_codice_stato = 'AN' THEN
        NEW.data_attivazione := NULL;
        NEW.data_chiusura    := NULL;
        NEW.periodo          := NULL;
        RETURN NEW;
    END IF;

    IF NEW.data_attivazione IS NOT NULL THEN
        NEW.periodo := daterange(
            NEW.data_attivazione,
            COALESCE(NEW.data_chiusura, 'infinity'::date),
            '[)');
    ELSE
        NEW.periodo := NULL;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_set_periodo()
IS 'Trigger BEFORE INSERT OR UPDATE su anagrafiche.clienti: deriva periodo = [data_attivazione, data_chiusura) (chiusura esclusa, aperto senza chiusura; NULL senza attivazione). Lo stato AN azzera date e periodo. Il periodo e'' la misura di «cliente attivo» del modello (ex_clienti_no_overlap_stesso_pdp, anagrafiche.fn_clienti_stessa_chiave). rev 2026-10-14: i controlli sulle date stanno in anagrafiche.trgfn_clienti_guard_stato_date. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
