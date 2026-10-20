{% include-markdown "it/dbzero/vendite/manual/fn_af_merce_per_riga.md" %}
# ⚙️ Funzione `fn_af_merce_per_riga`

```sql
CREATE FUNCTION fn_af_merce_per_riga(p_segment_keys character varying[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_af_merce_per_riga(p_segment_keys character varying[] DEFAULT NULL::character varying[])
 RETURNS TABLE(corsia character varying, riga_id bigint, tipo_movimento character varying, quantita numeric, misurabile boolean, da_componenti boolean, voci integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 WITH chiavi AS MATERIALIZED (
          SELECT b.k,
             (((b.k)::text || '#'::text))::character varying AS k_dies,
             (((b.k)::text || '$'::text))::character varying AS k_hi
            FROM ( SELECT DISTINCT (split_part((u_1.k)::text, '#'::text, 1))::character varying AS k
                    FROM unnest(fn_af_merce_per_riga.p_segment_keys) u_1(k)
                   WHERE ((u_1.k IS NOT NULL) AND ((u_1.k)::text <> ''::text))) b
         ), ca_in AS (
          SELECT ca.id,
             ca.segment_key,
             ca.meta,
             ca.stato_emissione
            FROM (chiavi s
              JOIN vendite.commesse_attivita ca ON ((((ca.segment_base)::text = (s.k)::text) AND (((ca.segment_key)::text = (s.k)::text) OR (((ca.segment_key)::text ~>=~ (s.k_dies)::text) AND ((ca.segment_key)::text ~<~ (s.k_hi)::text))))))
           WHERE (fn_af_merce_per_riga.p_segment_keys IS NOT NULL)
         UNION ALL
          SELECT ca.id,
             ca.segment_key,
             ca.meta,
             ca.stato_emissione
            FROM vendite.commesse_attivita ca
           WHERE (fn_af_merce_per_riga.p_segment_keys IS NULL)
         ), base AS (
          SELECT af.quantita,
             af.tipo_movimento,
             script.fn_segment_key_sorgente(ca.segment_key) AS corsia,
             script.fn_segment_key_riga(ca.segment_key) AS riga_id,
             split_part((ca.segment_key)::text, '#CMP:'::text, 1) AS kit_key,
             ((ca.segment_key)::text ~~ '%#CMP:%'::text) AS e_componente,
                 CASE
                     WHEN ((ca.meta ->> 'coeff_qta'::text) ~ '^[0-9]+(\.[0-9]+){0,1}$'::text) THEN NULLIF(((ca.meta ->> 'coeff_qta'::text))::numeric, (0)::numeric)
                     ELSE NULL::numeric
                 END AS coeff_qta
            FROM (vendite.attivita_fatturabili af
              JOIN ca_in ca ON ((ca.id = af.commessa_attivita_id)))
           WHERE (((script.fn_segment_key_sorgente(ca.segment_key))::text = ANY (ARRAY['ORDINE_VENDITA'::text, 'DDT_VENDITA'::text])) AND (script.fn_segment_key_riga(ca.segment_key) IS NOT NULL) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text))
         ), kit AS (
          SELECT b.corsia,
             b.riga_id,
             b.tipo_movimento,
             b.kit_key,
             max((b.quantita / b.coeff_qta)) AS quantita_padre,
             (bool_and((b.coeff_qta IS NOT NULL)) AND (min((b.quantita / b.coeff_qta)) = max((b.quantita / b.coeff_qta)))) AS misurabile
            FROM base b
           WHERE b.e_componente
           GROUP BY b.corsia, b.riga_id, b.tipo_movimento, b.kit_key
         ), unita_padre AS (
          SELECT k.corsia,
             k.riga_id,
             k.tipo_movimento,
             k.quantita_padre AS quantita,
             k.misurabile,
             true AS da_componenti
            FROM kit k
         UNION ALL
          SELECT b.corsia,
             b.riga_id,
             b.tipo_movimento,
             b.quantita,
             true,
             false
            FROM base b
           WHERE (NOT b.e_componente)
         )
  SELECT u.corsia,
     u.riga_id,
     u.tipo_movimento,
     COALESCE(sum(u.quantita), (0)::numeric) AS quantita,
     bool_and(u.misurabile) AS misurabile,
     bool_or(u.da_componenti) AS da_componenti,
     (count(*))::integer AS voci
    FROM unita_padre u
   GROUP BY u.corsia, u.riga_id, u.tipo_movimento;
END

COMMENT ON FUNCTION vendite.fn_af_merce_per_riga(p_segment_keys character varying[])
IS 'IL CONTATORE DELLE ATTIVITA'' FATTURABILI PER RIGA DI DOCUMENTO, PER CHIAVE (D14 giro 4 — D5, 2026-09-21): lo stesso conto di vendite.vw_af_merce_per_riga — che ne e'' la proiezione senza filtro, fn_af_merce_per_riga(NULL) — ristretto alle CHIAVI DI SEGMENTO chieste. Il seme sono chiavi senza suffisso (''DDT:<uid>:R:<riga>'', ''ORD:<uid>:R:<riga>''): di ciascuna entrano la chiave esatta e le chiavi con un suffisso (#RET:<n>, #CMP:<id>, anche combinati) — la base e'' cio'' che precede il primo #, la stessa grammatica con cui il conto ricava riga_id e kit_key. NULL = tutte; un array VUOTO semina zero righe. Le chiavi sono NORMALIZZATE (la base prima del primo #, DISTINCT): un duplicato, o una chiave passata col suffisso accanto alla sua base, non raddoppia la somma. ⛔ LA FORMA DEL PREDICATO NON E'' STILE: commesse_attivita e'' sotto RLS e sotto una policy salgono nell''indice solo clausole interamente leakproof — `=` e gli operatori del pattern `~>=~`/`~<~` con il bordo PRECALCOLATO nella CTE MATERIALIZED `chiavi` (scritto nella clausola, `k || ''$''` sarebbe textcat, non leakproof); un LIKE non diventa MAI Index Cond sotto una policy (textlike non e'' leakproof), nemmeno a costante (provato il 21-09 come app). Il range [k#, k$) e'' esattamente «comincia per k#» (''$'' e'' il byte dopo ''#''): il vicino numerico :R:1 non prende :R:12. Indice: ix_commesse_attivita_segment_key con varchar_pattern_ops (90_end/20260921-50). Rami in UNION ALL, mai `p IS NULL OR`. BEGIN ATOMIC: dipendenze in pg_depend, catena RLS leggibile dal presidio security_invoker. INVOKER: la RLS resta di chi legge. Stesse 7 colonne e stessi numeri della vista (rev 20260818-73); tipo_movimento perde il typmod nel RETURNS e la vista lo ricasta. Chiamanti per chiave: fn_partite_merce (chiavi DDT delle origini O + chiavi ORD dei fulfillment della chiusura), fn_situazione_merce_ordine (chiavi ORD delle righe in uscita). Brief: brief-db-partita-merce-per-documento §11. ⭐ rev 2026-10-10 (20261010-81): si entra in commesse_attivita dall''UGUAGLIANZA su segment_base (la base della chiave, colonna generata di 20261010-80): texteq e'' leakproof e la stima viene dalle statistiche della colonna. Il predicato a intervallo resta come filtro residuo e implica l''uguaglianza: risultati identici. Perche'': con il seme come parametro (piano generico, dentro la capability del DDT) l''intervallo era stimato all''11 % della tabella per chiave e la tabella si leggeva per intero sotto la policy. brief-db-segment-base-commesse-attivita. Rev 2026-10-20 (20261020-86, brief-db-grammatica-unica-documenti 2e, G-8): la corsia e'' il codice della sorgente (ORDINE_VENDITA | DDT_VENDITA) e la riga si leggono dalla chiave con script.fn_segment_key_sorgente/_riga, non con split_part.';
```

---
{% include-markdown "signature-core.md" %}
