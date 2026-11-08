{% include-markdown "it/dbzero/dbops/manual/vw_marcatori_automazione_senza_esecutore.md" %}
# 🔍 View `vw_marcatori_automazione_senza_esecutore`

> 📝 **Descrizione**
>
> Le tabelle con una colonna che promette un'automazione che nessuno esegue: tx_id senza il trigger di dbops.trgfn_tx_id_managed, storicizza senza quello di script.trgfn_storico_generic, cleanup_at senza il purge. Una tabella e' servita dai runner se e' ordinaria (partizioni comprese), il suo schema e' in dbops.fn_resolve_scope e dbops.fn_table_in_scope la ammette; per tx_id e storicizza basta anche il trigger montato a mano e abilitato; per cleanup_at no, e una tabella esclusa in dbops.automation_cleanup_exclusions resta scoperta. La colonna di storicizzazione si legge con dbops.fn_get_override_col (ruolo STORICIZZA_COL, default storicizza), come la provision dello storico; tx_id e cleanup_at col loro nome. Lo schema storico e gli schemi di sistema sono fuori: le shadow ricopiano le colonne della madre. Tre stati: NON_DICHIARATO e' un allarme, DEBITO_DICHIARATO e' il debito noto di dbops.marcatori_automazione_debito, DEBITO_ESTINTO e' una riga di registro da togliere. A catalogo in dbops.presidi; lo prova dbops/test-marcatori-automazione-senza-esecutore-v1.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_marcatori_automazione_senza_esecutore
WITH (security_invoker=on) AS
WITH ambito AS (
         SELECT dbops.fn_resolve_scope(NULL::text[]) AS schemi
        ), tabelle AS (
         SELECT c.oid,
            (n.nspname)::text AS schema_tabella,
            (c.relname)::text AS nome_tabella,
            (((n.nspname)::text = ANY (a.schemi)) AND dbops.fn_table_in_scope((n.nspname)::text, (c.relname)::text)) AS servita_dai_runner
           FROM ((pg_class c
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
             CROSS JOIN ambito a)
          WHERE ((c.relkind = 'r'::"char") AND (n.nspname <> ALL (ARRAY['information_schema'::name, 'storico'::name])) AND (n.nspname !~ '^pg_'::text))
        ), marcatori AS (
         SELECT t.oid,
            t.schema_tabella,
            t.nome_tabella,
            t.servita_dai_runner,
            m.marcatore
           FROM ((tabelle t
             CROSS JOIN LATERAL ( VALUES ('TX_ID'::text,'tx_id'::text), ('STORICIZZA'::text,dbops.fn_get_override_col(t.schema_tabella, t.nome_tabella, 'STORICIZZA_COL'::text, 'storicizza'::text)), ('CLEANUP_AT'::text,'cleanup_at'::text)) m(marcatore, colonna))
             JOIN pg_attribute att ON (((att.attrelid = t.oid) AND (att.attnum > 0) AND (NOT att.attisdropped) AND (att.attname = (m.colonna)::name))))
        ), esecutori AS (
         SELECT m.oid,
            m.schema_tabella,
            m.nome_tabella,
            m.servita_dai_runner,
            m.marcatore,
            (EXISTS ( SELECT 1
                   FROM ((pg_trigger tg
                     JOIN pg_proc p ON ((p.oid = tg.tgfoid)))
                     JOIN pg_namespace pn ON ((pn.oid = p.pronamespace)))
                  WHERE ((tg.tgrelid = m.oid) AND (NOT tg.tgisinternal) AND (tg.tgenabled <> 'D'::"char") AND (pn.nspname =
                        CASE m.marcatore
                            WHEN 'TX_ID'::text THEN 'dbops'::name
                            WHEN 'STORICIZZA'::text THEN 'script'::name
                            ELSE NULL::name
                        END) AND (p.proname =
                        CASE m.marcatore
                            WHEN 'TX_ID'::text THEN 'trgfn_tx_id_managed'::name
                            WHEN 'STORICIZZA'::text THEN 'trgfn_storico_generic'::name
                            ELSE NULL::name
                        END)))) AS trigger_a_mano,
            dbops.fn_cleanup_esclusa(m.schema_tabella, m.nome_tabella) AS esclusa_dalla_pulizia
           FROM marcatori m
        ), scoperti AS (
         SELECT e.marcatore,
            e.schema_tabella,
            e.nome_tabella,
                CASE
                    WHEN (e.marcatore = 'TX_ID'::text) THEN 'il trigger di dbops.trgfn_tx_id_managed: la tabella non e'' nell''ambito delle automazioni e nessuno lo ha montato a mano, quindi tx_id resta vuoto'::text
                    WHEN (e.marcatore = 'STORICIZZA'::text) THEN 'il trigger di script.trgfn_storico_generic: la tabella non e'' nell''ambito delle automazioni e nessuno lo ha montato a mano, quindi storicizza non produce nessuna versione'::text
                    WHEN e.esclusa_dalla_pulizia THEN 'il purge: la tabella e'' esclusa da dbops.automation_cleanup_exclusions, quindi cleanup_at non fa scadere niente'::text
                    ELSE 'il purge: la tabella non e'' nell''ambito delle automazioni, quindi cleanup_at non fa scadere niente'::text
                END AS manca
           FROM esecutori e
          WHERE
                CASE e.marcatore
                    WHEN 'CLEANUP_AT'::text THEN (NOT (e.servita_dai_runner AND (NOT e.esclusa_dalla_pulizia)))
                    ELSE (NOT (e.servita_dai_runner OR e.trigger_a_mano))
                END
        )
 SELECT s.marcatore,
    s.schema_tabella,
    s.nome_tabella,
    s.manca,
        CASE
            WHEN (d.id IS NULL) THEN 'NON_DICHIARATO'::text
            ELSE 'DEBITO_DICHIARATO'::text
        END AS stato,
    d.ragione,
    d.data_registrazione
   FROM (scoperti s
     LEFT JOIN dbops.marcatori_automazione_debito d ON (((d.marcatore = s.marcatore) AND (d.schema_tabella = s.schema_tabella) AND (d.nome_tabella = s.nome_tabella))))
UNION ALL
 SELECT d.marcatore,
    d.schema_tabella,
    d.nome_tabella,
    'niente: il marcatore ha un esecutore, la colonna non c''e'' piu'' o la tabella non esiste. La riga va tolta dal CSV del registro'::text AS manca,
    'DEBITO_ESTINTO'::text AS stato,
    d.ragione,
    d.data_registrazione
   FROM dbops.marcatori_automazione_debito d
  WHERE (NOT (EXISTS ( SELECT 1
           FROM scoperti s
          WHERE ((s.marcatore = d.marcatore) AND (s.schema_tabella = d.schema_tabella) AND (s.nome_tabella = d.nome_tabella)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
