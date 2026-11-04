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
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il codice di una riga si salva in upper(btrim(codice)):
    --   un codice dell'operatore non distingue le maiuscole, e
    --   l'indice UNIQUE della colonna lo rende vero.
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

    IF NEW.codice IS NOT NULL THEN
        NEW.codice := upper(btrim(NEW.codice));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_codice_maiuscolo()
IS 'Trigger function dell''automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04): salva NEW.codice in upper(btrim(NEW.codice)). Un codice dell''operatore e'' un identificativo e non distingue le maiuscole: col valore normalizzato, l''indice UNIQUE della colonna e'' un''unicita'' senza distinzione di maiuscole e nessun lettore ripete un upper() (linee-guida-sql §8.5). BEFORE INSERT OR UPDATE senza OF, perche'' anche i generatori a10_gen_codice scrivono il codice; fase a15, dopo di loro: anche un codice generato si salva normalizzato. Un UPDATE che non cambia il codice non lo tocca: riscrivere la riga non e'' cambiare il codice, e il lucchetto di colonna (script.trgfn_lock_columns) non deve scattare. NULL resta NULL. Non si monta a mano: lo monta dbops.fn_run_automations_codice_maiuscolo su ogni tabella dell''ambito con la colonna codice, tranne le eccezioni di dbops.automazione_codice_eccezioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
