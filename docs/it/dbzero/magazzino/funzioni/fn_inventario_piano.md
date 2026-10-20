{% include-markdown "it/dbzero/magazzino/manual/fn_inventario_piano.md" %}
# ⚙️ Funzione `fn_inventario_piano`

```sql
CREATE FUNCTION fn_inventario_piano(p_inventario_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_inventario_piano(p_inventario_id bigint)
 RETURNS TABLE(riga_id bigint, articolo_id uuid, ubicazione_id bigint, lotto_id bigint, asset_id bigint, qta_contata numeric, qta_sistema numeric, delta numeric, causale_codice_interno character varying, esito text, posting_blocco_reason text, posting_blocco_reason_key text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il PIANO di un inventario (D-L2-n) — che cosa il posting scrivera',
--   riga per riga e posizione per posizione — letto dal drawer al passaggio a
--   CONFIRM e da fn_posta_inventario per postare: una sede sola. Vedi il
--   COMMENT per il vocabolario di `esito`.
DECLARE
    v_magazzino_id magazzino.inventari.magazzino_id%TYPE;
BEGIN
    IF p_inventario_id IS NULL OR p_inventario_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_inventario_piano',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'inventario obbligatorio e maggiore di zero', 'p_inventario_id', p_inventario_id),
            NULL::uuid, 'magazzino.fn_inventario_piano', 'p_inventario_id (obbligatorio, maggiore di zero)');
    END IF;

    -- La testata, sotto RLS: fuori perimetro non c'e' => zero righe.
    SELECT i.magazzino_id INTO v_magazzino_id
      FROM magazzino.inventari i
     WHERE i.id = p_inventario_id;
    IF NOT FOUND THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH righe AS (
        SELECT r.id, r.articolo_id, r.ubicazione_id, r.lotto_id, r.asset_id,
               r.qta_contata
          FROM magazzino.inventari_righe r
         WHERE r.inventario_id = p_inventario_id
    ),
    -- Le posizioni a registro degli articoli contati, in questo magazzino.
    registro AS (
        SELECT m.articolo_id, m.ubicazione_id, m.lotto_id, m.asset_id,
               sum(m.qta) AS qta_sistema
          FROM magazzino.movimenti m
         WHERE m.magazzino_id = v_magazzino_id
           AND m.articolo_id IN (SELECT x.articolo_id FROM righe x)
         GROUP BY m.articolo_id, m.ubicazione_id, m.lotto_id, m.asset_id
    ),
    -- Gli articoli che in questo magazzino non hanno NESSUN movimento:
    -- per loro un delta > 0 e' il primo carico in assoluto (INV_INIZIALE).
    mai_movimentati AS (
        SELECT DISTINCT x.articolo_id
          FROM righe x
         WHERE NOT EXISTS (SELECT 1 FROM magazzino.movimenti m
                            WHERE m.magazzino_id = v_magazzino_id
                              AND m.articolo_id  = x.articolo_id)
    ),
    unione AS (
        SELECT r.id                                   AS riga_id,
               COALESCE(r.articolo_id,   g.articolo_id)   AS articolo_id,
               COALESCE(r.ubicazione_id, g.ubicazione_id) AS ubicazione_id,
               COALESCE(r.lotto_id,      g.lotto_id)      AS lotto_id,
               COALESCE(r.asset_id,      g.asset_id)      AS asset_id,
               r.qta_contata,
               COALESCE(g.qta_sistema, 0)             AS qta_sistema,
               CASE WHEN r.id IS NULL THEN NULL
                    ELSE r.qta_contata - COALESCE(g.qta_sistema, 0) END AS delta,
               CASE WHEN r.id IS NULL THEN '[]'::jsonb
                    ELSE script.fn_check_riga_magazzino(v_magazzino_id, r.articolo_id,
                                                        r.lotto_id, r.asset_id, r.ubicazione_id) END AS motivi
          FROM righe r
          FULL JOIN registro g
            ON  g.articolo_id   = r.articolo_id
            AND g.ubicazione_id IS NOT DISTINCT FROM r.ubicazione_id
            AND g.lotto_id      IS NOT DISTINCT FROM r.lotto_id
            AND g.asset_id      IS NOT DISTINCT FROM r.asset_id
         WHERE r.id IS NOT NULL OR g.qta_sistema <> 0
    )
    SELECT u.riga_id,
           u.articolo_id,
           u.ubicazione_id,
           u.lotto_id,
           u.asset_id,
           u.qta_contata,
           u.qta_sistema,
           u.delta,
           CASE
               WHEN u.riga_id IS NULL OR jsonb_array_length(u.motivi) > 0 OR u.delta = 0 THEN NULL
               WHEN u.delta > 0 AND EXISTS (SELECT 1 FROM mai_movimentati mm WHERE mm.articolo_id = u.articolo_id)
                    THEN 'INV_INIZIALE'::character varying
               WHEN u.delta > 0 THEN 'RETT_POS'::character varying
               ELSE 'RETT_NEG'::character varying
           END                                          AS causale_codice_interno,
           CASE
               WHEN u.riga_id IS NULL                   THEN 'NON_CONTATA'
               WHEN jsonb_array_length(u.motivi) > 0    THEN 'NON_POSTABILE'
               WHEN u.delta = 0                         THEN 'INVARIATA'
               WHEN u.delta > 0 AND EXISTS (SELECT 1 FROM mai_movimentati mm WHERE mm.articolo_id = u.articolo_id)
                                                        THEN 'INV_INIZIALE'
               WHEN u.delta > 0                         THEN 'RETT_POS'
               ELSE                                          'RETT_NEG'
           END                                          AS esito,
           u.motivi -> 0 ->> 'reason'                   AS posting_blocco_reason,
           u.motivi -> 0 ->> 'reason_key'               AS posting_blocco_reason_key
      FROM unione u
     ORDER BY u.riga_id NULLS LAST, u.articolo_id, u.ubicazione_id, u.lotto_id, u.asset_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_inventario_piano(p_inventario_id bigint)
IS 'Il PIANO di un inventario (D-L2-n): una riga per ogni posizione (articolo, ubicazione, lotto, asset — IS NOT DISTINCT FROM) che il registro del magazzino HA (giacenza <> 0) o che il conteggio NOMINA, per gli articoli contati, con qta_contata, qta_sistema (letto alla grana della riga, D-L2-f), delta, la causale che verra'' usata e l''esito: INV_INIZIALE (delta > 0 e nessun movimento dell''articolo in questo magazzino: primo carico), RETT_POS / RETT_NEG (contata con differenza), INVARIATA (delta zero: nessun movimento), NON_CONTATA (a registro, nessuna riga la copre: riga_id e qta_contata NULL, resta com''e'' — informazione, non blocco), NON_POSTABILE (C8: la primitiva la rifiuterebbe — posting_blocco_reason / _reason_key dal primo motivo di script.fn_check_riga_magazzino, la stessa funzione che la primitiva chiama). Una sede sola per UI e posting: fn_posta_inventario scrive qta_sistema DAL PIANO e posta le righe con delta <> 0. INVOKER, STABLE, sotto RLS: testata fuori perimetro = zero righe (il 404 lo da'' il BE sulla testata). Brief: brief-db-magazzino-lotto-2-motore, sezione 3 (D-L2-n), 6-ter C8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
