{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_dati_societari_required.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_dati_societari_required`

```sql
CREATE FUNCTION trgfn_soggetti_guard_dati_societari_required()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_dati_societari_required()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_policy       config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
    v_cod_int_tipo config.tipi_soggetto_dettaglio.codice_interno%TYPE;
    v_has_dati     boolean;   -- esito di un EXISTS: nessuna colonna da ancorare
BEGIN
    /*
    Controllo esistenza dati_societari SOLO per i casi in cui
    la policy del tipo_soggetto_dettaglio è 'REQUIRED'.

    Il trigger è DEFERRABLE INITIALLY DEFERRED, quindi il controllo avviene
    a fine transazione: è possibile inserire soggetto e dati_societari
    nella stessa transazione.
    */

    -- Se non è impostato il tipo_soggetto_dettaglio, al momento non applichiamo
    -- la regola di obbligatorietà. In futuro si può irrigidire se necessario.
    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Recupero policy e codice_interno dal tipo_soggetto_dettaglio
    SELECT tsd.dati_societari_policy,
        tsd.codice_interno
    INTO v_policy,
        v_cod_int_tipo
    FROM config.tipi_soggetto_dettaglio tsd
    WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    -- Tipo dettaglio non trovato o non coerente con la configurazione
    IF v_policy IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_soggetti_guard_dati_societari_required',
            'E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO',
            jsonb_build_object(
                'soggetto_id', NEW.id,
                'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                'codice_interno', v_cod_int_tipo
            ),
            new.tx_id,
            NEW.id::text,
            COALESCE(v_cod_int_tipo, '<NULL>')
        );
    END IF;

    -- Se la policy non è REQUIRED, nessun controllo aggiuntivo
    IF v_policy <> 'REQUIRED' THEN
        RETURN NEW;
    END IF;

    -- Per policy = REQUIRED: deve esistere una riga in anagrafiche.dati_societari
    SELECT EXISTS (
        SELECT 1
        FROM anagrafiche.dati_societari ds
        WHERE ds.soggetto_id = NEW.id
    )
    INTO v_has_dati;

    IF NOT v_has_dati THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_soggetti_guard_dati_societari_required',
            'E_DATI_SOCIETARI_REQUIRED_MANCANTI',
            jsonb_build_object(
                'soggetto_id', NEW.id,
                'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                'codice_interno', v_cod_int_tipo,
                'dati_societari_policy', v_policy
            ),
            new.tx_id,
            NEW.id::text,
            v_cod_int_tipo
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_dati_societari_required()
IS '
Constraint trigger function (DEFERRABLE) su anagrafiche.soggetti che verifica,
a fine transazione, che per i soggetti il cui tipo_soggetto_dettaglio ha
dati_societari_policy = ''REQUIRED'' esista una riga in anagrafiche.dati_societari.

In caso di violazione utilizza script.fn_log_and_raise_error con codice
E_DATI_SOCIETARI_REQUIRED_MANCANTI.
Rev 20261009-21 (brief-db-sesso-senza-default): la variabile della policy segue la colonna
(%TYPE), come codice_interno, non il tipo, che e'' passato al generico config.presenza_policy_enum.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
