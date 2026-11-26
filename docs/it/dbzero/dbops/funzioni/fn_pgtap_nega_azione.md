{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_nega_azione.md" %}
# ⚙️ Funzione `fn_pgtap_nega_azione`

```sql
CREATE FUNCTION fn_pgtap_nega_azione(p_auth_user_id integer, p_permission_codename character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_nega_azione(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: negare a un utente di fixture un'azione di processo, con un
--   override utente abilitata = false, valido da oggi e senza scadenza:
--   e' cosi' che un test costruisce il caso «azione negata», anche
--   quando il profilo la concede. Solo per i pgTAP.
-- Uso: PERFORM dbops.fn_pgtap_nega_azione(
--          (SELECT auth_user_id FROM _mondo), 'cambia_stato_commessa');
DECLARE
    v_azione_id   config.azioni_processo.id%TYPE;
    v_override_id config.user_override_azioni.id%TYPE;
BEGIN
    SELECT ap.id INTO v_azione_id
      FROM config.azioni_processo ap
     WHERE ap.permission_codename = p_permission_codename;

    IF v_azione_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_nega_azione: azione di processo % inesistente', p_permission_codename;
    END IF;

    PERFORM dbops.fn_pgtap_scrivi_override(
        'config.user_override_azioni'::regclass, p_auth_user_id,
        jsonb_build_object('azione_id', v_azione_id),
        jsonb_build_object('abilitata',  false,
                           'motivo',     'Fixture pgTAP: azione negata',
                           'valido_dal', (SELECT script.fn_data_operativa()),
                           'valido_al',  NULL));

    SELECT uoz.id INTO v_override_id
      FROM config.user_override_azioni uoz
     WHERE uoz.auth_user_id = p_auth_user_id
       AND uoz.azione_id    = v_azione_id;

    RETURN v_override_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_nega_azione(p_auth_user_id integer, p_permission_codename character varying)
IS 'Fixture pgTAP: nega a un utente un''azione di processo con un override (config.user_override_azioni, abilitata = false, valido da oggi senza scadenza), idempotente sulla UNIQUE (utente, azione): è così che un test costruisce il caso «azione negata», anche quando il profilo la concede. Lo scrive il verbo del SUPER_ADMIN config.fn_imposta_override_azioni, da dbops.fn_pgtap_scrivi_override: le altre voci dell''utente restano, i loro id cambiano. Ritorna l''id della riga. Gemello di dbops.fn_pgtap_concedi_azione, senza il tetto d''area. Azione inesistente -> RAISE. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
