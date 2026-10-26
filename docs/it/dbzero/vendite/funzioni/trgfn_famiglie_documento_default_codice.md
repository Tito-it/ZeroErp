# ⚙️ Funzione `trgfn_famiglie_documento_default_codice`

```sql
CREATE FUNCTION trgfn_famiglie_documento_default_codice()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_famiglie_documento_default_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dare un `codice` alla famiglia che nasce senza: vale il
    --   codice_interno, cioe' il valore che la lista mostrava
    --   prima che la colonna esistesse.
    --
    -- ⚠️ La stringa vuota vale NULL: un form che manda il campo
    --   vuoto non sceglie un codice, non lo sceglie affatto.
    -- ⚠️ Solo INSERT (vedi il trigger): in UPDATE un codice
    --   vuoto lo rifiutano NOT NULL e CHECK, non lo si ripara.
    -- =========================================================
    IF NEW.codice IS NULL OR btrim(NEW.codice) = '' THEN
        NEW.codice := NEW.codice_interno;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_famiglie_documento_default_codice()
IS 'Trigger BEFORE INSERT su vendite.famiglie_documento: se la famiglia nasce senza `codice` (NULL o stringa vuota), vale il codice_interno — il valore che la lista mostrava prima che la colonna esistesse. ⭐ Esiste perche'' le famiglie nascono anche dalla madre vendite.fn_crea_famiglia_documento e dal CRUD del backend, che il codice non lo passano: col default qui il NOT NULL regge senza cambiare la firma della madre. ⚠️ Solo INSERT: in UPDATE un codice vuoto e'' un errore dell''operatore, e lo rifiutano NOT NULL e chk_famiglie_documento_codice_nonvuoto invece di ripararlo in silenzio. Brief: brief-db-ricerca-full-colonne-da-accendere.md §3.5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
