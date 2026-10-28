# ⚙️ Funzione `fn_annulla_ddt`

```sql
CREATE FUNCTION fn_annulla_ddt(p_ddt_id bigint, p_legami_confermati integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_ddt(p_ddt_id bigint, p_legami_confermati integer DEFAULT NULL::integer)
 RETURNS TABLE(movimento_id bigint, prelievo_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

#variable_conflict use_column
-- =========================================================
-- Scopo: annullare una bolla. Con legami: conferma e ritiro dal
--   BB vendite.fn_documento_ritira_legami, poi lo stato dal verbo
--   di stato. p_legami_confermati e' un CONTEGGIO: tipo nudo.
--   Vedi l'intestazione del changeSet.
-- Ritorna: i movimenti di storno del verbo di stato (nessuno se
--   la bolla non muove merce).
-- =========================================================
DECLARE
    v_utente  config.user_override_azioni.auth_user_id%TYPE;
    v_trovato boolean;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_ddt_id IS NULL OR p_ddt_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ddt',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ddt_id', p_ddt_id),
            NULL::uuid, 'vendite.fn_annulla_ddt',
            'p_ddt_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata FOR UPDATE, nel perimetro (predicato della
    --    policy: DEFINER). Fuori perimetro come inesistente.
    SELECT true
      INTO v_trovato
      FROM vendite.ddt d
     WHERE d.id = p_ddt_id
       AND script.fn_scope_ef_whitelist_via_ddt(v_utente, d.id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_annulla_ddt',
            'E_DDT_NOT_FOUND', jsonb_build_object('ddt_id', p_ddt_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 3. Conferma e ritiro: il BB apre la porta e la lascia aperta.
    PERFORM vendite.fn_documento_ritira_legami('DDT_VENDITA', p_ddt_id, p_legami_confermati);

    -- 4. Lo stato, dal verbo di stato: matrice, permesso, storno.
    RETURN QUERY
        SELECT c.movimento_id, c.prelievo_id, c.qta
          FROM vendite.fn_cambia_stato_ddt(p_ddt_id, 'ANNULLATO') AS c;

    -- 5. Porta chiusa.
    PERFORM set_config('zeroerp.doc_ritira_legami', '', true);
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_ddt(p_ddt_id bigint, p_legami_confermati integer)
IS 'VERBO (2026-10-11; brief-db-ddt-righe-evase-dall-ordine D-8, riallineato da brief-db-annullo-documento-con-legami D-4): annulla una bolla. Testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_ddt; fuori perimetro E_DDT_NOT_FOUND). Conferma e ritiro dal BB vendite.fn_documento_ritira_legami: chi conferma DICHIARA quanti legami ha visto (p_legami_confermati, le righe di vendite.fn_documento_legami(''DDT'', id): legami con ordini e resi, righe di commessa NON_EMESSA); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Poi lo stato da vendite.fn_cambia_stato_ddt (matrice, permesso emetti_ddt sull''annullo di una emessa, storno del magazzino), di cui restituisce i movimenti, e la porta del ritiro si chiude. UNA transazione. Una bolla senza legami non ha niente da confermare. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''app. ⭐ rev 2026-10-19 (20261019-60, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
