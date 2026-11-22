{% include-markdown "it/dbzero/vendite/manual/fn_offerta_righe_espanse.md" %}
# ⚙️ Funzione `fn_offerta_righe_espanse`

```sql
CREATE FUNCTION fn_offerta_righe_espanse(p_offerta_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_righe_espanse(p_offerta_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, descrizione character varying, is_composito boolean, quantita numeric, uom_operativa_id bigint, qta_operativa numeric, factor_to_base numeric, prezzo_unitario numeric, sconto_percentuale numeric, iva_id integer, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, componenti jsonb, eccezione_id bigint, origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_resolver_context jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$


-- Scopo: righe effettive ordine-ready di un'offerta (listino + variazione
--   globale + eccezioni). Parte 1 dal core fn_espandi_listino_versione +
--   overlay OVERRIDE (ESCLUSIONE rimossa); Parte 2 AGGIUNTA standalone+bundle.
--   iva_id risolta dall'articolo (listino non porta iva; iva_perc non esiste
--   su ordini_righe: la percentuale si deriva da iva_id). sconto NULL: lo
--   sconto e' espresso come prezzo override (prezzo_unitario = prezzo netto).
--   quantita default 1 per righe da-listino senza eccezione.
-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): la versione
--   operativa e la variazione dalla sede unica vendite.fn_documento_listino_
--   operativo('OFFERTA_COMMERCIALE', id), comune con la lista delle righe e coi guard di
--   contratto e offerta. Stessa regola di prima (versione fissata, o in
--   vigore oggi). Firma e colonne invariate, ora ancorate con %TYPE (iva_id e
--   sconto_percentuale alla riga d'ordine, che e' la loro destinazione).
-- La provenienza del prezzo (origine_prezzo, versione, riga di listino, contesto)
--   e' quella che la riga d'ordine copia:
--   · dal listino dell'offerta (anche con l'ADESIONE): CONTRATTO_LISTINO, l'origine
--     del listino fissato dal documento (la stessa che il resolver da' alle righe
--     dell'offerta), con la versione, la riga di listino se l'unita' della riga e'
--     la sua, e nel contesto il prezzo base e la variazione globale;
--   · OVERRIDE e AGGIUNTA semplice: quella dell'eccezione;
--   · il kit: nessuna, perche' la riga la scrive COMPONENTI la somma. I suoi
--     componenti portano ciascuno la sua: quelli dell'eccezione (AGGIUNTA, e OVERRIDE
--     quando l'eccezione ha componenti suoi: il prezzo forzato e' la loro somma) da
--     vendite.fn_offerta_eccezione_componenti_espansi; quelli del listino
--     LISTINO_BUNDLE con la versione, senza riga e senza variazione.
DECLARE
    v_trovato             boolean := false;
    v_listino_versione_id vendite.listini_versioni.id%TYPE;
    v_tipo_var            vendite.offerte_commerciali.tipo_variazione_globale%TYPE;
    v_valore_var          vendite.offerte_commerciali.valore_variazione_globale%TYPE;
BEGIN
    SELECT true, lo.listino_versione_id,
           lo.tipo_variazione_globale, lo.valore_variazione_globale
      INTO v_trovato, v_listino_versione_id, v_tipo_var, v_valore_var
      FROM vendite.fn_documento_listino_operativo('OFFERTA_COMMERCIALE', p_offerta_id) lo;

    -- Offerta assente (o fuori perimetro): nessuna riga.
    IF NOT COALESCE(v_trovato, false) THEN
        RETURN;
    END IF;

    -- PARTE 1: righe dal listino (core) + overlay OVERRIDE; ESCLUSIONE rimossa.
    RETURN QUERY
    SELECT
        base.articolo_id,
        base.articolo_codice,
        base.articolo_descrizione,
        base.is_composito,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, base.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        CASE
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.prezzo_unitario
            ELSE                                      base.prezzo_da_listino
        END,
        NULL::numeric,
        a.iva_id::integer,
        ecc.tipo_eccezione,
        CASE
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN 'OVERRIDE'
            ELSE                                      'DA_LISTINO'
        END::varchar,
        CASE
            WHEN NOT base.is_composito THEN base.componenti
            ELSE COALESCE(
                     CASE WHEN ecc.tipo_eccezione = 'OVERRIDE'
                          THEN vendite.fn_offerta_eccezione_componenti_espansi(ecc.id) END,
                     (SELECT jsonb_agg(c.e || jsonb_build_object(
                                 'origine_prezzo',          'LISTINO_BUNDLE',
                                 'listino_versione_id',     v_listino_versione_id,
                                 'prezzo_resolver_context', jsonb_build_object(
                                     'prezzo_base_snapshot',        c.e -> 'prezzo',
                                     'tipo_variazione_applicata',   'NESSUNA',
                                     'valore_variazione_applicata', 0))
                                 ORDER BY c.n)
                        FROM jsonb_array_elements(base.componenti) WITH ORDINALITY AS c(e, n)))
        END,
        ecc.id,
        CASE
            WHEN base.is_composito                THEN NULL
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.origine_prezzo
            ELSE                                      'CONTRATTO_LISTINO'
        END::varchar,
        CASE
            WHEN base.is_composito                THEN NULL
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.listino_versione_id
            ELSE                                      v_listino_versione_id
        END,
        CASE
            WHEN base.is_composito                THEN NULL
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.listino_riga_id
            WHEN COALESCE(ecc.uom_operativa_id, base.uom_id) = base.uom_id
                                                  THEN base.listino_riga_id
        END,
        CASE
            WHEN base.is_composito                THEN NULL
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.prezzo_resolver_context
            ELSE jsonb_build_object(
                     'prezzo_base_snapshot',        base.prezzo_listino,
                     'tipo_variazione_applicata',   COALESCE(v_tipo_var, 'NESSUNA'),
                     'valore_variazione_applicata', COALESCE(v_valore_var, 0))
        END
      FROM vendite.fn_espandi_listino_versione(
               v_listino_versione_id, v_tipo_var, v_valore_var
           ) base
      JOIN catalogo.articoli a ON a.id = base.articolo_id
      LEFT JOIN vendite.offerte_commerciali_eccezioni ecc
             ON ecc.offerta_id            = p_offerta_id
            AND ecc.articolo_id           = base.articolo_id
            AND ecc.tipo_eccezione        IN (
                    'OVERRIDE'::vendite.tipo_eccezione_contratto,
                    'ESCLUSIONE'::vendite.tipo_eccezione_contratto,
                    -- rev 2026-10-29 (G-0-ter): l'ADESIONE porta la sua quantita'.
                    'ADESIONE'::vendite.tipo_eccezione_contratto
                )
            AND ecc.attivo
     WHERE ecc.tipo_eccezione IS DISTINCT FROM 'ESCLUSIONE'::vendite.tipo_eccezione_contratto;

    -- PARTE 2a: AGGIUNTA standalone (articolo non a listino).
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, FALSE,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, a.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        ecc.prezzo_unitario,
        NULL::numeric,
        a.iva_id::integer,
        ecc.tipo_eccezione,
        'AGGIUNTA'::varchar,
        NULL::jsonb,
        ecc.id,
        ecc.origine_prezzo, ecc.listino_versione_id, ecc.listino_riga_id,
        ecc.prezzo_resolver_context
      FROM vendite.offerte_commerciali_eccezioni ecc
      JOIN catalogo.articoli a
        ON a.id = ecc.articolo_id AND a.is_composito = FALSE AND a.attivo = TRUE
     WHERE ecc.offerta_id           = p_offerta_id
       AND ecc.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND ecc.attivo;

    -- PARTE 2b: AGGIUNTA bundle. Componenti da offerte_commerciali_eccezioni_componenti
--   (vendite.fn_offerta_eccezione_componenti_espansi).
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, TRUE,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, a.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        ecc.prezzo_unitario,
        NULL::numeric,
        a.iva_id::integer,
        ecc.tipo_eccezione,
        'AGGIUNTA'::varchar,
        vendite.fn_offerta_eccezione_componenti_espansi(ecc.id),
        ecc.id,
        NULL::varchar, NULL::bigint, NULL::bigint, NULL::jsonb
      FROM vendite.offerte_commerciali_eccezioni ecc
      JOIN catalogo.articoli a
        ON a.id = ecc.articolo_id AND a.is_composito = TRUE AND a.attivo = TRUE
     WHERE ecc.offerta_id           = p_offerta_id
       AND ecc.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND ecc.attivo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_righe_espanse(p_offerta_id bigint)
IS 'Le righe che riceve un ordine generato dall''offerta, nell''ordine in cui le copia vendite.fn_genera_ordine_da_offerta. Prima le righe del listino operativo dell''offerta (versione e variazione globale da vendite.fn_documento_listino_operativo, espanse da vendite.fn_espandi_listino_versione), con sopra le eccezioni OVERRIDE (il prezzo) e ADESIONE (la quantita''), senza le ESCLUSE; poi le AGGIUNTE, semplici e composte. iva_id e'' quella dell''articolo; sconto_percentuale e'' NULL, perche'' il prezzo e'' gia'' netto; senza eccezione la quantita'' e'' 1. origine dice da dove viene il prezzo (DA_LISTINO, OVERRIDE, AGGIUNTA). eccezione_id e'' la riga di offerte_commerciali_eccezioni da cui la riga viene, NULL per la riga del solo listino: e'' la sorgente_riga della riga d''ordine. origine_prezzo, listino_versione_id, listino_riga_id e prezzo_resolver_context sono la provenienza del prezzo che la riga d''ordine copia: per la riga dal listino CONTRATTO_LISTINO (il listino fissato dal documento) con la versione, la riga di listino quando l''unita'' della riga e'' la sua, e nel contesto prezzo base e variazione globale; per OVERRIDE e AGGIUNTA semplice quella dell''eccezione; per il kit nessuna, perche'' il suo prezzo e'' la somma dei componenti. componenti (solo sul kit) porta per ogni componente prezzo e provenienza, nella forma di un override di vendite.fn_componente_override: quelli dell''eccezione per l''AGGIUNTA e per l''OVERRIDE che ne ha (vendite.fn_offerta_eccezione_componenti_espansi), altrimenti quelli del listino, LISTINO_BUNDLE con la versione. Offerta assente o fuori perimetro: nessuna riga. Non e'' la lista del drawer, che e'' vendite.fn_offerta_righe_preview. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
