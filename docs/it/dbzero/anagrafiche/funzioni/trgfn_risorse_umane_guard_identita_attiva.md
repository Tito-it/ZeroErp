{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_guard_identita_attiva.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_guard_identita_attiva`

```sql
CREATE FUNCTION trgfn_risorse_umane_guard_identita_attiva()
```

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
    -- Solo la transizione attivo true -> false.
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
         WHERE id.soggetto_ruolo_id = NEW.soggetto_ruolo_id
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
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id),
                NULL::uuid,
                v_username);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_guard_identita_attiva()
IS 'Guard (BEFORE UPDATE OF attivo su risorse_umane): rifiuta attivo true->false se esiste un''identita_digitali OPERATORE attiva sullo stesso soggetto_ruolo_id — E_RISORSA_UMANA_IDENTITA_ATTIVA (CONFLITTO_STATO), nel VARIADIC lo username. Scritto a mano perche'' il legame non e'' una FK e l''automazione ATTIVO non lo vede; sostituisce il guard che leggeva la vista risorse_umane_auth_user (ritirata il 12-09-2026).';
```

</div>

---
{% include-markdown "signature-core.md" %}
