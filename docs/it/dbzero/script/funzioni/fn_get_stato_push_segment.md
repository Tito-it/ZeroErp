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
--   le attivita' dei componenti BoM (suffisso '#CMP:<id>'):
--     LIBERA   = nessuna attivita' (riga mai instradata)
--     ALLOCATA = attivita' presenti, non tutte EMESSE (in attesa
--                di fatturazione; ANNULLATA conta come allocata)
--     EMESSA   = attivita' presenti e tutte fatturate
--   Single source del predicato "gia' inviato": consumata dalle
--   fn_list_*_da_pushare (eleggibile <=> LIBERA) e dai rami
--   reason delle capability (brief-db-push-commessa-gia-inviato).
SELECT CASE
         WHEN count(*) = 0 THEN 'LIBERA'
         WHEN bool_and(ca.stato_emissione = 'EMESSA') THEN 'EMESSA'
         ELSE 'ALLOCATA'
       END
  FROM vendite.commesse_attivita ca
 WHERE ca.segment_key = p_segment_key
    OR ca.segment_key LIKE p_segment_key || '#CMP:%';
$function$

COMMENT ON FUNCTION script.fn_get_stato_push_segment(p_segment_key character varying)
IS 'Classificatore condiviso dello stato-push di una segment_key riga-documento su vendite.commesse_attivita, inclusi i componenti BoM (match uguaglianza O prefisso #CMP:%): LIBERA = mai instradata; ALLOCATA = attivita'' presenti non tutte fatturate (ANNULLATA inclusa: instradata = esclusa, decisione preventivi 2026-06-28); EMESSA = tutte fatturate. Il parametro e'' la segment_key EMESSA dalla push-list (per i contratti include :M:<mese> — push ricorrente mensile by design). Consumatori: fn_list_{ordini,ddt,contratti}_da_pushare (eleggibile <=> LIBERA) e rami reason di fn_available_actions_{ordine,ddt} (ALLOCATA -> GIA_INVIATO, EMESSA -> GIA_FATTURATO). Brief: brief-db-push-commessa-gia-inviato §4b Rev 1, rilievo ORD0000227.';
```

---
{% include-markdown "signature-core.md" %}
