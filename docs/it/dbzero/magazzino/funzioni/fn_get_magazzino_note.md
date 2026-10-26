{% include-markdown "it/dbzero/magazzino/manual/fn_get_magazzino_note.md" %}
# ⚙️ Funzione `fn_get_magazzino_note`

```sql
CREATE FUNCTION fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint DEFAULT NULL::bigint, _include_doc boolean DEFAULT true, _include_righe boolean DEFAULT true, _only_visible boolean DEFAULT true)
 RETURNS TABLE(target_tipo character varying, target_id bigint, target_riga_id bigint, anchor_tipo character varying, posizione character varying, seq integer, testo text, testo_md text, stile character varying, lingua character varying, visibile boolean, solo_stampa boolean, meta jsonb, data_insert timestamp with time zone, user_insert text, data_update timestamp with time zone, user_update text)
 LANGUAGE sql
 STABLE
AS $function$
 ------------------------------------------------------
 -- Funzione generica per estrarre note per target_tipo/target_id
 ------------------------------------------------------
  SELECT
    n.target_tipo,
    n.target_id,
    n.target_riga_id,
    n.anchor_tipo,
    n.posizione,
    n.seq,
    n.testo,
    n.testo_md,
    n.stile,
    n.lingua,
    n.visibile,
    n.solo_stampa,
    n.meta,
    n.data_insert,
    n.user_insert,
    n.data_update,
    n.user_update
  FROM magazzino.note AS n
  WHERE n.target_tipo = upper(_target_tipo)
    AND n.target_id   = _target_id
    AND (_target_riga_id IS NULL OR n.target_riga_id = _target_riga_id)
    AND (
          (_include_doc   AND n.anchor_tipo = 'DOCUMENTO')
       OR (_include_righe AND n.anchor_tipo = 'RIGA')
    )
    AND (_only_visible IS FALSE OR n.visibile IS TRUE)
  ORDER BY
    -- ordina prima DOCUMENTO poi RIGA, mantenendo il rendering naturale
    CASE n.anchor_tipo WHEN 'DOCUMENTO' THEN 1 ELSE 2 END,
    n.posizione,
    n.seq,
    n.id;  -- id come tie-breaker
$function$

COMMENT ON FUNCTION magazzino.fn_get_magazzino_note(_target_tipo text, _target_id bigint, _target_riga_id bigint, _include_doc boolean, _include_righe boolean, _only_visible boolean)
IS 'Estrae note per target_tipo/target_id (opz. riga), con filtri per DOCUMENTO/RIGA e visibilità.';
```

</div>

---
{% include-markdown "signature-core.md" %}
