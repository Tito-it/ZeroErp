{% include-markdown "it/dbzero/vendite/manual/fn_start_commessa_push_run.md" %}
# ⚙️ Funzione `fn_start_commessa_push_run`

```sql
CREATE FUNCTION fn_start_commessa_push_run(p_dry_run boolean, p_source_types text[], p_correlation_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_start_commessa_push_run(p_dry_run boolean DEFAULT false, p_source_types text[] DEFAULT NULL::text[], p_correlation_id uuid DEFAULT NULL::uuid)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id vendite.commesse_push_log.id%TYPE;
BEGIN
    -- Scopo: apre il giro di push commesse — una riga in stato IN_ESECUZIONE,
    --        con l'ora di partenza e il filo del giro — e ne restituisce
    --        l'identificativo, che il chiamante conserva per la chiusura.
    --
    -- ⭐ NESSUN GUARD, ed e' una decisione. L'apertura di un diario non ha
    --    niente da rifiutare: non cita nessuna entita' esterna, e ogni valore
    --    che riceve e' facoltativo. Un guard qui potrebbe solo impedire a un
    --    giro di partire per un difetto dell'appunto che lo registra —
    --    esattamente cio' che la D-12 del cantiere vieta.
    --
    -- ⚠️ p_correlation_id resta NULLABLE e non si genera d'ufficio: un uuid
    --    coniato qui non lo conoscerebbe nessun altro registro, quindi non
    --    cucirebbe niente. Un buco dichiarato si conta; un filo che non lega
    --    sembra un filo.
    INSERT INTO vendite.commesse_push_log (
        dry_run, source_types, risultato, stato, correlation_id
    ) VALUES (
        COALESCE(p_dry_run, FALSE), p_source_types, '{}'::jsonb,
        'IN_ESECUZIONE', p_correlation_id
    )
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_start_commessa_push_run(p_dry_run boolean, p_source_types text[], p_correlation_id uuid)
IS 'Apre un giro di push commesse: INSERT della riga in TESTA alla corsa, stato IN_ESECUZIONE, run_at = now(). Restituisce l''id, che va passato a vendite.fn_close_commessa_push_run. ⭐ Il motivo per cui la riga nasce all''inizio e non alla fine: prima l''evento d''avvio citava entity_id = 0, che non era un segnaposto ma un id CHE NON ESISTEVA ANCORA. E un giro interrotto smette di sparire — la riga rimasta IN_ESECUZIONE e'' l''unica prova che qualcosa e'' partito e non e'' tornato. ⚠️ Il guadagno vale sul batch, che gira in autocommit: nel push singolo dal drawer la transaction.atomic() esterna rolla anche questa riga. ⛔ Nessun guard: un diario che si apre non ha niente da rifiutare (D-12). Brief: brief-db-event-log-scope-e-riga-parlante, D-3 e D-7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
