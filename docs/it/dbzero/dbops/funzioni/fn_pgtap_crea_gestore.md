{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_gestore.md" %}
# ⚙️ Funzione `fn_pgtap_crea_gestore`

```sql
CREATE FUNCTION fn_pgtap_crea_gestore(p_etichetta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_gestore(p_etichetta text DEFAULT 'pgTAP'::text)
 RETURNS TABLE(gestore_id bigint, gestore_soggetto_ruolo_id bigint, gestore_soggetto_id uuid)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP il GESTORE dell'installazione.
--   `anagrafiche.gestori` e' dato di MACCHINA: da zero e' vuota, e
--   «il primo gestore» non esiste.
-- ⚠️ PRENDI-O-COSTRUISCI, e non e' pigrizia: il gestore e' un
--   singleton, e un secondo lo rifiuta un guard. Su dbdev questa
--   funzione risponde quello che c'e' e non scrive niente.
-- Uso:
--   CREATE TEMP TABLE tmp_gestore AS
--   SELECT * FROM dbops.fn_pgtap_crea_gestore('conto gestore');
-- ⛔ I conti bancari del gestore NON li scrive: sono il caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_id  anagrafiche.gestori.id%TYPE;
    v_sr  anagrafiche.gestori.soggetto_ruolo_id%TYPE;
    v_sog anagrafiche.soggetti.id%TYPE;
BEGIN
    SELECT g.id, g.soggetto_ruolo_id, sr.soggetto_id
      INTO v_id, v_sr, v_sog
      FROM anagrafiche.gestori g
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = g.soggetto_ruolo_id
     ORDER BY g.id
     LIMIT 1;

    IF v_id IS NOT NULL THEN
        RETURN QUERY SELECT v_id, v_sr, v_sog;
        RETURN;
    END IF;

    -- ⛔ LA FINESTRA DIFFERITA: il ruolo GE ha i suoi indirizzi
    --   obbligatori e un guard differito, e il preambolo dei pgTAP
    --   mette i vincoli IMMEDIATE.
    SET CONSTRAINTS ALL DEFERRED;

    v_sog := dbops.fn_pgtap_crea_soggetto_pg('Gestore ' || p_etichetta);
    v_sr  := dbops.fn_pgtap_crea_soggetto_ruolo(
                 v_sog, 'GE'::character varying);

    INSERT INTO anagrafiche.gestori
        (soggetto_ruolo_id, descrizione, cd_prod_software, valuta_id)
    VALUES (v_sr, 'Gestore pgTAP ' || p_etichetta, 'ZEROERP',
            dbops.fn_pgtap_valuta())
    RETURNING id INTO v_id;

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY SELECT v_id, v_sr, v_sog;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_gestore(p_etichetta text)
IS 'Fixture pgTAP: il GESTORE dell''installazione — lo PRENDE se c''e'', lo costruisce (soggetto + ruolo GE + riga, dentro la finestra differita) se non c''e'', con la valuta di dbops.fn_pgtap_valuta (il gestore e'' l''ultima radice della catena vendite.fn_get_valuta_id). ⚠️ anagrafiche.gestori e'' dato di MACCHINA: su un database ricostruito e'' vuota, e i quattro file che leggevano «il primo Gestore» non trovavano niente. ⛔ Prendi-o-costruisci e non costruisci-sempre, perche'' il gestore e'' un SINGLETON: un secondo lo rifiuta un guard, quindi un builder che creasse sempre sarebbe rosso proprio su dbdev. ⛔ I conti bancari del gestore NON li scrive: uso, IBAN e predefinito sono il caso del test. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
