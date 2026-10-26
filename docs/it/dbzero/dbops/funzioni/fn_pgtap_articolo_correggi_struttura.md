{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_articolo_correggi_struttura.md" %}
# ⚙️ Funzione `fn_pgtap_articolo_correggi_struttura`

```sql
CREATE FUNCTION fn_pgtap_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_utente_prima text := current_setting('app.current_user_id', true);
    v_ruolo_prima  text := current_setting('app.ruolo_applicativo', true);
    v_admin        integer;
BEGIN
    -- Scopo: cambiare i flag strutturali di un articolo usato
    --   dalla porta vera (verbo + SUPER_ADMIN), poi tornare al
    --   contesto di prima. Solo per fixture pgTAP.
    SELECT o.auth_user_id INTO v_admin
      FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP correggi struttura', true) o;

    PERFORM script.fn_pgtap_set_contesto_operatore(v_admin);
    PERFORM catalogo.fn_articolo_correggi_struttura(p_articolo_id, p_campi);

    PERFORM set_config('app.current_user_id',   COALESCE(v_utente_prima, ''), false);
    PERFORM set_config('app.ruolo_applicativo', COALESCE(v_ruolo_prima, ''),  false);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
IS 'Builder pgTAP (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): cambia i flag strutturali di un articolo gia'' usato dalla porta vera, catalogo.fn_articolo_correggi_struttura, come un SUPER_ADMIN costruito (dbops.fn_pgtap_crea_operatore_umano(.., true)), poi rimette app.current_user_id e app.ruolo_applicativo di chi chiama (anche vuoti). INVOKER: non aggira niente. Per i test che provano cosa succede a valle quando un articolo cambia dopo l''uso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
