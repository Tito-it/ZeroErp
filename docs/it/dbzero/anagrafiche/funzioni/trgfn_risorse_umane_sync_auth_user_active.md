{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_sync_auth_user_active.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_sync_auth_user_active`

```sql
CREATE FUNCTION trgfn_risorse_umane_sync_auth_user_active()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_sr_nuovo     anagrafiche.risorse_umane.soggetto_ruolo_id%TYPE;
    v_sr_prima     anagrafiche.risorse_umane.soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: dopo una scrittura sul rapporto, allinea
    --   auth_user.is_active di ogni credenziale con una veste
    --   OPERATORE sul ruolo del rapporto (e sul ruolo di prima,
    --   se e' cambiato o se il rapporto se n'e' andato).
    -- =========================================================
    IF TG_OP <> 'DELETE' THEN
        v_sr_nuovo := NEW.soggetto_ruolo_id;
    END IF;
    IF TG_OP <> 'INSERT' THEN
        v_sr_prima := OLD.soggetto_ruolo_id;
    END IF;

    FOR v_auth_user_id IN
        SELECT DISTINCT idg.auth_user_id
          FROM anagrafiche.identita_digitali idg
         WHERE idg.ruolo_applicativo = 'OPERATORE'
           AND idg.soggetto_ruolo_id IN (v_sr_nuovo, v_sr_prima)
         ORDER BY idg.auth_user_id
    LOOP
        PERFORM anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id);
    END LOOP;

    RETURN NULL;  -- AFTER: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
IS 'Trigger AFTER INSERT, UPDATE e DELETE su anagrafiche.risorse_umane: il rapporto decide se la veste OPERATORE di una persona e'' utilizzabile (script.fn_veste_utilizzabile), quindi a ogni nascita, cambio di attivo, date o ruolo, e cancellazione allinea django.auth_user.is_active di ogni credenziale con una veste OPERATORE sul ruolo del rapporto e sul ruolo di prima, con anagrafiche.fn_sync_auth_user_is_active. Le date che arrivano senza scritture le riallinea anagrafiche.fn_sync_auth_user_expired.';
```

</div>

---
{% include-markdown "signature-core.md" %}
