{% include-markdown "it/dbzero/script/manual/trgfn_codice_maiuscolo.md" %}
# ⚙️ Funzione `trgfn_codice_maiuscolo`

```sql
CREATE FUNCTION trgfn_codice_maiuscolo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_codice_maiuscolo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- text: il trigger serve colonne codice di tipi diversi, e il
    -- valore normalizzato deve poter superare la colonna.
    v_codice text;
    v_max    pg_catalog.pg_attribute.atttypmod%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il codice di una riga si salva nella forma di
    --   script.fn_codice_normalizzato: un codice dell'operatore
    --   non distingue le maiuscole, e l'indice UNIQUE della
    --   colonna lo rende vero.
    --   BEFORE INSERT OR UPDATE (senza OF: anche i generatori
    --   a10 scrivono il codice). Un UPDATE che non cambia il
    --   codice non lo tocca: riscrivere la riga non e' cambiare
    --   il codice, e il lucchetto di colonna non deve scattare.
    --   Montato dall'automazione CODICE_MAIUSCOLO, fase a15.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND NEW.codice IS NOT DISTINCT FROM OLD.codice THEN
        RETURN NEW;
    END IF;

    IF NEW.codice IS NULL THEN
        RETURN NEW;
    END IF;

    v_codice := script.fn_codice_normalizzato(NEW.codice);

    -- ⛔ La mappatura completa puo' allungare il codice (ß -> SS).
    --   NEW.codice ci sta gia' nella colonna: si guarda la
    --   lunghezza ammessa solo se il risultato e' piu' lungo.
    --   varchar(n): atttypmod = n + 4; text e varchar: -1.
    IF char_length(v_codice) > char_length(NEW.codice) THEN
        SELECT CASE WHEN a.atttypmod > 4 THEN a.atttypmod - 4 END
          INTO v_max
          FROM pg_catalog.pg_attribute a
         WHERE a.attrelid = TG_RELID
           AND a.attname  = 'codice'
           AND NOT a.attisdropped;

        IF char_length(v_codice) > v_max THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.trgfn_codice_maiuscolo',
                'E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO',
                jsonb_build_object(
                    'campo',              'codice',
                    'tabella',            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                    'codice',             NEW.codice,
                    'codice_normalizzato', v_codice,
                    'lunghezza_massima',  v_max),
                NULL::uuid,
                NEW.codice::text, v_codice, v_max::text);
        END IF;
    END IF;

    NEW.codice := v_codice;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_codice_maiuscolo()
IS 'Trigger function dell''automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04): salva NEW.codice nella forma di script.fn_codice_normalizzato — senza spazi ai lati, in maiuscolo con la mappatura Unicode completa (straße -> STRASSE). Un codice dell''operatore e'' un identificativo e non distingue le maiuscole: col valore normalizzato, l''indice UNIQUE della colonna e'' un''unicita'' senza distinzione di maiuscole e nessun lettore ripete la formula (linee-guida-sql §8.5). BEFORE INSERT OR UPDATE senza OF, perche'' anche i generatori a10_gen_codice scrivono il codice; fase a15, dopo di loro: anche un codice generato si salva normalizzato. Un UPDATE che non cambia il codice non lo tocca: riscrivere la riga non e'' cambiare il codice, e il lucchetto di colonna (script.trgfn_lock_columns) non deve scattare. NULL resta NULL. ⛔ Se la mappatura allunga il codice oltre una colonna varchar(n) solleva E_CODICE_TROPPO_LUNGO_IN_MAIUSCOLO (DATO_ERRATO, campo codice) invece del 22001 dell''assegnazione: la lunghezza si legge da pg_attribute solo quando il testo si e'' allungato. Le colonne non si allungano (Tid, 2026-11-04). Non si monta a mano: lo monta dbops.fn_run_automations_codice_maiuscolo su ogni tabella dell''ambito con la colonna codice, tranne le eccezioni di dbops.automazione_codice_eccezioni. Rev 2026-11-04 (20261104-33, richiesta BE brief-be-codice-maiuscolo §6): la forma dal BB, e la frase sulla lunghezza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
