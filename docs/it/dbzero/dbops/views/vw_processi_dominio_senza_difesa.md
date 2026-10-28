{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_difesa.md" %}
# 🔍 View `vw_processi_dominio_senza_difesa`

> 📝 **Descrizione**
>
> Tabelle di dominio in cui si SA dove sta l'emittente ma nessuno lo usa per filtrare: manca la policy RLS, manca il write-guard, o entrambi. ⛔ Una policy conta solo se la ROW LEVEL SECURITY e' ATTIVA sulla tabella (rev 2026-09-05): PostgreSQL conserva le policy di una tabella con la RLS disabilitata e non le applica, quindi prima bastava SCRIVERE una policy per far sparire la riga da qui lasciando la tabella aperta a tutti. ⭐ Non e' nato da una misura — nessun bersaglio era in quello stato — ma dalla scorciatoia che si stava per prendere sulla policy di config.email_outbox: un presidio che si spegne con una decorazione e' peggio di nessun presidio. ⚠️ FORCE ROW LEVEL SECURITY NON entra nel criterio: in questo database nessuna tabella lo usa, perche' l'owner deve poter leggere fuori dalla row security per le SECURITY DEFINER che derivano il perimetro. ⚠️ La regola resta «deve restare VUOTA», ma l'invariante verificabile e' «nessuna riga NON_DICHIARATO»: dichiarare un debito dice «sappiamo perche' e' qui», non «va bene che ci sia».

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_difesa AS
WITH bersagli AS (
         SELECT p.codice AS processo_codice,
            b.schema_tabella,
            b.nome_tabella,
            b.emittente_via,
            b.debito_dichiarato,
            b.note,
            c.oid AS rel_oid,
            c.relrowsecurity AS rls_attiva
           FROM (((dbops.processi p
             JOIN dbops.processi_bersagli b ON ((b.processo_id = p.id)))
             JOIN pg_class c ON ((c.relname = b.nome_tabella)))
             JOIN pg_namespace n ON (((n.oid = c.relnamespace) AND (n.nspname = b.schema_tabella))))
          WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (b.emittente_via IS NOT NULL) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))
        ), difese AS (
         SELECT b.processo_codice,
            b.schema_tabella,
            b.nome_tabella,
            b.emittente_via,
            b.debito_dichiarato,
            b.note,
            b.rel_oid,
            b.rls_attiva,
            (EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE (pol.polrelid = b.rel_oid))) AS ha_policy_scritta,
            (EXISTS ( SELECT 1
                   FROM (pg_trigger t
                     JOIN pg_proc pr ON ((pr.oid = t.tgfoid)))
                  WHERE ((t.tgrelid = b.rel_oid) AND (NOT t.tgisinternal) AND (pr.proname = 'trgfn_guard_emittente_scope'::name)))) AS ha_guard
           FROM bersagli b
        )
 SELECT processo_codice,
    schema_tabella,
    nome_tabella,
    emittente_via,
        CASE
            WHEN ((NOT ha_policy_scritta) AND (NOT ha_guard)) THEN 'policy RLS e write-guard'::text
            WHEN (ha_policy_scritta AND (NOT rls_attiva) AND (NOT ha_guard)) THEN 'la policy c''e'' ma la ROW LEVEL SECURITY non e'' attiva sulla tabella, e manca il write-guard'::text
            WHEN (ha_policy_scritta AND (NOT rls_attiva)) THEN 'la policy c''e'' ma la ROW LEVEL SECURITY non e'' attiva sulla tabella: non filtra niente'::text
            WHEN (NOT ha_policy_scritta) THEN 'policy RLS (lettura scoperta)'::text
            ELSE 'write-guard (scrittura scoperta)'::text
        END AS manca,
        CASE
            WHEN debito_dichiarato THEN 'DEBITO_DICHIARATO'::text
            ELSE 'NON_DICHIARATO'::text
        END AS stato,
    note AS nota
   FROM difese
  WHERE ((NOT (ha_policy_scritta AND rls_attiva)) OR (NOT ha_guard));
```

</div>


---
{% include-markdown "signature-core.md" %}
