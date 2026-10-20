{% include-markdown "it/dbzero/script/manual/vw_override_operatore_area.md" %}
# 🔍 View `vw_override_operatore_area`

> 📝 **Descrizione**
>
> Una riga per override di permesso SCRITTO di un operatore, con la sua area: AREA (config.user_override_aree), AZIONE (config.user_override_azioni, area dell'azione), OGGETTO (config.user_override_oggetti, area dell'oggetto a catalogo in config.area_model_overrides). (tipo, override_id) e' la chiave. Si contano gli override scritti, a prescindere dalla validita' temporale (D-2). Nessun filtro su attivo o riservato: il catalogo tiene attive le aree e le azioni che hanno override (block_deact, require_attivo) e la FK composita tiene a catalogo e non riservati gli oggetti, quindi ogni override scritto e' uno che il pannello mostra. Sede unica del conteggio degli override (totale della lista operatori, chip del riepilogo, badge del pannello): la legge script.fn_get_permessi_riepilogo_aree. security_invoker. Brief: brief-db-riepilogo-permessi-lista-operatori §3.1 (D-4, 2026-10-06).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_override_operatore_area
WITH (security_invoker=true) AS
SELECT uoa.auth_user_id,
    uoa.area_id,
    'AREA'::text AS tipo,
    uoa.id AS override_id
   FROM config.user_override_aree uoa
UNION ALL
 SELECT uoz.auth_user_id,
    ap.area_id,
    'AZIONE'::text AS tipo,
    uoz.id AS override_id
   FROM (config.user_override_azioni uoz
     JOIN config.azioni_processo ap ON ((ap.id = uoz.azione_id)))
UNION ALL
 SELECT uoo.auth_user_id,
    amo.area_id,
    'OGGETTO'::text AS tipo,
    uoo.id AS override_id
   FROM (config.user_override_oggetti uoo
     JOIN config.area_model_overrides amo ON ((((amo.app_label)::text = (uoo.app_label)::text) AND ((amo.model_name)::text = (uoo.model_name)::text))));
```

</div>


---
{% include-markdown "signature-core.md" %}
