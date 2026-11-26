{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_ba_padre.md" %}
# ⚙️ Funzione `fn_check_ba_padre`

```sql
CREATE FUNCTION fn_check_ba_padre(p_billing_account_id bigint, p_codice character varying, p_parent_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_ba_padre(p_billing_account_id bigint, p_codice character varying, p_parent_account_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    -- l'array dei motivi: nessuna colonna dietro
    v_motivi       jsonb := '[]'::jsonb;
    v_padre_padre  anagrafiche.billing_account.parent_account_id%TYPE;
    v_padre_codice anagrafiche.billing_account.codice%TYPE;
    v_altro_codice anagrafiche.billing_account.codice%TYPE;
BEGIN
    IF p_parent_account_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT ba.parent_account_id, ba.codice
      INTO v_padre_padre, v_padre_codice
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_parent_account_id;

    -- Il padre proposto ha gia' un padre.
    IF v_padre_padre IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',    'E_PARENT_CON_PADRE',
            'dettaglio', jsonb_build_object(
                             'billing_account_id', p_billing_account_id,
                             'parent_account_id',  p_parent_account_id,
                             'padre_del_padre_id', v_padre_padre),
            'valori',    jsonb_build_array(
                             COALESCE(v_padre_codice, p_parent_account_id::text)));
    END IF;

    -- Il BA fa gia' da padre.
    IF EXISTS (SELECT 1 FROM anagrafiche.billing_account f
                WHERE f.parent_account_id = p_billing_account_id) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',    'E_PARENT_HA_FIGLI',
            'dettaglio', jsonb_build_object(
                             'billing_account_id', p_billing_account_id,
                             'parent_account_id',  p_parent_account_id),
            'valori',    jsonb_build_array(
                             COALESCE(p_codice, p_billing_account_id::text)));
    END IF;

    -- Un altro padre dello stesso cliente sulla stessa azienda.
    -- «Stesso cliente» come nel guard del padre (2.2): la stessa
    -- identita' fiscale, o lo stesso soggetto.
    SELECT q.codice
      INTO v_altro_codice
      FROM anagrafiche.billing_account p
      JOIN anagrafiche.istanze_utilities ip ON ip.id = p.istanza_utility_id
      JOIN anagrafiche.soggetti sp          ON sp.id = ip.soggetto_id
      JOIN anagrafiche.billing_account q    ON q.id <> p.id
      JOIN anagrafiche.istanze_utilities iq ON iq.id = q.istanza_utility_id
      JOIN anagrafiche.soggetti sq          ON sq.id = iq.soggetto_id
     WHERE p.id = p_parent_account_id
       AND (sq.id = sp.id
            OR (sp.id_fiscale_univoco_cf_piva IS NOT NULL
                AND sq.id_fiscale_univoco_cf_piva = sp.id_fiscale_univoco_cf_piva))
       AND EXISTS (SELECT 1 FROM anagrafiche.billing_account f
                    WHERE f.parent_account_id = q.id
                      AND f.id IS DISTINCT FROM p_billing_account_id)
       AND script.fn_get_ba_emittente_sr_id_installazione(q.id)
           IS NOT DISTINCT FROM script.fn_get_ba_emittente_sr_id_installazione(p.id)
     ORDER BY q.id
     LIMIT 1;

    IF v_altro_codice IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',    'E_PARENT_SECONDO_PADRE',
            'dettaglio', jsonb_build_object(
                             'billing_account_id', p_billing_account_id,
                             'parent_account_id',  p_parent_account_id),
            'valori',    jsonb_build_array(
                             v_altro_codice,
                             COALESCE(v_padre_codice, p_parent_account_id::text)));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_ba_padre(p_billing_account_id bigint, p_codice character varying, p_parent_account_id bigint)
IS 'I motivi per cui il billing account non puo'' prendere il padre proposto: il padre ha gia'' un padre (E_PARENT_CON_PADRE), il billing account fa gia'' da padre (E_PARENT_HA_FIGLI), il cliente ha gia'' un altro padre sulla stessa azienda (E_PARENT_SECONDO_PADRE). L''albero ha un livello solo, e un cliente (la stessa identita'' fiscale, o lo stesso soggetto) un solo padre per azienda (script.fn_get_ba_emittente_sr_id_installazione). Padre NULL: nessun motivo. Il billing account entra per parametri e fra i figli dell''altro padre si esclude. SECURITY DEFINER: legge righe che la RLS di chi scrive puo'' nascondere, e risponde solo i codici dei billing account. La chiama anagrafiche.trgfn_billing_account_guard_normalize.';
```

</div>

---
{% include-markdown "signature-core.md" %}
