{% include-markdown "it/dbzero/vendite/manual/fn_get_scope_fatture_lotto.md" %}
# ⚙️ Funzione `fn_get_scope_fatture_lotto`

```sql
CREATE FUNCTION fn_get_scope_fatture_lotto(p_lotto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_scope_fatture_lotto(p_lotto_id bigint)
 RETURNS TABLE(fattura_id bigint, billing_account_id bigint, utility_id integer, tipo_doc_fiscale_id bigint, emittente_soggetto_ruolo_id bigint, valuta_id integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_incomplete BIGINT[];
BEGIN
    -- ===== Guard parametri =====
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_scope_fatture_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- ===== Il lotto deve esistere =====
    -- ⚠️ «lotto inesistente» e «lotto vuoto» sono due risposte
    --    diverse: la seconda e' legittima (un giro che non ha
    --    niente da fare), la prima e' un errore del chiamante.
    --    Senza questo guard sarebbero indistinguibili, perche'
    --    entrambe darebbero zero righe.
    IF NOT EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti l
         WHERE l.id = p_lotto_id
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_scope_fatture_lotto', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::TEXT);
    END IF;

    -- ===== Lo scope dev'essere completo =====
    -- Le tre colonne nullable della chiave. Le altre due
    -- (billing account ed emittente) sono NOT NULL a schema.
    SELECT array_agg(f.id ORDER BY f.id)
      INTO v_incomplete
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
       AND (f.utility_id          IS NULL
         OR f.tipo_doc_fiscale_id IS NULL
         OR f.valuta_id           IS NULL);

    IF v_incomplete IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_scope_fatture_lotto', 'E_PIPELINE_SCOPE_INCOMPLETE',
            jsonb_build_object(
                'lotto_id', p_lotto_id,
                'fatture',  to_jsonb(v_incomplete),
                'campi',    jsonb_build_array('utility_id', 'tipo_doc_fiscale_id', 'valuta_id')),
            -- ⚠️ Il valore VARIADIC non e' facoltativo: il
            --    messaggio di questo codice non ha segnaposti,
            --    ma senza almeno un argomento la chiamata non
            --    risolve la firma di fn_log_and_raise_error.
            NULL::uuid, p_lotto_id::TEXT);
    END IF;

    -- ===== Lo scope =====
    -- ⭐ `f.utility_id` e non COALESCE(lotto, billing account):
    --    e' la colonna su cui i giri filtrano davvero, e
    --    passarne un'altra puo' solo produrre un no-op muto.
    RETURN QUERY
    SELECT f.id,
           f.billing_account_id,
           f.utility_id,
           f.tipo_doc_fiscale_id,
           f.emittente_soggetto_ruolo_id,
           f.valuta_id
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
     WHERE lf.lotto_id = p_lotto_id
     ORDER BY f.id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_scope_fatture_lotto(p_lotto_id bigint)
IS 'Le fatture di un lotto con i cinque elementi di scope che i giri usano come chiave: billing account, utility, tipo doc fiscale, emittente, valuta. Una riga per fattura, ordinata per id. ⭐ E'' la DEFINIZIONE UNICA dello scope del lotto: prima viveva in Python (_SCOPE_FATTURE_LOTTO_SQL) e serviva a validazione, generazione e applicazione; con le due madri per lotto i lettori diventano quattro, e una regola di dominio con quattro lettori non sta fuori dal database. 🔴 Legge `f.utility_id` e NON COALESCE(lotto, billing account) come faceva la versione Python: la colonna della fattura e'' quella su cui fn_genera_fondi_fattura_source filtra, e passarne un''altra non produce un errore ma un NO-OP MUTO — nessun fondo, nessun log. ⚠️ Solleva invece di restituire zero righe in due casi: lotto inesistente (E_LOTTO_NON_TROVATO, che «lotto vuoto» non deve poter mascherare) e scope incompleto (E_PIPELINE_SCOPE_INCOMPLETE, con gli id delle fatture nel contesto). Il secondo e'' un cambio di comportamento voluto: con una utility mancante prima il giro proseguiva senza fare niente, e una fattura emessa senza il fondo che le spettava non se ne accorge nessuno — un task rosso si''. ℹ️ SECURITY INVOKER: il perimetro RLS resta quello del chiamante. R-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
