{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_cambio_natura_soggetto.md" %}
# ⚙️ Funzione `fn_check_cambio_natura_soggetto`

```sql
CREATE FUNCTION fn_check_cambio_natura_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_partita_iva text, p_cliente_pa character, p_split_payment character)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_partita_iva text, p_cliente_pa character, p_split_payment character)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi       jsonb := '[]'::jsonb;
    v_vecchia_id   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE;
    v_vecchia      record;
    v_nuova        record;
    v_nuova_nome   config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_vecchia_nome config.tipi_soggetto_dettaglio.descrizione%TYPE;
    v_doc          config.sorgenti.codice_interno%TYPE;
    v_doc_nome     config.sorgenti.etichetta%TYPE;
    v_tit_tipo     config.tipi_titolo_iva.descrizione%TYPE;
    v_tit_visibili integer;  -- conteggi: nessuna colonna di cui siano il riflesso
    v_tit_tutti    integer;
    v_ind_n        integer;
    v_ind_tipo     config.tipi_indirizzi.descrizione%TYPE;
    v_indr_n       integer;  -- conteggio: nessuna colonna di cui sia il riflesso
    v_indr_tipo    config.tipi_indirizzi.descrizione%TYPE;
    v_indr_ruolo   config.tipi_ruoli.descrizione%TYPE;
    v_dettaglio    jsonb;
BEGIN
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_check_cambio_natura_soggetto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
            NULL::uuid,
            'il soggetto e'' obbligatorio');
    END IF;

    SELECT s.tipo_soggetto_dettaglio_id
      INTO v_vecchia_id
      FROM anagrafiche.soggetti s
     WHERE s.id = p_soggetto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_check_cambio_natura_soggetto', 'E_SOGGETTO_NOT_FOUND',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text);
    END IF;

    -- Nessun cambio, nessun motivo.
    IF v_vecchia_id IS NOT DISTINCT FROM p_tipo_soggetto_dettaglio_id THEN
        RETURN v_motivi;
    END IF;

    v_dettaglio := jsonb_build_object(
        'campo',                      'tipo_soggetto_dettaglio_id',
        'soggetto_id',                p_soggetto_id,
        'tipo_soggetto_dettaglio_id', p_tipo_soggetto_dettaglio_id);

    -- ---- 0. Natura nuova NULL: una natura scritta non si svuota --
    --   D-T5-1 a (Tid, 2026-11-23, brief-db-revisione-anagrafiche §20):
    --   qui la natura vecchia c'e' sempre (il cambio e' DISTINCT), e il
    --   passaggio X -> NULL -> Y saltava la macro-tipologia, i documenti
    --   e la matrice natura <-> ruolo (S38). Vale per tutti, anche per il
    --   SUPER_ADMIN. Torna da solo, come la macro-tipologia: gli altri
    --   motivi parlano di una natura nuova che qui non c'e'. Un soggetto
    --   senza natura la riceve una volta, come prima.
    IF p_tipo_soggetto_dettaglio_id IS NULL THEN
        SELECT COALESCE(tsd.descrizione, tsd.codice_interno)
          INTO v_vecchia_nome
          FROM config.tipi_soggetto_dettaglio tsd
         WHERE tsd.id = v_vecchia_id;
        RETURN v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_VERSO_NESSUNA',
            'reason',     'VERSO_NESSUNA',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna',
            'dettaglio',  v_dettaglio,
            'valori',     jsonb_build_array(v_vecchia_nome));
    END IF;

    SELECT tsd.tipo_soggetto_id, tsd.formato_piva, tsd.dati_societari_policy,
           COALESCE(tsd.descrizione, tsd.codice_interno) AS nome
      INTO v_nuova
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = p_tipo_soggetto_dettaglio_id;

    IF NOT FOUND THEN
        RETURN v_motivi;   -- natura inesistente: parla la FK
    END IF;
    v_nuova_nome := v_nuova.nome;

    IF v_vecchia_id IS NOT NULL THEN
        SELECT tsd.tipo_soggetto_id, tsd.formato_piva,
               COALESCE(tsd.descrizione, tsd.codice_interno) AS nome
          INTO v_vecchia
          FROM config.tipi_soggetto_dettaglio tsd
         WHERE tsd.id = v_vecchia_id;
        v_vecchia_nome := v_vecchia.nome;

        -- ---- 1. un'altra macro-tipologia: torna da solo ----------
        IF v_vecchia.tipo_soggetto_id IS DISTINCT FROM v_nuova.tipo_soggetto_id THEN
            RETURN v_motivi || jsonb_build_object(
                'codice',     'E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA',
                'reason',     'ALTRA_MACRO_TIPOLOGIA',
                'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.altra_macro_tipologia',
                'dettaglio',  v_dettaglio,
                'valori',     jsonb_build_array(v_vecchia_nome, v_nuova_nome));
        END IF;

        -- ---- 2. l'identita' fiscale cambia, con documenti ---------
        IF (v_vecchia.formato_piva = 'NON_APPLICABILE')
           IS DISTINCT FROM (v_nuova.formato_piva = 'NON_APPLICABILE') THEN
            v_doc := anagrafiche.fn_soggetto_primo_documento(p_soggetto_id);
            IF v_doc IS NOT NULL THEN
                SELECT s.etichetta INTO v_doc_nome
                  FROM config.sorgenti s WHERE s.codice_interno = v_doc;
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_CAMBIO_NATURA_CON_DOCUMENTI',
                    'reason',     'CON_DOCUMENTI',
                    'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.con_documenti',
                    'dettaglio',  v_dettaglio || jsonb_build_object('sorgente', v_doc),
                    'valori',     jsonb_build_array(v_nuova_nome, COALESCE(v_doc_nome, v_doc)));
            END IF;
        END IF;
    END IF;

    -- ---- 3. P.IVA su una natura che non ne ha -------------------
    IF v_nuova.formato_piva = 'NON_APPLICABILE'
       AND NULLIF(btrim(p_partita_iva), '') IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_PIVA_NON_APPLICABILE',
            'reason',     'PIVA_NON_APPLICABILE',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.piva_non_applicabile',
            'dettaglio',  v_dettaglio || jsonb_build_object('campo', 'partita_iva'),
            'valori',     jsonb_build_array(v_nuova_nome));
    END IF;

    -- ---- 4. i flag del regime PA, uno per volta ---------------
    IF anagrafiche.fn_regime_pa_campo_non_ammesso(
           p_tipo_soggetto_dettaglio_id, p_cliente_pa, 'N') = 'cliente_pa' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CLIENTE_PA_NON_AMMESSO',
            'reason',     'CLIENTE_PA',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.cliente_pa',
            'dettaglio',  v_dettaglio || jsonb_build_object('campo', 'cliente_pa'),
            'valori',     jsonb_build_array(v_nuova_nome));
    END IF;
    IF anagrafiche.fn_regime_pa_campo_non_ammesso(
           p_tipo_soggetto_dettaglio_id, 'N', p_split_payment) = 'split_payment' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_SPLIT_PAYMENT_NON_AMMESSO',
            'reason',     'SPLIT_PAYMENT',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.split_payment',
            'dettaglio',  v_dettaglio || jsonb_build_object('campo', 'split_payment'),
            'valori',     jsonb_build_array(v_nuova_nome));
    END IF;

    -- ---- 5. e 6. i titoli IVA: visibili, poi di altri emittenti -
    SELECT count(*)::integer,
           (array_agg(tt.descrizione ORDER BY t.ordine, t.tipo_titolo_iva_id, t.titolo_iva_id))[1]
      INTO v_tit_visibili, v_tit_tipo
      FROM anagrafiche.fn_titoli_iva_non_ammessi(p_soggetto_id, p_tipo_soggetto_dettaglio_id) t
      JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id;
    v_tit_tutti := anagrafiche.fn_titoli_iva_non_ammessi_conta(
                       p_soggetto_id, p_tipo_soggetto_dettaglio_id);

    IF v_tit_visibili > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI',
            'reason',     'TITOLI_IVA',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.titoli_iva',
            'dettaglio',  v_dettaglio || jsonb_build_object('titoli', v_tit_visibili),
            'valori',     jsonb_build_array(v_nuova_nome, v_tit_tipo));
    END IF;
    IF v_tit_tutti > v_tit_visibili THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI',
            'reason',     'TITOLI_IVA_ALTRI_EMITTENTI',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.titoli_iva_altri_emittenti',
            'dettaglio',  v_dettaglio || jsonb_build_object('titoli', v_tit_tutti - v_tit_visibili),
            'valori',     jsonb_build_array(v_nuova_nome, (v_tit_tutti - v_tit_visibili)::text));
    END IF;

    -- ---- 7. i dati societari su una natura che non ne ha -------
    IF v_nuova.dati_societari_policy = 'NONE'
       AND EXISTS (SELECT 1 FROM anagrafiche.dati_societari d
                    WHERE d.soggetto_id = p_soggetto_id) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_CON_DATI_SOCIETARI',
            'reason',     'DATI_SOCIETARI',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.dati_societari',
            'dettaglio',  v_dettaglio,
            'valori',     jsonb_build_array(v_nuova_nome));
    END IF;

    -- ---- 8. gli indirizzi di un tipo che la natura non ammette -
    SELECT count(*)::integer,
           (array_agg(ti.descrizione ORDER BY ti.id, i.id))[1]
      INTO v_ind_n, v_ind_tipo
      FROM anagrafiche.indirizzi_soggetti i
      JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
     WHERE i.soggetto_id = p_soggetto_id
       AND NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(
                   p_tipo_soggetto_dettaglio_id, i.tipo_indirizzo_id,
                   script.fn_data_operativa());

    IF v_ind_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI',
            'reason',     'INDIRIZZI',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.indirizzi',
            'dettaglio',  v_dettaglio || jsonb_build_object('indirizzi', v_ind_n),
            'valori',     jsonb_build_array(v_nuova_nome, v_ind_tipo, v_ind_n::text));
    END IF;

    -- ---- 9. gli indirizzi dei ruoli, di un tipo che la natura non ammette
    --   La regola e' quella del guard degli indirizzi del ruolo
    --   (trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo): il ruolo
    --   non porta un tipo che la natura del soggetto vieta. Il primo
    --   per tipo e per riga nomina il tipo e il suo ruolo.
    SELECT count(*)::integer,
           (array_agg(ti.descrizione ORDER BY ti.id, i.id))[1],
           (array_agg(tr.descrizione ORDER BY ti.id, i.id))[1]
      INTO v_indr_n, v_indr_tipo, v_indr_ruolo
      FROM anagrafiche.indirizzi i
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = i.soggetto_ruolo_id
      JOIN config.tipi_ruoli tr          ON tr.id = sr.tipo_ruolo_id
      JOIN config.tipi_indirizzi ti      ON ti.id = i.tipo_indirizzo_id
     WHERE sr.soggetto_id = p_soggetto_id
       AND NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(
                   p_tipo_soggetto_dettaglio_id, i.tipo_indirizzo_id,
                   script.fn_data_operativa());

    IF v_indr_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI',
            'reason',     'INDIRIZZI_RUOLO',
            'reason_key', 'anagrafiche.soggetti.cambio_natura_blocco.indirizzi_ruolo',
            'dettaglio',  v_dettaglio || jsonb_build_object(
                              'indirizzi', v_indr_n, 'ruolo', v_indr_ruolo),
            'valori',     jsonb_build_array(v_nuova_nome, v_indr_tipo,
                                            v_indr_ruolo, v_indr_n::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_cambio_natura_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_partita_iva text, p_cliente_pa character, p_split_payment character)
IS 'I motivi per cui il soggetto non puo'' passare alla natura di dettaglio data: check pura, array ordinato di {codice, reason, reason_key, dettaglio, valori}, [] se il cambio si puo'' fare o se la natura non cambia. Il cambio non pulisce niente: i motivi si tolgono a mano. In ordine: la natura tolta (E_CAMBIO_NATURA_VERSO_NESSUNA, da solo); un''altra macro-tipologia (E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA, da solo); l''identita'' fiscale che cambia (P.IVA che nasce o sparisce) con il soggetto in un documento, in qualunque ruolo (E_CAMBIO_NATURA_CON_DOCUMENTI, anagrafiche.fn_soggetto_primo_documento); la P.IVA proposta su una natura che non ne ha (E_CAMBIO_NATURA_PIVA_NON_APPLICABILE); cliente_pa e split_payment proposti a S e non ammessi (E_CLIENTE_PA_NON_AMMESSO, E_SPLIT_PAYMENT_NON_AMMESSO, anagrafiche.fn_regime_pa_campo_non_ammesso); titoli IVA vigenti non ammessi visibili a chi agisce (E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI) e non visibili, di altri emittenti (E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI); la riga di dati societari su una natura senza dati societari (E_CAMBIO_NATURA_CON_DATI_SOCIETARI); indirizzi del soggetto di un tipo non ammesso (E_CAMBIO_NATURA_INDIRIZZI_NON_AMMESSI, anagrafiche.fn_tipo_indirizzo_ammesso_per_natura); indirizzi dei ruoli del soggetto di un tipo non ammesso, con lo stesso predicato (E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI, la regola del guard anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo; valori: natura, tipo e ruolo del primo, quanti). Natura nuova NULL su una natura scritta: una natura scritta non si svuota (E_CAMBIO_NATURA_VERSO_NESSUNA, da solo, per tutti; D-T5-1 a, brief-db-revisione-anagrafiche §20, 2026-11-24: fino ad allora contavano solo i titoli vigenti, e X -> NULL -> Y saltava gli altri motivi); un soggetto senza natura la riceve una volta. P.IVA e flag sono i valori proposti; la natura vecchia e'' quella salvata. Forma giuridica, sesso e indirizzi obbligatori non sono motivi: li giudicano i guard dello stato finale. SECURITY INVOKER: i titoli visibili sono quelli della RLS di chi chiama. Soggetto NULL: E_PARAMETRO_INVALIDO; inesistente: E_SOGGETTO_NOT_FOUND. La leggono anagrafiche.trgfn_soggetti_guard_cambio_natura e anagrafiche.fn_nature_proponibili_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
