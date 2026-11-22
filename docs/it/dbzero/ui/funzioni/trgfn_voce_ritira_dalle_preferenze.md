{% include-markdown "it/dbzero/ui/manual/trgfn_voce_ritira_dalle_preferenze.md" %}
# ⚙️ Funzione `trgfn_voce_ritira_dalle_preferenze`

```sql
CREATE FUNCTION trgfn_voce_ritira_dalle_preferenze()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_voce_ritira_dalle_preferenze()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una colonna tolta dalla lista (ui.lista_colonna) o una card
--   tolta dal pool (ui.dashboard_widget) esce dalle preferenze di quel
--   contenitore che la nominano; il resto della configurazione resta.
-- Montaggio: AFTER DELETE FOR EACH ROW, fase z10, sulle due tabelle.
BEGIN
    IF TG_WHEN <> 'AFTER' OR TG_LEVEL <> 'ROW' OR TG_OP <> 'DELETE'
       OR TG_RELID NOT IN ('ui.lista_colonna'::regclass, 'ui.dashboard_widget'::regclass) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso AFTER DELETE FOR EACH ROW su ui.lista_colonna o ui.dashboard_widget'),
            NULL::uuid,
            format('%s: atteso AFTER DELETE FOR EACH ROW su ui.lista_colonna o ui.dashboard_widget',
                   TG_NAME));
    END IF;

    IF TG_RELID = 'ui.lista_colonna'::regclass THEN
        UPDATE ui.lista_preferenza_utente pu
           SET configurazione = ui.fn_configurazione_senza_codici(
                                    pu.configurazione, 'colonne', ARRAY[OLD.codice])
         WHERE pu.lista_id = OLD.lista_id
           AND pu.configurazione IS DISTINCT FROM ui.fn_configurazione_senza_codici(
                                    pu.configurazione, 'colonne', ARRAY[OLD.codice]);
    ELSE
        -- Non il codice della card ritirata: la card puo' essere uscita dal
        -- catalogo nella stessa istruzione, e ui.widget non l'avrebbe piu'.
        -- Esce ogni codice che il pool della dashboard non ha piu'.
        UPDATE ui.dashboard_preferenza_utente pu
           SET configurazione = ui.fn_configurazione_senza_codici(
                                    pu.configurazione, 'widget', o.codici)
          FROM (SELECT p.id, array_agg(DISTINCT (e.value ->> 'codice'))::varchar[] AS codici
                  FROM ui.dashboard_preferenza_utente p
                 CROSS JOIN LATERAL jsonb_array_elements(
                           CASE WHEN jsonb_typeof(p.configurazione -> 'widget') = 'array'
                                THEN p.configurazione -> 'widget' ELSE '[]'::jsonb END) AS e(value)
                 WHERE p.dashboard_id = OLD.dashboard_id
                   AND e.value ->> 'codice' IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM ui.dashboard_widget dw
                                     JOIN ui.widget w ON w.id = dw.widget_id
                                    WHERE dw.dashboard_id = p.dashboard_id
                                      AND w.codice        = e.value ->> 'codice')
                 GROUP BY p.id) AS o
         WHERE o.id = pu.id;
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_voce_ritira_dalle_preferenze()
IS 'Sul catalogo delle colonne (ui.lista_colonna) e sul pool delle dashboard (ui.dashboard_widget), AFTER DELETE FOR EACH ROW, fase z10: la voce ritirata esce dalle preferenze di quella lista (chiave colonne di ui.lista_preferenza_utente.configurazione) o di quella dashboard (chiave widget di ui.dashboard_preferenza_utente.configurazione), con ui.fn_configurazione_senza_codici; l''elenco che resta vuoto esce e segue il preset. Per la lista esce il codice della colonna cancellata. Per la dashboard esce ogni codice che il pool non ha più: la risposta non dipende dal catalogo delle card, che la stessa istruzione può aver già svuotato. La riscrittura passa dai trigger della preferenza: il guard di forma giudica ciò che resta. Gli UPDATE che farebbero uscire un codice dal suo contenitore li rifiuta il lucchetto (lista_colonna.lista_id e codice, dashboard_widget.dashboard_id e widget_id, widget.codice). Montata altrove: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
