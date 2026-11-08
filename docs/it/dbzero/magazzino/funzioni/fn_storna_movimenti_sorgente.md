# ⚙️ Funzione `fn_storna_movimenti_sorgente`

```sql
CREATE FUNCTION fn_storna_movimenti_sorgente(p_sorgente_tipo_id bigint, p_sorgente_righe bigint[], p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_storna_movimenti_sorgente(p_sorgente_tipo_id bigint, p_sorgente_righe bigint[], p_sorgente_id bigint DEFAULT NULL::bigint, p_sorgente_uid uuid DEFAULT NULL::uuid)
 RETURNS TABLE(movimento_id bigint, storno_di_movimento_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
-- Scopo: stornare tutti i movimenti di un documento (tipo + chiave del
--   documento; facoltativamente solo alcune sue righe) che non sono uno
--   storno e non sono gia' stornati, dal piu' recente. Lo specchio lo
--   compone QUI, dall'originale, e lo scrive la primitiva nel suo ramo
--   storno (M-8). Ritorna un record per storno.
-- ⚠️ p_sorgente_righe e' bigint[] e non %TYPE[]: la sintassi non esiste.
DECLARE
    v_orig magazzino.movimenti%ROWTYPE;
BEGIN
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_storna_movimenti_sorgente',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'tipo di sorgente obbligatorio e maggiore di zero',
                               'p_sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, 'magazzino.fn_storna_movimenti_sorgente',
            'p_sorgente_tipo_id (obbligatorio, maggiore di zero)');
    END IF;
    IF num_nonnulls(p_sorgente_id, p_sorgente_uid) <> 1
       OR (p_sorgente_id IS NOT NULL AND p_sorgente_id <= 0) THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_storna_movimenti_sorgente',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'una sola chiave del documento (id maggiore di zero, o uid)',
                               'p_sorgente_id', p_sorgente_id, 'p_sorgente_uid', p_sorgente_uid),
            NULL::uuid, 'magazzino.fn_storna_movimenti_sorgente',
            'p_sorgente_id / p_sorgente_uid (esattamente una: il documento da stornare)');
    END IF;

    FOR v_orig IN
        SELECT m.*
          FROM magazzino.movimenti m
         WHERE m.sorgente_tipo_id = p_sorgente_tipo_id
           AND m.sorgente_id  IS NOT DISTINCT FROM p_sorgente_id
           AND m.sorgente_uid IS NOT DISTINCT FROM p_sorgente_uid
           AND (p_sorgente_righe IS NULL OR m.sorgente_riga = ANY (p_sorgente_righe))
           AND m.storno_di_movimento_id IS NULL
           AND NOT EXISTS (SELECT 1 FROM magazzino.movimenti s
                            WHERE s.storno_di_movimento_id = m.id)
         ORDER BY m.id DESC
    LOOP
        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id           => v_orig.magazzino_id,
            p_articolo_id            => v_orig.articolo_id,
            p_causale                => CASE WHEN v_orig.qta < 0 THEN 'STORNO_POS' ELSE 'STORNO_NEG' END,
            p_qta                    => -v_orig.qta,
            p_sorgente_tipo_id       => v_orig.sorgente_tipo_id,
            p_sorgente_id            => v_orig.sorgente_id,
            p_sorgente_uid           => v_orig.sorgente_uid,
            p_sorgente_riga          => v_orig.sorgente_riga,
            p_sorgente_dettaglio     => v_orig.sorgente_dettaglio,
            p_lotto_id               => v_orig.lotto_id,
            p_asset_id               => v_orig.asset_id,
            p_ubicazione_id          => v_orig.ubicazione_id,
            p_data_mov               => now(),
            p_storno_di_movimento_id => v_orig.id);
        storno_di_movimento_id := v_orig.id;
        qta                    := -v_orig.qta;
        RETURN NEXT;
    END LOOP;
    RETURN;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_storna_movimenti_sorgente(p_sorgente_tipo_id bigint, p_sorgente_righe bigint[], p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'La utility di storno (M-8), per DOCUMENTO: per ogni movimento del documento (p_sorgente_tipo_id + la sua chiave, p_sorgente_id o p_sorgente_uid, una sola e obbligatoria) che non e'' uno storno e non e'' gia'' stornato, dal piu'' recente, scrive lo SPECCHIO attraverso il ramo storno di magazzino.fn_scrivi_movimento: stessa provenienza intera (tipo, documento, riga, dettaglio), articolo, magazzino e posizione (lotto, seriale, ubicazione), quantita'' opposta, causale STORNO_POS (se l''originale era un''uscita) o STORNO_NEG, costo dell''originale (lo mette la primitiva). p_sorgente_righe restringe alle righe del documento indicate (sorgente_riga); NULL = tutto il documento, vuoto = niente. Lo specchio lo compone il programma leggendo l''originale: non puo'' divergere. Lo storno doppio lo rifiuta la primitiva (uq_mag_movimenti_storno_di). Ritorna (movimento_id, storno_di_movimento_id, qta) per storno. Generica: non nomina le tabelle dei documenti. SECURITY DEFINER, RISERVATA: la chiamano i verbi (vendite.fn_cambia_stato_ddt all''annullo di una bolla emessa, vendite.fn_annulla_reso all''annullo di un reso confermato). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt (P-8); brief-db-sorgente-documento-e-riga lotto M (per documento).';
```

</div>

---
{% include-markdown "signature-core.md" %}
