{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_risorsa_umana_v2.md" %}
# ⚙️ Funzione `fn_crea_risorsa_umana_v2`

```sql
CREATE FUNCTION fn_crea_risorsa_umana_v2(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_risorsa_umana_v2(p_soggetto_id uuid DEFAULT NULL::uuid, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date, p_auth_user_id integer DEFAULT NULL::integer, p_is_super_admin boolean DEFAULT false, p_attivo boolean DEFAULT true)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sr_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_ru_id        anagrafiche.risorse_umane.id%TYPE;
    v_identita_id  anagrafiche.identita_digitali.id%TYPE;
    v_profilo_sa   config.profili_accesso_bindings.profilo_accesso_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo (v2 multi-face native, Chunk A Fase 7 2026-04-29):
    --   Crea risorsa_umana + identita_digitali OPERATORE
    --   (+ binding SUPER_ADMIN se p_is_super_admin=true).
    --   Niente piu' enum legacy ruolo_sistema; il chiamante
    --   esprime direttamente "is super admin?" + "attiva?".
    --
    -- Body identico a v1 salvo:
    --   Step 3: identita_digitali.attivo = p_attivo
    --           (era hardcoded true in v1).
    --   Step 4: IF p_is_super_admin invece di
    --           IF p_ruolo_sistema='ADMIN'.
    -- =========================================================

    -- Validazione parametri obbligatori
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid, 'Soggetto obbligatorio.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_qualifica_id'),
            NULL::uuid, 'Qualifica obbligatoria.'
        );
    END IF;

    -- Guard prerequisiti
    IF NOT EXISTS (
        SELECT 1 FROM config.qualifiche
         WHERE id = p_qualifica_id AND attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('qualifica_id', p_qualifica_id),
            NULL::uuid, 'Qualifica non trovata o non attiva.'
        );
    END IF;

    IF p_unita_organizzativa_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM config.unita_organizzative
             WHERE id = p_unita_organizzativa_id AND attivo = true
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
                'E_ADMIN_UO_NON_TROVATA',
                jsonb_build_object('campo', 'unita_organizzativa_id', 'unita_organizzativa_id', p_unita_organizzativa_id),
                NULL::uuid,
                'Unita'' organizzativa non trovata o non attiva.'
            );
        END IF;
    END IF;

    IF p_auth_user_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM django.auth_user WHERE id = p_auth_user_id
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid, 'auth_user non trovato.'
            );
        END IF;
    END IF;

    -- ⛔ Il profilo SUPER_ADMIN si RISOLVE, non si scrive (rev 20260923-10):
    --   per tipo, fra i profili attivi, esattamente uno, PRIMA di ogni
    --   scrittura. ⭐ Dal 20261019-17 la regola sta nel lettore
    --   config.fn_profilo_super_admin_id (R-BE-11, regola del 2): era scritta
    --   qui e nel backend.
    IF p_is_super_admin AND p_auth_user_id IS NOT NULL THEN
        v_profilo_sa := config.fn_profilo_super_admin_id();
    END IF;

    -- Step 1: soggetto_ruolo RIS_UMANA
    SELECT script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id, 'RIS_UMANA'
    ) INTO v_sr_id;

    -- ⛔ Una persona e' una risorsa umana sola (uq_risorse_umane_soggetto_ruolo,
    --   non parziale: vale anche per una risorsa spenta). Senza questo guard il
    --   secondo operatore sullo stesso soggetto arrivava al client come 23505,
    --   E_DATABASE. Il rimedio e' sulla risorsa che c'e' (reinvito, riattivazione),
    --   non una seconda. (rev 20261002-01)
    -- ⚠️ Il controllo e' sulla CHIAVE del vincolo (soggetto_ruolo_id), non su
    --   attivo: una risorsa disattivata occupa lo slot come una attiva.
    -- ⚠️ Il segnaposto e' la frase dell'operatore: ragione_sociale_completa e'
    --   nullable, quindi si ripiega su nome e cognome, poi su «Il soggetto» —
    --   mai una frase con un buco al posto del nome.
    IF EXISTS (
        SELECT 1 FROM anagrafiche.risorse_umane ru
         WHERE ru.soggetto_ruolo_id = v_sr_id
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
            'E_RISORSA_UMANA_GIA_PRESENTE',
            jsonb_build_object('campo',             'soggetto_id',
                               'soggetto_id',       p_soggetto_id,
                               'soggetto_ruolo_id', v_sr_id),
            NULL::uuid,
            COALESCE(
                (SELECT COALESCE(NULLIF(btrim(s.ragione_sociale_completa), ''),
                                 NULLIF(btrim(concat_ws(' ', s.nome, s.cognome)), ''),
                                 NULLIF(btrim(s.ragione_sociale), ''))
                   FROM anagrafiche.soggetti s
                  WHERE s.id = p_soggetto_id),
                'Il soggetto'));
    END IF;

    -- Step 2: risorsa umana
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id, soggetto_id, qualifica_id,
        unita_organizzativa_id, valido_dal, valido_al, attivo
    )
    VALUES (
        v_sr_id, p_soggetto_id, p_qualifica_id,
        p_unita_organizzativa_id, p_valido_dal, p_valido_al, true
    )
    RETURNING id INTO v_ru_id;

    -- Step 3: identita_digitali OPERATORE.
    -- Differenza vs v1: attivo = p_attivo (default true).
    IF p_auth_user_id IS NOT NULL THEN
        INSERT INTO anagrafiche.identita_digitali (
            soggetto_ruolo_id,
            auth_user_id,
            ruolo_applicativo,
            attivo,
            valido_dal,
            valido_al
        )
        VALUES (
            v_sr_id,
            p_auth_user_id,
            'OPERATORE'::config.ruolo_applicativo,
            p_attivo,
            COALESCE(p_valido_dal, (SELECT script.fn_data_operativa())),
            p_valido_al
        )
        RETURNING id INTO v_identita_id;

        -- Step 4: binding SUPER_ADMIN se richiesto, sul profilo
        -- risolto nei guard (rev 20260923-10: era l'id 9100 cablato).
        -- Differenza vs v1: predicato boolean diretto invece
        -- di confronto con enum legacy.
        IF p_is_super_admin THEN
            -- rev 2026-10-18: il BB del binding (regola del 2);
            -- attivo = true e' il DEFAULT della colonna.
            PERFORM config.fn_lega_profilo_identita(v_profilo_sa, v_identita_id);
        END IF;
    END IF;

    RETURN v_ru_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_risorsa_umana_v2(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
IS 'Building block multi-face native (v2 Chunk A Fase 7 2026-04-29). Sostituisce v1 (firma con p_ruolo_sistema config.ruolo_sistema) con p_is_super_admin/p_attivo. Body invariato salvo: identita_digitali.attivo=p_attivo (era hardcoded true) e binding SUPER_ADMIN gated su p_is_super_admin invece di p_ruolo_sistema=ADMIN. v1 droppata in Chunk B post BE migrato. ⛔ Rev 20260923-10: il profilo del binding SUPER_ADMIN si RISOLVE per config.profili_accesso.tipo = SUPER_ADMIN fra i profili attivi (chiave stabile, linee-guida-sql §6d), non piu'' con l''id cablato 9100; se i profili attivi di quel tipo non sono esattamente uno solleva E_CONFIG_MANCANTE prima di ogni scrittura. ⛔ Rev 20261002-01: una persona e'' una risorsa umana sola (uq_risorse_umane_soggetto_ruolo, anche spenta): se il soggetto lo e'' gia'' solleva E_RISORSA_UMANA_GIA_PRESENTE (campo soggetto_id) invece di lasciar arrivare il 23505; vale per ogni chiamante, non solo per fn_crea_operatore_v2. Rev 2026-10-18: il binding SUPER_ADMIN lo scrive il BB config.fn_lega_profilo_identita (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 8); comportamento invariato. ⭐ Rev 2026-10-18 (20261019-17, R-BE-11, regola del 2): il profilo SUPER_ADMIN lo risolve config.fn_profilo_super_admin_id, sede unica della regola che era scritta qui e nel backend; la firma si ancora con %TYPE. Comportamento invariato.';
```

---
{% include-markdown "signature-core.md" %}
