{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_concedi_azione.md" %}
# ⚙️ Funzione `fn_pgtap_concedi_azione`

```sql
CREATE FUNCTION fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: concedere a un utente di fixture un'azione di processo, con un
--   override utente valido da oggi e senza scadenza. Solo per i pgTAP.
-- Uso: PERFORM dbops.fn_pgtap_concedi_azione(
--          (SELECT auth_user_id FROM _mondo), 'registra_magazzino');
DECLARE
    v_azione_id   config.azioni_processo.id%TYPE;
    v_override_id config.user_override_azioni.id%TYPE;
BEGIN
    SELECT ap.id
      INTO v_azione_id
      FROM config.azioni_processo ap
     WHERE ap.permission_codename = p_permission_codename;

    IF v_azione_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_concedi_azione: azione di processo % inesistente', p_permission_codename;
    END IF;

    INSERT INTO config.user_override_azioni
           (auth_user_id, azione_id, abilitata, motivo, valido_dal, valido_al)
    VALUES (p_auth_user_id, v_azione_id, true, 'Fixture pgTAP', CURRENT_DATE, NULL)
    ON CONFLICT ON CONSTRAINT uq_user_override_azioni_user_azione
    DO UPDATE SET abilitata  = true,
                  valido_dal = CURRENT_DATE,
                  valido_al  = NULL
    RETURNING id INTO v_override_id;

    RETURN v_override_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_concedi_azione(p_auth_user_id integer, p_permission_codename character varying)
IS 'Fixture pgTAP: concede un''azione di processo a un utente con un override (config.user_override_azioni, abilitata, valido da oggi senza scadenza), idempotente sulla UNIQUE (utente, azione). Serve ai pgTAP dei verbi che applicano un''azione con script.fn_guard_azione: l''operatore di fn_pgtap_crea_emittente_operatore non ne ha. Azione inesistente -> RAISE. Solo per i pgTAP (brief-db-magazzino-verbi-con-permesso §3.2).';
```

---
{% include-markdown "signature-core.md" %}
