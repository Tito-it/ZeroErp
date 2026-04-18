# ⚙️ Funzione `trgfn_risorse_umane_auth_user_sync_identita`

```sql
CREATE FUNCTION trgfn_risorse_umane_auth_user_sync_identita()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_identita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_ruolo_id anagrafiche.risorse_umane.soggetto_ruolo_id%TYPE;
    v_valido_dal        anagrafiche.risorse_umane.valido_dal%TYPE;
    v_valido_al         anagrafiche.risorse_umane.valido_al%TYPE;
    v_identita_id       anagrafiche.identita_digitali.id%TYPE;
    v_identita_attiva   boolean;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger-ponte temporaneo (§4.6.D.4 WIP multi-face-auth)
    -- Propaga RUA -> identita_digitali (OPERATORE).
    -- ------------------------------------------------------------

    -- Risolvo soggetto_ruolo_id e finestra dal record RU parent.
    -- NOTA: RUA.risorsa_umana_id -> RU.soggetto_ruolo_id.
    SELECT ru.soggetto_ruolo_id, ru.valido_dal, ru.valido_al
      INTO v_soggetto_ruolo_id, v_valido_dal, v_valido_al
      FROM anagrafiche.risorse_umane ru
     WHERE ru.id = NEW.risorsa_umana_id;

    -- Stato attivo identita: composto (RUA.attivo AND ruolo!=DISABILITATO).
    v_identita_attiva := (NEW.attivo AND NEW.ruolo_sistema <> 'DISABILITATO'::config.ruolo_sistema);

    -- UPSERT identita_digitali OPERATORE.
    -- ON CONFLICT su UNIQUE auth_user_id (indice totale).
    INSERT INTO anagrafiche.identita_digitali (
        soggetto_ruolo_id,
        auth_user_id,
        ruolo_applicativo,
        attivo,
        valido_dal,
        valido_al,
        deve_cambiare_password,
        invito_inviato_at,
        tentativi_falliti,
        bloccato_fino_a,
        totp_obbligatorio,
        storicizza
    )
    VALUES (
        v_soggetto_ruolo_id,
        NEW.auth_user_id,
        'OPERATORE'::config.ruolo_applicativo,
        v_identita_attiva,
        COALESCE(v_valido_dal, CURRENT_DATE),
        v_valido_al,
        COALESCE(NEW.deve_cambiare_password, false),
        NEW.invito_inviato_at,
        COALESCE(NEW.tentativi_falliti, 0),
        NEW.bloccato_fino_a,
        COALESCE(NEW.totp_obbligatorio, false),
        COALESCE(NEW.storicizza, true)
    )
    ON CONFLICT (auth_user_id) DO UPDATE
       SET soggetto_ruolo_id      = EXCLUDED.soggetto_ruolo_id,
           attivo                 = EXCLUDED.attivo,
           valido_dal             = EXCLUDED.valido_dal,
           valido_al              = EXCLUDED.valido_al,
           deve_cambiare_password = EXCLUDED.deve_cambiare_password,
           invito_inviato_at      = EXCLUDED.invito_inviato_at,
           tentativi_falliti      = EXCLUDED.tentativi_falliti,
           bloccato_fino_a        = EXCLUDED.bloccato_fino_a,
           totp_obbligatorio      = EXCLUDED.totp_obbligatorio,
           storicizza             = EXCLUDED.storicizza
    RETURNING id INTO v_identita_id;

    -- Sync binding SUPER_ADMIN col ruolo_sistema.
    IF NEW.ruolo_sistema = 'ADMIN'::config.ruolo_sistema THEN
        -- INSERT se non esiste (NOT EXISTS per gestire l'indice
        -- parziale UNIQUE su identita_digitale_id).
        INSERT INTO config.profili_accesso_bindings (
            profilo_accesso_id, identita_digitale_id, attivo
        )
        SELECT 9100, v_identita_id, true
         WHERE NOT EXISTS (
             SELECT 1 FROM config.profili_accesso_bindings pab
              WHERE pab.identita_digitale_id = v_identita_id
         );

        -- Riattiva binding se esisteva ma era inattivo.
        UPDATE config.profili_accesso_bindings
           SET attivo = true
         WHERE identita_digitale_id = v_identita_id
           AND profilo_accesso_id = 9100
           AND attivo = false;
    ELSE
        -- DELETE binding SUPER_ADMIN se esistente (l'utente
        -- ha perso il privilegio di bypass).
        DELETE FROM config.profili_accesso_bindings
         WHERE identita_digitale_id = v_identita_id
           AND profilo_accesso_id = 9100;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_identita()
IS 'Trigger-ponte temporaneo (§4.6.D.4 WIP): propaga INSERT/UPDATE RUA -> identita_digitali OPERATORE e sincronizza binding SUPER_ADMIN (9100) col ruolo_sistema. Rimovibile al cutover §4.6.H.3 quando il bridge legacy viene eliminato.';
```

---
{% include-markdown "signature-core.md" %}
