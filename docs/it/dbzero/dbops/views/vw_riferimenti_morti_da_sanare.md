{% include-markdown "it/dbzero/dbops/manual/vw_riferimenti_morti_da_sanare.md" %}
# 🔍 View `vw_riferimenti_morti_da_sanare`

> 📝 **Descrizione**
>
> Riferimenti morti (REALE/ORFANA) e funzioni che NON SI SONO POTUTE CONTROLLARE (NON_MISURATO), non coperti dal registro del debito (dbops.riferimenti_morti_esenzioni): e' la lista di lavoro. Deve essere vuota. Ogni SELECT ricompila con plpgsql_check tutte le funzioni plpgsql (dbops.fn_check_funzioni_riferimenti_morti): e' una lettura pesante. NON_MISURATO non e' un dettaglio: senza quelle righe la vista tornerebbe VUOTA proprio quando plpgsql_check e' rotto, cioe' direbbe «nessun riferimento morto» quando nessuno ha potuto guardare. Una riga NON_MISURATO non e' un riferimento morto e non si registra come debito: si ripara lo strumento. Ma resta lavoro, e resta VISIBILE: la conta anche il digest dei presidi, per cui questa vista e' un REGISTRO a cadenza settimanale (perimetro DEFINER).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_riferimenti_morti_da_sanare
WITH (security_invoker=on) AS
SELECT classe,
    schema_nome,
    funzione,
    argomenti,
    esito
   FROM dbops.fn_check_funzioni_riferimenti_morti() m(classe, schema_nome, funzione, argomenti, esito)
  WHERE ((classe = ANY (ARRAY['REALE'::text, 'ORFANA'::text, 'NON_MISURATO'::text])) AND (NOT (EXISTS ( SELECT 1
           FROM dbops.riferimenti_morti_esenzioni e
          WHERE ((e.schema_nome = m.schema_nome) AND (e.funzione = m.funzione) AND (m.esito ~~ e.esito_like))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
