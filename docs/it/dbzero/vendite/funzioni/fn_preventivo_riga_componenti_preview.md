{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_riga_componenti_preview.md" %}
# ⚙️ Funzione `fn_preventivo_riga_componenti_preview`

```sql
CREATE FUNCTION fn_preventivo_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer)
 RETURNS TABLE(articolo_componente_id uuid, componente_id uuid, componente_codice character varying, componente_descrizione character varying, coeff_qta_snapshot numeric, quantita_componente numeric, uom_id bigint, uom_codice character varying, iva_id bigint, prezzo_suggerito numeric, origine_prezzo character varying, resolver_error_reason text, obbligatorio boolean, esposizione_in_fattura character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: preview read-only dei componenti BoM CASO A per il drawer riga
--   (form atomic). Per ogni componente attivo e valido tenta
--   fn_resolve_prezzo_listino_v2; se fallisce ritorna prezzo_suggerito=NULL
--   + motivazione in resolver_error_reason. Nessun side-effect (STABLE).
--   rev 2026-05-13: modello unificato — rimosso filtro esposto_in_fattura=TRUE;
--   obbligatorio e esposto_in_fattura sono ora esposti nella proiezione.
--   rev 2026-10-01: esposizione_in_fattura (NASCOSTO | DESCRITTIVO | VALORIZZATO)
--   al posto del booleano esposto_in_fattura
--   (brief-db-esposizione-componenti-kit-in-fattura).
DECLARE
    v_rec     record;
    v_resolve record;
BEGIN
    FOR v_rec IN
        SELECT ac.id          AS bom_entry_id,
               ac.componente_id,
               ac.coeff_qta,
               ac.obbligatorio,
               ac.esposizione_in_fattura,
               a.codice       AS a_codice,
               a.descrizione  AS a_descrizione,
               a.uom_id       AS a_uom_id,
               a.iva_id       AS a_iva_id,
               um.codice      AS um_codice
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
          LEFT JOIN catalogo.unita_misura um ON um.id = a.uom_id
         WHERE ac.prodotto_id        = p_articolo_id
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.validita           @> p_data_riferimento
    LOOP
        articolo_componente_id := v_rec.bom_entry_id;
        componente_id          := v_rec.componente_id;
        componente_codice      := v_rec.a_codice;
        componente_descrizione := v_rec.a_descrizione;
        coeff_qta_snapshot     := v_rec.coeff_qta;
        quantita_componente    := v_rec.coeff_qta * p_quantita_padre;
        uom_id                 := v_rec.a_uom_id;
        uom_codice             := v_rec.um_codice;
        iva_id                 := v_rec.a_iva_id;
        obbligatorio           := v_rec.obbligatorio;
        esposizione_in_fattura := v_rec.esposizione_in_fattura;

        BEGIN
            SELECT * INTO v_resolve
              FROM vendite.fn_resolve_prezzo_listino_v2(
                  v_rec.componente_id,
                  v_rec.a_uom_id,
                  p_data_riferimento,
                  p_ba_id,
                  p_utility_id::integer,
                  p_emittente_sr_id,
                  p_classe_utenza_id,
                  p_articolo_id  -- p_articolo_padre_contesto: attiva STADIO BUNDLE
              );
            prezzo_suggerito      := v_resolve.prezzo_finale;
            origine_prezzo        := v_resolve.origine;
            resolver_error_reason := NULL;
        EXCEPTION WHEN SQLSTATE 'P0001' THEN
            GET STACKED DIAGNOSTICS resolver_error_reason = MESSAGE_TEXT;
            prezzo_suggerito := NULL;
            origine_prezzo   := NULL;
        END;

        RETURN NEXT;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_riga_componenti_preview(p_articolo_id uuid, p_uom_id bigint, p_quantita_padre numeric, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_sr_id bigint, p_classe_utenza_id integer)
IS 'Preview componenti BoM CASO A per drawer riga preventivo (form atomic). Read-only STABLE. rev 2026-05-13, modello unificato: aggiunta obbligatorio + esposto_in_fattura nella proiezione. Rimosso filtro esposto_in_fattura=TRUE: tutti i componenti attivi e validi sono restituiti. prezzo_suggerito=NULL + resolver_error_reason se listino mancante. rev 2026-10-01: esposto_in_fattura (boolean) diventa esposizione_in_fattura (NASCOSTO | DESCRITTIVO | VALORIZZATO), letta dalla distinta (brief-db-esposizione-componenti-kit-in-fattura).';
```

</div>

---
{% include-markdown "signature-core.md" %}
