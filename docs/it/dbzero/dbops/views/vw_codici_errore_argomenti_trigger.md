{% include-markdown "it/dbzero/dbops/manual/vw_codici_errore_argomenti_trigger.md" %}
# 🔍 View `vw_codici_errore_argomenti_trigger`

> 📝 **Descrizione**
>
> SEDE UNICA della lettura «i codici E_* che un trigger passa alla sua funzione negli argomenti» (pg_trigger.tgargs, tagliati da dbops.fn_trigger_argomenti): una riga per (trigger, argomento) che e' per INTERO un codice (^E_[A-Z0-9_]+$ — una sottostringa no: ORDINE_VENDITA non e' E_VENDITA). Serve ai building block trigger che ricevono il codice da TG_ARGV (trgfn_lock_columns, trgfn_doc_*_lock_fuori_bozza, trgfn_doc_guard_emittente_ba…), che il corpo della funzione non nomina.
> LETTORI: dbops.vw_punti_canale_campo (presidio C2) e dbops.vw_codici_errore_da_dichiarare (misura del terzo lato). Prima tutti e due cercavano i codici solo nel corpo, e per loro questi siti non esistevano.
> tabella e funzione sono TESTO schema.nome (un regclass in colonna si stampa col search_path di chi legge); posizione parte da 1, come fn_trigger_argomenti. ⚠️ Riconosce la forma di un codice di progetto, non la grammatica di un BB: un BB che passasse i codici in una lista va letto dalla funzione di grammatica che usa il trigger stesso. Origine: D24 di migliorie-generali-da-test-valutazione.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_codici_errore_argomenti_trigger
WITH (security_invoker=true) AS
SELECT tg.tgfoid AS funzione_oid,
    (((fn.nspname)::text || '.'::text) || (p.proname)::text) AS funzione,
    tg.oid AS trigger_oid,
    (tg.tgname)::text AS trigger_nome,
    (((tn.nspname)::text || '.'::text) || (c.relname)::text) AS tabella,
    (a.posizione)::integer AS posizione,
    a.argomento AS codice
   FROM (((((pg_trigger tg
     JOIN pg_proc p ON ((p.oid = tg.tgfoid)))
     JOIN pg_namespace fn ON ((fn.oid = p.pronamespace)))
     JOIN pg_class c ON ((c.oid = tg.tgrelid)))
     JOIN pg_namespace tn ON ((tn.oid = c.relnamespace)))
     CROSS JOIN LATERAL unnest(dbops.fn_trigger_argomenti(tg.tgargs)) WITH ORDINALITY a(argomento, posizione))
  WHERE ((NOT tg.tgisinternal) AND (tg.tgnargs > 0) AND (a.argomento ~ '^E_[A-Z0-9_]+$'::text));
```

</div>


---
{% include-markdown "signature-core.md" %}
