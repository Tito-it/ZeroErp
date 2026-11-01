{% include-markdown "it/dbzero/anagrafiche/manual/fn_provisiona_dati_di_sviluppo.md" %}
# ⚙️ Funzione `fn_provisiona_dati_di_sviluppo`

```sql
CREATE FUNCTION fn_provisiona_dati_di_sviluppo(p_password_hash jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_provisiona_dati_di_sviluppo(p_password_hash jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(tipo text, chiave text, radice_id text, esito text, secondo_fattore boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_hash       jsonb := COALESCE(p_password_hash, '{}'::jsonb);
    v_ambiente   dbops.installazione.ambiente%TYPE;
    v_guc_user   text := current_setting('app.current_user_id', true);
    v_guc_ef     text := current_setting('app.current_emittente_id', true);
    v_el         jsonb;
    v_sog        anagrafiche.soggetti.id%TYPE;
    v_sr         anagrafiche.soggetti_ruoli.id%TYPE;
    v_ef         anagrafiche.emittenti_fiscali.id%TYPE;
    v_au         anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_idg        anagrafiche.identita_digitali.id%TYPE;
    v_esito      text;
    v_sigla      anagrafiche.emittenti_fiscali.codice%TYPE;
    v_piva       anagrafiche.soggetti.partita_iva%TYPE;
    v_det        anagrafiche.indirizzi_soggetti.indirizzo_dettaglio_id%TYPE;
    v_smoke      anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ef_a       anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittenti  jsonb := '{}'::jsonb;   -- codice -> {ef, sr}
    v_radici     jsonb := '{}'::jsonb;   -- chiave soggetto -> soggetto_id
    v_fatte      text[] := ARRAY[]::text[];  -- credenziali gia' restituite
    v_profili    jsonb := '{}'::jsonb;   -- codice profilo -> id
    v_aree       jsonb;
    -- I cataloghi che i dati di prova usano: seed di 80_data.
    v_tsd_sc     config.tipi_soggetto_dettaglio.id%TYPE;
    v_forma_srl  config.forme_giuridiche.id%TYPE;
    v_prov       config.province.id%TYPE;
    v_valuta     config.valute.id%TYPE;
    v_utility    config.utilities.id%TYPE;
    v_categoria  anagrafiche.categorie_clienti.id%TYPE;
    v_qualifica  config.qualifiche.id%TYPE;
    -- ⭐ L'ELENCO: il contratto del software (brief BE §7.2, §7.3).
    c_emittenti  CONSTANT jsonb := '[
        {"chiave": "DEV-EMITTENTE-A", "codice": "DEVA", "ragione_sociale": "Emittente di prova A", "magazzino": "DEVA-MAG"},
        {"chiave": "DEV-EMITTENTE-B", "codice": "DEVB", "ragione_sociale": "Emittente di prova B", "magazzino": "DEVB-MAG"}]';
    c_clienti    CONSTANT jsonb := '[
        {"chiave": "DEV-CLIENTE-1", "ragione_sociale": "Cliente di prova 1", "emittente": "DEVA"},
        {"chiave": "DEV-CLIENTE-2", "ragione_sociale": "Cliente di prova 2", "emittente": "DEVA"},
        {"chiave": "DEV-CLIENTE-3", "ragione_sociale": "Cliente di prova 3", "emittente": "DEVA"},
        {"chiave": "DEV-CLIENTE-B", "ragione_sociale": "Cliente di prova B", "emittente": "DEVB"}]';
    c_fornitori  CONSTANT jsonb := '[
        {"chiave": "DEV-FORNITORE-1", "ragione_sociale": "Fornitore di prova 1"}]';
    c_profili    CONSTANT jsonb := '[
        {"codice": "DEV_LETTURA",   "descrizione": "Profilo di prova: lettura su tutte le aree",   "livello": "LETTURA"},
        {"codice": "DEV_OPERATIVO", "descrizione": "Profilo di prova: tutto su tutte le aree",     "livello": "TUTTO"}]';
    c_operatori  CONSTANT jsonb := '[
        {"username": "dev.smoke",      "super_admin": true,  "profilo": null,            "whitelist": false, "secondo_fattore": true,  "override": []},
        {"username": "dev.lettura",    "super_admin": false, "profilo": "DEV_LETTURA",   "whitelist": true,  "secondo_fattore": false, "override": []},
        {"username": "dev.bloccato",   "super_admin": false, "profilo": "DEV_LETTURA",   "whitelist": true,  "secondo_fattore": false,
         "override": [{"app_label": "vendite", "model_name": "contratto", "livello": "BLOCCATO", "motivo": "Utente di prova: contratti bloccati"}]},
        {"username": "dev.emittente",  "super_admin": false, "profilo": "DEV_OPERATIVO", "whitelist": true,  "secondo_fattore": false, "override": []},
        {"username": "dev.multiveste", "super_admin": false, "profilo": "DEV_LETTURA",   "whitelist": true,  "secondo_fattore": false, "override": []}]';
    c_vesti      CONSTANT jsonb := '[
        {"username": "dev.portale1",   "veste": "CLIENTE_PORTALE",   "radice": "DEV-CLIENTE-1",   "ruolo": "CL"},
        {"username": "dev.portale2",   "veste": "CLIENTE_PORTALE",   "radice": "DEV-CLIENTE-2",   "ruolo": "CL"},
        {"username": "dev.fornitore",  "veste": "FORNITORE_PORTALE", "radice": "DEV-FORNITORE-1", "ruolo": "FO"},
        {"username": "dev.multiveste", "veste": "CLIENTE_PORTALE",   "radice": "DEV-CLIENTE-3",   "ruolo": "CL"}]';
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare o riallineare i dati di sviluppo dell'elenco
    --   (emittenti A e B coi magazzini, clienti 1, 2 e B,
    --   fornitore 1, gli utenti dev.* con persone, vesti,
    --   profili, whitelist, override ed emittente attivo), e
    --   etichettarne le radici. Una riga per radice.
    --
    -- Regole:
    --   - fuori da SVILUPPO non parte (la regola pura sul
    --     valore vero dell'ambiente);
    --   - una radice si ritrova dalla sua etichetta; un omonimo
    --     senza etichetta e' E_RADICE_DI_PROVA_SENZA_ETICHETTA;
    --   - le GUC di sessione si rimettono com'erano.
    -- =========================================================

    -- 0. LA PORTA.
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_provisiona_dati_di_sviluppo',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    IF jsonb_typeof(v_hash) <> 'object' THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_provisiona_dati_di_sviluppo',
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tipo_password_hash', jsonb_typeof(v_hash)),
            NULL::uuid,
            'anagrafiche.fn_provisiona_dati_di_sviluppo',
            'le password non sono un oggetto username -> hash');
    END IF;

    -- I cataloghi.
    SELECT t.id INTO v_tsd_sc FROM config.tipi_soggetto_dettaglio t
     WHERE t.codice_interno = 'SC' AND t.stato_iso2 = 'IT';
    SELECT fg.id INTO v_forma_srl FROM config.forme_giuridiche fg
     WHERE fg.codice = 'SRL' AND fg.attivo;
    SELECT min(p.id) INTO v_prov FROM config.province p;
    SELECT v.id INTO v_valuta FROM config.valute v WHERE v.codice = 'EUR';
    SELECT u.id INTO v_utility FROM config.utilities u WHERE u.codice_interno = 'BASE';
    SELECT min(cc.id) INTO v_categoria FROM anagrafiche.categorie_clienti cc;
    SELECT q.id INTO v_qualifica FROM config.qualifiche q WHERE q.codice_interno = 'DIPENDENTE';

    -- Un indirizzo di prova: il primo stradario, civico 1
    -- (fn_create_indirizzo e' idempotente).
    v_det := anagrafiche.fn_create_indirizzo(
                 p_stradario_id := (SELECT min(s.id) FROM config.stradario s),
                 p_civico       := 1);

    -- Le GUC vuote: i BA li lega il BB all'emittente chiesto.
    PERFORM set_config('app.current_user_id', '', true);
    PERFORM set_config('app.current_emittente_id', '', true);

    -- 1. I PROFILI (configurazione, non radici): su tutte le
    --    aree presenti adesso.
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_profili) AS e LOOP
        SELECT jsonb_agg(jsonb_build_object('area_id', af.id, 'livello', v_el ->> 'livello') ORDER BY af.id)
          INTO v_aree
          FROM config.aree_funzionali af;
        v_profili := v_profili || jsonb_build_object(
            v_el ->> 'codice',
            config.fn_scrivi_profilo_accesso('AD_HOC', v_el ->> 'codice', v_el ->> 'descrizione',
                                             COALESCE(v_aree, '[]'::jsonb)));
    END LOOP;

    -- 2. GLI EMITTENTI.
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_emittenti) AS e LOOP
        SELECT sp.soggetto_id INTO v_sog FROM dbops.soggetti_di_prova sp
         WHERE sp.chiave = v_el ->> 'chiave';

        IF v_sog IS NULL THEN
            -- La sigla in una variabile: un «->> 'codice'» dentro la
            -- chiamata che solleva e' il marcatore del rubinetto del
            -- primo motivo (script/test-rubinetto-primo-motivo-v1).
            v_sigla := v_el ->> 'codice';
            IF EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali ef
                        WHERE ef.codice = v_sigla) THEN
                PERFORM script.fn_log_and_raise_error(
                    'anagrafiche', 'anagrafiche.fn_provisiona_dati_di_sviluppo',
                    'E_RADICE_DI_PROVA_SENZA_ETICHETTA',
                    jsonb_build_object('tipo', 'emittente', 'chiave', v_sigla),
                    NULL::uuid,
                    'l''emittente', v_sigla);
            END IF;

            v_piva := dbops.fn_pgtap_piva_libera();
            v_sog := anagrafiche.fn_crea_soggetto_pg(
                         p_ragione_sociale            := v_el ->> 'ragione_sociale',
                         p_tipo_soggetto_dettaglio_id := v_tsd_sc,
                         p_email                      := lower(v_el ->> 'codice') || '@sviluppo.invalid',
                         p_codice_fiscale             := v_piva,
                         p_partita_iva                := v_piva,
                         p_stato_iso2                 := 'IT',
                         p_forma_giuridica_id         := v_forma_srl,
                         p_id_prov_iscri_rea          := v_prov,
                         p_iscrizione_rea             := 'REA-' || v_piva,
                         p_capitale_sociale           := 10000.00,
                         p_socio_unico                := 'SM',
                         p_liquidazione               := 'LN');
            PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_sog, jsonb_build_object('tipo_indirizzo_codice_interno', ti.codice_interno, 'indirizzo_dettaglio_id', v_det))
               FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
               JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
              WHERE m.tipo_soggetto_dettaglio_id = v_tsd_sc AND m.attivo AND m.obbligatorio;
            INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave) VALUES (v_sog, v_el ->> 'chiave');

            -- Il ruolo EF non ha indirizzi obbligatori: lo crea il BB.
            SELECT e.emittente_fiscale_id, e.soggetto_ruolo_id INTO v_ef, v_sr
              FROM anagrafiche.fn_crea_emittente_fiscale(v_sog, v_el ->> 'codice',
                                                          jsonb_build_object('valuta_id', v_valuta)) e;
            v_esito := 'creata';
        ELSE
            SELECT ef.id, ef.soggetto_ruolo_id INTO v_ef, v_sr
              FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
             WHERE sr.soggetto_id = v_sog;
            v_esito := 'riallineata';
        END IF;

        v_emittenti := v_emittenti || jsonb_build_object(v_el ->> 'codice',
                           jsonb_build_object('ef', v_ef, 'sr', v_sr));
        tipo := 'SOGGETTO'; chiave := v_el ->> 'chiave'; radice_id := v_sog::text;
        esito := v_esito; secondo_fattore := NULL;
        RETURN NEXT;
    END LOOP;
    v_ef_a := (v_emittenti -> 'DEVA' ->> 'ef')::bigint;

    -- 3. I CLIENTI, col BA legato al loro emittente.
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_clienti) AS e LOOP
        SELECT sp.soggetto_id INTO v_sog FROM dbops.soggetti_di_prova sp
         WHERE sp.chiave = v_el ->> 'chiave';

        IF v_sog IS NULL THEN
            v_piva := dbops.fn_pgtap_piva_libera();
            v_sog := anagrafiche.fn_crea_soggetto_pg(
                         p_ragione_sociale            := v_el ->> 'ragione_sociale',
                         p_tipo_soggetto_dettaglio_id := v_tsd_sc,
                         p_email                      := lower(v_el ->> 'chiave') || '@sviluppo.invalid',
                         p_codice_fiscale             := v_piva,
                         p_partita_iva                := v_piva,
                         p_stato_iso2                 := 'IT',
                         p_forma_giuridica_id         := v_forma_srl,
                         p_id_prov_iscri_rea          := v_prov,
                         p_iscrizione_rea             := 'REA-' || v_piva,
                         p_capitale_sociale           := 10000.00,
                         p_socio_unico                := 'SM',
                         p_liquidazione               := 'LN');
            PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_sog, jsonb_build_object('tipo_indirizzo_codice_interno', ti.codice_interno, 'indirizzo_dettaglio_id', v_det))
               FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
               JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
              WHERE m.tipo_soggetto_dettaglio_id = v_tsd_sc AND m.attivo AND m.obbligatorio;
            INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave) VALUES (v_sog, v_el ->> 'chiave');

            PERFORM anagrafiche.fn_crea_cliente(
                p_soggetto_id                 := v_sog,
                p_utility_id                  := v_utility,
                p_billing_account             := jsonb_build_object('categoria_cliente_id', v_categoria,
                                                                    'valuta_id', v_valuta),
                p_indirizzi                   := jsonb_build_array(jsonb_build_object(
                                                     'indirizzo_dettaglio_id', v_det,
                                                     'tipo_indirizzo_codice_interno', 'FATT')),
                p_emittente_soggetto_ruolo_id := (v_emittenti -> (v_el ->> 'emittente') ->> 'sr')::bigint);
            v_esito := 'creata';
        ELSE
            v_esito := 'riallineata';
        END IF;

        v_radici := v_radici || jsonb_build_object(v_el ->> 'chiave', v_sog);
        tipo := 'SOGGETTO'; chiave := v_el ->> 'chiave'; radice_id := v_sog::text;
        esito := v_esito; secondo_fattore := NULL;
        RETURN NEXT;
    END LOOP;

    -- 4. IL FORNITORE.
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_fornitori) AS e LOOP
        SELECT sp.soggetto_id INTO v_sog FROM dbops.soggetti_di_prova sp
         WHERE sp.chiave = v_el ->> 'chiave';

        IF v_sog IS NULL THEN
            v_piva := dbops.fn_pgtap_piva_libera();
            v_sog := anagrafiche.fn_crea_soggetto_pg(
                         p_ragione_sociale            := v_el ->> 'ragione_sociale',
                         p_tipo_soggetto_dettaglio_id := v_tsd_sc,
                         p_email                      := lower(v_el ->> 'chiave') || '@sviluppo.invalid',
                         p_codice_fiscale             := v_piva,
                         p_partita_iva                := v_piva,
                         p_stato_iso2                 := 'IT',
                         p_forma_giuridica_id         := v_forma_srl,
                         p_id_prov_iscri_rea          := v_prov,
                         p_iscrizione_rea             := 'REA-' || v_piva,
                         p_capitale_sociale           := 10000.00,
                         p_socio_unico                := 'SM',
                         p_liquidazione               := 'LN');
            PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_sog, jsonb_build_object('tipo_indirizzo_codice_interno', ti.codice_interno, 'indirizzo_dettaglio_id', v_det))
               FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
               JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
              WHERE m.tipo_soggetto_dettaglio_id = v_tsd_sc AND m.attivo AND m.obbligatorio;
            INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave) VALUES (v_sog, v_el ->> 'chiave');

            PERFORM anagrafiche.fn_crea_fornitore(
                v_sog, '{}'::jsonb, NULL::jsonb,
                jsonb_build_array(jsonb_build_object('indirizzo_dettaglio_id', v_det,
                                                     'tipo_indirizzo_codice_interno', 'FATT')));
            v_esito := 'creata';
        ELSE
            v_esito := 'riallineata';
        END IF;

        v_radici := v_radici || jsonb_build_object(v_el ->> 'chiave', v_sog);
        tipo := 'SOGGETTO'; chiave := v_el ->> 'chiave'; radice_id := v_sog::text;
        esito := v_esito; secondo_fattore := NULL;
        RETURN NEXT;
    END LOOP;

    -- 5. GLI OPERATORI, con la loro persona.
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_operatori) AS e LOOP
        SELECT cp.auth_user_id INTO v_au FROM dbops.credenziali_di_prova cp
         WHERE cp.chiave = v_el ->> 'username';

        IF v_au IS NULL THEN
            IF EXISTS (SELECT 1 FROM django.auth_user u WHERE u.username = v_el ->> 'username') THEN
                PERFORM script.fn_log_and_raise_error(
                    'anagrafiche', 'anagrafiche.fn_provisiona_dati_di_sviluppo',
                    'E_RADICE_DI_PROVA_SENZA_ETICHETTA',
                    jsonb_build_object('tipo', 'utente', 'chiave', v_el ->> 'username'),
                    NULL::uuid,
                    'l''utente', v_el ->> 'username');
            END IF;

            SELECT m.auth_user_id INTO v_au
              FROM anagrafiche.fn_crea_operatore_v2(
                       p_cognome                      := initcap(substr(v_el ->> 'username', 5)),
                       p_nome                         := 'Dev',
                       p_codice_fiscale               := dbops.fn_pgtap_cf_libero(),
                       p_sesso                        := 'M',
                       p_username                     := v_el ->> 'username',
                       p_email                        := (v_el ->> 'username') || '@sviluppo.invalid',
                       p_password_hash                := COALESCE(v_hash ->> (v_el ->> 'username'),
                                                                  '!sviluppo-senza-password'),
                       p_qualifica_id                 := v_qualifica,
                       p_is_super_admin               := (v_el ->> 'super_admin')::boolean,
                       p_indirizzo_resid_dettaglio_id := v_det) m;
            INSERT INTO dbops.credenziali_di_prova (auth_user_id, chiave) VALUES (v_au, v_el ->> 'username');

            -- La persona dietro la credenziale: radice anche lei.
            INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave)
            SELECT sr.soggetto_id, 'DEV-PERSONA-' || upper(substr(v_el ->> 'username', 5))
              FROM anagrafiche.identita_digitali idg
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = idg.soggetto_ruolo_id
             WHERE idg.auth_user_id = v_au
               AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo;
            v_esito := 'creata';
        ELSE
            IF v_hash ->> (v_el ->> 'username') IS NOT NULL THEN
                UPDATE django.auth_user u
                   SET password = v_hash ->> (v_el ->> 'username')
                 WHERE u.id = v_au;
            END IF;
            v_esito := 'riallineata';
        END IF;

        -- Il riallineamento (anche alla nascita): veste accesa,
        -- profilo, whitelist, override, emittente attivo.
        SELECT idg.id INTO v_idg
          FROM anagrafiche.identita_digitali idg
         WHERE idg.auth_user_id = v_au
           AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo;
        PERFORM anagrafiche.fn_accendi_veste(v_idg, v_au, ARRAY['OPERATORE']::config.ruolo_applicativo[]);

        IF v_el ->> 'profilo' IS NOT NULL THEN
            PERFORM config.fn_lega_profilo_identita((v_profili ->> (v_el ->> 'profilo'))::integer, v_idg);
        END IF;
        IF (v_el ->> 'whitelist')::boolean THEN
            PERFORM script.fn_change_user_emittenti_scope(v_au, ARRAY[v_ef_a]);
        END IF;
        PERFORM config.fn_imposta_override_oggetti(v_au, v_el -> 'override');
        PERFORM config.fn_imposta_emittente_attivo(v_au, v_ef_a);

        IF v_el ->> 'username' = 'dev.smoke' THEN
            v_smoke := v_au;
        END IF;

        -- La persona, una riga anche lei (creata o riallineata
        -- insieme alla sua credenziale).
        SELECT sp.soggetto_id INTO v_sog FROM dbops.soggetti_di_prova sp
         WHERE sp.chiave = 'DEV-PERSONA-' || upper(substr(v_el ->> 'username', 5));
        tipo := 'SOGGETTO'; chiave := 'DEV-PERSONA-' || upper(substr(v_el ->> 'username', 5));
        radice_id := v_sog::text; esito := v_esito; secondo_fattore := NULL;
        RETURN NEXT;

        v_fatte := v_fatte || (v_el ->> 'username');
        tipo := 'CREDENZIALE'; chiave := v_el ->> 'username'; radice_id := v_au::text;
        esito := v_esito; secondo_fattore := (v_el ->> 'secondo_fattore')::boolean;
        RETURN NEXT;
    END LOOP;

    -- 6. I MAGAZZINI PREDEFINITI degli emittenti, per conto di
    --    dev.smoke dentro l'emittente: il guard di scope della
    --    tabella vuole un operatore (dentro una DEFINER senza
    --    operatore ferma una riga che ha un padrone).
    PERFORM set_config('app.current_user_id', v_smoke::text, true);
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_emittenti) AS e LOOP
        IF NOT EXISTS (SELECT 1 FROM magazzino.magazzini mg WHERE mg.codice = v_el ->> 'magazzino') THEN
            PERFORM set_config('app.current_emittente_id',
                               v_emittenti -> (v_el ->> 'codice') ->> 'ef', true);
            PERFORM magazzino.fn_crea_magazzino(
                v_el ->> 'magazzino',
                'Magazzino di prova ' || (v_el ->> 'codice'),
                v_det,
                '{"predefinito": true}'::jsonb,
                (v_emittenti -> (v_el ->> 'codice') ->> 'ef')::bigint);
        END IF;
    END LOOP;
    PERFORM set_config('app.current_user_id', '', true);
    PERFORM set_config('app.current_emittente_id', '', true);

    -- 7. LE VESTI DEI PORTALI (e le loro credenziali).
    FOR v_el IN SELECT e FROM jsonb_array_elements(c_vesti) AS e LOOP
        SELECT cp.auth_user_id INTO v_au FROM dbops.credenziali_di_prova cp
         WHERE cp.chiave = v_el ->> 'username';

        IF v_au IS NULL THEN
            IF EXISTS (SELECT 1 FROM django.auth_user u WHERE u.username = v_el ->> 'username') THEN
                PERFORM script.fn_log_and_raise_error(
                    'anagrafiche', 'anagrafiche.fn_provisiona_dati_di_sviluppo',
                    'E_RADICE_DI_PROVA_SENZA_ETICHETTA',
                    jsonb_build_object('tipo', 'utente', 'chiave', v_el ->> 'username'),
                    NULL::uuid,
                    'l''utente', v_el ->> 'username');
            END IF;
            v_au := anagrafiche.fn_crea_auth_user(
                        p_username      := v_el ->> 'username',
                        p_email         := (v_el ->> 'username') || '@sviluppo.invalid',
                        p_password_hash := COALESCE(v_hash ->> (v_el ->> 'username'),
                                                    '!sviluppo-senza-password'),
                        p_first_name    := 'Dev',
                        p_last_name     := initcap(substr(v_el ->> 'username', 5)));
            INSERT INTO dbops.credenziali_di_prova (auth_user_id, chiave) VALUES (v_au, v_el ->> 'username');
            v_esito := 'creata';
        ELSE
            IF v_hash ->> (v_el ->> 'username') IS NOT NULL
               AND NOT (v_el ->> 'username') = ANY (v_fatte) THEN
                UPDATE django.auth_user u
                   SET password = v_hash ->> (v_el ->> 'username')
                 WHERE u.id = v_au;
            END IF;
            v_esito := 'riallineata';
        END IF;

        SELECT sr.id INTO v_sr
          FROM anagrafiche.soggetti_ruoli sr
          JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
         WHERE sr.soggetto_id = (v_radici ->> (v_el ->> 'radice'))::uuid
           AND tr.codice_interno = v_el ->> 'ruolo';

        SELECT idg.id INTO v_idg
          FROM anagrafiche.identita_digitali idg
         WHERE idg.auth_user_id = v_au
           AND idg.soggetto_ruolo_id = v_sr
           AND idg.ruolo_applicativo = (v_el ->> 'veste')::config.ruolo_applicativo;
        IF v_idg IS NULL THEN
            PERFORM anagrafiche.fn_crea_veste_portale(v_au, v_sr,
                                                      (v_el ->> 'veste')::config.ruolo_applicativo, true);
        ELSE
            PERFORM anagrafiche.fn_accendi_veste(v_idg, v_au,
                                                 ARRAY[(v_el ->> 'veste')]::config.ruolo_applicativo[]);
        END IF;

        -- Una credenziale con piu' vesti (dev.multiveste) si dice una volta.
        IF NOT (v_el ->> 'username') = ANY (v_fatte) THEN
            v_fatte := v_fatte || (v_el ->> 'username');
            tipo := 'CREDENZIALE'; chiave := v_el ->> 'username'; radice_id := v_au::text;
            esito := v_esito; secondo_fattore := false;
            RETURN NEXT;
        END IF;
    END LOOP;

    -- Le GUC com'erano.
    PERFORM set_config('app.current_user_id', COALESCE(v_guc_user, ''), true);
    PERFORM set_config('app.current_emittente_id', COALESCE(v_guc_ef, ''), true);
    RETURN;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_provisiona_dati_di_sviluppo(p_password_hash jsonb)
IS 'Verbo dei dati di sviluppo (2026-10-18): crea o riallinea gli utenti e i soggetti di prova dell''elenco del brief BE §7 (emittenti DEVA e DEVB coi magazzini predefiniti; clienti 1, 2 e 3 su A, B su B, con BA legato al loro emittente; fornitore 1; gli operatori dev.smoke SUPER_ADMIN, dev.lettura e dev.bloccato col profilo DEV_LETTURA, dev.bloccato con vendite.contratto BLOCCATO, dev.emittente con DEV_OPERATIVO, dev.multiveste; le vesti dev.portale1, dev.portale2, dev.fornitore e la veste portale di dev.multiveste, sul cliente 3: un ruolo cliente ha una sola veste portale attiva) e ne etichetta le radici in dbops.credenziali_di_prova e dbops.soggetti_di_prova (anche le persone degli operatori, DEV-PERSONA-<NOME>). Per prima cosa l''ambiente: fuori da SVILUPPO E_DATI_DI_SVILUPPO_IN_PRODUZIONE (dbops.fn_dati_di_sviluppo_ammessi_su_valori), non dichiarato E_CONFIG_MANCANTE. Idempotente per chiave: una radice etichettata si riallinea (vesti accese, profili riscritti su tutte le aree, whitelist su A, override, emittente attivo A, password se data); un omonimo senza etichetta (username, sigla di un emittente) e'' E_RADICE_DI_PROVA_SENZA_ETICHETTA. p_password_hash: username -> hash Django; assente alla nascita = password inutilizzabile, assente dopo = invariata. Scrive solo dai BB e dalle madri (vedi il changeSet); sue sono le etichette e la password di una credenziale riallineata. SECURITY DEFINER: e'' l''unico scrittore delle etichette. Le GUC app.current_user_id e app.current_emittente_id le governa lui (vuote per i BA, dev.smoke per i magazzini) e le rimette com''erano. Il secondo fattore lo fa il BE dopo: la colonna secondo_fattore dice chi deve averlo. Ritorna una riga per radice (tipo, chiave, radice_id, esito creata/riallineata, secondo_fattore). Brief: brief-db-processi-accensione-per-ambiente (R-4, 2b-3); brief-be-utenti-di-sviluppo §7. Rev 2026-10-18 (D-4 di Tid): gli indirizzi dei soggetti di prova passano a anagrafiche.fn_crea_indirizzo_soggetto in jsonb (contratto nuovo della madre).';
```

</div>

---
{% include-markdown "signature-core.md" %}
