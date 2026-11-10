{% include-markdown "it/dbzero/vendite/manual/fn_ddt_riga_componenti_init.md" %}
# ⚙️ Funzione `fn_ddt_riga_componenti_init`

```sql
CREATE FUNCTION fn_ddt_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb DEFAULT NULL::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$

-- Scopo: Popola ddt_righe_componenti per una riga composita.
--   Modello unificato: tutti i componenti attivi inseriti con attivo=TRUE.
--   BoM = contratto immutabile: l'operatore non sceglie quali includere.
DECLARE
    v_articolo_id      catalogo.articoli.id%TYPE;
    v_codice_articolo  catalogo.articoli.codice%TYPE;
    v_uom_id           catalogo.unita_misura.id%TYPE;
    v_qta_padre        vendite.ddt_righe.quantita%TYPE;
    v_ddt_id           vendite.ddt.id%TYPE;
    v_is_composito     catalogo.articoli.is_composito%TYPE;
    v_ba_id            anagrafiche.billing_account.id%TYPE;
    v_utility_id       vendite.ddt.utility_id%TYPE;
    v_comp             record;
    v_resolve          record;
    v_prezzo           vendite.listini_righe.prezzo%TYPE;
    v_origine          vendite.ddt_righe_componenti.origine_prezzo%TYPE;
    v_inserted         integer := 0;
BEGIN
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ddt_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_riga_id'),
            NULL::uuid, 'p_riga_id obbligatorio e > 0');
    END IF;
    IF p_emittente_sr_id IS NULL OR p_emittente_sr_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ddt_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_sr_id'),
            NULL::uuid, 'p_emittente_sr_id obbligatorio e > 0');
    END IF;

    SELECT dr.articolo_id, dr.uom_operativa_id, dr.quantita, dr.ddt_id,
           a.is_composito, a.codice
      INTO v_articolo_id, v_uom_id, v_qta_padre, v_ddt_id,
           v_is_composito, v_codice_articolo
      FROM vendite.ddt_righe dr
      JOIN catalogo.articoli a ON a.id = dr.articolo_id
     WHERE dr.id = p_riga_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ddt_riga_componenti_init',
            -- rev 2026-08-07: era E_PARAMETRO_INVALIDO, cioe' 400 su un 404.
            --   Gemello di fn_contratto_riga_componenti_init (20260807-02):
            --   stessa forma, stesso difetto, trovato dalla stessa lente.
            'E_DDT_RIGA_NON_TROVATA',
            jsonb_build_object('p_riga_id', p_riga_id),
            NULL::uuid, p_riga_id::text);
    END IF;
    IF NOT COALESCE(v_is_composito, FALSE) THEN RETURN 0; END IF;

    IF EXISTS (
        SELECT 1 FROM vendite.ddt_righe_componenti
         WHERE riga_ddt_id = p_riga_id
    ) THEN RETURN 0; END IF;

    SELECT d.billing_account_id, d.utility_id
      INTO v_ba_id, v_utility_id
      FROM vendite.ddt d WHERE d.id = v_ddt_id;

    FOR v_comp IN
        SELECT ac.id          AS bom_entry_id,
               ac.componente_id,
               ac.coeff_qta,
               ac.obbligatorio,
               a.uom_id       AS componente_uom_id,
               a.iva_id       AS componente_iva_id
          FROM catalogo.fn_distinta_alla_data(v_articolo_id, p_data_riferimento) ac
          JOIN catalogo.articoli a ON a.id = ac.componente_id
    LOOP
        IF p_componenti_overrides IS NOT NULL
           AND p_componenti_overrides ? v_comp.componente_id::text THEN
            v_prezzo  := (p_componenti_overrides ->> v_comp.componente_id::text)::numeric;
            v_origine := 'MANUALE';
            -- ⚠️ Stessa regola della clausola WHEN del trigger (20260819-15):
            --   l'override a zero su un componente obbligatorio si vieta
            --   finche' il documento vende. Senza questa condizione il divieto
            --   sarebbe stato allentato nel trigger e rimasto qui, cioe' in
            --   due posti che dicono cose diverse sulla stessa regola.
            IF v_prezzo = 0 AND COALESCE(v_comp.obbligatorio, TRUE)
               AND vendite.fn_check_ddt_riga_richiede_prezzo(p_riga_id) THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_ddt_riga_componenti_init',
                    'E_PARAMETRO_INVALIDO',
                    jsonb_build_object('componente_id', v_comp.componente_id,
                        'hint', 'prezzo override deve essere diverso da zero'),
                    NULL::uuid, p_riga_id::text);
            END IF;
            INSERT INTO vendite.ddt_righe_componenti (
                riga_ddt_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, quantita, uom_operativa_id, factor_to_base,
                prezzo_unitario, iva_id, origine_prezzo, attivo, prezzo_resolver_context
            ) VALUES (
                p_riga_id, v_comp.bom_entry_id, v_comp.componente_id,
                v_comp.coeff_qta, v_comp.coeff_qta * v_qta_padre,
                v_comp.componente_uom_id, 1,
                v_prezzo, v_comp.componente_iva_id, v_origine,
                TRUE,
                jsonb_build_object('override', true,
                    'emittente_sr_id', p_emittente_sr_id,
                    'data_riferimento', p_data_riferimento,
                    'ba_id', v_ba_id, 'utility_id', v_utility_id)
            );
        ELSE
            -- rev 2026-08-19: il BEGIN..END resta un blocco nudo, senza
            --   EXCEPTION. Il commento storico diceva che lo si teneva per non
            --   re-indentare venticinque righe: ora che la chiamata cambia
            --   comunque, la ragione decade — ma toglierlo sposterebbe righe
            --   che questo changeSet non ha motivo di toccare, e un diff piu'
            --   grande e' un diff piu' difficile da rivedere.
            BEGIN
                SELECT * INTO v_resolve
                  FROM vendite.fn_resolve_prezzo_listino_v2_esito(
                      v_comp.componente_id, v_comp.componente_uom_id,
                      p_data_riferimento, v_ba_id, v_utility_id::integer,
                      p_emittente_sr_id, NULL,
                      v_articolo_id  -- p_articolo_padre_contesto: attiva STADIO BUNDLE
                  );
                INSERT INTO vendite.ddt_righe_componenti (
                    riga_ddt_id, articolo_componente_id, componente_id,
                    coeff_qta_snapshot, quantita, uom_operativa_id, factor_to_base,
                    prezzo_unitario, iva_id, origine_prezzo, attivo, prezzo_resolver_context
                ) VALUES (
                    p_riga_id, v_comp.bom_entry_id, v_comp.componente_id,
                    v_comp.coeff_qta, v_comp.coeff_qta * v_qta_padre,
                    v_comp.componente_uom_id, 1,
                    -- ⭐ Prezzo NULL quando il nucleo non ha risolto: e' il
                    --   punto in cui un kit puo' finalmente viaggiare senza
                    --   vendersi. Prima qui il resolver sollevava e la riga
                    --   non si creava affatto.
                    CASE WHEN v_resolve.esito_codice IS NULL
                         THEN v_resolve.prezzo_finale END,
                    v_comp.componente_iva_id,
                    v_resolve.origine,
                    TRUE,
                    jsonb_build_object('emittente_sr_id', p_emittente_sr_id,
                        'data_riferimento', p_data_riferimento,
                        'ba_id', v_ba_id, 'utility_id', v_utility_id,
                        'listino_id', v_resolve.listino_id,
                        'listino_versione_id', v_resolve.listino_versione_id,
                        'listino_riga_id', v_resolve.listino_riga_id,
                        'contratto_id', v_resolve.contratto_id,
                        'origine', v_resolve.origine,
                        -- Il motivo per cui il prezzo manca resta scritto qui:
                        -- NULL se ha risolto, il codice dell'esito altrimenti.
                        'esito_codice', v_resolve.esito_codice)
                );
            -- ⚠️ rev 2026-08-07: qui c'era `EXCEPTION WHEN SQLSTATE 'P0001'`,
            --   che catturava QUALUNQUE errore di dominio del resolver e lo
            --   ri-sollevava come E_DOC_COMPONENTE_LISTINO_MANCANTE tenendo solo
            --   MESSAGE_TEXT: il codice strutturato originale andava perso, e con
            --   lui il tipo di risposta. Sette codici diversi arrivavano al client
            --   come 422 «listino non configurato» anche quando il listino non
            --   c'entrava nulla. Ora l'errore del resolver passa col proprio codice.
            --   Il blocco BEGIN..END resta: non serve piu' a nulla di funzionale,
            --   ma toglierlo vorrebbe dire re-indentare venticinque righe per
            --   niente. Brief terzo lato §18.3.
            END;
        END IF;
        v_inserted := v_inserted + 1;
    END LOOP;

    IF v_inserted = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ddt_riga_componenti_init',
            'E_DOC_COMPOSITO_BOM_VUOTA',
            jsonb_build_object('articolo_id', v_articolo_id,
                'data_riferimento', p_data_riferimento),
            NULL::uuid,
            v_codice_articolo,
            p_data_riferimento::text
        );
    END IF;

    RETURN v_inserted;
END;

$function$

COMMENT ON FUNCTION vendite.fn_ddt_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
IS 'Popola vendite.ddt_righe_componenti per una riga composita. BoM = contratto immutabile: l''operatore non sceglie quali componenti includere. rev 2026-08-19: usa il NUCLEO fn_resolve_prezzo_listino_v2_esito. Se il prezzo di un componente non si risolve la riga si crea lo stesso con prezzo_unitario NULL e con esito_codice in prezzo_resolver_context — prima l''intera riga-kit falliva, ed era l''unica ragione per cui un kit non poteva viaggiare su un DDT che non vende. Il divieto dell''override a zero sui componenti obbligatori si applica solo se la causale e'' fatturabile (stessa regola della WHEN del trigger 20260819-15). Brief: brief-ddt-righe-senza-prezzo §9 slice C (C5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
