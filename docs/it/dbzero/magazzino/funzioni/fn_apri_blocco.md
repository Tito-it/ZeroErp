# ⚙️ Funzione `fn_apri_blocco`

```sql
CREATE FUNCTION fn_apri_blocco(p_magazzino_id bigint, p_articolo_id uuid, p_qta numeric, p_soggetto_ruolo_id bigint, p_nota text, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_apri_blocco(p_magazzino_id bigint, p_articolo_id uuid, p_qta numeric, p_soggetto_ruolo_id bigint, p_nota text, p_lotto_id bigint DEFAULT NULL::bigint, p_asset_id bigint DEFAULT NULL::bigint, p_ubicazione_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: aprire un blocco manuale — riservare p_qta pezzi (POSITIVA:
--   il verso lo mette il verbo) per qualcuno o per un motivo (D-L3-j).
-- Ritorna: l'id dell'atteso aperto.
DECLARE
    v_utente    config.user_override_azioni.auth_user_id%TYPE;
    v_causale   magazzino.causali.id%TYPE;
    v_motivi    jsonb;
    v_id        magazzino.movimenti_attesi.id%TYPE;
BEGIN
    -- 0. Il permesso, prima di ogni altra cosa.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_azione(v_utente, 'blocca_merce');

    IF p_magazzino_id IS NULL OR p_magazzino_id <= 0
       OR p_articolo_id IS NULL
       OR p_qta IS NULL OR p_qta <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_apri_blocco',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'magazzino e articolo obbligatori, quantita'' positiva',
                               'p_magazzino_id', p_magazzino_id, 'p_qta', p_qta),
            NULL::uuid, 'magazzino.fn_apri_blocco',
            'p_magazzino_id (maggiore di zero), p_articolo_id (obbligatorio), p_qta (maggiore di zero: il verso lo mette il verbo)');
    END IF;

    -- Il magazzino, nel perimetro di chi agisce (DEFINER: il predicato della policy).
    IF NOT EXISTS (SELECT 1 FROM magazzino.magazzini m
                    WHERE m.id = p_magazzino_id AND m.attivo
                      AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, m.id)) THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_apri_blocco',
            'E_MAG_MAGAZZINO_NON_VALIDO',
            jsonb_build_object('detail', 'magazzino inesistente, spento o fuori perimetro',
                               'magazzino_id', p_magazzino_id),
            NULL::uuid, p_magazzino_id::text);
    END IF;

    -- La posizione, come la giudicherebbe la primitiva.
    v_motivi := script.fn_check_riga_magazzino(p_magazzino_id, p_articolo_id,
                                               p_lotto_id, p_asset_id, p_ubicazione_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'magazzino', 'magazzino.fn_apri_blocco', v_motivi, NULL, NULL::uuid,
        jsonb_build_object('magazzino_id', p_magazzino_id, 'articolo_id', p_articolo_id));

    SELECT c.id INTO v_causale
      FROM magazzino.causali c
     WHERE c.codice_interno = 'SCARICO_VEN' AND c.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_apri_blocco',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'magazzino.causali.SCARICO_VEN'),
            NULL::uuid, VARIADIC ARRAY['causale di magazzino SCARICO_VEN (magazzino.causali, attiva)']);
    END IF;

    INSERT INTO magazzino.movimenti_attesi
           (articolo_id, magazzino_id, qta, causale_id, stato,
            soggetto_ruolo_id, nota, lotto_id, asset_id, ubicazione_id, meta)
    VALUES (p_articolo_id, p_magazzino_id, -p_qta, v_causale, 'APERTA',
            p_soggetto_ruolo_id, NULLIF(btrim(p_nota), ''), p_lotto_id, p_asset_id, p_ubicazione_id,
            jsonb_build_object('aperto_da', v_utente))
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_apri_blocco(p_magazzino_id bigint, p_articolo_id uuid, p_qta numeric, p_soggetto_ruolo_id bigint, p_nota text, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint)
IS 'VERBO: apre un blocco manuale (D-L3-j) — un atteso in uscita (SCARICO_VEN, qta = -p_qta: la quantita'' si passa POSITIVA), APERTA, senza sorgente, per chi (p_soggetto_ruolo_id) o perche'' (p_nota): lo pretende il CHECK per_chi. Prima riga script.fn_guard_azione(utente, ''blocca_merce''). SECURITY DEFINER: il magazzino deve essere attivo e nel perimetro di chi agisce (E_MAG_MAGAZZINO_NON_VALIDO), la posizione la giudica script.fn_check_riga_magazzino come per la primitiva. In meta aperto_da. Il blocco ferma gli scarichi degli altri (M-3) finche'' non lo libera magazzino.fn_libera_blocco. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
