{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_obbligatori_ruoli.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_obbligatori_ruoli`

```sql
CREATE FUNCTION trgfn_soggetti_guard_obbligatori_ruoli()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    FOR v_ruolo_id IN
        SELECT sr.id
          FROM anagrafiche.soggetti_ruoli sr
         WHERE sr.soggetto_id = NEW.id
         ORDER BY sr.id
    LOOP
        PERFORM anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(v_ruolo_id, NEW.tx_id);
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli()
IS 'Constraint trigger DEFERRABLE su anagrafiche.soggetti, AFTER UPDATE quando cambia la natura (tipo_soggetto_dettaglio_id): ogni ruolo del soggetto deve avere, a fine transazione, gli indirizzi obbligatori che il requisito chiede sulla natura nuova. Il requisito del ruolo dipende dalla natura (anagrafiche.fn_indirizzi_obbligatori_ruolo); il controllo e'' anagrafiche.fn_guard_indirizzi_obbligatori_ruolo, ruolo per ruolo in ordine di id (E_INDIRIZZO_OBBLIGATORIO_MANCANTE al primo mancante). Gli indirizzi che la natura nuova vieta li ferma prima anagrafiche.fn_check_cambio_natura_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
