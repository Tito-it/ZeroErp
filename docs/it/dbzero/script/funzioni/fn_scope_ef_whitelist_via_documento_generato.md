# ⚙️ Funzione `fn_scope_ef_whitelist_via_documento_generato`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del documento generato a cui la riga
    --   appartiene.
    -- ⭐ Delega alla CANONICA, non a un altro adattatore: la
    --   testata porta `emittente_fiscale_id` NOT NULL, quindi la
    --   risalita e' di un anello solo — ed e' esattamente cio'
    --   che fa rls_documenti_generati_ef_whitelist, cosi' il
    --   satellite e la testata non possono divergere.
    -- ⚠️ Documento inesistente -> emittente NULL -> la canonica
    --   risponde false quando la whitelist e' valorizzata:
    --   fail-closed, come tutta la famiglia.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT dg.emittente_fiscale_id
           FROM documenti.documenti_generati dg
          WHERE dg.id = p_documento_generato_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_documento_generato(p_auth_user_id integer, p_documento_generato_id bigint)
IS 'Adattatore di scope per i satelliti di documenti.documenti_generati (documenti_generati_eventi, documenti_generati_file): risale da documento_generato_id all''emittente_fiscale_id (NOT NULL) e delega a script.fn_scope_ef_whitelist — la CANONICA, la stessa che protegge la testata, cosi'' il satellite e il documento non possono divergere. ⛔ Non _via_sr e non _via_efba: questa testata nomina l''emittente per emittente fiscale, e le tre hanno la stessa firma (integer, bigint) — scambiarle compila, gira e confronta due numerazioni diverse, cioe'' risponde quasi sempre false. STABLE e NON security definer, come gli altri fn_scope_*. Documento inesistente -> emittente NULL -> false a whitelist valorizzata (fail-closed). ⚠️ documenti_generati_file porta storage_key, file_name e sha256: fuori perimetro non si leggono metadati, si leggono le coordinate del PDF di un''altra azienda. Brief: brief-db-perimetro-emittente-righe-documento.md §11.16';
```

---
{% include-markdown "signature-core.md" %}
