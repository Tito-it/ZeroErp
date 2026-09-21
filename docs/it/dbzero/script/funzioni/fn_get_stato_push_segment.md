{% include-markdown "it/dbzero/script/manual/fn_get_stato_push_segment.md" %}
# ⚙️ Funzione `fn_get_stato_push_segment`

```sql
CREATE FUNCTION fn_get_stato_push_segment(p_segment_key character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stato_push_segment(p_segment_key character varying)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (count(*) = 0) THEN 'LIBERA'::text
             WHEN bool_and(((ca.stato_emissione)::text = 'EMESSA'::text)) THEN 'EMESSA'::text
             ELSE 'ALLOCATA'::text
         END AS "case"
    FROM vendite.commesse_attivita ca
   WHERE (((ca.segment_key)::text = (fn_get_stato_push_segment.p_segment_key)::text) OR (((ca.segment_key)::text ~>=~ ((fn_get_stato_push_segment.p_segment_key)::text || '#CMP:'::text)) AND ((ca.segment_key)::text ~<~ ((fn_get_stato_push_segment.p_segment_key)::text || '#CMP;'::text))) OR (((ca.segment_key)::text ~>=~ ((fn_get_stato_push_segment.p_segment_key)::text || '#RET:'::text)) AND ((ca.segment_key)::text ~<~ ((fn_get_stato_push_segment.p_segment_key)::text || '#RET;'::text))));
END

COMMENT ON FUNCTION script.fn_get_stato_push_segment(p_segment_key character varying)
IS 'Classifica lo stato-push di una segment_key rispetto a vendite.commesse_attivita: LIBERA (mai instradata) / ALLOCATA (attivita'' presenti, non tutte emesse) / EMESSA (tutte fatturate). Fonte UNICA del predicato «gia'' inviato», consumata dalle fn_list_*_da_pushare (eleggibile <=> LIBERA), dalla diagnosi del DDT (colonna `segment`, da cui il lister deriva) e dai rami reason delle capability. Vede i suffissi dei componenti BoM (#CMP:) e, dal 2026-08-18, quelli delle RETTIFICHE (#RET:<n>, con o senza #CMP a seguire). ⚠️ Il suffisso di rettifica non e'' cosmesi: su una partita fatturata dalla corsia ORD il segmento DDT non ha attivita'' NORMALE e resterebbe LIBERA anche a nota di credito emessa — a impedire la ri-spinta ci sarebbe SOLO la cintura XOR sullo stato dell''ordine, e due cinture sono una mentre una e'' zero. brief-design-note-credito-resi N11. ⭐ rev 2026-09-21 (D14 giro 4, D8): il predicato e'' un RANGE sugli operatori del pattern (`~>=~`/`~<~`, a byte, leakproof) al posto dei due LIKE: commesse_attivita e'' sotto RLS e sotto una policy un LIKE non diventa mai Index Cond (textlike non e'' leakproof) — la lettura era una scansione intera con la policy valutata riga per riga, per OGNI riga della diagnosi. Con l''indice varchar_pattern_ops (90_end/20260921-50) e'' un BitmapOr di tre Index Cond sopra la policy. Semantica identica per le chiavi che riceve (nessun jolly `_`/`%`). BEGIN ATOMIC: dipendenze in pg_depend. ⛔ Niente LIKE nel corpo: pinnato da script/test-fn-get-stato-push-segment-v1.';
```

---
{% include-markdown "signature-core.md" %}
