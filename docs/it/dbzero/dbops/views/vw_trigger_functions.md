{% include-markdown "it/dbzero/dbops/manual/vw_trigger_functions.md" %}
# 🔍 View `vw_trigger_functions`

> 📝 **Descrizione**
>
> INVENTARIO: ogni trigger montato nel database con la tabella su cui sta, la funzione che esegue e la definizione COMPLETA di quella funzione (pg_get_functiondef). E' un attrezzo per leggere, non un presidio: la sua non-vuotezza e' la condizione NORMALE — a database sano ha una riga per trigger, e nel 2026 sono migliaia. ⛔ Non entra in nessun digest, ed e' il caso da cui la regola si vede meglio: un elenco che si apre con duemila righe non e' un allarme, e un avviso rumoroso viene ignorato al secondo invio, cioe' finisce come il presidio che voleva salvare. ⚠️ Porta il corpo INTERO di ogni funzione-trigger: una SELECT senza WHERE su questa vista e' pesante, e non e' il modo di usarla — si filtra per tabella o per nome funzione. ⭐ Dichiarata come INVENTARIO in dbops.presidi: se una vista mancasse dal catalogo non si saprebbe se e' un inventario o una dimenticanza. Brief: brief-db-un-destinatario-per-i-presidi §2.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_trigger_functions AS
SELECT n.nspname AS schema,
    cls.relname AS tabella,
    trg.tgname AS nome_trigger,
    p.proname AS nome_funzione,
    pg_get_functiondef(p.oid) AS definizione_funzione
   FROM (((pg_trigger trg
     JOIN pg_class cls ON ((trg.tgrelid = cls.oid)))
     JOIN pg_proc p ON ((trg.tgfoid = p.oid)))
     JOIN pg_namespace n ON ((n.oid = cls.relnamespace)))
  WHERE (NOT trg.tgisinternal)
  ORDER BY n.nspname, cls.relname, trg.tgname;
```

</div>


---
{% include-markdown "signature-core.md" %}
