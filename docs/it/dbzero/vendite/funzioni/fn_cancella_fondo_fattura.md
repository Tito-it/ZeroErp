{% include-markdown "it/dbzero/vendite/manual/fn_cancella_fondo_fattura.md" %}
# ⚙️ Funzione `fn_cancella_fondo_fattura`

```sql
CREATE FUNCTION fn_cancella_fondo_fattura(p_source_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cancella_fondo_fattura(p_source_id bigint)
 RETURNS TABLE(deleted_righe integer, deleted_fondi integer, deleted_source integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: il gesto «cancella il fondo» dell'endpoint DELETE
    --   /api/v1/vendite/fondi-fattura/{id}/. Il permesso in prima
    --   riga, poi la primitiva, che fa tutto il resto (perimetro
    --   sull'atto, criterio, tre DELETE).
    -- ⭐ L'azione e' quella che l'endpoint controlla gia'
    --   (governa_fondo_fattura, risposta 3d §4.5): chi arriva dal
    --   backend non riceve un rifiuto nuovo.
    -- ⚠️ Le due GUC che dentro un verbo DEFINER aprirebbero una porta
    --   si spengono all'ingresso: quella delle righe contabili, e
    --   quella del reset del lotto, che col proprietario aprirebbe le
    --   porte dei guard della fattura.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('vendite.fn_cancella_fondo_fattura');
    PERFORM script.fn_guard_azione(v_utente, 'governa_fondo_fattura');

    PERFORM set_config('zeroerp.allow_contabile_riga_delete_override', '', true);
    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', '', true);

    RETURN QUERY
    SELECT p.deleted_righe, p.deleted_fondi, p.deleted_source
      FROM vendite.fn_applica_cancellazione_fondo_fattura(p_source_id) AS p;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cancella_fondo_fattura(p_source_id bigint)
IS 'Il verbo del gesto «cancella il fondo» (endpoint DELETE /api/v1/vendite/fondi-fattura/{id}/): SECURITY DEFINER, in prima riga script.fn_guard_azione con governa_fondo_fattura, la stessa azione dell''endpoint. Spegne all''ingresso la GUC delle righe contabili e quella del reset del lotto, poi chiama la primitiva vendite.fn_applica_cancellazione_fondo_fattura, che rimette il perimetro sull''atto (fuori: E_FONDO_NON_TROVATO), legge il criterio e fa i tre DELETE, oppure rifiuta dicendo perche''. Firma e risultato di sempre. brief-db-porte-aperte-dalla-sola-guc §13 (giro 8).';
```

</div>

---
{% include-markdown "signature-core.md" %}
