{% include-markdown "it/dbzero/vendite/manual/fn_provision_registri_famiglia.md" %}
# ⚙️ Funzione `fn_provision_registri_famiglia`

```sql
CREATE FUNCTION fn_provision_registri_famiglia(p_famiglia_documento character varying)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provision_registri_famiglia(p_famiglia_documento character varying)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dare a UNA famiglia il suo registro su tutti gli
    --   emittenti che ancora non ce l'hanno, e dire quanti ne ha
    --   creati.
    --
    -- ⛔ Perche' serve: senza, una famiglia creata dal CRUD
    --   nasce senza registri, e i suoi documenti non si numerano.
    --   Il fail-closed di fn_get_registro_documento lo direbbe,
    --   ma al primo documento — non alla creazione.
    --
    -- ⚠️ Una famiglia NON ATTIVA non provisiona niente: il filtro
    --   sta nella primitiva (`fd.attivo IS TRUE`), e qui non si
    --   ripete. Una famiglia spenta non deve far nascere registri.
    -- =========================================================
    IF p_famiglia_documento IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_provision_registri_famiglia',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_famiglia_documento'),
            NULL::uuid,
            'vendite.fn_provision_registri_famiglia',
            'codice della famiglia di documento non valorizzato');
    END IF;

    RETURN vendite.fn_provision_registri(
               p_emittente_soggetto_ruolo_id => NULL,
               p_famiglia_documento          => p_famiglia_documento);
END;
$function$

COMMENT ON FUNCTION vendite.fn_provision_registri_famiglia(p_famiglia_documento character varying)
IS 'Da a UNA famiglia di documento il suo registro di numerazione su tutti gli emittenti fiscali che ancora non ce l''hanno, e torna quanti ne ha creati. ⛔ E'' la gemella che mancava: il provisioning esisteva solo per emittente (trigger su anagrafiche.emittenti_fiscali), quindi una famiglia nuova nasceva senza registri e i suoi documenti non si numeravano — il fail-closed di fn_get_registro_documento lo dice, ma al primo documento, non alla creazione. La chiama la madre vendite.fn_crea_famiglia_documento. ⭐ INVOLUCRO SOTTILE: la regola sta nella primitiva vendite.fn_provision_registri, qui c''e'' solo il filtro. ⚠️ Una famiglia NON ATTIVA non provisiona niente, e il filtro sta nella primitiva: una famiglia spenta non deve far nascere registri. ⚠️ A differenza della gemella per emittente, un parametro NULL qui SOLLEVA: nessun trigger la chiama a tappeto, ci arriva chi ha deciso di provisionare una famiglia precisa, e un NULL li'' e'' un chiamante rotto. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.6 (DB-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
