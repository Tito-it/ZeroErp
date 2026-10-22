{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_guard_contratto.md" %}
# ⚙️ Funzione `trgfn_attivita_guard_contratto`

```sql
CREATE FUNCTION trgfn_attivita_guard_contratto()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_guard_contratto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Il codice del motivo, dalla check.
    v_codice config.codici_errore.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   AFTER INSERT OR UPDATE su commesse_attivita e
    --   attivita_fatturabili: il contratto citato come
    --   provenienza del prezzo e' del billing account della
    --   commessa (vendite.fn_check_contratto_provenienza).
    -- =========================================================
    IF NEW.contratto_id IS NULL THEN
        RETURN NULL;
    END IF;

    IF TG_OP = 'UPDATE'
       AND NEW.contratto_id IS NOT DISTINCT FROM OLD.contratto_id
       AND NEW.commessa_id  IS NOT DISTINCT FROM OLD.commessa_id THEN
        RETURN NULL;
    END IF;

    v_codice := vendite.fn_check_contratto_provenienza(
        NEW.commessa_id, NEW.contratto_id);

    IF v_codice IS NOT NULL THEN
        -- Frase chiusa: il contratto puo' essere di un'azienda
        -- che l'operatore non vede.
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, v_codice,
            jsonb_build_object(
                'campo',        'contratto_id',
                'tabella',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',           NEW.id,
                'commessa_id',  NEW.commessa_id,
                'contratto_id', NEW.contratto_id),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NULL;   -- trigger AFTER: il valore di ritorno e' ignorato
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_guard_contratto()
IS 'Guard AFTER INSERT OR UPDATE su vendite.commesse_attivita e vendite.attivita_fatturabili (decisione di Tid D-1, 2026-10-21): il contratto citato come provenienza del prezzo (contratto_id) e'' del billing account della commessa della riga -> altrimenti E_ATTIVITA_CONTRATTO_INCOERENTE (TECNICO: il contratto lo scrive il programma dal risolutore dei prezzi, non l''operatore; frase chiusa, campo contratto_id). Predicato: vendite.fn_check_contratto_provenienza (SECURITY DEFINER). AFTER: giudica la riga finale. Contratto NULL -> passa; in UPDATE giudica solo se cambiano contratto o commessa. Gemello di vendite.trgfn_attivita_guard_listino_riga, che giudica l''altra meta'' della provenienza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
