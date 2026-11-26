{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_guard_identita_attiva.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_guard_identita_attiva`

```sql
CREATE FUNCTION trgfn_risorse_umane_guard_identita_attiva()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_guard_identita_attiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⛔ Tipo ESPLICITO e non %TYPE: la colonna e' di django.auth_user, e in CI
    --    Liquibase gira PRIMA delle migrazioni Django — al CREATE lo schema
    --    django non esiste, e un %TYPE si risolve proprio al CREATE. Il DB puo'
    --    CHIAMARE dentro django.* (il SELECT sotto e' late-bound, plpgsql), non
    --    DIPENDERNE. Provato in CI il 12-09: «lo schema "django" non esiste».
    v_username text;
BEGIN
    -- ------------------------------------------------------------
    -- Guard: una risorsa umana con un'identita' OPERATORE ancora
    -- attiva non si disattiva («figli prima, padre poi»). Il legame
    -- risorsa umana -> identita' passa da soggetto_ruolo_id, non da
    -- una FK: per questo il guard e' scritto a mano e non generato.
    -- Solo la transizione attivo true -> false. La veste si cerca
    -- sul ruolo di prima E su quello nuovo: uno spegnimento che
    -- nella stessa scrittura sposta il ruolo non la lascia accesa
    -- su quello di prima.
    -- ------------------------------------------------------------
    IF TG_OP = 'UPDATE'
       AND COALESCE(OLD.attivo, false) IS TRUE
       AND COALESCE(NEW.attivo, false) IS FALSE
    THEN
        SELECT au.username
          INTO v_username
          FROM anagrafiche.identita_digitali id
          JOIN django.auth_user au
            ON au.id = id.auth_user_id
         WHERE id.soggetto_ruolo_id IN (OLD.soggetto_ruolo_id, NEW.soggetto_ruolo_id)
           AND id.ruolo_applicativo = 'OPERATORE'
           AND id.attivo            = true
         ORDER BY id.id
         LIMIT 1;

        IF FOUND THEN
            -- campo -> il frontend (quale interruttore accendere);
            -- VARIADIC -> l'operatore (chi e' l'utente ancora attivo).
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche',
                'trgfn_risorse_umane_guard_identita_attiva',
                'E_RISORSA_UMANA_IDENTITA_ATTIVA',
                jsonb_build_object(
                    'campo',             'attivo',
                    'risorsa_umana_id',  NEW.id,
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                    'soggetto_ruolo_id_prima', OLD.soggetto_ruolo_id),
                NULL::uuid,
                v_username);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_guard_identita_attiva()
IS 'Guard BEFORE UPDATE OF attivo su anagrafiche.risorse_umane: rifiuta attivo true -> false se c''e'' ancora una veste OPERATORE accesa sul soggetto_ruolo_id del rapporto, quello di prima o quello nuovo della stessa scrittura: E_RISORSA_UMANA_IDENTITA_ATTIVA (CONFLITTO_STATO), nel VARIADIC lo username. Si spegne prima la veste, poi il rapporto. Scritto a mano perche'' il legame fra rapporto e veste passa dal ruolo anagrafico e non da una FK, e l''automazione ATTIVO non lo vede.';
```

</div>

---
{% include-markdown "signature-core.md" %}
