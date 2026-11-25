{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_iu_sync_catasto_unita_indirizzo.md" %}
# ⚙️ Funzione `trgfn_iu_sync_catasto_unita_indirizzo`

```sql
CREATE FUNCTION trgfn_iu_sync_catasto_unita_indirizzo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   La tabella ponte catasto_unita_immobiliari_indirizzi e
    --   l'unita' catastale seguono l'istanza.
    --
    -- Regole (AFTER: la tabella mostra gia' la riga nuova):
    --   1. UPDATE: la coppia (unita', civico) di prima esce dalla
    --      ponte se nessun'altra istanza ha la stessa coppia;
    --   2. UPDATE che cambia unita': l'unita' di prima che
    --      nessuna istanza nomina piu' si cancella (lo storico
    --      tiene la versione, la ponte la segue in cascata);
    --   3. la coppia nuova entra, idempotente.
    -- =========================================================
    IF TG_OP = 'UPDATE' THEN
        -- 1) La coppia di prima.
        IF OLD.catasto_unita_immobiliare_id IS NOT NULL
           AND OLD.indirizzo_dettaglio_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
                 FROM anagrafiche.istanze_utilities iu
                WHERE iu.catasto_unita_immobiliare_id = OLD.catasto_unita_immobiliare_id
                  AND iu.indirizzo_dettaglio_id       = OLD.indirizzo_dettaglio_id)
        THEN
            DELETE FROM anagrafiche.catasto_unita_immobiliari_indirizzi x
             WHERE x.catasto_unita_id       = OLD.catasto_unita_immobiliare_id
               AND x.indirizzo_dettaglio_id = OLD.indirizzo_dettaglio_id;
        END IF;

        -- 2) L'unita' di prima, se nessuno la nomina piu'.
        IF OLD.catasto_unita_immobiliare_id IS NOT NULL
           AND OLD.catasto_unita_immobiliare_id IS DISTINCT FROM NEW.catasto_unita_immobiliare_id
           AND NOT EXISTS (
               SELECT 1
                 FROM anagrafiche.istanze_utilities iu
                WHERE iu.catasto_unita_immobiliare_id = OLD.catasto_unita_immobiliare_id)
        THEN
            DELETE FROM anagrafiche.catasto_unita_immobiliari u
             WHERE u.id = OLD.catasto_unita_immobiliare_id;
        END IF;
    END IF;

    -- 3) La coppia nuova.
    IF NEW.catasto_unita_immobiliare_id IS NOT NULL AND NEW.indirizzo_dettaglio_id IS NOT NULL THEN
        INSERT INTO anagrafiche.catasto_unita_immobiliari_indirizzi (
            catasto_unita_id,
            indirizzo_dettaglio_id)
        VALUES (
            NEW.catasto_unita_immobiliare_id,
            NEW.indirizzo_dettaglio_id)
        ON CONFLICT ON CONSTRAINT uq_catunitaindir
        DO NOTHING;
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()
IS 'Trigger AFTER su anagrafiche.istanze_utilities, all''INSERT con unita'' e civico e all''UPDATE che cambia l''uno o l''altro: la tabella ponte catasto_unita_immobiliari_indirizzi e l''unita'' catastale seguono l''istanza. Al cambio la coppia (unita'', civico) di prima esce dalla ponte se nessun''altra istanza ha la stessa coppia (le coppie scritte a mano con altri civici restano), e l''unita'' di prima che nessuna istanza nomina piu'' si cancella (lo storico continuo tiene la versione, la ponte la segue in cascata). Poi la coppia nuova entra, idempotente. La regola sta nella guida catasto-delle-istanze.';
```

</div>

---
{% include-markdown "signature-core.md" %}
