{% include-markdown "it/dbzero/vendite/manual/fn_offerta_eccezione_componenti_init.md" %}
# ⚙️ Funzione `fn_offerta_eccezione_componenti_init`

```sql
CREATE FUNCTION fn_offerta_eccezione_componenti_init(p_eccezione_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_eccezione_componenti_init(p_eccezione_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb DEFAULT NULL::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_articolo_id  catalogo.articoli.id%TYPE;
    v_uom_id       catalogo.unita_misura.id%TYPE;
    v_qta_padre    vendite.offerte_commerciali_eccezioni.quantita%TYPE;
    v_offerta_id   vendite.offerte_commerciali.id%TYPE;
    v_is_composito catalogo.articoli.is_composito%TYPE;
    v_ba_id        anagrafiche.billing_account.id%TYPE;
    v_utility_id   vendite.offerte_commerciali.utility_id%TYPE;
    v_istanza_id   vendite.offerte_commerciali.istanza_utility_id%TYPE;
    v_comp         record;
    v_resolve      record;
    v_prezzo       numeric;
    v_origine      text;
    v_inserted     integer := 0;
BEGIN
    -- Guard input
    IF p_eccezione_id IS NULL OR p_eccezione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_offerta_eccezione_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_eccezione_id'),
            NULL::uuid,
            'p_eccezione_id obbligatorio e > 0'
        );
    END IF;

    IF p_emittente_sr_id IS NULL OR p_emittente_sr_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_offerta_eccezione_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_sr_id'),
            NULL::uuid,
            'p_emittente_sr_id obbligatorio e > 0'
        );
    END IF;

    -- Legge dati eccezione padre
    SELECT oce.articolo_id,
           oce.uom_operativa_id,
           oce.quantita,
           oce.offerta_id
      INTO v_articolo_id, v_uom_id, v_qta_padre, v_offerta_id
      FROM vendite.offerte_commerciali_eccezioni oce
     WHERE oce.id = p_eccezione_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_offerta_eccezione_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('p_eccezione_id', p_eccezione_id),
            NULL::uuid,
            'eccezione offerta non trovata'
        );
    END IF;

    -- No-op silenzioso su articolo non composito (CASO B)
    SELECT a.is_composito INTO v_is_composito
      FROM catalogo.articoli a WHERE a.id = v_articolo_id;

    IF NOT COALESCE(v_is_composito, FALSE) THEN
        RETURN 0;
    END IF;

    -- No-op su eccezione a consumo: quantita NULL non permette
    -- il calcolo delle quantita dei componenti.
    IF v_qta_padre IS NULL THEN
        RETURN 0;
    END IF;

    -- Idempotenza: se gia' presenti componenti, no-op
    IF EXISTS (
        SELECT 1 FROM vendite.offerte_commerciali_eccezioni_componenti
         WHERE eccezione_offerta_id = p_eccezione_id
    ) THEN
        RETURN 0;
    END IF;

    -- Legge billing_account_id, utility_id, istanza_utility_id dall'offerta
    SELECT o.billing_account_id, o.utility_id, o.istanza_utility_id
      INTO v_ba_id, v_utility_id, v_istanza_id
      FROM vendite.offerte_commerciali o WHERE o.id = v_offerta_id;

    -- Itera sui componenti BoM esposti (CASO A: esposto_in_fattura = TRUE).
    -- Per ogni componente: override oppure fn_resolve_prezzo_listino_v2.
    -- Fallback individuale su P0001: prezzo=0, MANUALE.
    FOR v_comp IN
        SELECT ac.id          AS bom_entry_id,
               ac.componente_id,
               ac.coeff_qta,
               a.uom_id       AS componente_uom_id,
               a.iva_id       AS componente_iva_id
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
         WHERE ac.prodotto_id        = v_articolo_id
           AND ac.esposto_in_fattura = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.validita           @> p_data_riferimento
    LOOP
        IF p_componenti_overrides IS NOT NULL
           AND p_componenti_overrides ? v_comp.bom_entry_id::text
        THEN
            v_prezzo  := (p_componenti_overrides ->> v_comp.bom_entry_id::text)::numeric;
            v_origine := 'MANUALE';
            INSERT INTO vendite.offerte_commerciali_eccezioni_componenti (
                eccezione_offerta_id,
                articolo_componente_id,
                componente_id,
                coeff_qta_snapshot,
                quantita,
                uom_operativa_id,
                factor_to_base,
                prezzo_unitario,
                iva_id,
                origine_prezzo,
                prezzo_resolver_context
            ) VALUES (
                p_eccezione_id,
                v_comp.bom_entry_id,
                v_comp.componente_id,
                v_comp.coeff_qta,
                v_comp.coeff_qta * v_qta_padre,
                v_comp.componente_uom_id,
                1,
                v_prezzo,
                v_comp.componente_iva_id,
                v_origine,
                jsonb_build_object(
                    'override',           true,
                    'emittente_sr_id',    p_emittente_sr_id,
                    'data_riferimento',   p_data_riferimento,
                    'ba_id',              v_ba_id,
                    'utility_id',         v_utility_id,
                    'istanza_utility_id', v_istanza_id
                )
            );
        ELSE
            BEGIN
                SELECT * INTO v_resolve
                  FROM vendite.fn_resolve_prezzo_listino_v2(
                      v_comp.componente_id,
                      v_comp.componente_uom_id,
                      p_data_riferimento,
                      v_ba_id,
                      v_utility_id::integer,
                      p_emittente_sr_id,
                      NULL,
                      v_articolo_id
                  );
                INSERT INTO vendite.offerte_commerciali_eccezioni_componenti (
                    eccezione_offerta_id,
                    articolo_componente_id,
                    componente_id,
                    coeff_qta_snapshot,
                    quantita,
                    uom_operativa_id,
                    factor_to_base,
                    prezzo_unitario,
                    iva_id,
                    origine_prezzo,
                    prezzo_resolver_context
                ) VALUES (
                    p_eccezione_id,
                    v_comp.bom_entry_id,
                    v_comp.componente_id,
                    v_comp.coeff_qta,
                    v_comp.coeff_qta * v_qta_padre,
                    v_comp.componente_uom_id,
                    1,
                    v_resolve.prezzo_finale,
                    v_comp.componente_iva_id,
                    v_resolve.origine,
                    jsonb_build_object(
                        'emittente_sr_id',    p_emittente_sr_id,
                        'data_riferimento',   p_data_riferimento,
                        'ba_id',              v_ba_id,
                        'utility_id',         v_utility_id,
                        'istanza_utility_id', v_istanza_id,
                        'listino_id',         v_resolve.listino_id,
                        'listino_versione_id', v_resolve.listino_versione_id,
                        'listino_riga_id',    v_resolve.listino_riga_id,
                        'contratto_id',       v_resolve.contratto_id,
                        'origine',            v_resolve.origine
                    )
                );
            EXCEPTION WHEN SQLSTATE 'P0001' THEN
                INSERT INTO vendite.offerte_commerciali_eccezioni_componenti (
                    eccezione_offerta_id,
                    articolo_componente_id,
                    componente_id,
                    coeff_qta_snapshot,
                    quantita,
                    uom_operativa_id,
                    factor_to_base,
                    prezzo_unitario,
                    iva_id,
                    origine_prezzo,
                    prezzo_resolver_context
                ) VALUES (
                    p_eccezione_id,
                    v_comp.bom_entry_id,
                    v_comp.componente_id,
                    v_comp.coeff_qta,
                    v_comp.coeff_qta * v_qta_padre,
                    v_comp.componente_uom_id,
                    1,
                    0,
                    v_comp.componente_iva_id,
                    'MANUALE',
                    jsonb_build_object(
                        'error',              'resolver_not_found',
                        'emittente_sr_id',    p_emittente_sr_id,
                        'data_riferimento',   p_data_riferimento,
                        'ba_id',              v_ba_id,
                        'utility_id',         v_utility_id,
                        'istanza_utility_id', v_istanza_id
                    )
                );
            END;
        END IF;
        v_inserted := v_inserted + 1;
    END LOOP;

    RETURN v_inserted;
END;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_eccezione_componenti_init(p_eccezione_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
IS 'Inizializza componenti BoM CASO A (esposto_in_fattura=TRUE) per un''eccezione offerta composita. Loop su articoli_componenti; per ogni componente: override da p_componenti_overrides {bom_entry_id::text: prezzo} oppure fn_resolve_prezzo_listino_v2. Fallback individuale su P0001: prezzo=0/MANUALE. Idempotente. Ritorna n. componenti inseriti. Rev 2026-05-26.';
```

---
{% include-markdown "signature-core.md" %}
