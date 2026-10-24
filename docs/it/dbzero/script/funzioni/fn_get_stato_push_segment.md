{% include-markdown "it/dbzero/script/manual/fn_get_stato_push_segment.md" %}
# ⚙️ Funzione `fn_get_stato_push_segment`

```sql
CREATE FUNCTION fn_get_stato_push_segment(p_segment_key character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

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
   WHERE (((ca.segment_base)::text = split_part((fn_get_stato_push_segment.p_segment_key)::text, '#'::text, 1)) AND (((ca.segment_key)::text = (fn_get_stato_push_segment.p_segment_key)::text) OR (((ca.segment_key)::text ~>=~ ((fn_get_stato_push_segment.p_segment_key)::text || '#CMP:'::text)) AND ((ca.segment_key)::text ~<~ ((fn_get_stato_push_segment.p_segment_key)::text || '#CMP;'::text))) OR (((ca.segment_key)::text ~>=~ ((fn_get_stato_push_segment.p_segment_key)::text || '#RET:'::text)) AND ((ca.segment_key)::text ~<~ ((fn_get_stato_push_segment.p_segment_key)::text || '#RET;'::text)))) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text));
END

COMMENT ON FUNCTION script.fn_get_stato_push_segment(p_segment_key character varying)
IS 'Classifica lo stato-push di una segment_key rispetto a vendite.commesse_attivita: LIBERA (nessuna attivita'' viva: mai instradata, o instradata e ritirata) / ALLOCATA (attivita'' vive presenti, non tutte emesse) / EMESSA (attivita'' vive tutte fatturate). Fonte UNICA del predicato «gia'' inviato», consumata dalle fn_list_*_da_pushare (eleggibile <=> LIBERA), dalla diagnosi del DDT (colonna `segment`, da cui il lister deriva), dai rami reason delle capability e, dal 2026-10-12, da vendite.vw_preventivi_righe_smistabili_commessa, vendite.vw_preventivi_smistamento_righe e vendite.fn_list_consumi_da_pushare, che prima avevano un predicato proprio. Vede i suffissi dei componenti BoM (#CMP:) e, dal 2026-08-18, quelli delle RETTIFICHE (#RET:<n>, con o senza #CMP a seguire). ⚠️ Il suffisso di rettifica non e'' cosmesi: su una partita fatturata dalla corsia ORD il segmento DDT non ha attivita'' NORMALE e resterebbe LIBERA anche a nota di credito emessa — a impedire la ri-spinta ci sarebbe SOLO la cintura XOR sullo stato dell''ordine, e due cinture sono una mentre una e'' zero. brief-design-note-credito-resi N11. ⭐ rev 2026-09-21 (D14 giro 4, D8): il predicato e'' un RANGE sugli operatori del pattern (`~>=~`/`~<~`, a byte, leakproof) al posto dei due LIKE: commesse_attivita e'' sotto RLS e sotto una policy un LIKE non diventa mai Index Cond (textlike non e'' leakproof). Con l''indice varchar_pattern_ops (90_end/20260921-50) e'' un BitmapOr di tre Index Cond sopra la policy. BEGIN ATOMIC: dipendenze in pg_depend. ⛔ Niente LIKE nel corpo: pinnato da script/test-fn-get-stato-push-segment-v1. ⭐ rev 2026-10-10 (20261010-82): si entra in commesse_attivita dall''UGUAGLIANZA su segment_base = split_part(p_segment_key, ''#'', 1) (colonna generata di 20261010-80, indicizzata): texteq e'' leakproof e la stima viene dalle statistiche. brief-db-segment-base-commesse-attivita. ⭐ rev 2026-10-12 (20261012-08, brief-db-annullo-a-valle-riapre-a-monte D-5 di Tid): una riga ANNULLATA non occupa piu'' il segmento. Prima contava come allocata, e il ritiro delle righe all''annullo della commessa lasciava il documento a monte consumato per sempre. Sicuro sul modello: una riga ANNULLATA con sorgente nasce dal ritiro all''annullo del documento a monte (morto, escluso dai lister per stato) o della commessa (il documento a monte deve tornare spingibile); ANNULLATA e'' irreversibile. Scritto «<> ''ANNULLATA''» e non come elenco degli stati vivi: uno stato nuovo OCCUPA, solo il ritiro libera. Effetto (N11): un accredito annullato nella corsia ORD riporta il segmento della bolla a LIBERA, com''era prima dell''accredito.';
```

</div>

---
{% include-markdown "signature-core.md" %}
