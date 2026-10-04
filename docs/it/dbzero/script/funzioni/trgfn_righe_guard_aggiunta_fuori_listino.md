{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_aggiunta_fuori_listino.md" %}
# ⚙️ Funzione `trgfn_righe_guard_aggiunta_fuori_listino`

```sql
CREATE FUNCTION trgfn_righe_guard_aggiunta_fuori_listino()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_aggiunta_fuori_listino()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare una riga AGGIUNTA (contratto o offerta) il cui
--   articolo e' gia' nella versione operativa del listino del
--   documento: per un articolo del listino si usa OVERRIDE.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
--        WHEN (NEW.tipo_eccezione = 'AGGIUNTA'), fascia _a10_.
-- TG_ARGV[0]: documento ('CONTRATTO' | 'OFFERTA').
-- TG_ARGV[1]: colonna del documento padre ('contratto_id',
--   'offerta_id').
-- Versione: vendite.fn_documento_listino_operativo (fissata, o in
--   vigore oggi; NULL senza listino = AGGIUNTA sempre valida).
DECLARE
    v_documento           text   := TG_ARGV[0];
    v_documento_id        bigint := (to_jsonb(NEW) ->> TG_ARGV[1])::bigint;
    v_listino_id          vendite.listini.id%TYPE;
    v_listino_versione_id vendite.listini_versioni.id%TYPE;
    v_etichetta           text;
BEGIN
    SELECT lo.listino_id, lo.listino_versione_id
      INTO v_listino_id, v_listino_versione_id
      FROM vendite.fn_documento_listino_operativo(v_documento, v_documento_id) lo;

    -- Nessuna versione operativa: nessun listino da cui l'articolo
    -- possa venire. L'AGGIUNTA e' sempre valida.
    IF v_listino_versione_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM vendite.listini_righe lr
         WHERE lr.listino_versione_id = v_listino_versione_id
           AND lr.articolo_id         = NEW.articolo_id
           AND lr.attivo              = TRUE
    ) THEN
        RETURN NEW;
    END IF;

    -- Il documento nel messaggio: l'etichetta per l'operatore.
    SELECT t.etichetta
      INTO v_etichetta
      FROM script.fn_get_stato_testata_documento(v_documento, v_documento_id) t;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO',
        jsonb_build_object(
            'campo',               'articolo_id',
            'documento',           v_documento,
            TG_ARGV[1],            v_documento_id,
            'articolo_id',         NEW.articolo_id,
            'listino_id',          v_listino_id,
            'listino_versione_id', v_listino_versione_id),
        NEW.tx_id,
        NEW.articolo_id::text,
        COALESCE(v_etichetta, initcap(v_documento) || ' #' || v_documento_id::text));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_aggiunta_fuori_listino()
IS 'Guard: una riga AGGIUNTA di vendite.contratti_righe o di vendite.offerte_commerciali_eccezioni e'' un articolo FUORI dal listino; se l''articolo sta (riga attiva) nella versione operativa del listino del documento (vendite.fn_documento_listino_operativo: fissata, o in vigore oggi) si rifiuta con E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO (campo articolo_id; valori: l''articolo e l''etichetta del documento, da script.fn_get_stato_testata_documento). Nessun listino = AGGIUNTA sempre valida. TG_ARGV[0] = documento (CONTRATTO | OFFERTA), TG_ARGV[1] = colonna del padre. Trigger _a10_ BEFORE INSERT OR UPDATE WHEN (NEW.tipo_eccezione = ''AGGIUNTA''). Prende il posto di vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino (solo contratto, ritirata nello stesso giro): fn_push_offerta_a_contratto copia le righe 1:1 con la stessa versione di listino, e la regola deve valere ai due capi. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R5b).';
```

---
{% include-markdown "signature-core.md" %}
