{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto.md" %}
# ⚙️ Funzione `trgfn_indirizzi_soggetti_guard_obbligatori_soggetto`

```sql
CREATE FUNCTION trgfn_indirizzi_soggetti_guard_obbligatori_soggetto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.soggetto_id IS NOT DISTINCT FROM NEW.soggetto_id
       AND OLD.tipo_indirizzo_id IS NOT DISTINCT FROM NEW.tipo_indirizzo_id THEN
        RETURN NULL;
    END IF;

    -- Si giudica solo cio' che l'indirizzo che esce soddisfaceva (D-T7a-1).
    PERFORM anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(
        OLD.soggetto_id, OLD.tx_id, OLD.tipo_indirizzo_id);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto()
IS 'Constraint trigger DEFERRABLE su anagrafiche.indirizzi_soggetti, AFTER UPDATE OR DELETE: quando si cancella un indirizzo del soggetto, o se ne cambia il tipo o il soggetto, il soggetto di prima (OLD.soggetto_id) deve avere ancora i suoi indirizzi obbligatori, a fine transazione. Il controllo e'' anagrafiche.fn_guard_indirizzi_obbligatori_soggetto (E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO), col tipo che esce: si giudicano solo le righe che quel tipo soddisfaceva, e il tx_id della riga va al log; un soggetto cancellato nella stessa transazione tace. Un UPDATE che non cambia ne'' il tipo ne'' il soggetto non chiede niente. Gemello di anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo, il layer RUOLO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
