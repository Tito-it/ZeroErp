{% include-markdown "it/dbzero/vendite/manual/fn_fattura_origini.md" %}
# ⚙️ Funzione `fn_fattura_origini`

```sql
CREATE FUNCTION fn_fattura_origini(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_fattura_origini(p_fattura_id bigint)
 RETURNS TABLE(livello integer, tipo_id bigint, tipo_codice_interno character varying, etichetta character varying, uid text, codice text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_tipo_fattura config.sorgenti.id%TYPE;   -- per chiamare il lineage dalla fattura
    v_doc     record;     -- un documento di livello 1
    v_tab     record;     -- la sua tabella (config.fn_sorgente_tabella)
    -- Tipi nudi solo dove %TYPE non si puo' usare: la chiave di nodo
    -- e' CALCOLATA (id o uid a seconda di key_selector, sempre testo,
    -- come vendite.fn_documento_lineage.from_uid); gli array non
    -- accettano %TYPE[] (sintassi non valida), la colonna e' accanto.
    v_chiave  text;       -- la sua chiave di nodo (key_selector)
    v_semi_t  bigint[]  := ARRAY[]::bigint[];   -- config.sorgenti.id: i documenti di livello 1,
    v_semi_u  text[]    := ARRAY[]::text[];     -- chiave di nodo, in parallelo
    v_tipi    bigint[]  := ARRAY[]::bigint[];   -- config.sorgenti.id: i candidati,
    v_uids    text[]    := ARRAY[]::text[];     -- chiave di nodo,
    v_livelli integer[] := ARRAY[]::integer[];  -- e livello (fn_documento_lineage.livello), in parallelo
    i         integer;    -- indice del ciclo
BEGIN
    -- ==========================================================
    -- Scopo: i documenti a monte che una fattura cita (D-G1):
    --   i suoi genitori diretti di ogni tipo e i loro antenati,
    --   tenuti i tipi con config.sorgenti.citato_in_fattura.
    -- rev 2026-10-27 (20261027-22, brief-modello-documento-
    --   vendita §15.10): nasce, dalle righe fatturate.
    -- rev 2026-10-27 (20261027-26, §15.11, Q-F7): le sorgenti di
    --   ogni tipo (la nota di credito: archi N e S); la risalita
    --   non attraversa G e segue solo legami vivi.
    -- ==========================================================
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_fattura_origini',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_fattura_id', p_fattura_id),
            NULL::uuid, 'vendite.fn_fattura_origini',
            'p_fattura_id obbligatorio e maggiore di zero');
    END IF;

    -- (1a) Livello 1 dall'arco G: i documenti delle righe FATTURATE
    -- qui. La riga di commessa porta il suo, con la chiave
    -- <testata>.uid::text.
    FOR v_doc IN
        SELECT DISTINCT ca.sorgente_tipo_id AS t, ca.sorgente_uid AS u,
                        s.codice_interno, s.key_selector
          FROM vendite.fatture_righe fr
          JOIN vendite.attivita_fatturabili af ON af.fattura_riga_id = fr.id
          JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
          JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
         WHERE fr.fattura_id = p_fattura_id
           AND ca.sorgente_uid IS NOT NULL
    LOOP
        -- La chiave del nodo, dal registro: join alla tabella del
        -- documento sulla sua uid. Senza colonna uid la chiave della
        -- riga e' gia' quella del nodo.
        SELECT ft.schema_tabella, ft.nome_tabella, ft.relid
          INTO v_tab
          FROM config.fn_sorgente_tabella(v_doc.codice_interno) ft;
        IF v_tab.relid IS NULL THEN
            CONTINUE;
        END IF;

        IF EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_tab.relid AND a.attname = 'uid'
                      AND NOT a.attisdropped) THEN
            v_chiave := NULL;
            EXECUTE format('SELECT (x.%I)::text FROM %I.%I x WHERE x.uid::text = $1',
                           v_doc.key_selector, v_tab.schema_tabella, v_tab.nome_tabella)
               INTO v_chiave
              USING v_doc.u;
        ELSE
            v_chiave := v_doc.u;
        END IF;

        -- Un documento che chi legge non vede (RLS) non torna.
        CONTINUE WHEN v_chiave IS NULL;

        v_semi_t := v_semi_t || v_doc.t;
        v_semi_u := v_semi_u || v_chiave;
    END LOOP;

    -- (1b) Livello 1 dagli altri archi: i genitori diretti della
    -- fattura nel lineage, di qualunque tipo (la nota di credito:
    -- la fattura rettificata, arco N; il reso, arco S). G no: e' a
    -- grana di commessa, e lo sostituisce il passo (1a).
    SELECT s.id INTO v_tipo_fattura
      FROM config.sorgenti s
     WHERE s.codice_interno = 'FATTURA';

    -- Le due aggregazioni con lo stesso ORDER BY: gli array restano
    -- allineati (tipo i con chiave i).
    SELECT v_semi_t || coalesce(array_agg(l.from_tipo_id ORDER BY l.from_tipo_id, l.from_uid), ARRAY[]::bigint[]),
           v_semi_u || coalesce(array_agg(l.from_uid ORDER BY l.from_tipo_id, l.from_uid), ARRAY[]::text[])
      INTO v_semi_t, v_semi_u
      FROM (SELECT DISTINCT l0.from_tipo_id, l0.from_uid
              FROM vendite.fn_documento_lineage(v_tipo_fattura, p_fattura_id::text, 'indietro') l0
             WHERE l0.livello = 1
               AND l0.arco <> 'G'
               AND l0.is_legame_ritirato IS NOT TRUE) l;

    -- (2) Da ogni documento di livello 1, la risalita: solo legami
    -- vivi e mai attraverso G (dalla fattura rettificata si
    -- tornerebbe alla commessa intera). Livello = 1 + la distanza.
    FOR i IN 1 .. coalesce(cardinality(v_semi_t), 0) LOOP
        SELECT v_tipi || coalesce(array_agg(x.t), ARRAY[]::bigint[]),
               v_uids || coalesce(array_agg(x.u), ARRAY[]::text[]),
               v_livelli || coalesce(array_agg(x.liv), ARRAY[]::integer[])
          INTO v_tipi, v_uids, v_livelli
          FROM (
            WITH RECURSIVE e AS (
                SELECT l.from_tipo_id, l.from_uid, l.to_tipo_id, l.to_uid
                  FROM vendite.fn_documento_lineage(v_semi_t[i], v_semi_u[i], 'indietro') l
                 WHERE l.arco <> 'G'
                   AND l.is_legame_ritirato IS NOT TRUE
            ), r(t, u, dist) AS (
                SELECT v_semi_t[i], v_semi_u[i], 0
                UNION
                SELECT e.from_tipo_id, e.from_uid, r.dist + 1
                  FROM r
                  JOIN e ON e.to_tipo_id = r.t AND e.to_uid = r.u
                 WHERE r.dist < 10
            )
            SELECT r.t, r.u, 1 + min(r.dist) AS liv
              FROM r
             GROUP BY r.t, r.u
          ) x;
    END LOOP;

    -- ⛔ Nessun candidato: si esce QUI. Con due array NULL o vuoti
    --   il lettore dei nodi non va chiamato (senza seme risponde
    --   con TUTTI i nodi del sistema).
    IF cardinality(v_tipi) = 0 THEN
        RETURN;
    END IF;

    -- Ogni documento citato una volta, col livello piu' vicino;
    -- la decorazione dal lettore dei nodi (fuori gli annullati e
    -- quelli che chi legge non vede).
    RETURN QUERY
    WITH c AS (
        SELECT a.t, a.u, min(a.liv) AS liv
          FROM unnest(v_tipi, v_uids, v_livelli) a(t, u, liv)
          JOIN config.sorgenti s ON s.id = a.t
         WHERE s.citato_in_fattura
         GROUP BY a.t, a.u
    )
    SELECT c.liv, s.id, s.codice_interno, s.etichetta, c.u, n.codice::text
      FROM c
      JOIN vendite.fn_documento_lineage_nodi(v_tipi, v_uids) n
        ON n.tipo_id = c.t AND n.uid = c.u
      JOIN config.sorgenti s ON s.id = c.t
     WHERE n.is_abortito IS NOT TRUE
     ORDER BY c.liv, s.codice_interno, n.codice, c.u;
END;
$function$

COMMENT ON FUNCTION vendite.fn_fattura_origini(p_fattura_id bigint)
IS 'Le ORIGINI di una fattura (D-G1 = c, Q-F6 = b, Q-F7): i documenti a monte che la fattura cita, di qualunque tipo — DDT, ordine, contratto, offerta, preventivo; per la nota di credito la fattura rettificata e il reso —, non la commessa, che per il cliente e'' un contenitore interno. Livello 1 = i genitori diretti della fattura nel lineage; l''arco G (commessa -> fattura), a grana di commessa, e'' sostituito dai documenti delle righe FATTURATE (la riga di commessa di ogni attivita'' fatturabile porta il suo documento, chiave <testata>.uid tradotta nella chiave del nodo con config.sorgenti.key_selector e un join alla tabella del documento). Poi la risalita del lineage all''indietro (vendite.fn_documento_lineage) da ogni documento di livello 1, solo per legami vivi e mai attraverso G: dalla fattura rettificata si tornerebbe alla commessa intera, e una fattura citata porta gia'' i suoi riferimenti. Tiene i soli tipi con config.sorgenti.citato_in_fattura: quali tipi si citano e'' un dato del registro. Ogni documento una volta, col livello piu'' vicino (P-3, l''unione); fuori gli annullati (stato abortito) e i documenti che chi legge non vede (INVOKER, come il lineage). Ordine: livello, tipo, codice. Una fattura senza documenti a monte risponde zero righe. La leggono la stampa e il dettaglio della fattura. Brief: brief-modello-documento-vendita §15.10, §15.11 (Tid 2026-10-27).';
```

</div>

---
{% include-markdown "signature-core.md" %}
