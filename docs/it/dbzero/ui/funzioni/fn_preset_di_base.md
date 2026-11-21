{% include-markdown "it/dbzero/ui/manual/fn_preset_di_base.md" %}
# ⚙️ Funzione `fn_preset_di_base`

```sql
CREATE FUNCTION fn_preset_di_base(p_famiglia text, p_contenitore_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_preset_di_base(p_famiglia text, p_contenitore_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo, p_emittente_fiscale_id bigint)
 RETURNS TABLE(preset_id integer, ambito ui.ambito_preset, contenuto_aggiornato_il jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 WITH profili AS MATERIALIZED (
          SELECT pa.profilo_accesso_id,
             pa.priorita
            FROM script.fn_get_profili_accesso_applicabili(fn_preset_di_base.p_auth_user_id, fn_preset_di_base.p_veste) pa(profilo_accesso_id, priorita)
           WHERE (fn_preset_di_base.p_veste IS NOT NULL)
         ), candidati AS (
          SELECT lp.id,
             lp.ambito,
             lp.profilo_accesso_id,
             lp.emittente_fiscale_id,
             lp.contenuto_aggiornato_il
            FROM ui.lista_preset lp
           WHERE ((fn_preset_di_base.p_famiglia = 'lista'::text) AND (lp.lista_id = fn_preset_di_base.p_contenitore_id) AND lp.attivo AND (EXISTS ( SELECT 1
                    FROM (ui.lista_preset_colonna pc
                      JOIN ui.lista_colonna lc ON ((lc.id = pc.colonna_id)))
                   WHERE ((pc.preset_id = lp.id) AND lc.attivo))))
         UNION ALL
          SELECT dp.id,
             dp.ambito,
             dp.profilo_accesso_id,
             dp.emittente_fiscale_id,
             dp.contenuto_aggiornato_il
            FROM ui.dashboard_preset dp
           WHERE ((fn_preset_di_base.p_famiglia = 'dashboard'::text) AND (dp.dashboard_id = fn_preset_di_base.p_contenitore_id) AND dp.attivo AND (EXISTS ( SELECT 1
                    FROM ((ui.dashboard_preset_widget pw
                      JOIN ui.widget w ON ((w.id = pw.widget_id)))
                      JOIN ui.dashboard_widget dw ON (((dw.dashboard_id = dp.dashboard_id) AND (dw.widget_id = w.id))))
                   WHERE ((pw.preset_id = dp.id) AND w.attivo))))
         )
  SELECT c.id,
     c.ambito,
     c.contenuto_aggiornato_il
    FROM (candidati c
      LEFT JOIN profili pr ON (((c.ambito = 'ruolo'::ui.ambito_preset) AND (pr.profilo_accesso_id = c.profilo_accesso_id))))
   WHERE (((c.ambito = 'ruolo'::ui.ambito_preset) AND (pr.profilo_accesso_id IS NOT NULL)) OR ((c.ambito = 'emittente_fiscale'::ui.ambito_preset) AND (c.emittente_fiscale_id = fn_preset_di_base.p_emittente_fiscale_id) AND (EXISTS ( SELECT 1
            FROM anagrafiche.emittenti_fiscali ef
           WHERE ((ef.id = c.emittente_fiscale_id) AND ef.attivo)))) OR (c.ambito = 'sistema'::ui.ambito_preset))
   ORDER BY
         CASE c.ambito
             WHEN 'ruolo'::ui.ambito_preset THEN 1
             WHEN 'emittente_fiscale'::ui.ambito_preset THEN 2
             ELSE 3
         END, pr.priorita
  LIMIT 1;
END

COMMENT ON FUNCTION ui.fn_preset_di_base(p_famiglia text, p_contenitore_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo, p_emittente_fiscale_id bigint)
IS 'Il preset di base di una lista (p_famiglia = ''lista'') o di una dashboard (''dashboard'') per un utente: lo standard delle chiavi che la preferenza non ha, e la base del banner del preset aggiornato. Un candidato vale se e'' acceso e ha contenuto: almeno una colonna attiva; per la dashboard almeno un widget acceso che sta nel pool. Ordine: il preset di ruolo del profilo applicabile piu'' prioritario, solo con la veste valorizzata (con la veste NULL il passo del ruolo si salta: il ripiego non allarga e non sceglie per id); poi quello dell''azienda p_emittente_fiscale_id, se l''azienda e'' accesa; poi quello di sistema. Un posto ha al piu'' un preset acceso (uq_ui_lista_preset_posto, uq_ui_dashboard_preset_posto): la scelta e'' deterministica. Una riga (id, ambito, contenuto_aggiornato_il: la mappa {chiave: data} del contenuto del preset) o nessuna. La leggono ui.fn_resolve_lista_config e ui.fn_resolve_dashboard_config. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
