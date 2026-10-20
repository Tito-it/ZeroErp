# ⚙️ Funzione `fn_segment_key_sorgente`

```sql
CREATE FUNCTION fn_segment_key_sorgente(p_segment_key character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_segment_key_sorgente(p_segment_key character varying)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- =========================================================
-- Scopo: il documento da cui viene una riga di commessa, letto
--   dalla sua chiave: il codice della sorgente (DDT_VENDITA,
--   ORDINE_VENDITA, ...), oppure MAN per le righe a mano.
-- ⭐ Perche' dalla chiave e non da sorgente_tipo_id (L2e-2 =
--   (a)): le rettifiche da reso e gli oneri non hanno sorgente
--   per progetto (chk_commesse_attivita_senza_sorgente_onere_
--   rettifica), e la rettifica conta nella merce della bolla.
--   Il documento sta solo nella chiave.
-- ⚠️ Il prefisso finisce al primo ':': un codice di sorgente
--   non contiene ':'. Nessun SET: si espande in linea.
-- Brief: brief-db-grammatica-unica-documenti §13.3 (2e).
-- =========================================================
SELECT split_part(p_segment_key, ':', 1);
$function$

COMMENT ON FUNCTION script.fn_segment_key_sorgente(p_segment_key character varying)
IS 'Il documento da cui viene una riga di commessa, letto dalla chiave: il codice della sorgente (o MAN). Dalla chiave e non da sorgente_tipo_id perche'' rettifiche e oneri non hanno sorgente per progetto (L2e-2 = (a)). LANGUAGE sql IMMUTABLE senza SET: si espande in linea. Brief: brief-db-grammatica-unica-documenti §13.3.';
```

---
{% include-markdown "signature-core.md" %}
