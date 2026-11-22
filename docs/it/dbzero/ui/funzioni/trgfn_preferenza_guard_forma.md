{% include-markdown "it/dbzero/ui/manual/trgfn_preferenza_guard_forma.md" %}
# ⚙️ Funzione `trgfn_preferenza_guard_forma`

```sql
CREATE FUNCTION trgfn_preferenza_guard_forma()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preferenza_guard_forma()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la configurazione di una preferenza (ui.lista_preferenza_utente,
--   ui.dashboard_preferenza_utente) ha la forma ammessa, e sulle liste
--   la misura e' del catalogo.
-- Montaggio: BEFORE INSERT OR UPDATE OF configurazione e del contenitore,
--   FOR EACH ROW; la famiglia si legge dalla tabella.
DECLARE
    -- text: 'lista' o 'dashboard', dalla tabella; non il riflesso di una colonna
    v_famiglia text;
    -- il contenitore della riga, nuovo e vecchio (lista_id o dashboard_id, integer tutti e due)
    v_new_id   ui.lista_definizione.id%TYPE;
    v_old_id   ui.lista_definizione.id%TYPE;
    -- jsonb: il primo motivo {chiave, motivo}, o NULL
    v_motivo   jsonb;
BEGIN
    v_famiglia := CASE TG_RELID
                      WHEN 'ui.lista_preferenza_utente'::regclass     THEN 'lista'
                      WHEN 'ui.dashboard_preferenza_utente'::regclass THEN 'dashboard'
                  END;
    IF v_famiglia IS NULL OR TG_WHEN <> 'BEFORE' OR TG_LEVEL <> 'ROW'
       OR TG_OP NOT IN ('INSERT', 'UPDATE') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preferenza_utente o ui.dashboard_preferenza_utente'),
            NULL::uuid,
            format('%s: atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preferenza_utente o ui.dashboard_preferenza_utente',
                   TG_NAME));
    END IF;

    v_new_id := (to_jsonb(NEW) ->> (v_famiglia || '_id'))::integer;
    IF TG_OP = 'UPDATE' THEN
        v_old_id := (to_jsonb(OLD) ->> (v_famiglia || '_id'))::integer;
        IF NEW.configurazione IS NOT DISTINCT FROM OLD.configurazione
           AND v_new_id IS NOT DISTINCT FROM v_old_id THEN
            RETURN NEW;
        END IF;
    END IF;

    v_motivo := ui.fn_check_forma_configurazione(v_famiglia, v_new_id, NEW.configurazione);
    IF v_motivo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_UI_CONFIGURAZIONE_FORMA',
            jsonb_build_object(
                'campo',  'configurazione',
                'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',     NEW.id,
                'chiave', v_motivo ->> 'chiave',
                'motivo', v_motivo ->> 'motivo'),
            NULL::uuid,
            VARIADIC ARRAY[v_motivo ->> 'chiave', v_motivo ->> 'motivo']);
    END IF;

    IF v_famiglia = 'lista' THEN
        PERFORM ui.fn_guard_misura_pagina(NEW.configurazione -> 'pagina_dimensione');
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preferenza_guard_forma()
IS 'Il guard di forma delle preferenze utente (ui.lista_preferenza_utente, ui.dashboard_preferenza_utente; la famiglia dalla tabella). A ogni INSERT, e a ogni UPDATE che cambia la configurazione o la lista (la dashboard), chiede la forma a ui.fn_check_forma_configurazione e al primo motivo solleva E_UI_CONFIGURAZIONE_FORMA (DATO_ERRATO), con la chiave e il motivo nel contesto e nella frase, campo = configurazione. Sulle liste giudica poi la misura di pagina con ui.fn_guard_misura_pagina (E_UI_MISURA_PAGINA_NON_AMMESSA). Un UPDATE che riscrive la configurazione uguale (il riallineamento del banner, «Ignora») passa senza giudizio. Montata BEFORE INSERT OR UPDATE OF configurazione e del contenitore, fase a10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
