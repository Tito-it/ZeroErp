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
AS $function$
-- Scopo: classificare lo stato-push della segment_key di una riga
--   documento rispetto a vendite.commesse_attivita, vedendo anche
--   le attivita' dei componenti BoM (suffisso '#CMP:<id>') e le
--   RETTIFICHE (suffisso '#RET:<n>', dal 2026-08-18):
--     LIBERA   = nessuna attivita' (riga mai instradata)
--     ALLOCATA = attivita' presenti, non tutte EMESSE (in attesa
--                di fatturazione; ANNULLATA conta come allocata)
--     EMESSA   = attivita' presenti e tutte fatturate
--   Single source del predicato "gia' inviato": consumata dalle
--   fn_list_*_da_pushare (eleggibile <=> LIBERA) e dai rami
--   reason delle capability (brief-db-push-commessa-gia-inviato).
-- rev 2026-08-18 (brief nota di credito, N11): il suffisso
--   '#RET:%' copre sia la rettifica semplice sia quella per
--   componente, perche' '#CMP:' viene DOPO '#RET:<n>'.
--   ⚠️ Su una partita fatturata dalla corsia ORD il segmento DDT
--   non ha attivita' NORMALE e resterebbe LIBERA anche a nota di
--   credito emessa: a impedire la ri-spinta ci sarebbe SOLO la
--   cintura XOR sullo stato dell'ordine. Due cinture sono una;
--   una e' zero.
SELECT CASE
         WHEN count(*) = 0 THEN 'LIBERA'
         WHEN bool_and(ca.stato_emissione = 'EMESSA') THEN 'EMESSA'
         ELSE 'ALLOCATA'
       END
  FROM vendite.commesse_attivita ca
 WHERE ca.segment_key = p_segment_key
    OR ca.segment_key LIKE p_segment_key || '#CMP:%'
    OR ca.segment_key LIKE p_segment_key || '#RET:%';
$function$

COMMENT ON FUNCTION script.fn_get_stato_push_segment(p_segment_key character varying)
IS 'Classifica lo stato-push di una segment_key rispetto a vendite.commesse_attivita: LIBERA (mai instradata) / ALLOCATA (attivita'' presenti, non tutte emesse) / EMESSA (tutte fatturate). Fonte UNICA del predicato «gia'' inviato», consumata dalle fn_list_*_da_pushare (eleggibile <=> LIBERA) e dai rami reason delle capability. Vede i suffissi dei componenti BoM (#CMP:) e, dal 2026-08-18, quelli delle RETTIFICHE (#RET:<n>, con o senza #CMP a seguire). ⚠️ Il suffisso di rettifica non e'' cosmesi: su una partita fatturata dalla corsia ORD il segmento DDT non ha attivita'' NORMALE e resterebbe LIBERA anche a nota di credito emessa — a impedire la ri-spinta ci sarebbe SOLO la cintura XOR sullo stato dell''ordine, e due cinture sono una mentre una e'' zero. brief-design-note-credito-resi N11.';
```

---
{% include-markdown "signature-core.md" %}
