{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_guard_regime_conferma.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_guard_regime_conferma`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_guard_regime_conferma()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_scritta boolean;   -- il chiamante ha scritto la conferma
BEGIN
    -- ------------------------------------------------------------
    -- Guard: data e autore della conferma del regime li scrive il
    -- database (trgfn_emittenti_fiscali_regime_conferma, a20), da
    -- una dichiarazione del regime. Fase a10, BEFORE INSERT /
    -- UPDATE OF regime_fiscale_confermato_il, _da: qui NEW porta
    -- ancora i valori del chiamante.
    -- ------------------------------------------------------------
    IF TG_OP = 'INSERT' THEN
        -- La INSERT non conferma mai.
        v_scritta := NEW.regime_fiscale_confermato_il IS NOT NULL
                  OR NEW.regime_fiscale_confermato_da IS NOT NULL;
    ELSE
        -- Il valore, non la menzione: riscrivere lo stesso valore
        -- non scrive una conferma.
        v_scritta := NEW.regime_fiscale_confermato_il IS DISTINCT FROM OLD.regime_fiscale_confermato_il
                  OR NEW.regime_fiscale_confermato_da IS DISTINCT FROM OLD.regime_fiscale_confermato_da;
    END IF;

    IF v_scritta THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_EMITTENTE_REGIME_CONFERMA_DERIVATA',
            jsonb_build_object(
                'table',                        TG_TABLE_NAME,
                'operazione',                   TG_OP,
                'emittente_fiscale_id',         NEW.id,
                'regime_fiscale_confermato_il', NEW.regime_fiscale_confermato_il,
                'regime_fiscale_confermato_da', NEW.regime_fiscale_confermato_da
            ),
            NULL::uuid,
            COALESCE(NEW.codice, NEW.id::text)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma()
IS 'Guard a10 su anagrafiche.emittenti_fiscali (BEFORE INSERT / UPDATE OF regime_fiscale_confermato_il, regime_fiscale_confermato_da): le due colonne della conferma del regime non si scrivono da fuori. Rifiuta una INSERT che le valorizza (la INSERT non conferma mai) e un UPDATE che le cambia (il valore, non la menzione: riscriverle uguali passa). Le deriva il trigger a20 trgfn_emittenti_fiscali_regime_conferma da un UPDATE OF regime_fiscale_rf, e parla dopo questo guard: e'' l''ordine a10 < a20 che separa lo scrittore esterno dalla derivazione. Errore: E_EMITTENTE_REGIME_CONFERMA_DERIVATA (TECNICO). Brief: brief-db-esigibilita-iva-per-cassa-emittente (sezione 10).';
```

</div>

---
{% include-markdown "signature-core.md" %}
