# ⚙️ Funzione `fn_articolo_erogazioni`

```sql
CREATE FUNCTION fn_articolo_erogazioni(p_articolo_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_articolo_erogazioni(p_articolo_id uuid)
 RETURNS TABLE(tipo_erogazione character varying, fonte_quantita_attesa character varying, e_default boolean, generazione_canone character varying, origine text, ordine integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: come si puo' erogare un articolo su una riga di contratto o di
--   offerta — le combinazioni (erogazione, fonte) ammesse, quella di
--   default, e la generazione_canone da proporre sulle CANONE.
-- Regola (decisioni di Tid del 2026-10-07, brief-db-offerta-emissione-ed-
--   erogazione §C.5):
--   · l'articolo con una tipologia di listino: le combinazioni della
--     tipologia (config.listini_tipologie_erogazioni) — B-R1, B-D4;
--   · senza tipologia: quelle della natura di vendita
--     (config.nature_vendita_erogazioni), che e' NOT NULL — B-D1. Vince la
--     tipologia: le due non si sommano;
--   · l'articolo composito ammette in piu' DERIVATA_COMPONENTI, accanto a
--     ogni erogazione ammessa, se il vocabolario la dichiara coerente
--     (config.erogazioni_fonti) — B-D5: e' un fatto della distinta, non della
--     tipologia. Mai di default.
-- Ordine (`ordine`, §D.4 punto 1): il default per primo, poi per
--   erogazione; dentro un'erogazione DERIVATA_COMPONENTI per ultima, poi
--   per fonte. Chi deve scegliere UNA combinazione (l'eredita') prende la
--   prima che gli serve; il form mostra la lista in quest'ordine. Cosi'
--   la prima fonte che il form propone per un'erogazione e' quella che
--   il DB scriverebbe.
-- Zero righe se l'articolo non c'e'.
-- ⭐ Sede UNICA del perimetro e del suo ordine: la leggono il trigger
--   d'eredita', la check del guard e la lettura per il form. Il default e
--   il perimetro non possono dissentire, perche' sono la stessa riga.
DECLARE
    v_tipologia catalogo.articoli.listino_tipologia_id%TYPE;
    v_natura    catalogo.articoli.natura_vendita_id%TYPE;
    v_composito catalogo.articoli.is_composito%TYPE;
BEGIN
    SELECT a.listino_tipologia_id, a.natura_vendita_id, a.is_composito
      INTO v_tipologia, v_natura, v_composito
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH base AS (
        SELECT te.tipo_erogazione, te.fonte_quantita_attesa, te.e_default,
               te.generazione_canone, 'TIPOLOGIA'::text AS origine
          FROM config.listini_tipologie_erogazioni te
         WHERE v_tipologia IS NOT NULL
           AND te.tipologia_id = v_tipologia
        UNION ALL
        SELECT ne.tipo_erogazione, ne.fonte_quantita_attesa, ne.e_default,
               ne.generazione_canone, 'NATURA'::text
          FROM config.nature_vendita_erogazioni ne
         WHERE v_tipologia IS NULL
           AND ne.natura_vendita_id = v_natura
    ), distinta AS (
        -- B-D5: il composito ammette la quantita' derivata dai componenti,
        --   per ogni erogazione che la base ammette, se coerente.
        SELECT DISTINCT ON (b.tipo_erogazione)
               b.tipo_erogazione, ef.fonte_quantita_attesa, false AS e_default,
               b.generazione_canone, 'DISTINTA'::text AS origine
          FROM base b
          JOIN config.erogazioni_fonti ef
            ON ef.tipo_erogazione = b.tipo_erogazione
           AND ef.fonte_quantita_attesa = 'DERIVATA_COMPONENTI'
         WHERE v_composito IS TRUE
           AND NOT EXISTS (SELECT 1 FROM base b2
                            WHERE b2.tipo_erogazione = b.tipo_erogazione
                              AND b2.fonte_quantita_attesa = 'DERIVATA_COMPONENTI')
         ORDER BY b.tipo_erogazione, b.e_default DESC
    ), tutte AS (
        SELECT * FROM base
        UNION ALL
        SELECT * FROM distinta
    )
    SELECT t.tipo_erogazione, t.fonte_quantita_attesa, t.e_default,
           t.generazione_canone, t.origine,
           (row_number() OVER (
               ORDER BY t.e_default DESC,
                        t.tipo_erogazione,
                        (t.fonte_quantita_attesa = 'DERIVATA_COMPONENTI'),
                        t.fonte_quantita_attesa))::integer
      FROM tutte t;
END;
$function$

COMMENT ON FUNCTION vendite.fn_articolo_erogazioni(p_articolo_id uuid)
IS 'Building block: come si può erogare un articolo su una riga di contratto o di offerta. Restituisce le combinazioni (tipo_erogazione, fonte_quantita_attesa) ammesse, e_default su quella che la riga eredita quando non la indica, la generazione_canone da proporre sulle CANONE, l''origine (TIPOLOGIA | NATURA | DISTINTA) e l''ordine (1 = la prima: il default, poi per erogazione; dentro un''erogazione DERIVATA_COMPONENTI per ultima, poi per fonte). Regola (decisioni di Tid del 2026-10-07): con una tipologia di listino, le combinazioni della tipologia (config.listini_tipologie_erogazioni); senza, quelle della natura di vendita (config.nature_vendita_erogazioni) — vince la tipologia, le due non si sommano; un articolo composito ammette in più DERIVATA_COMPONENTI accanto a ogni erogazione ammessa, se il vocabolario config.erogazioni_fonti la dichiara coerente, mai di default. Zero righe se l''articolo non c''è. Sede unica del perimetro e del suo ordine: la leggono script.trgfn_righe_default_erogazione_da_articolo (eredità, prende la prima combinazione che le serve), script.fn_check_riga_erogazione (guard) e vendite.fn_documento_riga_erogazioni (form, ordina su ordine): la prima fonte che il form propone per un''erogazione è quella che il DB scriverebbe. STABLE, SECURITY INVOKER. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.7 (B3); ordine dal 20261007-66 (§D.4 punto 1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
