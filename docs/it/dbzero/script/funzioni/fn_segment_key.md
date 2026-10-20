# ⚙️ Funzione `fn_segment_key`

```sql
CREATE FUNCTION fn_segment_key(p_sorgente character varying, p_uid text, p_riga bigint, p_mese date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_segment_key(p_sorgente character varying, p_uid text, p_riga bigint DEFAULT NULL::bigint, p_mese date DEFAULT NULL::date)
 RETURNS character varying
 LANGUAGE sql
 STABLE
AS $function$
-- =========================================================
-- Scopo: costruire la chiave d'idempotenza del push di un
--   documento verso la commessa: <sorgente>:<uid>[:R:<riga>]
--   [:M:<AAAA-MM>]. Il SOLO costruttore (G-8, regola del 2).
-- Parametri: p_sorgente il codice della sorgente (ORDINE_VENDITA,
--   DDT_VENDITA, PREVENTIVO, CONTRATTO, ATTIVITA_CONSUMI); p_uid
--   l'uid della testata; p_riga e p_mese facoltativi.
-- ⚠️ STABLE e non IMMUTABLE: to_char lo e'. Nessun SET: il
--   planner la espande in linea.
-- ⚠️ I suffissi (#CMP:<componente> del kit, #RET:<...> della
--   rettifica) li aggiunge chi scrive quella riga, alla chiave
--   che riceve da qui.
-- Brief: brief-db-grammatica-unica-documenti §13.3 (2e).
-- =========================================================
SELECT p_sorgente || ':' || p_uid
       || COALESCE(':R:' || p_riga::text, '')
       || COALESCE(':M:' || to_char(p_mese, 'YYYY-MM'), '');
$function$

COMMENT ON FUNCTION script.fn_segment_key(p_sorgente character varying, p_uid text, p_riga bigint, p_mese date)
IS 'La chiave d''idempotenza del push verso la commessa: <sorgente>:<uid>[:R:<riga>][:M:<AAAA-MM>], col codice della sorgente come prefisso (G-8). Il SOLO costruttore; i suffissi #CMP:/#RET: li aggiunge chi scrive la riga. LANGUAGE sql STABLE senza SET: si espande in linea. Brief: brief-db-grammatica-unica-documenti §13.3.';
```

---
{% include-markdown "signature-core.md" %}
