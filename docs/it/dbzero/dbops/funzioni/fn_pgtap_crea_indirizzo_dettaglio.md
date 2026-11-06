{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_indirizzo_dettaglio.md" %}
# ⚙️ Funzione `fn_pgtap_crea_indirizzo_dettaglio`

```sql
CREATE FUNCTION fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
     WHERE s.obsoleto_dal IS NULL          -- una via viva: sulla soppressa l'indirizzo non nasce
     ORDER BY s.id
     LIMIT 1;
    IF v_stradario_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_indirizzo_dettaglio: config.stradario e'' vuoto — e'' un seed di 80_data, non un dato di macchina';
    END IF;

    -- via_norm, civico_norm e indirizzo_normalizzato li calcola il trigger
    -- BEFORE INSERT (trgfn_indirizzi_dettaglio_normalize). L'arbitro
    -- dell'ON CONFLICT sono le colonne di uq_indirizzi_dettaglio_norm_v2
    -- (NULLS NOT DISTINCT), sui valori normalizzati dal trigger.
    INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, interno, altro)
    VALUES (v_stradario_id, 99999, left(p_etichetta, 10), 'Fixture pgTAP: ' || p_etichetta)
    ON CONFLICT (stradario_id, civico, estensione_civico,
                 palazzina, scala, piano, interno)
    DO UPDATE SET data_update = now()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text)
IS 'Fixture pgTAP: fabbrica un indirizzo (anagrafiche.indirizzi_dettaglio) e ne restituisce l''id: civico 99999 sulla prima via viva di seed, interno uguale all''etichetta. Etichette diverse danno indirizzi diversi, la stessa etichetta lo stesso id (ON CONFLICT sulle colonne della chiave dell''indirizzo). Esiste perche'' gli indirizzi sono dati di macchina: su un database ricostruito da zero non ce n''e'' nessuno, mentre le vie sono seed. ⚠️ Non e'' un indirizzo vero: un test sulla normalizzazione o sulla geolocalizzazione si costruisce il suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
