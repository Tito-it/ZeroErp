{% include-markdown "it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md" %}
# ⚙️ Funzione `fn_resolve_prezzo_listino_v2`

```sql
CREATE FUNCTION fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer)
 RETURNS TABLE(prezzo_finale numeric, prezzo_base_snapshot numeric, tipo_variazione_applicata character varying, valore_variazione_applicata numeric, origine character varying, listino_id bigint, listino_versione_id bigint, listino_riga_id bigint, contratto_id bigint, promo_id bigint, categoria_cliente_listino_id bigint, categoria_cliente_id_snapshot smallint, classe_utenza_id_snapshot integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Accumulatori del risultato (%TYPE dove riflettono colonne).
    v_prezzo_finale            vendite.listini_righe.prezzo%TYPE;
    v_prezzo_base              vendite.listini_righe.prezzo%TYPE;
    v_tipo_var                 anagrafiche.categorie_clienti_listini.tipo_variazione%TYPE;
    v_valore_var               anagrafiche.categorie_clienti_listini.valore_variazione%TYPE;
    v_origine                  varchar(32);
    v_listino_id               vendite.listini.id%TYPE;
    v_listino_versione_id      vendite.listini_versioni.id%TYPE;
    v_listino_riga_id          vendite.listini_righe.id%TYPE;
    v_contratto_id             vendite.contratti.id%TYPE;
    v_promo_id                 vendite.promo_articoli.id%TYPE;
    v_categoria_cli_listino_id anagrafiche.categorie_clienti_listini.id%TYPE;

    -- Snapshot output: categoria e classe congelate al momento del calcolo.
    v_snapshot_categoria       anagrafiche.billing_account.categoria_cliente_id%TYPE;
    v_snapshot_classe          config.classi_utenze.id%TYPE;

    -- Dimensioni derivate dal BA.
    v_categoria_cliente_id     anagrafiche.billing_account.categoria_cliente_id%TYPE;
    v_partecipa_promo          anagrafiche.categorie_clienti.partecipa_promo%TYPE;
    v_ba_found                 boolean;

    -- Buffer CONTRATTO.
    v_contr_listino_id         vendite.contratti.listino_id%TYPE;
    v_contr_tipo_var           vendite.contratti.tipo_variazione_globale%TYPE;
    v_contr_valore_var         vendite.contratti.valore_variazione_globale%TYPE;
    v_contr_riga_prezzo        vendite.contratti_righe.prezzo_unitario%TYPE;
    v_contr_cat_snapshot       vendite.contratti.categoria_cliente_id_snapshot%TYPE;

    -- Buffer PROMO.
    v_promo_tipo_var           vendite.promo_articoli.tipo_variazione%TYPE;
    v_promo_valore_var         vendite.promo_articoli.valore_variazione%TYPE;

    -- Buffer CATEGORIA.
    v_matrice_listino_id       anagrafiche.categorie_clienti_listini.listino_id%TYPE;
    v_matrice_tipo_var         anagrafiche.categorie_clienti_listini.tipo_variazione%TYPE;
    v_matrice_valore_var       anagrafiche.categorie_clienti_listini.valore_variazione%TYPE;
BEGIN
    -- Guard input: ID > 0 obbligatori, data NOT NULL.
    IF p_articolo_id IS NULL
       OR p_uom_id IS NULL OR p_uom_id <= 0
       OR p_data_riferimento IS NULL
       OR p_ba_id IS NULL OR p_ba_id <= 0
       OR p_utility_id IS NULL OR p_utility_id <= 0
       OR p_emittente_soggetto_ruolo_id IS NULL
       OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_listino_v2',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'articolo_id', p_articolo_id,
                'uom_id', p_uom_id,
                'data_riferimento', p_data_riferimento,
                'ba_id', p_ba_id,
                'utility_id', p_utility_id,
                'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id,
                'classe_utenza_id', p_classe_utenza_id
            ),
            NULL::uuid,
            'parametri resolver pricing v2 non validi'
        );
    END IF;

    -- Dimensioni BA: categoria + partecipa_promo.
    SELECT ba.categoria_cliente_id,
           cc.partecipa_promo,
           TRUE
      INTO v_categoria_cliente_id,
           v_partecipa_promo,
           v_ba_found
      FROM anagrafiche.billing_account ba
      LEFT JOIN anagrafiche.categorie_clienti cc
        ON cc.id = ba.categoria_cliente_id
     WHERE ba.id = p_ba_id;

    IF NOT COALESCE(v_ba_found, FALSE) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_listino_v2',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('ba_id', p_ba_id),
            NULL::uuid,
            format('billing_account inesistente: %s', p_ba_id)
        );
    END IF;

    -- Classe utenza snapshot: e' sempre il valore fornito dal
    -- caller (rappresenta la classe del punto fornitura al
    -- momento del calcolo).
    v_snapshot_classe := p_classe_utenza_id;

    -- STADIO 1: contratto attivo per (ba, utility, data).
    -- Estraggo anche categoria_cliente_id_snapshot dal contratto.
    SELECT c.id,
           c.listino_id,
           c.tipo_variazione_globale,
           c.valore_variazione_globale,
           c.categoria_cliente_id_snapshot
      INTO v_contratto_id,
           v_contr_listino_id,
           v_contr_tipo_var,
           v_contr_valore_var,
           v_contr_cat_snapshot
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s
        ON s.id = c.stato_doc_contratto_id
     WHERE c.billing_account_id = p_ba_id
       AND c.utility_id         = p_utility_id
       AND c.validita          @> p_data_riferimento
       AND s.codice_interno     = 'ATTIVO'
     LIMIT 1;

    IF v_contratto_id IS NOT NULL THEN
        -- Categoria snapshot dal contratto (congelata alla
        -- creazione). Fallback al BA se il contratto pre-D1
        -- ha il campo ancora NULL.
        v_snapshot_categoria := COALESCE(v_contr_cat_snapshot, v_categoria_cliente_id);

        -- Stadio 1a: override riga.
        SELECT cr.prezzo_unitario
          INTO v_contr_riga_prezzo
          FROM vendite.contratti_righe cr
         WHERE cr.contratto_id          = v_contratto_id
           AND cr.articolo_id           = p_articolo_id
           AND COALESCE(cr.attivo, TRUE) = TRUE
           AND cr.prezzo_unitario IS NOT NULL
         LIMIT 1;

        IF v_contr_riga_prezzo IS NOT NULL THEN
            v_prezzo_base   := v_contr_riga_prezzo;
            v_prezzo_finale := v_contr_riga_prezzo;
            v_tipo_var      := 'NESSUNA';
            v_valore_var    := NULL;
            v_origine       := 'CONTRATTO_OVERRIDE';
        ELSE
            -- Stadio 1b: listino del contratto.
            IF v_contr_listino_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite',
                    'fn_resolve_prezzo_listino_v2',
                    'E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C',
                    jsonb_build_object(
                        'contratto_id', v_contratto_id,
                        'articolo_id', p_articolo_id,
                        'uom_id', p_uom_id
                    ),
                    NULL::uuid,
                    v_contratto_id::text,
                    p_articolo_id::text,
                    p_uom_id::text
                );
            END IF;

            SELECT lv.id, lr.id, lr.prezzo
              INTO v_listino_versione_id, v_listino_riga_id, v_prezzo_base
              FROM vendite.listini_versioni lv
              JOIN vendite.listini_righe lr
                ON lr.listino_versione_id = lv.id
             WHERE lv.listino_id    = v_contr_listino_id
               AND lv.validita     @> p_data_riferimento
               AND lv.attivo        = TRUE
               AND lr.articolo_id   = p_articolo_id
               AND lr.uom_id        = p_uom_id
               AND lr.attivo        = TRUE
             LIMIT 1;

            IF v_listino_riga_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite',
                    'fn_resolve_prezzo_listino_v2',
                    'E_PREZZO_LISTINO_RIGA_NON_TROVATA',
                    jsonb_build_object(
                        'origine_stadio', 'CONTRATTO_LISTINO',
                        'contratto_id', v_contratto_id,
                        'listino_id', v_contr_listino_id,
                        'articolo_id', p_articolo_id,
                        'uom_id', p_uom_id,
                        'data_riferimento', p_data_riferimento
                    ),
                    NULL::uuid,
                    p_articolo_id::text,
                    p_uom_id::text,
                    v_contr_listino_id::text,
                    p_data_riferimento::text
                );
            END IF;

            v_listino_id := v_contr_listino_id;

            IF v_contr_tipo_var IS NOT NULL THEN
                v_prezzo_finale := CASE v_contr_tipo_var
                    WHEN 'PERCENTUALE'  THEN v_prezzo_base * (1 + v_contr_valore_var / 100.0)
                    WHEN 'VALORE_FISSO' THEN v_prezzo_base + v_contr_valore_var
                END;
                v_tipo_var   := v_contr_tipo_var;
                v_valore_var := v_contr_valore_var;
            ELSE
                v_prezzo_finale := v_prezzo_base;
                v_tipo_var      := 'NESSUNA';
                v_valore_var    := NULL;
            END IF;

            v_origine := 'CONTRATTO_LISTINO';
        END IF;

    ELSE
        -- STADIO 2: CATEGORIA. Snapshot dal BA direttamente.
        v_snapshot_categoria := v_categoria_cliente_id;

        IF v_categoria_cliente_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                'fn_resolve_prezzo_listino_v2',
                'E_PREZZO_LISTINO_NON_TROVATO',
                jsonb_build_object(
                    'motivo', 'BA senza categoria_cliente_id e senza contratto attivo',
                    'ba_id', p_ba_id
                ),
                NULL::uuid,
                p_articolo_id::text
            );
        END IF;

        -- Lookup matrice in singola query: tenta match con classe
        -- specifica (se fornita) e fallback NULL nello stesso scan.
        -- ORDER BY classe_utenza_id IS NULL privilegia il match
        -- specifico (FALSE < TRUE). L'EXCLUDE no-overlap garantisce
        -- al piu' 1 riga per ciascuno dei due scenari.
        SELECT ccl.id, ccl.listino_id, ccl.tipo_variazione, ccl.valore_variazione
          INTO v_categoria_cli_listino_id,
               v_matrice_listino_id,
               v_matrice_tipo_var,
               v_matrice_valore_var
          FROM anagrafiche.categorie_clienti_listini ccl
         WHERE ccl.categoria_cliente_id        = v_categoria_cliente_id
           AND ccl.utility_id                  = p_utility_id
           AND ccl.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND (ccl.classe_utenza_id = p_classe_utenza_id
                OR ccl.classe_utenza_id IS NULL)
           AND ccl.validita                   @> p_data_riferimento
           AND ccl.attivo                      = TRUE
         ORDER BY ccl.classe_utenza_id IS NULL
         LIMIT 1;

        IF v_categoria_cli_listino_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                'fn_resolve_prezzo_listino_v2',
                'E_CATEGORIA_LISTINO_NON_MAPPATA',
                jsonb_build_object(
                    'categoria_cliente_id', v_categoria_cliente_id,
                    'utility_id', p_utility_id,
                    'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id,
                    'classe_utenza_id', p_classe_utenza_id,
                    'data_riferimento', p_data_riferimento
                ),
                NULL::uuid,
                v_categoria_cliente_id::text,
                p_utility_id::text,
                p_emittente_soggetto_ruolo_id::text,
                COALESCE(p_classe_utenza_id::text, 'NULL'),
                p_data_riferimento::text
            );
        END IF;

        SELECT lv.id, lr.id, lr.prezzo
          INTO v_listino_versione_id, v_listino_riga_id, v_prezzo_base
          FROM vendite.listini_versioni lv
          JOIN vendite.listini_righe lr
            ON lr.listino_versione_id = lv.id
         WHERE lv.listino_id    = v_matrice_listino_id
           AND lv.validita     @> p_data_riferimento
           AND lv.attivo        = TRUE
           AND lr.articolo_id   = p_articolo_id
           AND lr.uom_id        = p_uom_id
           AND lr.attivo        = TRUE
         LIMIT 1;

        IF v_listino_riga_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                'fn_resolve_prezzo_listino_v2',
                'E_PREZZO_LISTINO_RIGA_NON_TROVATA',
                jsonb_build_object(
                    'origine_stadio', 'CATEGORIA',
                    'categoria_cliente_id', v_categoria_cliente_id,
                    'listino_id', v_matrice_listino_id,
                    'articolo_id', p_articolo_id,
                    'uom_id', p_uom_id,
                    'data_riferimento', p_data_riferimento
                ),
                NULL::uuid,
                p_articolo_id::text,
                p_uom_id::text,
                v_matrice_listino_id::text,
                p_data_riferimento::text
            );
        END IF;

        v_listino_id := v_matrice_listino_id;

        IF v_matrice_tipo_var IS NOT NULL THEN
            v_prezzo_finale := CASE v_matrice_tipo_var
                WHEN 'PERCENTUALE'  THEN v_prezzo_base * (1 + v_matrice_valore_var / 100.0)
                WHEN 'VALORE_FISSO' THEN v_prezzo_base + v_matrice_valore_var
            END;
            v_tipo_var   := v_matrice_tipo_var;
            v_valore_var := v_matrice_valore_var;
        ELSE
            v_prezzo_finale := v_prezzo_base;
            v_tipo_var      := 'NESSUNA';
            v_valore_var    := NULL;
        END IF;

        v_origine := 'CATEGORIA';
    END IF;

    -- STADIO 0: PROMO OVERLAY.
    IF v_partecipa_promo IS TRUE THEN
        SELECT pa.id, pa.tipo_variazione, pa.valore_variazione
          INTO v_promo_id, v_promo_tipo_var, v_promo_valore_var
          FROM vendite.promo_articoli pa
         WHERE pa.articolo_id = p_articolo_id
           AND pa.uom_id      = p_uom_id
           AND pa.validita   @> p_data_riferimento
           AND pa.attivo      = TRUE
         LIMIT 1;

        IF v_promo_id IS NOT NULL THEN
            v_prezzo_finale := CASE v_promo_tipo_var
                WHEN 'PERCENTUALE'  THEN v_prezzo_base * (1 + v_promo_valore_var / 100.0)
                WHEN 'VALORE_FISSO' THEN v_prezzo_base + v_promo_valore_var
                WHEN 'PREZZO_FISSO' THEN v_promo_valore_var
            END;
            v_tipo_var   := v_promo_tipo_var;
            v_valore_var := v_promo_valore_var;
            v_origine    := 'PROMO';
        END IF;
    END IF;

    -- Proiezione finale sui campi OUT.
    prezzo_finale                := v_prezzo_finale;
    prezzo_base_snapshot         := v_prezzo_base;
    tipo_variazione_applicata    := v_tipo_var;
    valore_variazione_applicata  := v_valore_var;
    origine                      := v_origine;
    listino_id                   := v_listino_id;
    listino_versione_id          := v_listino_versione_id;
    listino_riga_id              := v_listino_riga_id;
    contratto_id                 := v_contratto_id;
    promo_id                     := v_promo_id;
    categoria_cliente_listino_id := v_categoria_cli_listino_id;
    -- Nuovi snapshot.
    categoria_cliente_id_snapshot := v_snapshot_categoria;
    classe_utenza_id_snapshot     := v_snapshot_classe;

    RETURN NEXT;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
IS 'Resolver prezzi pricing v5 a 3 stadi. Output: 13 colonne inclusi categoria_cliente_id_snapshot (dal contratto se STADIO 1, dal BA se STADIO 2) e classe_utenza_id_snapshot (input p_classe_utenza_id).';
```

---
{% include-markdown "signature-core.md" %}
