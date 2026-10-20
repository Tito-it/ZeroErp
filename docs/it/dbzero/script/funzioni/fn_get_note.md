{% include-markdown "it/dbzero/script/manual/fn_get_note.md" %}
# ⚙️ Funzione `fn_get_note`

```sql
CREATE FUNCTION fn_get_note(p_note_table regclass, _target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_note(p_note_table regclass, _target_tipo text, _target_id bigint, _target_riga_id bigint DEFAULT NULL::bigint, _include_doc boolean DEFAULT true, _include_righe boolean DEFAULT true, _only_visible boolean DEFAULT true)
 RETURNS TABLE(target_tipo text, target_id bigint, target_riga_id bigint, anchor_tipo text, posizione text, seq integer, testo text, testo_md text, stile character varying, lingua character varying, visibile boolean, solo_stampa boolean, meta jsonb, data_insert timestamp with time zone, user_insert text, data_update timestamp with time zone, user_update text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  sql text;
BEGIN
  /*
    Funzione generica per estrarre note normalizzate da una tabella *.note:
    - p_note_table: regclass della tabella (es. 'vendite.note'::regclass)
    - lingua  da config.lingue (l.codice_iso) via id_lingua
    - stile   da config.note_stili (s.codice) via id_stile
  */
  sql := $q$
    SELECT
      n.target_tipo,
      n.target_id,
      n.target_riga_id,
      n.anchor_tipo,
      n.posizione,
      n.seq,
      n.testo,
      n.testo_md,
      s.codice                      AS stile,
      l.codice_iso                  AS lingua,
      n.visibile,
      n.solo_stampa,
      n.meta,
      n.data_insert,
      n.user_insert,
      n.data_update,
      n.user_update
    FROM %s AS n
    JOIN config.note_stili AS s
      ON s.id = n.id_stile
    LEFT JOIN config.lingue AS l
      ON l.id = n.id_lingua
    WHERE n.target_tipo = UPPER($1)
      AND n.target_id   = $2
      AND ($3 IS NULL OR n.target_riga_id = $3)
      AND (
            ($4 AND n.anchor_tipo = 'DOCUMENTO')
         OR ($5 AND n.anchor_tipo = 'RIGA')
      )
      AND (NOT $6 OR n.visibile IS TRUE)
    ORDER BY
      CASE n.anchor_tipo WHEN 'DOCUMENTO' THEN 1 ELSE 2 END,
      n.posizione,
      n.seq,
      n.id
  $q$;

  RETURN QUERY
  EXECUTE format(sql, p_note_table::text)
  USING _target_tipo, _target_id, _target_riga_id, _include_doc, _include_righe, _only_visible;
END;
$function$

COMMENT ON FUNCTION script.fn_get_note(p_note_table regclass, _target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
IS 'Funzione generica: legge note normalizzate da una tabella *.note (passata come regclass); stile/lingua da domini. La lingua esce com''e'' (varchar), senza il cast a char(5) che la riempiva di spazi (20261010-35).';
```

</div>

---
{% include-markdown "signature-core.md" %}
