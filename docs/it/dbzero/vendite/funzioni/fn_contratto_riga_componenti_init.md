{% include-markdown "it/dbzero/vendite/manual/fn_contratto_riga_componenti_init.md" %}
# ⚙️ Funzione `fn_contratto_riga_componenti_init`

```sql
CREATE FUNCTION fn_contratto_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb DEFAULT NULL::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: Popola contratti_righe_componenti per una riga composita.
--   Modello unificato: tutti i componenti attivi inseriti con attivo=TRUE.
--   BoM = contratto immutabile: l'operatore non sceglie quali includere.
--   No-op su quantita IS NULL (riga a consumo).
--   rev 2026-06-05: guard difensivo — no-op su tipo_eccezione = 'ESCLUSIONE'
--   (articolo escluso interamente, nessun componente; protegge il CHECK prezzo NULL).
DECLARE
    v_articolo_id      catalogo.articoli.id%TYPE;
    v_codice_articolo  catalogo.articoli.codice%TYPE;
    v_uom_id           catalogo.unita_misura.id%TYPE;
    v_qta_padre        vendite.contratti_righe.quantita%TYPE;
    v_contratto_id     vendite.contratti.id%TYPE;
    v_tipo_eccezione   vendite.contratti_righe.tipo_eccezione%TYPE;
    v_is_composito     catalogo.articoli.is_composito%TYPE;
    v_ba_id            anagrafiche.billing_account.id%TYPE;
    v_utility_id       vendite.contratti.utility_id%TYPE;
    v_istanza_id       vendite.contratti.istanza_utility_id%TYPE;
    v_comp             record;
    v_resolve          record;
    v_prezzo           vendite.listini_righe.prezzo%TYPE;
    v_origine          vendite.contratti_righe_componenti.origine_prezzo%TYPE;
    -- La provenienza dichiarata da un override (vendite.fn_componente_override).
    v_ov_versione      vendite.listini_righe.listino_versione_id%TYPE;
    v_ov_riga          vendite.listini_righe.id%TYPE;
    v_ov_contesto      vendite.preventivi_righe.prezzo_resolver_context%TYPE;
    v_inserted         integer := 0;
BEGIN
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_contratto_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_riga_id'),
            NULL::uuid, 'p_riga_id obbligatorio e > 0');
    END IF;
    IF p_emittente_sr_id IS NULL OR p_emittente_sr_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_contratto_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_sr_id'),
            NULL::uuid, 'p_emittente_sr_id obbligatorio e > 0');
    END IF;

    SELECT cr.articolo_id, cr.uom_operativa_id, cr.quantita, cr.contratto_id,
           cr.tipo_eccezione, a.is_composito, a.codice
      INTO v_articolo_id, v_uom_id, v_qta_padre, v_contratto_id,
           v_tipo_eccezione, v_is_composito, v_codice_articolo
      FROM vendite.contratti_righe cr
      JOIN catalogo.articoli a ON a.id = cr.articolo_id
     WHERE cr.id = p_riga_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_contratto_riga_componenti_init',
            -- rev 2026-08-07: era E_PARAMETRO_INVALIDO, cioe' 400 su un 404.
            'E_CONTRATTO_RIGA_NON_TROVATA',
            jsonb_build_object('p_riga_id', p_riga_id),
            NULL::uuid, p_riga_id::text);
    END IF;
    IF NOT v_is_composito THEN RETURN 0; END IF;

    -- Guard difensivo: ESCLUSIONE = articolo escluso interamente,
    -- nessun prezzo (CHECK chk_contrighe_prezzo_per_tipo_eccezione
    -- impone prezzo_unitario IS NULL) e quindi nessun componente BoM.
    -- Inizializzare i componenti scatenerebbe il ricalcolo del prezzo padre
    -- (trigger _z90_ricalcola_padre -> SUM figli) in violazione del CHECK.
    -- rev 2026-10-29 (20261029-42, G-0-ter): anche l'ADESIONE, che il prezzo
    -- non lo ha: il kit aderito prende prezzo e componenti dal listino.
    IF v_tipo_eccezione IN ('ESCLUSIONE', 'ADESIONE') THEN RETURN 0; END IF;

    -- No-op su riga a consumo senza quantita fissa
    IF v_qta_padre IS NULL THEN RETURN 0; END IF;

    IF EXISTS (
        SELECT 1 FROM vendite.contratti_righe_componenti
         WHERE riga_contratto_id = p_riga_id
    ) THEN RETURN 0; END IF;

    SELECT c.billing_account_id, c.utility_id, c.istanza_utility_id
      INTO v_ba_id, v_utility_id, v_istanza_id
      FROM vendite.contratti c WHERE c.id = v_contratto_id;

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
            -- L'override: un prezzo (MANUALE) o un prezzo con la sua provenienza, quando
            -- lo passa chi copia i componenti da un documento a monte.
            SELECT o.prezzo, o.origine_prezzo, o.listino_versione_id, o.listino_riga_id, o.prezzo_resolver_context
              INTO v_prezzo, v_origine, v_ov_versione, v_ov_riga, v_ov_contesto
              FROM vendite.fn_componente_override(p_componenti_overrides -> v_comp.componente_id::text) o;
            IF v_prezzo = 0 AND v_comp.obbligatorio THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_contratto_riga_componenti_init',
                    -- rev 2026-08-07: era E_PARAMETRO_INVALIDO. Non e' un parametro
                    --   malformato: e' una regola di dominio, e il codice giusto
                    --   esisteva gia'. Il suo messaggio dice «Componente obbligatorio
                    --   [%s]», quindi il valore variadico e' il COMPONENTE, non il
                    --   documento. Brief terzo lato §19.4.
                    'E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO',
                    jsonb_build_object('componente_id', v_comp.componente_id,
                        'riga_id', p_riga_id,
                        'hint', 'prezzo override deve essere diverso da zero'),
                    NULL::uuid, v_comp.componente_id::text);
            END IF;
            INSERT INTO vendite.contratti_righe_componenti (
                riga_contratto_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, quantita, uom_operativa_id, factor_to_base,
                prezzo_unitario, iva_id, origine_prezzo, attivo, listino_versione_id, listino_riga_id, prezzo_resolver_context
            ) VALUES (
                p_riga_id, v_comp.bom_entry_id, v_comp.componente_id,
                v_comp.coeff_qta, v_comp.coeff_qta * v_qta_padre,
                v_comp.componente_uom_id, 1,
                v_prezzo, v_comp.componente_iva_id, v_origine,
                TRUE,
                v_ov_versione, v_ov_riga,
                jsonb_build_object('override', true,
                    'emittente_sr_id', p_emittente_sr_id,
                    'data_riferimento', p_data_riferimento,
                    'ba_id', v_ba_id, 'utility_id', v_utility_id,
                    'istanza_utility_id', v_istanza_id) || COALESCE(v_ov_contesto, '{}'::jsonb)
            );
        ELSE
            BEGIN
                SELECT * INTO v_resolve
                  FROM vendite.fn_resolve_prezzo_listino_v2(
                      v_comp.componente_id, v_comp.componente_uom_id,
                      p_data_riferimento, v_ba_id, v_utility_id::integer,
                      p_emittente_sr_id, NULL,
                      v_articolo_id  -- p_articolo_padre_contesto: attiva STADIO BUNDLE
                  );
                INSERT INTO vendite.contratti_righe_componenti (
                    riga_contratto_id, articolo_componente_id, componente_id,
                    coeff_qta_snapshot, quantita, uom_operativa_id, factor_to_base,
                    prezzo_unitario, iva_id, origine_prezzo, attivo, listino_versione_id, listino_riga_id, prezzo_resolver_context
                ) VALUES (
                    p_riga_id, v_comp.bom_entry_id, v_comp.componente_id,
                    v_comp.coeff_qta, v_comp.coeff_qta * v_qta_padre,
                    v_comp.componente_uom_id, 1,
                    v_resolve.prezzo_finale, v_comp.componente_iva_id,
                    v_resolve.origine,
                    TRUE,
                    v_resolve.listino_versione_id, v_resolve.listino_riga_id,
                    jsonb_build_object('emittente_sr_id', p_emittente_sr_id,
                        'data_riferimento', p_data_riferimento,
                        'ba_id', v_ba_id, 'utility_id', v_utility_id,
                        'istanza_utility_id', v_istanza_id) || vendite.fn_prezzo_resolver_contesto(to_jsonb(v_resolve))
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

    -- (raggiunto solo se v_qta_padre IS NOT NULL)
    IF v_inserted = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_contratto_riga_componenti_init',
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

COMMENT ON FUNCTION vendite.fn_contratto_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
IS 'Inizializza componenti BoM per riga contratto. rev 2026-08-07, tre correzioni dal quarto lato (brief §18.3/§19.4): (1) riga inesistente -> E_CONTRATTO_RIGA_NON_TROVATA (897) invece di E_PARAMETRO_INVALIDO, 400 su un 404; (2) componente obbligatorio con prezzo override zero -> E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO, che gia'' esisteva: e'' una regola di dominio, non un parametro malformato, e il suo messaggio nomina il COMPONENTE quindi cambia anche il valore variadico; (3) tolto l''handler EXCEPTION WHEN SQLSTATE P0001, che inghiottiva SETTE codici diversi del resolver listini e li ri-sollevava tutti come listino mancante, perdendo il codice strutturato originale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
