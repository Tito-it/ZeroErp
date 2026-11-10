{% include-markdown "it/dbzero/vendite/manual/fn_listini_attivi_uom_non_convertibili.md" %}
# ⚙️ Funzione `fn_listini_attivi_uom_non_convertibili`

```sql
CREATE FUNCTION fn_listini_attivi_uom_non_convertibili(p_articolo_id uuid, p_uom_id bigint, p_uom_altra_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listini_attivi_uom_non_convertibili(p_articolo_id uuid, p_uom_id bigint, p_uom_altra_id bigint)
 RETURNS TABLE(riga_id bigint, listino_versione_id bigint, listino_id bigint, articolo_id uuid, primo_giorno date, nel_perimetro boolean)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
BEGIN ATOMIC
 WITH r AS (
          SELECT lr.id,
             lr.listino_versione_id,
             lv.listino_id,
             lr.articolo_id,
             catalogo.fn_uom_primo_giorno_non_convertibile(lr.articolo_id, lr.uom_id, lv.validita) AS primo,
             script.fn_scope_ef_whitelist_via_listino_versione((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer, lr.listino_versione_id) AS visibile
            FROM (((vendite.listini_righe lr
              JOIN catalogo.articoli a ON ((a.id = lr.articolo_id)))
              JOIN vendite.listini_versioni lv ON ((lv.id = lr.listino_versione_id)))
              JOIN config.stati_doc_listino_versioni s ON ((s.id = lv.stato_doc_listino_versione_id)))
           WHERE (((s.codice_interno)::text = 'ATTIVA'::text) AND (lv.attivo IS TRUE) AND (lr.attivo IS TRUE) AND
                 CASE
                     WHEN (fn_listini_attivi_uom_non_convertibili.p_articolo_id IS NOT NULL) THEN ((lr.articolo_id = fn_listini_attivi_uom_non_convertibili.p_articolo_id) AND (lr.uom_id = fn_listini_attivi_uom_non_convertibili.p_uom_id))
                     ELSE (((lr.uom_id = fn_listini_attivi_uom_non_convertibili.p_uom_id) AND (a.uom_id = fn_listini_attivi_uom_non_convertibili.p_uom_altra_id)) OR ((lr.uom_id = fn_listini_attivi_uom_non_convertibili.p_uom_altra_id) AND (a.uom_id = fn_listini_attivi_uom_non_convertibili.p_uom_id)))
                 END)
         )
  SELECT
         CASE
             WHEN r.visibile THEN r.id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.listino_versione_id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.listino_id
             ELSE NULL::bigint
         END AS "case",
         CASE
             WHEN r.visibile THEN r.articolo_id
             ELSE NULL::uuid
         END AS "case",
     r.primo,
     COALESCE(r.visibile, false) AS "coalesce"
    FROM r
   WHERE (r.primo IS NOT NULL)
   ORDER BY COALESCE(r.visibile, false) DESC, r.primo, r.listino_id, r.id;
END

COMMENT ON FUNCTION vendite.fn_listini_attivi_uom_non_convertibili(p_articolo_id uuid, p_uom_id bigint, p_uom_altra_id bigint)
IS 'I prezzi di listino delle versioni ATTIVE che, con le conversioni di adesso, sono in un''unita'' che in un giorno del periodo della versione non si converte per l''articolo (catalogo.fn_uom_primo_giorno_non_convertibile): quelli che una mappatura o una conversione generale lascerebbe scoperti chiudendosi. Filtro: p_articolo_id valorizzato = la mappatura di quell''articolo, righe dell''articolo nell''unita'' p_uom_id; p_articolo_id NULL = la conversione generale fra p_uom_id e p_uom_altra_id, righe in una delle due unita'' di articoli la cui base e'' l''altra. Solo righe e versioni attive (attivo); una BOZZA la giudica l''attivazione (script.fn_check_versione_listino_attivabile), una CHIUSA non vende piu''. primo_giorno: il primo giorno scoperto. nel_perimetro: la riga sta nel perimetro di chi chiama (script.fn_scope_ef_whitelist_via_listino_versione, la regola della policy delle righe); fuori perimetro escono solo primo_giorno e nel_perimetro = false, gli altri campi sono NULL. Lettore: catalogo.trgfn_uom_guard_listini_attivi. SECURITY DEFINER con search_path bloccato: il catalogo e'' comune a tutte le aziende, i listini no. EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
