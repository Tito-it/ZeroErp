# ⚙️ Funzione `fn_posta_reso`

```sql
CREATE FUNCTION fn_posta_reso(p_reso_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_posta_reso(p_reso_id bigint)
 RETURNS TABLE(movimento_id bigint, rientro_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
-- Scopo: scrivere i carichi di un reso, uno per rientro, alla conferma.
--   Non ricontrolla: la primitiva e' la rete, la check della merce ha gia'
--   parlato. Non crea rientri, non guarda lo stato: QUANDO lo decide il verbo.
DECLARE
    v_reso        vendite.resi%ROWTYPE;
    v_sorgente_id config.sorgenti.id%TYPE;
    v_prel_src_id config.sorgenti.id%TYPE;
    v_prov_id     magazzino.movimenti.sorgente_id%TYPE;
    v_prov_uid    magazzino.movimenti.sorgente_uid%TYPE;
    v_costo       magazzino.movimenti.costo_unitario%TYPE;
    v_rientro     record;
BEGIN
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_posta_reso',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'reso maggiore di zero', 'p_reso_id', p_reso_id),
            NULL::uuid, 'vendite.fn_posta_reso', 'p_reso_id (obbligatorio, maggiore di zero)');
    END IF;

    SELECT r.* INTO v_reso FROM vendite.resi r WHERE r.id = p_reso_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_posta_reso',
            'E_RESO_NOT_FOUND', jsonb_build_object('reso_id', p_reso_id), NULL::uuid,
            p_reso_id::text);
    END IF;

    -- La provenienza e' il RESO (S-3), dal BB che la scrive; sotto, riga e
    -- rientro. Un tipo assente o spento e' E_SORG_CONF dal BB.
    SELECT p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid
      INTO v_sorgente_id, v_prov_id, v_prov_uid
      FROM script.fn_sorgente_provenienza('RESO_VENDITA', p_reso_id::text) p;
    -- Il tipo della bolla, per rileggere il costo dell'uscita d'origine: una
    -- lettura, non una scrittura (attivo o no, l'uscita e' gia' a registro).
    SELECT s.id INTO v_prel_src_id
      FROM config.sorgenti s
     WHERE s.codice_interno = 'DDT_VENDITA';
    IF v_prel_src_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_posta_reso',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.sorgenti.DDT_VENDITA'),
            NULL::uuid, VARIADIC ARRAY['sorgente DDT_VENDITA (config.sorgenti)']);
    END IF;

    FOR v_rientro IN
        SELECT x.id, rr.id AS resi_riga_id, x.qta AS x_qta, x.ubicazione_id,
               p.id AS prelievo_id, dr.id AS ddt_riga_id, dr.ddt_id,
               p.lotto_id, p.asset_id,
               COALESCE(drc.componente_id, dr.articolo_id) AS articolo_id
          FROM vendite.resi_righe_rientri x
          JOIN vendite.resi_righe rr          ON rr.id = x.resi_riga_id
          JOIN vendite.ddt_righe_prelievi p   ON p.id = x.ddt_riga_prelievo_id
          JOIN vendite.ddt_righe dr           ON dr.id = p.ddt_riga_id
          LEFT JOIN vendite.ddt_righe_componenti drc ON drc.id = p.ddt_riga_componente_id
         WHERE rr.reso_id = p_reso_id
           AND rr.attivo
         ORDER BY rr.riga_nr, rr.id, p.ddt_riga_componente_id NULLS FIRST, x.id
    LOOP
        -- Il costo dell'USCITA d'origine (D-3b-e): la merce rientra al valore al
        -- quale era uscita, e la media non si sposta per un andata-e-ritorno.
        -- Uscita senza costo (NULL) -> NULL, e vale la media: regola della primitiva.
        SELECT m.costo_unitario INTO v_costo
          FROM magazzino.movimenti m
         WHERE m.sorgente_tipo_id   = v_prel_src_id
           AND m.sorgente_id        = v_rientro.ddt_id
           AND m.sorgente_riga      = v_rientro.ddt_riga_id
           AND m.sorgente_dettaglio = v_rientro.prelievo_id
           AND m.qta < 0
           AND m.storno_di_movimento_id IS NULL
         ORDER BY m.id
         LIMIT 1;

        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id     => v_reso.magazzino_id,
            p_articolo_id      => v_rientro.articolo_id,
            p_causale          => 'CARICO_RESO_VEN',
            p_qta              => v_rientro.x_qta,
            p_sorgente_tipo_id => v_sorgente_id,
            p_sorgente_id      => v_prov_id,
            p_sorgente_uid     => v_prov_uid,
            p_sorgente_riga    => v_rientro.resi_riga_id,
            p_sorgente_dettaglio => v_rientro.id,
            p_costo_unitario   => v_costo,
            p_lotto_id         => v_rientro.lotto_id,
            p_asset_id         => v_rientro.asset_id,
            p_ubicazione_id    => v_rientro.ubicazione_id,
            p_data_mov         => script.fn_inizio_giorno_operativo(v_reso.data));
        rientro_id := v_rientro.id;
        qta        := v_rientro.x_qta;
        RETURN NEXT;
    END LOOP;
    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_posta_reso(p_reso_id bigint)
IS 'Il posting di un reso: un carico per rientro (provenienza: il reso RESO_VENDITA, la riga, il rientro come dettaglio; dal BB script.fn_sorgente_provenienza, brief-db-sorgente-documento-e-riga lotto M; D-3b-d), righe attive, in ordine di riga e di rientro. Nel magazzino del reso, causale CARICO_RESO_VEN, quantita'' positiva, articolo, lotto e seriale dal prelievo d''origine, ubicazione del rientro, data del reso. Il costo e'' quello dell''USCITA del prelievo d''origine (il movimento della bolla d''origine con quel prelievo come dettaglio, non uno storno: D-3b-e), passato alla primitiva come p_costo_unitario: la merce rientra al valore al quale era uscita; uscita senza costo -> NULL, e vale la media. Non ricontrolla (la primitiva e'' la rete, la check della merce ha gia'' parlato), non crea rientri, non guarda lo stato: QUANDO lo decide il verbo. SECURITY DEFINER, RISERVATA: ci si arriva solo da vendite.fn_conferma_reso. Ritorna (movimento_id, rientro_id, qta). Sta in vendite e non in magazzino: chi muove merce scrive il proprio posting e chiama la primitiva, il registro non legge le tabelle di un documento (D-2). Fino al 2026-10-01 era magazzino.fn_posta_reso. Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso (P-7), brief-db-magazzino-registro-anello-interno (P-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
