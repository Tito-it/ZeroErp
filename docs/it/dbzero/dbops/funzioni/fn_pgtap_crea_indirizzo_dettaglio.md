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
--   L'indirizzo lo trova o lo crea il building block del dominio, con le
--   sue regole: la via risolta, la chiave normalizzata, la riga spenta
--   che torna in uso.
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

    -- Trova o crea dal building block del dominio: la stessa strada di
    -- chi scrive un indirizzo vero.
    v_id := anagrafiche.fn_get_or_create_indirizzo_dettaglio(
                p_stradario_id => v_stradario_id,
                p_civico       => 99999,
                p_interno      => left(p_etichetta, 10)::varchar);

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_indirizzo_dettaglio(p_etichetta text)
IS 'Fixture pgTAP: fabbrica un indirizzo (anagrafiche.indirizzi_dettaglio) e ne restituisce l''id: civico 99999 sulla prima via viva di seed, interno uguale all''etichetta (i primi dieci caratteri). L''indirizzo lo trova o lo crea anagrafiche.fn_get_or_create_indirizzo_dettaglio, con le sue regole: via risolta, chiave normalizzata, riga disattivata che torna attiva. Etichette diverse danno indirizzi diversi, la stessa etichetta lo stesso id. Esiste perche'' gli indirizzi sono dati di macchina: su un database ricostruito da zero non ce n''e'' nessuno, mentre le vie sono seed. ⚠️ Non e'' un indirizzo vero: un test sulla normalizzazione o sulla geolocalizzazione si costruisce il suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
