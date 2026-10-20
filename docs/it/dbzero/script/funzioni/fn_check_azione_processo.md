{% include-markdown "it/dbzero/script/manual/fn_check_azione_processo.md" %}
# ⚙️ Funzione `fn_check_azione_processo`

```sql
CREATE FUNCTION fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_abilitata config.user_override_azioni.abilitata%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica azione di processo abilitata per l'utente.
    --
    -- Catena (rev 20261004-55, brief-db-permessi-tetto-area):
    --   la legge da script.fn_get_permessi_effettivi_azioni, sede
    --   unica: gate di contesto, identita' OPERATORE attiva, super
    --   admin (prima del tetto), override -> profilo -> negata, poi
    --   il TETTO D'AREA: l'area dell'azione deve arrivare al suo
    --   livello_minimo_area (script.fn_area_consente_azione).
    -- =========================================================

    -- Un codename NULL non e' un'azione: negata. Senza questa riga la
    -- sede comune lo leggerebbe come «tutto il catalogo».
    IF p_permission_codename IS NULL THEN
        RETURN false;
    END IF;

    -- Una riga sempre, anche per un codename fuori catalogo (negata).
    SELECT e.abilitata
      INTO v_abilitata
      FROM script.fn_get_permessi_effettivi_azioni(
               p_auth_user_id, p_permission_codename) e;

    RETURN COALESCE(v_abilitata, false);
END
$function$

COMMENT ON FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
IS 'Verifica se un''azione di processo e'' abilitata per un utente. Legge la catena da script.fn_get_permessi_effettivi_azioni (sede unica, con fn_get_user_actions_map e il pannello permessi): gate di contesto (app.ruolo_applicativo valorizzata e diversa da OPERATORE -> false), identita'' OPERATORE attiva, super admin -> true (prima del tetto), override utente valido, ereditato dal profilo, default negata; poi il TETTO D''AREA: l''azione vale solo se il livello dell''area dell''azione arriva al suo livello_minimo_area (script.fn_area_consente_azione). Codename NULL -> false. Rev 20261004-55 (brief-db-permessi-tetto-area R2): l''area e'' un tetto, anche sul profilo (D-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
