# ⚙️ Funzione `trgfn_riga_documento_provenienza_prezzo`

```sql
CREATE FUNCTION trgfn_riga_documento_provenienza_prezzo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_riga_documento_provenienza_prezzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- text nudo: il NOME della colonna dell'articolo, che ha due grafie.
    v_col_articolo text := CASE WHEN TG_TABLE_NAME LIKE '%\_componenti' ESCAPE '\'
                                THEN 'componente_id' ELSE 'articolo_id' END;
BEGIN
    -- =========================================================
    -- Scopo:
    --   BEFORE INSERT OR UPDATE sulle righe e sui componenti dei
    --   documenti di vendita: deriva la provenienza del prezzo
    --   (nessuna senza prezzo, MANUALE di default) e la fa
    --   decadere quando il prezzo cambia senza una provenienza
    --   nuova.
    -- =========================================================

    -- Senza prezzo, nessuna provenienza.
    IF NEW.prezzo_unitario IS NULL THEN
        NEW.origine_prezzo      := NULL;
        NEW.listino_versione_id := NULL;
        NEW.listino_riga_id     := NULL;
        RETURN NEW;
    END IF;

    -- La decadenza: il prezzo (o cio' a cui si riferisce) cambia,
    -- la provenienza da listino resta com'era.
    IF TG_OP = 'UPDATE'
       AND NEW.origine_prezzo IS NOT NULL
       AND NEW.origine_prezzo NOT IN ('MANUALE', 'COMPONENTI')
       AND (   NEW.prezzo_unitario  IS DISTINCT FROM OLD.prezzo_unitario
            OR NEW.uom_operativa_id IS DISTINCT FROM OLD.uom_operativa_id
            OR (to_jsonb(NEW) ->> v_col_articolo)
               IS DISTINCT FROM (to_jsonb(OLD) ->> v_col_articolo))
       AND NEW.origine_prezzo          IS NOT DISTINCT FROM OLD.origine_prezzo
       AND NEW.listino_versione_id     IS NOT DISTINCT FROM OLD.listino_versione_id
       AND NEW.listino_riga_id         IS NOT DISTINCT FROM OLD.listino_riga_id
       AND NEW.prezzo_resolver_context IS NOT DISTINCT FROM OLD.prezzo_resolver_context
    THEN
        NEW.origine_prezzo          := 'MANUALE';
        NEW.listino_versione_id     := NULL;
        NEW.listino_riga_id         := NULL;
        NEW.prezzo_resolver_context := NULL;
    END IF;

    -- Un prezzo senza origine e' MANUALE.
    IF NEW.origine_prezzo IS NULL THEN
        NEW.origine_prezzo := 'MANUALE';
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_riga_documento_provenienza_prezzo()
IS 'Trigger BEFORE INSERT OR UPDATE (fase a20) sulle righe principali e sui componenti di preventivi, ordini, contratti, DDT e offerte: la provenienza del prezzo segue il prezzo. Senza prezzo, origine, versione e riga di listino vanno a NULL. Un prezzo senza origine e'' MANUALE. In un UPDATE che cambia prezzo, articolo (articolo_id, o componente_id sui componenti) o unita'' di misura operativa lasciando la provenienza com''era (origine, versione, riga, contesto), un''origine da listino torna MANUALE e versione, riga e contesto vanno a NULL; chi riprende il prezzo dal listino scrive la provenienza nuova nella stessa istruzione. MANUALE e COMPONENTI non decadono. Confronta valori, non colonne nominate. Non solleva: la coerenza la giudicano i CHECK chk_<tabella>_provenienza_prezzo e il guard vendite.trgfn_riga_documento_guard_listino_provenienza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
