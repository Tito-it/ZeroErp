{% include-markdown "it/dbzero/script/manual/fn_get_permessi_riepilogo_aree.md" %}
# ⚙️ Funzione `fn_get_permessi_riepilogo_aree`

```sql
CREATE FUNCTION fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])
 RETURNS TABLE(auth_user_id integer, area_id integer, livello config.livello_accesso, override_count integer, voci_limitate integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il riepilogo per area di un insieme di operatori (la pagina della lista):
--   livello effettivo, override scritti, voci fermate dal tetto d'area
--   (brief-db-riepilogo-permessi-lista-operatori §3.2). Legge le sedi uniche:
--   fn_resolve_livello_area, vw_override_operatore_area,
--   fn_get_permessi_effettivi_azioni e fn_get_permessi_effettivi_oggetti.
BEGIN
    RETURN QUERY
    WITH utenti AS (
        -- Gli operatori chiesti, una volta ciascuno.
        SELECT DISTINCT u.u_id
          FROM unnest(p_auth_user_ids) u(u_id)
         WHERE u.u_id IS NOT NULL
    ),
    aree AS (
        SELECT af.id AS a_id, af.schema_db AS a_schema,
               af.ordinamento AS a_ordinamento, af.codice AS a_codice
          FROM config.aree_funzionali af
         WHERE af.attivo
    ),
    overrides AS (
        -- §3.1: gli override scritti, per (utente, area).
        SELECT o.auth_user_id AS o_user, o.area_id AS o_area, count(*) AS o_n
          FROM script.vw_override_operatore_area o
          JOIN utenti u ON u.u_id = o.auth_user_id
         GROUP BY o.auth_user_id, o.area_id
    ),
    limitate AS (
        -- Le voci che il tetto ferma: le risposte delle due sedi, contate.
        SELECT u.u_id AS l_user, e.area_id AS l_area
          FROM utenti u
         CROSS JOIN LATERAL script.fn_get_permessi_effettivi_azioni(u.u_id) e
         WHERE e.limitata_da_area
        UNION ALL
        SELECT u.u_id, af.id
          FROM utenti u
         CROSS JOIN LATERAL script.fn_get_permessi_effettivi_oggetti(u.u_id) e
          JOIN config.aree_funzionali af ON af.schema_db = e.area_schema_db
         WHERE e.limitato_da_area
    ),
    limitate_n AS (
        SELECT l.l_user, l.l_area, count(*) AS l_n
          FROM limitate l
         GROUP BY l.l_user, l.l_area
    )
    SELECT u.u_id,
           a.a_id,
           script.fn_resolve_livello_area(u.u_id, a.a_schema),
           COALESCE(o.o_n, 0)::integer,
           COALESCE(ln.l_n, 0)::integer
      FROM utenti u
     CROSS JOIN aree a
      LEFT JOIN overrides o
        ON o.o_user = u.u_id AND o.o_area = a.a_id
      LEFT JOIN limitate_n ln
        ON ln.l_user = u.u_id AND ln.l_area = a.a_id
     ORDER BY u.u_id, a.a_ordinamento, a.a_codice;
END;
$function$

COMMENT ON FUNCTION script.fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])
IS 'Il riepilogo permessi per area di un insieme di operatori (gli id della pagina della lista operatori): una riga per (operatore, area attiva), anche a zero override. livello = script.fn_resolve_livello_area; override_count = override scritti (script.vw_override_operatore_area, D-2); voci_limitate = azioni con limitata_da_area (script.fn_get_permessi_effettivi_azioni; un''azione spenta non puo'' esserlo: override e profili ne bloccano la disattivazione) + oggetti con limitato_da_area (script.fn_get_permessi_effettivi_oggetti). Non ricalcola il tetto e non aggiunge rami: super admin, veste spenta e gate di contesto rispondono come le funzioni lette. Duplicati e NULL nell''array si ignorano; array vuoto o NULL -> zero righe. Ordine: operatore, area per ordinamento e codice. plpgsql, STABLE, INVOKER. Brief: brief-db-riepilogo-permessi-lista-operatori §3.2 (2026-10-06).';
```

</div>

---
{% include-markdown "signature-core.md" %}
