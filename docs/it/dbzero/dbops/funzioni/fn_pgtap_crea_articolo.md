{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_articolo.md" %}
# ⚙️ Funzione `fn_pgtap_crea_articolo`

```sql
CREATE FUNCTION fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean, p_uom_id bigint, p_listino_tipologia_id smallint, p_is_composito boolean, p_is_solo_componente boolean, p_natura_vendita_id bigint, p_causale_onere_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean DEFAULT true, p_requires_lotto boolean DEFAULT false, p_requires_serial boolean DEFAULT false, p_uom_id bigint DEFAULT NULL::bigint, p_listino_tipologia_id smallint DEFAULT NULL::smallint, p_is_composito boolean DEFAULT false, p_is_solo_componente boolean DEFAULT false, p_natura_vendita_id bigint DEFAULT NULL::bigint, p_causale_onere_id bigint DEFAULT NULL::bigint)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un articolo COSTRUITO INTERO, con la
--   struttura che il test sceglie: pescarne uno dal catalogo darebbe un
--   articolo qualunque, cioe' un rifiuto che sembra un test rosso.
--   UoM: la prima attiva del seed, se il test non la sceglie.
-- Uso: v_art := dbops.fn_pgtap_crea_articolo('PGT-A', true, true, false);
--      v_kit := dbops.fn_pgtap_crea_articolo('PGT-K', false,
--                   p_listino_tipologia_id => v_tip, p_is_composito => true);
-- ⭐ Rev 20260923-01: `p_uom_id` per chi la UoM base la deve SCEGLIERE —
--   chi misura le conversioni, che il guard ammette solo fra unita' della
--   stessa tipologia. La colonna e' loccata: o si sceglie qui, o mai piu'.
-- ⭐ Rev 20261017-01: le otto colonne che il guard A-10 congela su un
--   articolo usato si scelgono TUTTE qui, nell'INSERT. Un UPDATE dopo il
--   builder dipende dall'ordine della fixture; dentro il builder sarebbe
--   lo stesso difetto spostato.
DECLARE
    v_uom catalogo.unita_misura.id%TYPE;
    v_id  catalogo.articoli.id%TYPE;
BEGIN
    IF p_uom_id IS NULL THEN
        SELECT u.id INTO v_uom FROM catalogo.unita_misura u WHERE u.attivo ORDER BY u.id LIMIT 1;
        IF v_uom IS NULL THEN
            RAISE EXCEPTION 'fn_pgtap_crea_articolo: catalogo.unita_misura e'' vuoto — e'' un seed di 80_data';
        END IF;
    ELSE
        -- ⚠️ Guard sul RISULTATO: una UoM inesistente o spenta qui parla,
        --   invece di arrivare alla FK con un messaggio che non nomina
        --   ne' la fixture ne' il parametro.
        SELECT u.id INTO v_uom
          FROM catalogo.unita_misura u
         WHERE u.id = p_uom_id AND u.attivo;
        IF v_uom IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_articolo: p_uom_id = % non e'' una unita'' di misura attiva a catalogo',
                p_uom_id;
        END IF;
    END IF;

    -- ⚠️ natura_vendita_id e' NOT NULL con un DEFAULT di tabella: NULL vuol
    --   dire «quello della tabella». Due rami invece di ricopiare qui il
    --   default: la sede del default resta il DDL.
    IF p_natura_vendita_id IS NULL THEN
        INSERT INTO catalogo.articoli (codice, descrizione, uom_id,
                                       gestito_a_magazzino, requires_lotto, requires_serial,
                                       listino_tipologia_id, is_composito, is_solo_componente,
                                       causale_onere_id)
        VALUES (p_codice, 'Fixture pgTAP: ' || p_codice, v_uom,
                COALESCE(p_gestito, true), COALESCE(p_requires_lotto, false), COALESCE(p_requires_serial, false),
                p_listino_tipologia_id, COALESCE(p_is_composito, false), COALESCE(p_is_solo_componente, false),
                p_causale_onere_id)
        RETURNING id INTO v_id;
    ELSE
        INSERT INTO catalogo.articoli (codice, descrizione, uom_id,
                                       gestito_a_magazzino, requires_lotto, requires_serial,
                                       listino_tipologia_id, is_composito, is_solo_componente,
                                       causale_onere_id, natura_vendita_id)
        VALUES (p_codice, 'Fixture pgTAP: ' || p_codice, v_uom,
                COALESCE(p_gestito, true), COALESCE(p_requires_lotto, false), COALESCE(p_requires_serial, false),
                p_listino_tipologia_id, COALESCE(p_is_composito, false), COALESCE(p_is_solo_componente, false),
                p_causale_onere_id, p_natura_vendita_id)
        RETURNING id INTO v_id;
    END IF;
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean, p_uom_id bigint, p_listino_tipologia_id smallint, p_is_composito boolean, p_is_solo_componente boolean, p_natura_vendita_id bigint, p_causale_onere_id bigint)
IS 'Fixture pgTAP: un articolo COSTRUITO INTERO, con la struttura scelta dal test; pescarne uno dal catalogo darebbe un articolo qualunque, e un rifiuto che sembra un test rosso. p_uom_id: l''unita'' BASE, colonna bloccata; senza, la prima attiva del seed. Gli altri parametri: gestito_a_magazzino, requires_lotto, requires_serial, listino_tipologia_id, is_composito, is_solo_componente, natura_vendita_id (NULL = il default di tabella) e causale_onere_id: sono le colonne che catalogo.trgfn_articoli_guard_struttura_se_usato congela su un articolo usato, e il builder le valorizza tutte nell''INSERT, perche'' un UPDATE di correzione dopo il builder dipenderebbe dall''ordine della fixture. Le combinazioni le giudicano i guard della tabella. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
