{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_normalize.md" %}
# ⚙️ Funzione `trgfn_soggetti_normalize`

```sql
CREATE FUNCTION trgfn_soggetti_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- 1) L'identificativo fiscale nella forma che l'indice d'unicita'
    --    e i guard confrontano (D-T5-2 a): maiuscole, nessuno spazio,
    --    vuoto -> NULL. Una regola sola per ogni strada di scrittura.
    NEW.codice_fiscale       := NULLIF(upper(regexp_replace(NEW.codice_fiscale, '\s', '', 'g')), '');
    NEW.partita_iva          := NULLIF(upper(regexp_replace(NEW.partita_iva, '\s', '', 'g')), '');
    NEW.piva_gruppo_acquisto := NULLIF(upper(regexp_replace(NEW.piva_gruppo_acquisto, '\s', '', 'g')), '');

    -- 2) Lo stato proposto, solo alla nascita (S43-1). In modifica uno
    --    stato NULL e' mezza chiave tolta: lo rifiuta il guard
    --    dell'identificativo, non lo sostituisce questo trigger.
    IF TG_OP = 'INSERT' AND NEW.stato_id IS NULL THEN
        NEW.stato_id := script.fn_stato_proposto_id(TG_NAME);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_normalize()
IS 'Normalize di anagrafiche.soggetti, fase a01: gira prima di tutti i guard, perche'' e'' la normalizzazione che i guard leggono. (1) codice_fiscale, partita_iva e piva_gruppo_acquisto in maiuscolo, senza spazi, vuoto -> NULL: e'' la forma che confrontano l''indice uq_soggetto_idstato_id_fiscale_univoco, il guard dell''identificativo e il validatore del formato, per ogni strada di scrittura. (2) stato_id NULL all''INSERT: lo stato proposto (script.fn_stato_proposto_id). In modifica non si propone niente: uno stato NULL lo rifiuta il guard dell''identificativo. La generazione del codice e'' del sistema codici.';
```

</div>

---
{% include-markdown "signature-core.md" %}
