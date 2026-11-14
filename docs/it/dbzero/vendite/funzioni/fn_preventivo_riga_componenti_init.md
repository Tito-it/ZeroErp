{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_riga_componenti_init.md" %}
# ⚙️ Funzione `fn_preventivo_riga_componenti_init`

```sql
CREATE FUNCTION fn_preventivo_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb DEFAULT NULL::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: Popola preventivi_righe_componenti per una riga composita.
--   Loop per-componente con fn_resolve_prezzo_listino_v2.
--   Override: mappa {componente_id::text: prezzo_numeric}.
--   Strict path: se nessun override e resolver fail -> raise.
--   Idempotente: no-op se componenti gia' presenti o articolo non composito.
--   Modello unificato: tutti i componenti attivi inseriti con attivo=TRUE.
--   BoM = contratto immutabile: l'operatore non sceglie quali includere.
DECLARE
    v_articolo_id      catalogo.articoli.id%TYPE;
    v_codice_articolo  catalogo.articoli.codice%TYPE;
    v_uom_id           catalogo.unita_misura.id%TYPE;
    v_qta_padre        vendite.preventivi_righe.quantita%TYPE;
    v_preventivo_id    vendite.preventivi.id%TYPE;
    v_is_composito     catalogo.articoli.is_composito%TYPE;
    v_ba_id            anagrafiche.billing_account.id%TYPE;
    v_utility_id       vendite.preventivi.utility_id%TYPE;
    v_comp             record;
    v_resolve          record;
    v_prezzo           vendite.listini_righe.prezzo%TYPE;
    v_origine          vendite.preventivi_righe_componenti.origine_prezzo%TYPE;
    -- La provenienza dichiarata da un override (vendite.fn_componente_override).
    v_ov_versione      vendite.listini_righe.listino_versione_id%TYPE;
    v_ov_riga          vendite.listini_righe.id%TYPE;
    v_ov_contesto      vendite.preventivi_righe.prezzo_resolver_context%TYPE;
    v_inserted         integer := 0;
BEGIN
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_preventivo_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_riga_id'),
            NULL::uuid, 'p_riga_id obbligatorio e > 0');
    END IF;
    IF p_emittente_sr_id IS NULL OR p_emittente_sr_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_preventivo_riga_componenti_init',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_sr_id'),
            NULL::uuid, 'p_emittente_sr_id obbligatorio e > 0');
    END IF;

    SELECT pr.articolo_id, pr.uom_operativa_id, pr.quantita, pr.preventivo_id,
           a.is_composito, a.codice
      INTO v_articolo_id, v_uom_id, v_qta_padre, v_preventivo_id,
           v_is_composito, v_codice_articolo
      FROM vendite.preventivi_righe pr
      JOIN catalogo.articoli a ON a.id = pr.articolo_id
     WHERE pr.id = p_riga_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_preventivo_riga_componenti_init',
            -- rev 2026-08-07: era E_PARAMETRO_INVALIDO, cioe' 400 su un 404.
            --   Gemello di fn_contratto_riga_componenti_init (20260807-02):
            --   stessa forma, stesso difetto, trovato dalla stessa lente.
            'E_PREVENTIVO_RIGA_NON_TROVATA',
            jsonb_build_object('p_riga_id', p_riga_id),
            NULL::uuid, p_riga_id::text);
    END IF;
    IF NOT v_is_composito THEN RETURN 0; END IF;

    -- Idempotenza: no-op se componenti gia' presenti
    IF EXISTS (
        SELECT 1 FROM vendite.preventivi_righe_componenti
         WHERE riga_preventivo_id = p_riga_id
    ) THEN RETURN 0; END IF;

    SELECT p.billing_account_id, p.utility_id
      INTO v_ba_id, v_utility_id
      FROM vendite.preventivi p WHERE p.id = v_preventivo_id;

    -- Loop su tutti i componenti attivi alla data (BoM = contratto immutabile)
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
            -- Guard prezzo=0 solo per componenti obbligatori
            IF v_prezzo = 0 AND v_comp.obbligatorio THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_preventivo_riga_componenti_init',
                    'E_PARAMETRO_INVALIDO',
                    jsonb_build_object('componente_id', v_comp.componente_id,
                        'hint', 'prezzo override deve essere diverso da zero'),
                    NULL::uuid, p_riga_id::text);
            END IF;
            INSERT INTO vendite.preventivi_righe_componenti (
                riga_preventivo_id, articolo_componente_id, componente_id,
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
                    'ba_id', v_ba_id, 'utility_id', v_utility_id) || COALESCE(v_ov_contesto, '{}'::jsonb)
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
                      v_articolo_id  -- p_articolo_padre_contesto: attiva STADIO BUNDLE
                  );
                INSERT INTO vendite.preventivi_righe_componenti (
                    riga_preventivo_id, articolo_componente_id, componente_id,
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
                    jsonb_build_object(
                        'emittente_sr_id', p_emittente_sr_id,
                        'data_riferimento', p_data_riferimento,
                        'ba_id', v_ba_id, 'utility_id', v_utility_id) || vendite.fn_prezzo_resolver_contesto(to_jsonb(v_resolve))
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
            'vendite', 'fn_preventivo_riga_componenti_init',
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

COMMENT ON FUNCTION vendite.fn_preventivo_riga_componenti_init(p_riga_id bigint, p_emittente_sr_id bigint, p_data_riferimento date, p_componenti_overrides jsonb)
IS 'Inizializza componenti BoM per riga preventivo. rev 2026-08-07: tolto l''handler EXCEPTION WHEN SQLSTATE P0001 che catturava qualunque errore del resolver listini e lo ri-sollevava come E_DOC_COMPONENTE_LISTINO_MANCANTE tenendo solo MESSAGE_TEXT (brief terzo lato §18.3). rev 2026-08-07 (bis): la riga inesistente solleva E_PREVENTIVO_RIGA_NON_TROVATA (901) invece di E_PARAMETRO_INVALIDO, che dava 400 su un 404 — sesto e ultimo dei punti trovati dalla lente del quarto lato (§19.4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
