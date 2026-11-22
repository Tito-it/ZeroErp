{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_obbligatori_ruolo.md" %}
# ⚙️ Funzione `trgfn_indirizzi_guard_obbligatori_ruolo`

```sql
CREATE FUNCTION trgfn_indirizzi_guard_obbligatori_ruolo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.soggetto_ruolo_id IS NOT DISTINCT FROM NEW.soggetto_ruolo_id
       AND OLD.tipo_indirizzo_id IS NOT DISTINCT FROM NEW.tipo_indirizzo_id THEN
        RETURN NULL;
    END IF;

    PERFORM anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(OLD.soggetto_ruolo_id, NULL::uuid);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo()
IS 'Constraint trigger DEFERRABLE su anagrafiche.indirizzi, AFTER UPDATE OR DELETE: quando si cancella un indirizzo del ruolo, o se ne cambia il tipo o il ruolo, il ruolo di prima (OLD.soggetto_ruolo_id) deve avere ancora i suoi indirizzi obbligatori, a fine transazione. Il controllo e'' anagrafiche.fn_guard_indirizzi_obbligatori_ruolo (E_INDIRIZZO_OBBLIGATORIO_MANCANTE); un ruolo cancellato nella stessa transazione tace. Un UPDATE che non cambia ne'' il tipo ne'' il ruolo non chiede niente. Gemello di anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto, il layer SOGGETTO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
