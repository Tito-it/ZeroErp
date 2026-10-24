# ⚙️ Funzione `fn_pgtap_crea_indirizzo_dettaglio`

```sql
CREATE FUNCTION fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text DEFAULT 'pgTAP'::text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un indirizzo (anagrafiche.indirizzi_dettaglio)
--   FABBRICANDOLO, non cercandolo: e' dato di macchina, e su un database
--   ricostruito da zero non ce n'e' nessuno; config.stradario invece e' seed.
--   Etichette diverse -> indirizzi diversi; la stessa etichetta -> lo stesso id.
-- Uso:
--   v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('magazzino A');
DECLARE
    v_stradario_id config.stradario.id%TYPE;
    v_id           anagrafiche.indirizzi_dettaglio.id%TYPE;
BEGIN
    -- Il primo stradario di seed: uno vale l'altro, serve solo come ancora.
    SELECT s.id INTO v_stradario_id
      FROM config.stradario s
     ORDER BY s.id
     LIMIT 1;
    IF v_stradario_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_indirizzo_dettaglio: config.stradario e'' vuoto — e'' un seed di 80_data, non un dato di macchina';
    END IF;

    -- via_norm, civico_norm e indirizzo_normalizzato li calcola il trigger
    -- BEFORE INSERT (trgfn_indirizzi_dettaglio_normalize). L'ON CONFLICT e'
    -- sull'espressione esatta di uq_indirizzi_dettaglio_norm.
    INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, interno, altro)
    VALUES (v_stradario_id, 99999, left(p_etichetta, 10), 'Fixture pgTAP: ' || p_etichetta)
    ON CONFLICT (stradario_id, civico,
                 COALESCE(estensione_civico, ''::character varying),
                 COALESCE(palazzina,         ''::character varying),
                 COALESCE(scala,             ''::character varying),
                 COALESCE(piano,             ''::character varying),
                 COALESCE(interno,           ''::character varying))
    DO UPDATE SET data_update = now()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text)
IS 'Helper di fixture pgTAP: fabbrica un anagrafiche.indirizzi_dettaglio (civico 99999 sul primo stradario di seed, interno = etichetta) e ne ritorna l''id; etichette diverse danno indirizzi diversi, la stessa etichetta lo stesso id. Esiste perche'' indirizzi_dettaglio e'' DATO DI MACCHINA: su un database ricostruito da zero non ce n''e'' nessuno, e una fixture che ne cerca uno «attivo» muore in ERRORE_FIXTURE senza eseguire un''asserzione — misurato il 2026-09-15 su quattro pgTAP di magazzino (magazzini.indirizzo_dettaglio_id e'' NOT NULL). ⚠️ Non e'' un indirizzo vero: un test che verifichi la normalizzazione o la geolocalizzazione si costruisce il suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
