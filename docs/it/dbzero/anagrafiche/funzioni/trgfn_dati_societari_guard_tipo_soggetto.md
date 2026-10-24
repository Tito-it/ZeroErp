{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_dati_societari_guard_tipo_soggetto.md" %}
# ⚙️ Funzione `trgfn_dati_societari_guard_tipo_soggetto`

```sql
CREATE FUNCTION trgfn_dati_societari_guard_tipo_soggetto()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
v_cod_int_tipo   config.tipi_soggetto_dettaglio.codice_interno%TYPE;
v_policy         config.tipi_soggetto_dettaglio.dati_societari_policy%TYPE;
BEGIN
/*
  Recupero:
  - tipo_soggetto_dettaglio (codice_interno + policy dati societari)
  per il soggetto associato a NEW.soggetto_id
*/
SELECT tsd.codice_interno,
        tsd.dati_societari_policy
INTO v_cod_int_tipo,
        v_policy
FROM anagrafiche.soggetti s
LEFT JOIN config.tipi_soggetto_dettaglio tsd
        ON s.tipo_soggetto_dettaglio_id = tsd.id
WHERE s.id = NEW.soggetto_id;

-- Nessun soggetto trovato per soggetto_id
IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
        'database',
        'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
        'E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO',
        jsonb_build_object(
                'soggetto_id', NEW.soggetto_id
        ),
        new.tx_id,
        NEW.soggetto_id::text,
        NULL
        );
END IF;

-- Tipo soggetto dettaglio non configurato o join non riuscita
IF v_policy IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
        'database',
        'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
        'E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO',
        jsonb_build_object(
                'soggetto_id', NEW.soggetto_id,
                'codice_interno', v_cod_int_tipo
        ),
        new.tx_id,
        NEW.soggetto_id::text,
        COALESCE(v_cod_int_tipo, '<NULL>')
        );
END IF;

/*
Policy dati societari:
- NONE      -> dati societari non ammessi per questo tipo -> errore
- OPTIONAL  -> dati societari abilitati (facoltativi)
- REQUIRED  -> dati societari abilitati e previsti come obbligatori a livello dominio
                (l'obbligatorietà verrà verificata da un constraint trigger su soggetti)
*/
IF v_policy = 'NONE' THEN
        PERFORM script.fn_log_and_raise_error(
        'database',
        'anagrafiche.trgfn_dati_societari_guard_tipo_soggetto',
        'E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO',
        jsonb_build_object(
                'soggetto_id', NEW.soggetto_id,
                'codice_interno', v_cod_int_tipo,
                'dati_societari_policy', v_policy
        ),
        new.tx_id,
        NEW.soggetto_id::text,
        v_cod_int_tipo
        );
END IF;

RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_dati_societari_guard_tipo_soggetto()
IS '
Function che controlla, in fase di INSERT/UPDATE su anagrafiche.dati_societari, che:
- il soggetto collegato esista in anagrafiche.soggetti;
- per il tipo_soggetto_dettaglio associato sia configurata una policy dati_societari_policy
diversa da ''NONE'' (tipo config.presenza_policy_enum).
In caso di violazione utilizza script.fn_log_and_raise_error con codici errore specifici.
Rev 20261009-20 (brief-db-sesso-senza-default): la variabile della policy segue la colonna
(%TYPE), come codice_interno, non il tipo, che e'' passato da config.dati_societari_policy_enum al generico
config.presenza_policy_enum.
';
```

</div>

---
{% include-markdown "signature-core.md" %}
