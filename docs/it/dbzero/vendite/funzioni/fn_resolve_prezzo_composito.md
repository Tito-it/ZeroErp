{% include-markdown "it/dbzero/vendite/manual/fn_resolve_prezzo_composito.md" %}
# ⚙️ Funzione `fn_resolve_prezzo_composito`

```sql
CREATE FUNCTION fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer)
 RETURNS TABLE(componente_id uuid, uom_id bigint, prezzo_unitario numeric, iva_id bigint, descrizione_fattura character varying, esposto_in_fattura boolean, coeff_qta numeric, origine_prezzo character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_has_esposti     boolean;
    v_prezzo_padre    vendite.listini_righe.prezzo%TYPE;
    v_origine_b1      vendite.commesse_attivita.origine_prezzo%TYPE;
    v_prezzo_totale   vendite.listini_righe.prezzo%TYPE := 0;
    v_articolo_iva_id catalogo.articoli.iva_id%TYPE;
    v_articolo_desc   catalogo.articoli.descrizione%TYPE;
    v_rec             record;
    v_resolve         record;
BEGIN
    -- =========================================================
    -- Scopo (post 22-04-2026, DB-3 Sprint C):
    --   Resolver BoM ibrido pricing v5. N righe se composito
    --   ha componenti esposti (CASO A), 1 riga altrimenti
    --   (CASO B1 prezzo diretto, CASO B2 Sigma pesata).
    --   Espone coeff_qta per BoMComponentExpander (DEC-3 §14.4.1).
    --
    -- Estensione 2026-05-11:
    --   Aggiunto origine_prezzo (ultima colonna, backward-compat).
    --   CASO A: origine per componente da fn_resolve_prezzo_listino_v2.
    --   CASO B1: origine dal resolver padre.
    --   CASO B2: NULL (Sigma aggregata).
    -- =========================================================

    IF p_prodotto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_composito',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_prodotto_id'),
            NULL::uuid,
            'p_prodotto_id obbligatorio'
        );
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM catalogo.articoli_componenti ac
         WHERE ac.prodotto_id            = p_prodotto_id
           AND ac.esposto_in_fattura     = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.validita              @> p_data_riferimento
    )
    INTO v_has_esposti;

    -- CASO A: almeno un componente esposto -> N righe
    IF v_has_esposti THEN
        FOR v_rec IN
            SELECT ac.componente_id,
                   ac.esposto_in_fattura,
                   ac.coeff_qta,
                   a.uom_id      AS componente_uom_id,
                   a.iva_id      AS componente_iva_id,
                   a.descrizione AS componente_descrizione
              FROM catalogo.articoli_componenti ac
              JOIN catalogo.articoli a ON a.id = ac.componente_id
             WHERE ac.prodotto_id            = p_prodotto_id
               AND ac.obbligatorio           = TRUE
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND ac.validita              @> p_data_riferimento
        LOOP
            SELECT *
              INTO v_resolve
              FROM vendite.fn_resolve_prezzo_listino_v2(
                  v_rec.componente_id,
                  v_rec.componente_uom_id,
                  p_data_riferimento,
                  p_ba_id,
                  p_utility_id,
                  p_emittente_soggetto_ruolo_id,
                  p_classe_utenza_id
              );

            componente_id       := v_rec.componente_id;
            uom_id              := v_rec.componente_uom_id;
            prezzo_unitario     := v_resolve.prezzo_finale;
            iva_id              := v_rec.componente_iva_id;
            descrizione_fattura := v_rec.componente_descrizione;
            esposto_in_fattura  := v_rec.esposto_in_fattura;
            coeff_qta           := v_rec.coeff_qta;
            origine_prezzo      := v_resolve.origine;
            RETURN NEXT;
        END LOOP;

        RETURN;
    END IF;

    -- CASO B: metadati padre
    SELECT a.iva_id, a.descrizione
      INTO v_articolo_iva_id, v_articolo_desc
      FROM catalogo.articoli a
     WHERE a.id = p_prodotto_id;

    -- CASO B1: prezzo diretto sul padre
    BEGIN
        SELECT *
          INTO v_resolve
          FROM vendite.fn_resolve_prezzo_listino_v2(
              p_prodotto_id,
              p_uom_id,
              p_data_riferimento,
              p_ba_id,
              p_utility_id,
              p_emittente_soggetto_ruolo_id,
              p_classe_utenza_id
          );
        v_prezzo_padre := v_resolve.prezzo_finale;
        v_origine_b1   := v_resolve.origine;
    EXCEPTION
        WHEN SQLSTATE 'P0001' THEN
            v_prezzo_padre := NULL;
            v_origine_b1   := NULL;
    END;

    IF v_prezzo_padre IS NOT NULL THEN
        componente_id       := p_prodotto_id;
        uom_id              := p_uom_id;
        prezzo_unitario     := v_prezzo_padre;
        iva_id              := v_articolo_iva_id;
        descrizione_fattura := v_articolo_desc;
        esposto_in_fattura  := FALSE;
        coeff_qta           := 1::numeric;
        origine_prezzo      := v_origine_b1;
        RETURN NEXT;
        RETURN;
    END IF;

    -- CASO B2: Sigma pesata, origine_prezzo = NULL
    FOR v_rec IN
        SELECT ac.componente_id,
               ac.coeff_qta,
               a.uom_id AS componente_uom_id
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
         WHERE ac.prodotto_id            = p_prodotto_id
           AND ac.obbligatorio           = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.validita              @> p_data_riferimento
    LOOP
        SELECT *
          INTO v_resolve
          FROM vendite.fn_resolve_prezzo_listino_v2(
              v_rec.componente_id,
              v_rec.componente_uom_id,
              p_data_riferimento,
              p_ba_id,
              p_utility_id,
              p_emittente_soggetto_ruolo_id,
              p_classe_utenza_id
          );
        v_prezzo_totale := v_prezzo_totale + v_resolve.prezzo_finale * v_rec.coeff_qta;
    END LOOP;

    componente_id       := p_prodotto_id;
    uom_id              := p_uom_id;
    prezzo_unitario     := v_prezzo_totale;
    iva_id              := v_articolo_iva_id;
    descrizione_fattura := v_articolo_desc;
    esposto_in_fattura  := FALSE;
    coeff_qta           := 1::numeric;
    origine_prezzo      := NULL;
    RETURN NEXT;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
IS '[DEPRECATED 2026-05-13 — modello unificato BoM] Resolver BoM ibrido pricing v5 CASO A/B. Con il modello unificato padre=sempre SUM(figli), il branching CASO A/B non ha piu'' significato. Le fn_*_riga_componenti_init usano direttamente fn_resolve_prezzo_listino_v2 per-componente. Da rimuovere dopo aggiornamento backend pricing_repository.py.';
```

---
{% include-markdown "signature-core.md" %}
