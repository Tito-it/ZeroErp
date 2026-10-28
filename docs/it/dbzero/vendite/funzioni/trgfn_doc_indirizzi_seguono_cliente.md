# ⚙️ Funzione `trgfn_doc_indirizzi_seguono_cliente`

```sql
CREATE FUNCTION trgfn_doc_indirizzi_seguono_cliente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: il selettore del montaggio (TG_ARGV).
    v_documento text := TG_ARGV[0];
    v_schema    pg_catalog.pg_namespace.nspname%TYPE;
    v_tabella   pg_catalog.pg_class.relname%TYPE;
    v_fk_col    pg_catalog.pg_attribute.attname%TYPE;
    v_ruolo     anagrafiche.soggetti_ruoli.id%TYPE;
    v_istanza   anagrafiche.indirizzi.istanza_utility_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il cliente del documento e' cambiato: gli indirizzi presi
    --   dall'anagrafica del cliente di prima non valgono piu'.
    --   Si tolgono, e lo slot di default si riempie dal nuovo.
    -- =========================================================
    SELECT s.schema_tabella, s.tabella, s.colonna_fk
      INTO v_schema, v_tabella, v_fk_col
      FROM script.fn_doc_indirizzi_sede(v_documento) AS s;

    IF v_tabella IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('trigger',   TG_NAME,
                               'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'documento', v_documento),
            NULL::uuid,
            COALESCE(v_documento, '<null>'));
    END IF;

    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      INTO v_ruolo, v_istanza
      FROM script.fn_get_cliente_testata_documento(v_documento, NEW.id) AS c;

    -- 1. Via le righe d'anagrafica che non sono del cliente nuovo.
    --    Gli una-tantum il predicato li lascia (NULL).
    EXECUTE format(
        'DELETE FROM %I.%I x '
        ' WHERE x.%I = $1 '
        '   AND script.fn_indirizzo_documento_fuori_cliente('
        '           x.origine_indirizzo_id, x.origine_soggetto_ruolo_id, $2, $3) IS NOT NULL',
        v_schema, v_tabella, v_fk_col)
      USING NEW.id, v_ruolo, v_istanza;

    -- 2. Lo slot di default, se e' rimasto vuoto.
    PERFORM vendite.fn_doc_indirizzo_default(v_documento, NEW.id);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_indirizzi_seguono_cliente()
IS 'Building block AFTER UPDATE FOR EACH ROW sulle testate il cui cliente si cambia in bozza (DDT: billing_account_id, destinatario_soggetto_ruolo_id; preventivo, offerta, contratto: billing_account_id, istanza_utility_id — nel WHEN del montaggio), TG_ARGV[0] = documento. Toglie le righe d''anagrafica che non sono del cliente nuovo (script.fn_indirizzo_documento_fuori_cliente, lo stesso predicato del guard vendite.trgfn_doc_indirizzi_guard_cliente e del motivo d''emissione); gli una-tantum restano. Poi riempie lo slot di default rimasto vuoto (vendite.fn_doc_indirizzo_default). Il cliente lo rilegge script.fn_get_cliente_testata_documento sulla riga finale. ⚠️ Il cliente si cambia solo in bozza (lock di testata), quindi il lock dei satelliti lascia passare. L''ordine non lo monta: il suo cliente non cambia mai (E_ORD_CLIENTE_IMMUTABILE). Brief: brief-db-indirizzi-documento-seguono-il-cliente (§5.3, D-1, D-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
