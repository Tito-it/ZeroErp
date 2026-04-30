{% include-markdown "it/dbzero/catalogo/manual/fn_duplica_componente_versione.md" %}
# ⚙️ Funzione `fn_duplica_componente_versione`

```sql
CREATE FUNCTION fn_duplica_componente_versione(p_articolo_id uuid, p_componente_row_id uuid, p_chiudi_al date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_duplica_componente_versione(p_articolo_id uuid, p_componente_row_id uuid, p_chiudi_al date DEFAULT NULL::date)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Endpoint atomico per duplicare la versione corrente di
--   un componente BoM. Chiude la riga sorgente al
--   p_chiudi_al (default oggi) e inserisce una nuova riga
--   con valido_dal = p_chiudi_al + 1, copiando i campi di
--   struttura + meta + note. Lock advisory sul prodotto
--   serializza duplicazioni concorrenti.
-- Restituisce: id (uuid) della nuova riga.
-- Tipi: parametri e variabili usano %TYPE delle colonne
--   target (linee-guida-sql.md). RETURNS resta uuid concreto
--   (PostgreSQL non supporta %TYPE nel RETURNS).
DECLARE
    v_fn_name    CONSTANT text := 'fn_duplica_componente_versione';
    v_chiudi_al  catalogo.articoli_componenti.valido_al%TYPE;
    v_old        catalogo.articoli_componenti%ROWTYPE;
    v_new_id     catalogo.articoli_componenti.id%TYPE;
BEGIN
    v_chiudi_al := COALESCE(p_chiudi_al, CURRENT_DATE);

    -- Guard parametri NULL: riconducibile a NOT FOUND.
    IF p_articolo_id IS NULL OR p_componente_row_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            v_fn_name,
            'E_BOM_RIGA_NOT_FOUND',
            jsonb_build_object(
                'articolo_id', p_articolo_id,
                'riga_id',     p_componente_row_id
            ),
            NULL::uuid,
            COALESCE(p_componente_row_id::text, 'NULL')
        );
    END IF;

    -- Lock advisory per prodotto: serializza duplicazioni
    -- concorrenti sullo stesso articolo. La granularita'
    -- per prodotto e' sufficiente perche' l'EXCLUDE GIST
    -- e' su (prodotto_id, componente_id, validita).
    PERFORM pg_advisory_xact_lock(
        hashtext('catalogo.articoli_componenti.duplica:' || p_articolo_id::text)
    );

    -- SELECT FOR UPDATE riga sorgente.
    SELECT * INTO v_old
      FROM catalogo.articoli_componenti
     WHERE id = p_componente_row_id
     FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            v_fn_name,
            'E_BOM_RIGA_NOT_FOUND',
            jsonb_build_object('riga_id', p_componente_row_id),
            NULL::uuid,
            p_componente_row_id::text
        );
    END IF;

    -- Guard prodotto mismatch.
    IF v_old.prodotto_id IS DISTINCT FROM p_articolo_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            v_fn_name,
            'E_BOM_PRODOTTO_MISMATCH',
            jsonb_build_object(
                'expected_prodotto_id', p_articolo_id,
                'actual_prodotto_id',   v_old.prodotto_id,
                'riga_id',              v_old.id
            ),
            NULL::uuid,
            v_old.prodotto_id::text,
            p_articolo_id::text
        );
    END IF;

    -- Guard sorgente gia' chiusa.
    IF v_old.valido_al IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            v_fn_name,
            'E_BOM_SORGENTE_GIA_CHIUSA',
            jsonb_build_object(
                'riga_id',   v_old.id,
                'valido_al', v_old.valido_al
            ),
            NULL::uuid,
            v_old.valido_al::text
        );
    END IF;

    -- UPDATE chiusura sorgente. Edge case
    -- v_chiudi_al < OLD.valido_dal: lasciamo propagare
    -- E_BOM_VALIDO_AL_INVALIDO dal trigger
    -- block_modifica_struttura (gia' UI-friendly, code 388).
    UPDATE catalogo.articoli_componenti
       SET valido_al = v_chiudi_al
     WHERE id = v_old.id;

    -- INSERT nuova versione. valido_dal = v_chiudi_al + 1
    -- e' obbligato dal pattern daterange canonicalizzato:
    -- la sorgente chiusa ha validita = [v_dal, v_chiudi_al+1),
    -- per non urtare l'EXCLUDE GIST la nuova deve partire
    -- da v_chiudi_al + 1.
    -- Cattura overlap con eventuali righe future esistenti
    -- sullo stesso (prodotto, componente).
    BEGIN
        INSERT INTO catalogo.articoli_componenti (
            prodotto_id,
            componente_id,
            coeff_qta,
            partecipa_qta,
            obbligatorio,
            determina_qta_padre,
            esposto_in_fattura,
            meta,
            note_target_tipo,
            note_id,
            valido_dal,
            valido_al,
            attivo
        )
        VALUES (
            v_old.prodotto_id,
            v_old.componente_id,
            v_old.coeff_qta,
            v_old.partecipa_qta,
            v_old.obbligatorio,
            v_old.determina_qta_padre,
            v_old.esposto_in_fattura,
            v_old.meta,
            v_old.note_target_tipo,
            v_old.note_id,
            v_chiudi_al + 1,
            NULL,
            true
        )
        RETURNING id INTO v_new_id;
    EXCEPTION
        WHEN exclusion_violation THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                v_fn_name,
                'E_BOM_VERSIONE_OVERLAP',
                jsonb_build_object(
                    'prodotto_id',      v_old.prodotto_id,
                    'componente_id',    v_old.componente_id,
                    'nuova_valido_dal', v_chiudi_al + 1,
                    'sorgente_id',      v_old.id
                ),
                NULL::uuid,
                (v_chiudi_al + 1)::text
            );
    END;

    RETURN v_new_id;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_duplica_componente_versione(p_articolo_id uuid, p_componente_row_id uuid, p_chiudi_al date)
IS 'Endpoint atomico: chiude la versione corrente di un componente BoM e ne apre una nuova con valido_dal = p_chiudi_al + 1. Copia componente_id, struttura, meta, note. Lock advisory per prodotto. Codici errore: E_BOM_VERSIONE_OVERLAP (400), E_BOM_SORGENTE_GIA_CHIUSA (401), E_BOM_RIGA_NOT_FOUND (402), E_BOM_PRODOTTO_MISMATCH (403). Edge case p_chiudi_al < valido_dal -> E_BOM_VALIDO_AL_INVALIDO (388, dal trigger).';
```

---
{% include-markdown "signature-core.md" %}
