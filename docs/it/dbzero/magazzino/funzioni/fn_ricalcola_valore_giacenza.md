{% include-markdown "it/dbzero/magazzino/manual/fn_ricalcola_valore_giacenza.md" %}
# ⚙️ Funzione `fn_ricalcola_valore_giacenza`

```sql
CREATE FUNCTION fn_ricalcola_valore_giacenza(p_magazzino_id bigint, p_articolo_id uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_ricalcola_valore_giacenza(p_magazzino_id bigint, p_articolo_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(articolo_id uuid, magazzino_id bigint, valore_prima numeric, valore_dopo numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: riscrivere la COPIA del valore (valore_giacenza) dal registro, per
--   un magazzino (obbligatorio) e opzionalmente un articolo: RI-SOMMA
--   round(qta * costo_unitario, 6) — lo stesso arrotondamento della
--   primitiva — mai ri-esecuzione (i costi scritti sono fatti). Le copie
--   del magazzino senza movimenti si cancellano. Ritorna, riga per riga,
--   il valore prima e dopo (che cosa ha toccato).
-- DEFINER del PROPRIETARIO: scrive dove l'app non scrive. p_magazzino_id
--   obbligatorio: un magazzino e' di un emittente (7-sexies).
BEGIN
    IF p_magazzino_id IS NULL OR p_magazzino_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_ricalcola_valore_giacenza',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'magazzino obbligatorio e maggiore di zero', 'p_magazzino_id', p_magazzino_id),
            NULL::uuid, 'magazzino.fn_ricalcola_valore_giacenza', 'p_magazzino_id (obbligatorio, maggiore di zero)');
    END IF;

    RETURN QUERY
    WITH registro AS (
        SELECT m.articolo_id, m.magazzino_id,
               sum(round(m.qta * COALESCE(m.costo_unitario, 0), 6)) AS valore
          FROM magazzino.movimenti m
         WHERE m.magazzino_id = p_magazzino_id
           AND (p_articolo_id IS NULL OR m.articolo_id = p_articolo_id)
         GROUP BY m.articolo_id, m.magazzino_id
    ),
    prima AS (
        SELECT vg.articolo_id, vg.magazzino_id, vg.valore
          FROM magazzino.valore_giacenza vg
         WHERE vg.magazzino_id = p_magazzino_id
           AND (p_articolo_id IS NULL OR vg.articolo_id = p_articolo_id)
    ),
    scritte AS (
        INSERT INTO magazzino.valore_giacenza (articolo_id, magazzino_id, valore)
        SELECT r.articolo_id, r.magazzino_id, r.valore FROM registro r
        -- ON CONSTRAINT, non (articolo_id, magazzino_id): le colonne di RETURNS TABLE
        -- sono variabili PL/pgSQL e un elenco di colonne nudo sarebbe ambiguo.
        ON CONFLICT ON CONSTRAINT uq_mag_valore_giacenza_art_mag DO UPDATE SET valore = EXCLUDED.valore
        RETURNING magazzino.valore_giacenza.articolo_id,
                  magazzino.valore_giacenza.magazzino_id,
                  magazzino.valore_giacenza.valore
    ),
    tolte AS (
        -- una copia senza registro puo' venire solo da fuori porta
        DELETE FROM magazzino.valore_giacenza vg
         WHERE vg.magazzino_id = p_magazzino_id
           AND (p_articolo_id IS NULL OR vg.articolo_id = p_articolo_id)
           AND NOT EXISTS (SELECT 1 FROM registro r
                            WHERE r.articolo_id = vg.articolo_id AND r.magazzino_id = vg.magazzino_id)
        RETURNING vg.articolo_id, vg.magazzino_id
    )
    SELECT s.articolo_id, s.magazzino_id, p.valore, s.valore
      FROM scritte s
      LEFT JOIN prima p ON p.articolo_id = s.articolo_id AND p.magazzino_id = s.magazzino_id
    UNION ALL
    SELECT t.articolo_id, t.magazzino_id, p.valore, NULL::numeric
      FROM tolte t
      LEFT JOIN prima p ON p.articolo_id = t.articolo_id AND p.magazzino_id = t.magazzino_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_ricalcola_valore_giacenza(p_magazzino_id bigint, p_articolo_id uuid)
IS 'Riscrive la COPIA del valore (valore_giacenza) dal registro per un magazzino (obbligatorio: e'' di un emittente, 7-sexies) e opzionalmente un articolo: RI-SOMMA round(qta * costo_unitario, 6) — lo stesso arrotondamento del passo 14 della primitiva (C7), cosi'' copia e ri-somma coincidono per costruzione — mai ri-esecuzione: i costi scritti sono fatti (M-4). Le copie del magazzino senza movimenti si cancellano (possono venire solo da fuori porta). Ritorna le coppie toccate con valore prima e dopo (NULL dopo = tolta). DEFINER del PROPRIETARIO, non di un superuser: scrive dove l''app ha solo SELECT (D-L2-b). Brief: brief-db-magazzino-lotto-2-motore, sezione 4.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
