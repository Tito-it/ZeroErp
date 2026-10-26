{% include-markdown "it/dbzero/script/manual/fn_check_riga_magazzino.md" %}
# ⚙️ Funzione `fn_check_riga_magazzino`

```sql
CREATE FUNCTION fn_check_riga_magazzino(p_magazzino_id bigint, p_articolo_id uuid, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_riga_magazzino(p_magazzino_id bigint, p_articolo_id uuid, p_lotto_id bigint DEFAULT NULL::bigint, p_asset_id bigint DEFAULT NULL::bigint, p_ubicazione_id bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi per cui una RIGA (articolo + lotto/seriale/
--   ubicazione) NON puo' diventare un movimento in questo magazzino: i
--   passi 5-8 della primitiva, in una sede sola (C8, 12.5.2).
--   Consumatori: magazzino.fn_scrivi_movimento (solleva il primo motivo) e
--   magazzino.fn_inventario_piano (esito NON_POSTABILE + reason).
-- Ritorna: [] se scrivibile; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio{campo, ...}, valori}.
-- Regole (D-L2-m, M-5, M-6):
--   5) articolo attivo e gestito_a_magazzino;
--   6) requires_lotto => lotto obbligatorio, altrimenti vietato; se c'e',
--      dell'articolo e attivo;
--   7) requires_serial => asset obbligatorio, altrimenti vietato; se c'e',
--      dell'articolo, attivo, e dello stesso emittente del magazzino;
--   8) magazzini.usa_ubicazioni => ubicazione obbligatoria, altrimenti
--      vietata; se c'e', del magazzino e attiva.
-- Perimetro: INVOKER sotto RLS. Un magazzino che non si vede non decide
--   niente sull'ubicazione: a fermarlo e' il passo 4 della primitiva.
DECLARE
    v_motivi         jsonb := '[]'::jsonb;
    v_art_codice     catalogo.articoli.codice%TYPE;
    v_art_attivo     catalogo.articoli.attivo%TYPE;
    v_gestito        catalogo.articoli.gestito_a_magazzino%TYPE;
    v_req_lotto      catalogo.articoli.requires_lotto%TYPE;
    v_req_serial     catalogo.articoli.requires_serial%TYPE;
    v_mag_codice     magazzino.magazzini.codice%TYPE;
    v_mag_ef_id      magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_usa_ubicazioni magazzino.magazzini.usa_ubicazioni%TYPE;
    v_lotto_codice   magazzino.lotti.codice%TYPE;
    v_lotto_ok       boolean;
    v_seriale        magazzino.assets.seriale%TYPE;
    v_asset_ok       boolean;
    v_asset_ef_id    magazzino.assets.emittente_fiscale_id%TYPE;
    v_ubi_codice     magazzino.ubicazioni.codice%TYPE;
    v_ubi_ok         boolean;
    v_art_label      text;
    v_mag_label      text;
BEGIN
    -- Guard di parametro: solo forme che nessuna interfaccia produce.
    IF p_magazzino_id IS NULL OR p_magazzino_id <= 0 OR p_articolo_id IS NULL
       OR (p_lotto_id IS NOT NULL AND p_lotto_id <= 0)
       OR (p_asset_id IS NOT NULL AND p_asset_id <= 0)
       OR (p_ubicazione_id IS NOT NULL AND p_ubicazione_id <= 0) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_riga_magazzino',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'magazzino e articolo obbligatori; gli id passati maggiori di zero',
                               'p_magazzino_id', p_magazzino_id, 'p_articolo_id', p_articolo_id,
                               'p_lotto_id', p_lotto_id, 'p_asset_id', p_asset_id,
                               'p_ubicazione_id', p_ubicazione_id),
            NULL::uuid,
            'script.fn_check_riga_magazzino',
            'p_magazzino_id / p_articolo_id (obbligatori), p_lotto_id / p_asset_id / p_ubicazione_id (se passati, maggiori di zero)');
    END IF;

    -- L'articolo (catalogo.articoli non ha RLS) e il magazzino (sotto RLS).
    SELECT a.codice, a.attivo, a.gestito_a_magazzino, a.requires_lotto, a.requires_serial
      INTO v_art_codice, v_art_attivo, v_gestito, v_req_lotto, v_req_serial
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id;
    v_art_label := COALESCE(v_art_codice, p_articolo_id::text);

    SELECT m.codice, m.emittente_fiscale_id, m.usa_ubicazioni
      INTO v_mag_codice, v_mag_ef_id, v_usa_ubicazioni
      FROM magazzino.magazzini m
     WHERE m.id = p_magazzino_id;
    v_mag_label := COALESCE(v_mag_codice, p_magazzino_id::text);

    -- ============================================================
    -- 5) L'articolo: attivo e gestito a magazzino.
    -- ============================================================
    IF NOT COALESCE(v_art_attivo, false) OR NOT COALESCE(v_gestito, false) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_ARTICOLO_NON_GESTITO',
            'reason',     'ARTICOLO_NON_GESTITO',
            'reason_key', 'magazzino.riga.blocco.articolo_non_gestito',
            'dettaglio',  jsonb_build_object('campo', 'articolo_id',
                                             'articolo_id', p_articolo_id,
                                             'attivo', v_art_attivo,
                                             'gestito_a_magazzino', v_gestito),
            -- «L'articolo %s non e' gestito a magazzino: nessun movimento si puo' registrare.»
            'valori',     jsonb_build_array(v_art_label));
        -- Senza articolo (o non gestito) i passi 6-7 non hanno senso: si
        -- risponde il primo motivo e basta, il resto seguirebbe da un dato
        -- che non c'e'.
        RETURN v_motivi;
    END IF;

    -- ============================================================
    -- 6) Il lotto: decide l'articolo.
    -- ============================================================
    IF v_req_lotto AND p_lotto_id IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_LOTTO_OBBLIGATORIO',
            'reason',     'LOTTO_OBBLIGATORIO',
            'reason_key', 'magazzino.riga.blocco.lotto_obbligatorio',
            'dettaglio',  jsonb_build_object('campo', 'lotto_id', 'articolo_id', p_articolo_id),
            -- «L'articolo %s si movimenta per lotti: indica il lotto.»
            'valori',     jsonb_build_array(v_art_label));
    ELSIF p_lotto_id IS NOT NULL THEN
        SELECT l.codice, (l.attivo AND l.articolo_id = p_articolo_id)
          INTO v_lotto_codice, v_lotto_ok
          FROM magazzino.lotti l
         WHERE l.id = p_lotto_id;
        IF NOT v_req_lotto THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_LOTTO_NON_AMMESSO',
                'reason',     'LOTTO_NON_AMMESSO',
                'reason_key', 'magazzino.riga.blocco.lotto_non_ammesso',
                'dettaglio',  jsonb_build_object('campo', 'lotto_id', 'articolo_id', p_articolo_id,
                                                 'lotto_id', p_lotto_id),
                -- «L'articolo %s non si movimenta per lotti: il lotto %s non va indicato.»
                'valori',     jsonb_build_array(v_art_label, COALESCE(v_lotto_codice, p_lotto_id::text)));
        ELSIF NOT COALESCE(v_lotto_ok, false) THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_LOTTO_DI_ALTRO_ARTICOLO',
                'reason',     'LOTTO_DI_ALTRO_ARTICOLO',
                'reason_key', 'magazzino.riga.blocco.lotto_di_altro_articolo',
                'dettaglio',  jsonb_build_object('campo', 'lotto_id', 'articolo_id', p_articolo_id,
                                                 'lotto_id', p_lotto_id),
                -- «Il lotto %s non e' dell'articolo %s, oppure non e' piu' attivo.»
                'valori',     jsonb_build_array(COALESCE(v_lotto_codice, p_lotto_id::text), v_art_label));
        END IF;
    END IF;

    -- ============================================================
    -- 7) Il seriale: decide l'articolo; l'asset e' dell'emittente del magazzino.
    -- ============================================================
    IF v_req_serial AND p_asset_id IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_SERIALE_OBBLIGATORIO',
            'reason',     'SERIALE_OBBLIGATORIO',
            'reason_key', 'magazzino.riga.blocco.seriale_obbligatorio',
            'dettaglio',  jsonb_build_object('campo', 'asset_id', 'articolo_id', p_articolo_id),
            -- «L'articolo %s si movimenta per seriale: indica il seriale.»
            'valori',     jsonb_build_array(v_art_label));
    ELSIF p_asset_id IS NOT NULL THEN
        SELECT s.seriale, (s.attivo AND s.articolo_id = p_articolo_id), s.emittente_fiscale_id
          INTO v_seriale, v_asset_ok, v_asset_ef_id
          FROM magazzino.assets s
         WHERE s.id = p_asset_id;
        IF NOT v_req_serial THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_SERIALE_NON_AMMESSO',
                'reason',     'SERIALE_NON_AMMESSO',
                'reason_key', 'magazzino.riga.blocco.seriale_non_ammesso',
                'dettaglio',  jsonb_build_object('campo', 'asset_id', 'articolo_id', p_articolo_id,
                                                 'asset_id', p_asset_id),
                -- «L'articolo %s non si movimenta per seriale: il seriale %s non va indicato.»
                'valori',     jsonb_build_array(v_art_label, COALESCE(v_seriale, p_asset_id::text)));
        ELSIF NOT COALESCE(v_asset_ok, false) THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_ASSET_DI_ALTRO_ARTICOLO',
                'reason',     'SERIALE_DI_ALTRO_ARTICOLO',
                'reason_key', 'magazzino.riga.blocco.seriale_di_altro_articolo',
                'dettaglio',  jsonb_build_object('campo', 'asset_id', 'articolo_id', p_articolo_id,
                                                 'asset_id', p_asset_id),
                -- «Il seriale %s non e' dell'articolo %s, oppure non e' piu' attivo.»
                'valori',     jsonb_build_array(COALESCE(v_seriale, p_asset_id::text), v_art_label));
        ELSIF v_mag_ef_id IS NOT NULL AND v_asset_ef_id IS DISTINCT FROM v_mag_ef_id THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_ASSET_DI_ALTRO_EMITTENTE',
                'reason',     'SERIALE_DI_ALTRO_EMITTENTE',
                'reason_key', 'magazzino.riga.blocco.seriale_di_altro_emittente',
                'dettaglio',  jsonb_build_object('campo', 'asset_id', 'asset_id', p_asset_id,
                                                 'asset_emittente_fiscale_id', v_asset_ef_id,
                                                 'magazzino_emittente_fiscale_id', v_mag_ef_id),
                -- «Il seriale %s non appartiene all'emittente del magazzino %s.»
                'valori',     jsonb_build_array(COALESCE(v_seriale, p_asset_id::text), v_mag_label));
        END IF;
    END IF;

    -- ============================================================
    -- 8) L'ubicazione: decide il magazzino (D-L2-m).
    -- ============================================================
    IF v_usa_ubicazioni IS NOT NULL THEN          -- il magazzino si vede
        IF v_usa_ubicazioni AND p_ubicazione_id IS NULL THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_UBICAZIONE_OBBLIGATORIA',
                'reason',     'UBICAZIONE_OBBLIGATORIA',
                'reason_key', 'magazzino.riga.blocco.ubicazione_obbligatoria',
                'dettaglio',  jsonb_build_object('campo', 'ubicazione_id', 'magazzino_id', p_magazzino_id),
                -- «Il magazzino %s usa le ubicazioni: indica in quale ubicazione.»
                'valori',     jsonb_build_array(v_mag_label));
        ELSIF p_ubicazione_id IS NOT NULL THEN
            SELECT u.codice, (u.attivo AND u.magazzino_id = p_magazzino_id)
              INTO v_ubi_codice, v_ubi_ok
              FROM magazzino.ubicazioni u
             WHERE u.id = p_ubicazione_id;
            IF NOT v_usa_ubicazioni THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_MAG_UBICAZIONE_NON_AMMESSA',
                    'reason',     'UBICAZIONE_NON_AMMESSA',
                    'reason_key', 'magazzino.riga.blocco.ubicazione_non_ammessa',
                    'dettaglio',  jsonb_build_object('campo', 'ubicazione_id', 'magazzino_id', p_magazzino_id,
                                                     'ubicazione_id', p_ubicazione_id),
                    -- «Il magazzino %s non usa le ubicazioni: l'ubicazione %s non va indicata.»
                    'valori',     jsonb_build_array(v_mag_label, COALESCE(v_ubi_codice, p_ubicazione_id::text)));
            ELSIF NOT COALESCE(v_ubi_ok, false) THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO',
                    'reason',     'UBICAZIONE_DI_ALTRO_MAGAZZINO',
                    'reason_key', 'magazzino.riga.blocco.ubicazione_di_altro_magazzino',
                    'dettaglio',  jsonb_build_object('campo', 'ubicazione_id', 'magazzino_id', p_magazzino_id,
                                                     'ubicazione_id', p_ubicazione_id),
                    -- «L'ubicazione %s non e' del magazzino %s, oppure non e' piu' attiva.»
                    'valori',     jsonb_build_array(COALESCE(v_ubi_codice, p_ubicazione_id::text), v_mag_label));
            END IF;
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_riga_magazzino(p_magazzino_id bigint, p_articolo_id uuid, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint)
IS 'La riga e'' scrivibile a registro? I passi 5-8 della primitiva in una sede sola (C8, linee-guida-sql 12.5.2): pura, STABLE, INVOKER — [] se si'', altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio (con campo), valori}: 5) articolo attivo e gestito_a_magazzino (E_MAG_ARTICOLO_NON_GESTITO, e si ferma li''); 6) lotto deciso dall''articolo — requires_lotto => obbligatorio, altrimenti vietato; se c''e'', dell''articolo e attivo (E_MAG_LOTTO_*); 7) seriale deciso dall''articolo — requires_serial => obbligatorio, altrimenti vietato; se c''e'', dell''articolo, attivo e dello stesso emittente del magazzino (E_MAG_SERIALE_*, E_MAG_ASSET_*); 8) ubicazione decisa dal MAGAZZINO — usa_ubicazioni => obbligatoria, altrimenti vietata; se c''e'', del magazzino e attiva (E_MAG_UBICAZIONE_*). Letta da magazzino.fn_scrivi_movimento (solleva il primo motivo) e da magazzino.fn_inventario_piano (esito NON_POSTABILE): il piano mostra cio'' che il posting rifiutera''. Non guarda il magazzino in se'' (passo 4 della primitiva) ne'' la disponibilita'' (fn_check_disponibilita_uscita). Le reason_key magazzino.riga.blocco.* sono chiavi i18n del frontend. Brief: brief-db-magazzino-lotto-2-motore, sezione 6-ter C8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
