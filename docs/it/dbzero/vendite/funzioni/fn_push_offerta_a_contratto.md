{% include-markdown "it/dbzero/vendite/manual/fn_push_offerta_a_contratto.md" %}
# ⚙️ Funzione `fn_push_offerta_a_contratto`

```sql
CREATE FUNCTION fn_push_offerta_a_contratto(p_offerta_id bigint, p_pratica_id bigint, p_chiudi_contratto_esistente boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_push_offerta_a_contratto(p_offerta_id bigint, p_pratica_id bigint, p_chiudi_contratto_esistente boolean DEFAULT false)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-57, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi CONTRATTI diventa CONTRATTO, il codice
--   della sorgente; firma e RETURNS ancorati.
DECLARE
    -- Il BERSAGLIO dei due guard di idempotenza: l'array {tipo,id} dei
    -- documenti gia' generati. ⚠️ `jsonb` esplicito — e' un frammento del
    -- context, non il valore di una colonna.
    v_bersagli jsonb;
    v_offerta               vendite.offerte_commerciali%ROWTYPE;
    v_stato_cod             config.stati_doc_offerte.codice_interno%TYPE;
    v_stato_draft_id        config.stati_doc_contratti.id%TYPE;
    v_sorgente_ofc_id       config.sorgenti.id%TYPE;
    v_sorgente_contratto_id config.sorgenti.id%TYPE;
    v_contratto_id          vendite.contratti.id%TYPE;
    v_contratto_uid         vendite.contratti.uid%TYPE;
    v_eccezione             vendite.offerte_commerciali_eccezioni%ROWTYPE;
    v_riga_id               vendite.contratti_righe.id%TYPE;
    v_overlap_id            vendite.contratti.id%TYPE;
    v_overlap_numero        vendite.contratti.numero%TYPE;
    c_ambito        CONSTANT vendite.contratti.ambito%TYPE := 'COMMODITY';
BEGIN
    -- Guard: parametro obbligatorio e valido.
    IF p_offerta_id IS NULL OR p_offerta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('param', 'p_offerta_id', 'value', p_offerta_id),
            NULL::uuid,
            'p_offerta_id = ' || COALESCE(p_offerta_id::text, 'NULL')
        );
    END IF;

    -- Carica offerta.
    SELECT * INTO v_offerta
      FROM vendite.offerte_commerciali
     WHERE id = p_offerta_id;

    -- Guard: offerta non trovata.
    -- ⚠️ rev 2026-08-06: qui c'era E_PARAMETRO_INVALIDO. L'operatore leggeva
    --   «Parametro non valido: offerta non trovata: 42» — una frase che
    --   contraddice se' stessa — e il backend rispondeva 400 su una condizione
    --   che e' un 404. Il valore variadico non deve piu' ripetere la frase: il
    --   messaggio di E_OFFERTA_NON_TROVATA la dice gia'. Brief §18.2/§18.5a.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_OFFERTA_NON_TROVATA',
            jsonb_build_object('offerta_id', p_offerta_id),
            NULL::uuid,
            p_offerta_id::text
        );
    END IF;

    -- Recupera codice stato dell'offerta.
    SELECT codice_interno INTO v_stato_cod
      FROM config.stati_doc_offerte
     WHERE id = v_offerta.stato_doc_offerta_id;

    -- Guard: push ammesso SOLO da stato ACCETTATA.
    IF v_stato_cod IS DISTINCT FROM 'ACCETTATA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_OFFERTA_PUSH_STATO_NON_AMMESSO',
            jsonb_build_object(
                'offerta_id',     p_offerta_id,
                'stato_corrente', COALESCE(v_stato_cod, 'NULL')
            ),
            NULL::uuid,
            p_offerta_id::text,
            COALESCE(v_stato_cod, 'NULL')
        );
    END IF;

    -- Guard idempotenza: contratto gia' generato per questa offerta?
    --
    -- ⭐ IL BERSAGLIO NON E' L'OFFERTA — ed e' la cosa che questo scaglione ha
    --    insegnato. La frase nomina l'offerta perche' e' il soggetto del
    --    discorso, ma l'operatore l'offerta ce l'ha gia' davanti: quello che
    --    non riesce a raggiungere e' il CONTRATTO che risulta gia' generato.
    --    Il bersaglio e' «dove devi andare», non «di cosa stiamo parlando».
    --
    -- ⚠️ L'EXISTS diventa una raccolta: costa una scansione uguale e porta via
    --    gli id. Sono un array perche' se i contratti fossero piu' d'uno —
    --    l'anomalia che questo guard esiste per fermare — l'operatore deve
    --    poterli vedere tutti, non solo il primo.
    --
    -- ⭐ rev 2026-10-11 (D-3/D-6 di brief-db-annullo-documento-con-legami):
    --    solo i documenti VIVI, dalla sede unica vendite.fn_offerta_documenti_vivi.
    --    Un contratto annullato conserva la provenienza ma non consuma l'offerta.
    SELECT jsonb_agg(jsonb_build_object('tipo', d.tipo, 'id', d.documento_id::text)
                     ORDER BY d.documento_id)
      INTO v_bersagli
      FROM vendite.fn_offerta_documenti_vivi(p_offerta_id) AS d
     WHERE d.tipo = 'CONTRATTO';

    IF v_bersagli IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_OFFERTA_CONTRATTO_GIA_GENERATO',
            jsonb_build_object('offerta_id', p_offerta_id,
                               'bersaglio',  v_bersagli),
            NULL::uuid,
            p_offerta_id::text
        );
    END IF;

    -- Guard mutua esclusivita': ordine gia' generato per questa offerta?
    -- Stesso principio del guard qui sopra: si manda l'operatore sull'ORDINE
    -- che esiste, non sull'offerta che ha gia' aperto.
    -- Solo gli ordini VIVI (rev 2026-10-11, come sopra).
    SELECT jsonb_agg(jsonb_build_object('tipo', d.tipo, 'id', d.documento_id::text)
                     ORDER BY d.documento_id)
      INTO v_bersagli
      FROM vendite.fn_offerta_documenti_vivi(p_offerta_id) AS d
     WHERE d.tipo = 'ORDINE_VENDITA';

    IF v_bersagli IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_OFFERTA_ORDINE_GIA_GENERATO',
            jsonb_build_object('offerta_id', p_offerta_id,
                               'bersaglio',  v_bersagli),
            NULL::uuid,
            p_offerta_id::text
        );
    END IF;

    -- Config: stato DRAFT contratto.
    SELECT id INTO v_stato_draft_id
      FROM config.stati_doc_contratti
     WHERE codice_interno = 'DRAFT';

    IF v_stato_draft_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('tabella', 'config.stati_doc_contratti', 'codice', 'DRAFT'),
            NULL::uuid,
            'stato DRAFT non trovato in config.stati_doc_contratti'
        );
    END IF;

    -- Config: sorgente OFFERTA_COMMERCIALE.
    SELECT id INTO v_sorgente_ofc_id
      FROM config.sorgenti
     WHERE codice_interno = 'OFFERTA_COMMERCIALE';

    IF v_sorgente_ofc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_push_offerta_a_contratto',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('tabella', 'config.sorgenti', 'codice', 'OFFERTA_COMMERCIALE'),
            NULL::uuid,
            'sorgente OFFERTA_COMMERCIALE non trovata in config.sorgenti'
        );
    END IF;

    -- =====================================================
    -- Successione su overlap (meccanismo generico, brief §3.4)
    -- =====================================================
    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.contratti.overlap:'
                 || v_offerta.billing_account_id::text || ':'
                 || v_offerta.istanza_utility_id::text || ':'
                 || v_offerta.utility_id::text || ':'
                 || c_ambito)
    );

    v_overlap_id := vendite.fn_contratto_sovrapposto(
        v_offerta.billing_account_id,
        v_offerta.istanza_utility_id,
        v_offerta.utility_id,
        c_ambito,
        v_offerta.validita_dal,
        v_offerta.validita_al
    );

    IF v_overlap_id IS NOT NULL THEN
        SELECT numero INTO v_overlap_numero
          FROM vendite.contratti WHERE id = v_overlap_id;

        IF NOT COALESCE(p_chiudi_contratto_esistente, false) THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_push_offerta_a_contratto',
                'E_CONTRATTO_OVERLAP_ESISTENTE',
                jsonb_build_object(
                    'offerta_id',           p_offerta_id,
                    'contratto_overlap_id', v_overlap_id,
                    'numero',               v_overlap_numero,
                    'validita_dal',         v_offerta.validita_dal,
                    'validita_al',          v_offerta.validita_al
                ),
                NULL::uuid,
                COALESCE(v_overlap_numero, v_overlap_id::text)
            );
        ELSE
            PERFORM vendite.fn_chiudi_contratto_per_successione(
                v_overlap_id, v_offerta.validita_dal
            );
        END IF;
    END IF;

    -- INSERT contratto in DRAFT — copia campi business 1:1 dall'offerta.
    BEGIN
        INSERT INTO vendite.contratti (
            billing_account_id,
            istanza_utility_id,
            utility_id,
            listino_id,
            listino_versione_id,
            valore_variazione_globale,
            tipo_variazione_globale,
            valido_dal,
            valido_al,
            stato_doc_contratto_id,
            sorgente_tipo_id,
            sorgente_uid,
            offerta_id,
            emittente_fiscale_id,
            meta
        )
        VALUES (
            v_offerta.billing_account_id,
            v_offerta.istanza_utility_id,
            v_offerta.utility_id,
            v_offerta.listino_id,
            v_offerta.listino_versione_id,
            v_offerta.valore_variazione_globale,
            v_offerta.tipo_variazione_globale,
            v_offerta.validita_dal,
            v_offerta.validita_al,
            v_stato_draft_id,
            v_sorgente_ofc_id,
            v_offerta.uid,
            p_offerta_id,
            v_offerta.emittente_fiscale_id,
            COALESCE(v_offerta.meta, '{}'::jsonb)
        )
        RETURNING id, uid INTO v_contratto_id, v_contratto_uid;
    EXCEPTION
        WHEN exclusion_violation THEN
            v_overlap_id := vendite.fn_contratto_sovrapposto(
                v_offerta.billing_account_id,
                v_offerta.istanza_utility_id,
                v_offerta.utility_id,
                c_ambito,
                v_offerta.validita_dal,
                v_offerta.validita_al
            );
            SELECT numero INTO v_overlap_numero
              FROM vendite.contratti WHERE id = v_overlap_id;

            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_push_offerta_a_contratto',
                'E_CONTRATTO_OVERLAP_ESISTENTE',
                jsonb_build_object(
                    'offerta_id',           p_offerta_id,
                    'contratto_overlap_id', v_overlap_id,
                    'numero',               v_overlap_numero,
                    'backstop',             true
                ),
                NULL::uuid,
                COALESCE(v_overlap_numero, COALESCE(v_overlap_id::text, '?'))
            );
    END;

    -- Cascata indirizzi (D-1): copia 1:1 gli snapshot dell'offerta
    -- filtrati sui tipi ammessi in ambito CONTRATTI. origine_*
    -- propagati; idempotente (uno-per-tipo).
    INSERT INTO vendite.contratti_indirizzi (
        contratto_id, tipo_indirizzo_id, snapshot,
        origine_indirizzo_id, origine_soggetto_ruolo_id)
    SELECT v_contratto_id, oi.tipo_indirizzo_id, oi.snapshot,
           oi.origine_indirizzo_id, oi.origine_soggetto_ruolo_id
      FROM vendite.offerte_commerciali_indirizzi oi
      JOIN config.tipi_indirizzi_allowed a
        ON a.tipo_indirizzo_id = oi.tipo_indirizzo_id
       AND a.ambito = 'CONTRATTO'
       AND a.attivo IS TRUE
     WHERE oi.offerta_id = p_offerta_id
    ON CONFLICT (contratto_id, tipo_indirizzo_id) DO NOTHING;

    -- Copia eccezioni offerta -> contratti_righe (loop per-eccezione).
    FOR v_eccezione IN
        SELECT *
          FROM vendite.offerte_commerciali_eccezioni
         WHERE offerta_id = p_offerta_id
         ORDER BY id
    LOOP
        INSERT INTO vendite.contratti_righe (
            contratto_id,
            articolo_id,
            tipo_eccezione,
            tipo_erogazione,
            fonte_quantita_attesa,
            periodicita,
            generazione_canone,
            competenza_canone,
            prezzo_unitario,
            quantita,
            qta_operativa,
            uom_operativa_id,
            factor_to_base,
            ordine,
            attivo,
            meta,
            stato_approvazione_prezzo,
            pratica_approvazione_prezzo_id
        )
        VALUES (
            v_contratto_id,
            v_eccezione.articolo_id,
            v_eccezione.tipo_eccezione,
            v_eccezione.tipo_erogazione,
            v_eccezione.fonte_quantita_attesa,
            v_eccezione.periodicita,
            v_eccezione.generazione_canone,
            v_eccezione.competenza_canone,
            v_eccezione.prezzo_unitario,
            v_eccezione.quantita,
            v_eccezione.qta_operativa,
            v_eccezione.uom_operativa_id,
            v_eccezione.factor_to_base,
            v_eccezione.ordine,
            v_eccezione.attivo,
            v_eccezione.meta,
            v_eccezione.stato_approvazione_prezzo,
            v_eccezione.pratica_approvazione_prezzo_id
        )
        RETURNING id INTO v_riga_id;

        -- Copia componenti dell'eccezione -> contratti_righe_componenti.
        INSERT INTO vendite.contratti_righe_componenti (
            riga_contratto_id,
            articolo_componente_id,
            componente_id,
            coeff_qta_snapshot,
            quantita,
            uom_operativa_id,
            factor_to_base,
            qta_operativa,
            prezzo_unitario,
            iva_id,
            origine_prezzo,
            prezzo_resolver_context,
            stato_approvazione_prezzo,
            pratica_approvazione_prezzo_id,
            meta,
            ordine,
            attivo
        )
        SELECT
            v_riga_id,
            occ.articolo_componente_id,
            occ.componente_id,
            occ.coeff_qta_snapshot,
            occ.quantita,
            occ.uom_operativa_id,
            occ.factor_to_base,
            occ.qta_operativa,
            occ.prezzo_unitario,
            occ.iva_id,
            occ.origine_prezzo,
            occ.prezzo_resolver_context,
            occ.stato_approvazione_prezzo,
            occ.pratica_approvazione_prezzo_id,
            occ.meta,
            occ.ordine,
            occ.attivo
        FROM vendite.offerte_commerciali_eccezioni_componenti occ
        WHERE occ.eccezione_offerta_id = v_eccezione.id;
    END LOOP;

    -- Copia utility offerta -> contratti_utilities (1:1).
    INSERT INTO vendite.contratti_utilities (
        contratto_id,
        istanza_utility_id,
        utility_id,
        istanza_dati_precontrattuali_id,
        classe_utenza_id,
        tipo_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        v_contratto_id,
        ocu.istanza_utility_id,
        ocu.utility_id,
        ocu.istanza_dati_precontrattuali_id,
        ocu.classe_utenza_id,
        ocu.tipo_utenza_id,
        ocu.param_1_num,
        ocu.param_2_txt,
        ocu.meta
    FROM vendite.offerte_commerciali_utilities ocu
    WHERE ocu.offerta_id = p_offerta_id
    ON CONFLICT ON CONSTRAINT uq_contratti_utilities_contratto_id
    DO UPDATE SET
        istanza_utility_id              = EXCLUDED.istanza_utility_id,
        utility_id                      = EXCLUDED.utility_id,
        istanza_dati_precontrattuali_id = EXCLUDED.istanza_dati_precontrattuali_id,
        classe_utenza_id                = EXCLUDED.classe_utenza_id,
        tipo_utenza_id                  = EXCLUDED.tipo_utenza_id,
        param_1_num                     = EXCLUDED.param_1_num,
        param_2_txt                     = EXCLUDED.param_2_txt,
        meta                            = EXCLUDED.meta;

    -- Collegamento pratica (facoltativo).
    IF p_pratica_id IS NOT NULL THEN
        SELECT id INTO v_sorgente_contratto_id
          FROM config.sorgenti
         WHERE codice_interno = 'CONTRATTO';

        IF v_sorgente_contratto_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_push_offerta_a_contratto',
                'E_CONFIG_MANCANTE',
                jsonb_build_object('tabella', 'config.sorgenti', 'codice', 'CONTRATTO'),
                NULL::uuid,
                'sorgente CONTRATTO non trovata in config.sorgenti'
            );
        END IF;

        INSERT INTO pratiche.pratiche_sorgenti (
            pratica_id,
            sorgente_tipo_id,
            sorgente_uid,
            ruolo_link
        )
        VALUES (
            p_pratica_id,
            v_sorgente_contratto_id,
            v_contratto_uid::text,
            'COLLEGATO'
        )
        ON CONFLICT ON CONSTRAINT uq_pratiche_sorgenti_pratica_tipo_uid_ruolo
        DO NOTHING;
    END IF;

    RETURN v_contratto_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_push_offerta_a_contratto(p_offerta_id bigint, p_pratica_id bigint, p_chiudi_contratto_esistente boolean)
IS 'Genera un contratto DRAFT da un''offerta commerciale ACCETTATA. Rev6 (2026-06-08): guard di mutua esclusivita'' offerta->contratto/ordine (E_OFFERTA_ORDINE_GIA_GENERATO) — un''offerta genera al massimo uno tra contratto e ordine. Rev5 (2026-06-01): trasporta 1:1 stato_approvazione_prezzo + pratica_approvazione_prezzo_id anche sulle RIGHE (oltre che sui componenti). Rev4 (2026-05-31): consumatore del meccanismo generico di successione contratti (advisory lock + overlap + routing + backstop). Copia eccezioni+componenti e utility; idempotente (E_OFFERTA_CONTRATTO_GIA_GENERATO). ⭐ rev 2026-08-24: i due guard di idempotenza portano il BERSAGLIO, e il bersaglio NON e'' l''offerta — e'' il documento GIA'' GENERATO (il contratto, oppure l''ordine). La frase nomina l''offerta perche'' e'' il soggetto del discorso, ma l''operatore l''offerta ce l''ha gia'' davanti: cio'' che non riesce a raggiungere e'' il documento che gli blocca la strada. E'' un array perche'' se i documenti fossero piu'' d''uno — l''anomalia che il guard esiste per fermare — deve poterli vedere tutti. Da qui il canale DATATYPE dell''eccezione, e il frontend ci disegna «vai al contratto». ⚠️ L''EXISTS e'' diventato una raccolta: stessa scansione, in piu'' gli id. Brief: brief-db-bersaglio-errore.md §6 L6. rev 2026-10-11 (20261011-74, brief-db-annullo-documento-con-legami D-3/D-6): i due guard (E_OFFERTA_CONTRATTO_GIA_GENERATO, E_OFFERTA_ORDINE_GIA_GENERATO) guardano i soli documenti VIVI, letti da vendite.fn_offerta_documenti_vivi (sede unica, con la capability dell''offerta): un contratto o un ordine annullato conserva la provenienza ma non consuma piu'' l''offerta. Gli indici unici uq_contratti_offerta_id e uq_ordini_v_documento_origine_offerta valgono sui soli vivi (20261011-68, -70). Rev 2026-10-20 (20261020-57, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi CONTRATTI diventa CONTRATTO, il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
