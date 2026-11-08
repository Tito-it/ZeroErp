{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_difesa.md" %}
# 🔍 View `vw_processi_dominio_senza_difesa`

> 📝 **Descrizione**
>
> LIVELLO 2 del presidio sui processi: bersagli dei processi DOMINIO vivi (ritiro non raggiunto, script.fn_e_obsoleto) in cui si SA dove sta l'emittente ma nessuno lo usa per filtrare. DEVE restare senza righe NON_DICHIARATO. Due difese, guardate separatamente: la LETTURA vuole una policy e la ROW LEVEL SECURITY attiva (PostgreSQL conserva le policy di una tabella con la RLS disabilitata e non le applica); la SCRITTURA vuole il guard script.trgfn_guard_emittente_scope, riconosciuto per OID, montato su INSERT e UPDATE e non disattivato, oppure la porta dichiarata in dbops.processi_bersagli.porta_scrittura: una funzione SECURITY DEFINER, con la RLS attiva e policy permissive che coprono INSERT e UPDATE (la policy difende le scritture dell'applicazione, la porta quelle del proprietario). `manca` dice quale difesa manca; una porta dichiarata che non esiste o non e' DEFINER, o senza policy sulla scrittura, lo dice. FORCE ROW LEVEL SECURITY non entra nel criterio: nessuna tabella lo usa, perche' il proprietario deve leggere fuori dalla row security nelle SECURITY DEFINER che derivano il perimetro. Dichiarare un debito (`stato` DEBITO_DICHIARATO) dice «sappiamo perche' e' qui», non «va bene che ci sia».

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
            b.porta_scrittura,
            c.oid AS rel_oid,
            c.relrowsecurity AS rls_attiva
           FROM (((dbops.processi p
             JOIN dbops.processi_bersagli b ON ((b.processo_id = p.id)))
             JOIN pg_class c ON ((c.relname = b.nome_tabella)))
             JOIN pg_namespace n ON (((n.oid = c.relnamespace) AND (n.nspname = b.schema_tabella))))
          WHERE ((p.classe = 'DOMINIO'::text) AND (NOT script.fn_e_obsoleto(p.obsoleto_dal)) AND (b.emittente_via IS NOT NULL) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))
        ), difese AS (
         SELECT b.processo_codice,
            b.schema_tabella,
            b.nome_tabella,
            b.emittente_via,
            b.debito_dichiarato,
            b.note,
            b.porta_scrittura,
            b.rel_oid,
            b.rls_attiva,
            (EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE (pol.polrelid = b.rel_oid))) AS ha_policy_scritta,
            (EXISTS ( SELECT 1
                   FROM pg_trigger t
                  WHERE ((t.tgrelid = b.rel_oid) AND (NOT t.tgisinternal) AND (t.tgfoid = ('script.trgfn_guard_emittente_scope'::regproc)::oid) AND (t.tgenabled <> 'D'::"char") AND (((t.tgtype)::integer & 4) <> 0) AND (((t.tgtype)::integer & 16) <> 0)))) AS ha_guard,
            ((b.porta_scrittura IS NOT NULL) AND (EXISTS ( SELECT 1
                   FROM (pg_proc pr
                     JOIN pg_namespace pn ON ((pn.oid = pr.pronamespace)))
                  WHERE ((pn.nspname = split_part(b.porta_scrittura, '.'::text, 1)) AND (pr.proname = split_part(b.porta_scrittura, '.'::text, 2)) AND pr.prosecdef)))) AS porta_valida,
            ((EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE ((pol.polrelid = b.rel_oid) AND pol.polpermissive AND (pol.polcmd = ANY (ARRAY['*'::"char", 'a'::"char"]))))) AND (EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE ((pol.polrelid = b.rel_oid) AND pol.polpermissive AND (pol.polcmd = ANY (ARRAY['*'::"char", 'w'::"char"])))))) AS policy_su_scrittura
           FROM bersagli b
        ), giudizio AS (
         SELECT d.processo_codice,
            d.schema_tabella,
            d.nome_tabella,
            d.emittente_via,
            d.debito_dichiarato,
            d.note,
            d.porta_scrittura,
            d.rel_oid,
            d.rls_attiva,
            d.ha_policy_scritta,
            d.ha_guard,
            d.porta_valida,
            d.policy_su_scrittura,
            (d.ha_guard OR (d.porta_valida AND d.rls_attiva AND d.policy_su_scrittura)) AS scrittura_difesa
           FROM difese d
        )
 SELECT processo_codice,
    schema_tabella,
    nome_tabella,
    emittente_via,
        CASE
            WHEN ((NOT ha_policy_scritta) AND (NOT scrittura_difesa)) THEN 'policy RLS e write-guard'::text
            WHEN (ha_policy_scritta AND (NOT rls_attiva) AND (NOT scrittura_difesa)) THEN 'la policy c''e'' ma la ROW LEVEL SECURITY non e'' attiva sulla tabella, e manca il write-guard'::text
            WHEN (ha_policy_scritta AND (NOT rls_attiva)) THEN 'la policy c''e'' ma la ROW LEVEL SECURITY non e'' attiva sulla tabella: non filtra niente'::text
            WHEN (NOT ha_policy_scritta) THEN 'policy RLS (lettura scoperta)'::text
            WHEN ((porta_scrittura IS NOT NULL) AND (NOT porta_valida)) THEN 'la porta di scrittura dichiarata non esiste o non e'' SECURITY DEFINER, e manca il write-guard'::text
            WHEN (porta_scrittura IS NOT NULL) THEN 'la porta di scrittura e'' dichiarata ma le policy non coprono INSERT e UPDATE, e manca il write-guard'::text
            ELSE 'write-guard (scrittura scoperta)'::text
        END AS manca,
        CASE
            WHEN debito_dichiarato THEN 'DEBITO_DICHIARATO'::text
            ELSE 'NON_DICHIARATO'::text
        END AS stato,
    note AS nota
   FROM giudizio
  WHERE ((NOT (ha_policy_scritta AND rls_attiva)) OR (NOT scrittura_difesa));
```

</div>


---
{% include-markdown "signature-core.md" %}
