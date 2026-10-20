{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_sync_auth_user_active.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_sync_auth_user_active`

```sql
CREATE FUNCTION trgfn_identita_digitali_sync_auth_user_active()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE per coerenza automatica con la colonna sorgente.
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger function: trgfn_identita_digitali_sync_auth_user_active
    --
    -- Scopo:
    --   A seguito di INSERT o UPDATE di colonne rilevanti su
    --   identita_digitali, propaga lo stato a django.auth_user
    --   invocando la funzione sync centralizzata.
    --
    -- Evento: AFTER INSERT / AFTER UPDATE OF attivo, valido_dal,
    --         valido_al, ruolo_applicativo, auth_user_id
    -- Tabella: anagrafiche.identita_digitali
    --
    -- Scelta di passare NEW.auth_user_id in entrambi i casi
    -- (INSERT e UPDATE). Sul DELETE non scattiamo: il caso
    -- "eliminazione identita" e' atipico (preferiamo disattivare
    -- via attivo=false). Se necessario, aggiungere un trigger
    -- AFTER DELETE dedicato che chiami con OLD.auth_user_id.
    -- ------------------------------------------------------------

    v_auth_user_id := NEW.auth_user_id;

    -- La funzione sync gestisce internamente i casi edge
    -- (ruolo DISABILITATO, finestra scaduta, ecc.) e aggiorna
    -- auth_user.is_active solo se cambia.
    PERFORM anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id);

    RETURN NULL; -- AFTER trigger: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato/finestra/ruolo su anagrafiche.identita_digitali. Delega a fn_sync_auth_user_is_active(auth_user_id). Copre tutti i ruoli applicativi (§4.5.3 WIP multi-face-auth); il gemello su risorse_umane (trgfn_risorse_umane_sync_auth_user_active) risolve l''utente dalla stessa madre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
