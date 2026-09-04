# 🔍 View `vw_processi_dominio_senza_emittente`

> 📝 **Descrizione**
>
> LIVELLO 1 del presidio sui processi: processi dichiarati DOMINIO che non possono rispettare un perimetro emittente — nessun bersaglio dichiarato, bersaglio senza percorso, o percorso dichiarato su tabella/colonna inesistente. DEVE restare VUOTA. ⭐ Prende l'omissione di progetto PRIMA che il processo giri: a runtime non e' recuperabile, perche' la RLS non puo' filtrare su una colonna che non esiste. ⚠️ Come dbops.vw_liste_multi_emittente_non_certificate, prova che la struttura c'e', non che il codice la usi bene; e non prende il verso opposto (dovrebbe essere DOMINIO ma e' dichiarato manutenzione), che resta un errore umano. Brief: brief-db-processi-automatici-identita-e-perimetro §8.

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_emittente AS
WITH dominio AS (
         SELECT p.id,
            p.codice,
            p.canale
           FROM dbops.processi p
          WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL))
        )
 SELECT d.codice AS processo_codice,
    d.canale,
    NULL::text AS schema_tabella,
    NULL::text AS nome_tabella,
    NULL::text AS emittente_via,
    NULL::text AS emittente_colonna,
    'nessun bersaglio dichiarato'::text AS motivo
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
        END AS motivo
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


---
{% include-markdown "signature-core.md" %}
