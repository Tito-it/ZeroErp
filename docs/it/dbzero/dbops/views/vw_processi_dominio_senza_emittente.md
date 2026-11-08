{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_emittente.md" %}
# 🔍 View `vw_processi_dominio_senza_emittente`

> 📝 **Descrizione**
>
> LIVELLO 1 del presidio sui processi: processi DOMINIO vivi (ritiro non raggiunto, script.fn_e_obsoleto) che non possono rispettare un perimetro emittente: nessun bersaglio dichiarato, bersaglio senza percorso, o percorso su tabella o colonna inesistente. DEVE restare VUOTA. Prende l'omissione di progetto prima che il processo giri: la RLS non puo' filtrare su una colonna che non esiste. `stato` (DEBITO_DICHIARATO / NON_DICHIARATO, da dbops.processi_bersagli.debito_dichiarato) e `nota` come la sorella di livello 2, dbops.vw_processi_dominio_senza_difesa. Dichiarare un debito non lo assolve: l'invariante verificabile e' «nessuna riga NON_DICHIARATO». Prova che la struttura c'e', non che il codice la usi bene, e non prende il verso opposto (un processo che dovrebbe essere DOMINIO e' dichiarato di manutenzione).

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_emittente AS
WITH dominio AS (
         SELECT p.id,
            p.codice,
            p.canale
           FROM dbops.processi p
          WHERE ((p.classe = 'DOMINIO'::text) AND (NOT script.fn_e_obsoleto(p.obsoleto_dal)))
        )
 SELECT d.codice AS processo_codice,
    d.canale,
    NULL::text AS schema_tabella,
    NULL::text AS nome_tabella,
    NULL::text AS emittente_via,
    NULL::text AS emittente_colonna,
    'nessun bersaglio dichiarato'::text AS motivo,
    'NON_DICHIARATO'::text AS stato,
    NULL::text AS nota
   FROM dominio d
  WHERE (NOT (EXISTS ( SELECT 1
           FROM dbops.processi_bersagli b
          WHERE (b.processo_id = d.id))))
UNION ALL
 SELECT d.codice AS processo_codice,
    d.canale,
    b.schema_tabella,
    b.nome_tabella,
    b.emittente_via,
    b.emittente_colonna,
        CASE
            WHEN (NOT (EXISTS ( SELECT 1
               FROM (pg_class c
                 JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
              WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))))) THEN 'tabella inesistente'::text
            WHEN (b.emittente_via IS NULL) THEN 'percorso verso l''emittente non dichiarato'::text
            ELSE 'colonna del percorso inesistente'::text
        END AS motivo,
        CASE
            WHEN b.debito_dichiarato THEN 'DEBITO_DICHIARATO'::text
            ELSE 'NON_DICHIARATO'::text
        END AS stato,
    b.note AS nota
   FROM (dominio d
     JOIN dbops.processi_bersagli b ON ((b.processo_id = d.id)))
  WHERE ((NOT (EXISTS ( SELECT 1
           FROM (pg_class c
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))))) OR (b.emittente_via IS NULL) OR (NOT (EXISTS ( SELECT 1
           FROM ((pg_attribute a
             JOIN pg_class c ON ((c.oid = a.attrelid)))
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE ((n.nspname = b.schema_tabella) AND (c.relname = b.nome_tabella) AND (a.attname = b.emittente_colonna) AND (a.attnum > 0) AND (NOT a.attisdropped))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
