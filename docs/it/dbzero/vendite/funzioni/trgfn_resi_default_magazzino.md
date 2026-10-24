# ⚙️ Funzione `trgfn_resi_default_magazzino`

```sql
CREATE FUNCTION trgfn_resi_default_magazzino()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_default_magazzino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: un reso nato senza magazzino prende quello da cui era partita la
--   bolla d'origine (D-3b-a). Solo se manca: chi lo sceglie vince.
-- ⚠️ Non il predefinito dell'emittente (D-L3-h): la domanda del reso e'
--   «da dove era partita?», e la risposta sta sulla bolla.
DECLARE
    v_magazzino_id vendite.ddt.magazzino_id%TYPE;
BEGIN
    IF NEW.magazzino_id IS NULL AND NEW.sorgente_uid IS NOT NULL THEN
        SELECT d.magazzino_id INTO v_magazzino_id
          FROM vendite.ddt d
          JOIN config.sorgenti s ON s.id = NEW.sorgente_tipo_id
                                AND s.codice_interno = 'DDT_VENDITA'
         WHERE d.uid = NEW.sorgente_uid;
        NEW.magazzino_id := v_magazzino_id;   -- NULL se la bolla non ne ha uno
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_default_magazzino()
IS 'BEFORE INSERT su vendite.resi: se magazzino_id manca, prende il magazzino della bolla d''origine (sorgente DDT_VENDITA, per uid) — D-3b-a: la merce rientra, di norma, da dove era partita. Non il predefinito dell''emittente. Bolla senza magazzino: resta NULL, e se il reso muove merce lo chiede la check della conferma. Gira dopo trgfn_resi_normalize e prima del guard (ordine alfabetico dei trigger, fascia z10). Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
