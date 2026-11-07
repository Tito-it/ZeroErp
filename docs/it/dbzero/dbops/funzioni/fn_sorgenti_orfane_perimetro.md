{% include-markdown "it/dbzero/dbops/manual/fn_sorgenti_orfane_perimetro.md" %}
# ⚙️ Funzione `fn_sorgenti_orfane_perimetro`

```sql
CREATE FUNCTION fn_sorgenti_orfane_perimetro()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sorgenti_orfane_perimetro()
 RETURNS TABLE(tabella regclass, schema_tabella name, nome_tabella name, grammatica text, ha_sorgente_id boolean, ha_sorgente_uid boolean, ha_sorgente_riga boolean, ha_sorgente_dettaglio boolean, orfani_esclusi_perche text, guard_esente_perche text)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
BEGIN ATOMIC
 WITH col AS (
          SELECT a.attrelid,
             bool_or((a.attname = 'sorgente_tipo_id'::name)) AS ha_tipo,
             bool_or((a.attname = 'sorgente_id'::name)) AS ha_id,
             bool_or((a.attname = 'sorgente_uid'::name)) AS ha_uid,
             bool_or((a.attname = 'sorgente_riga'::name)) AS ha_riga,
             bool_or((a.attname = 'sorgente_dettaglio'::name)) AS ha_dett
            FROM pg_attribute a
           WHERE ((a.attnum > 0) AND (NOT a.attisdropped) AND (a.attname = ANY (ARRAY['sorgente_tipo_id'::name, 'sorgente_id'::name, 'sorgente_uid'::name, 'sorgente_riga'::name, 'sorgente_dettaglio'::name])))
           GROUP BY a.attrelid
         ), esenzioni(tabella, orfani_perche, guard_perche) AS (
          VALUES (to_regclass('vendite.attivita_fatturabili'::text),('sorgente_uid porta un''impronta d''idempotenza, non la chiave del documento; '::text || 'la provenienza e'' commessa_attivita_id (FK). Le sue sorgente_* si ritirano nel lotto C'::text),NULL::text), (to_regclass('vendite.fatture_righe'::text),('la provenienza e'' la riga di commessa in sorgente_riga; sorgente_uid non e'' la '::text || 'chiave del documento. Passa al modello nel lotto R'::text),NULL::text), (to_regclass('pratiche.reconcile_errori'::text),'e'' un log: rimanda per costruzione anche a documenti che non ci sono piu'''::text,'e'' un log scritto dentro un EXCEPTION: un guard d''esistenza lo farebbe tacere'::text)
         )
  SELECT (c.oid)::regclass AS oid,
     n.nspname,
     c.relname,
         CASE
             WHEN (EXISTS ( SELECT 1
                FROM script.fn_sorgente_guard_montaggi() m(tabella, schema_tabella, nome_tabella, livello_minimo, azione_cancellazione, argomenti_validi, ha_sorgente_riga, ha_sorgente_dettaglio)
               WHERE ((m.tabella)::oid = ((c.oid)::regclass)::oid))) THEN 'UNICO'::text
             WHEN (EXISTS ( SELECT 1
                FROM pg_trigger tg
               WHERE ((tg.tgrelid = c.oid) AND (NOT tg.tgisinternal) AND (tg.tgfoid = ('script.trgfn_guard_sorgente_polimorfa_tipizzata()'::regprocedure)::oid)))) THEN 'MODELLO_A'::text
             ELSE 'TESTUALE'::text
         END AS "case",
     col.ha_id,
     col.ha_uid,
     col.ha_riga,
     col.ha_dett,
     e.orfani_perche,
     e.guard_perche
    FROM (((col
      JOIN pg_class c ON ((c.oid = col.attrelid)))
      JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
      LEFT JOIN esenzioni e ON (((e.tabella)::oid = ((c.oid)::regclass)::oid)))
   WHERE ((c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])) AND (n.nspname <> 'storico'::name) AND col.ha_tipo AND (col.ha_id OR col.ha_uid) AND ((c.relpersistence <> 't'::"char") OR ((n.oid = pg_my_temp_schema()) AND has_table_privilege(c.oid, 'SELECT'::text))))
   ORDER BY n.nspname, c.relname;
END

COMMENT ON FUNCTION dbops.fn_sorgenti_orfane_perimetro()
IS 'Il perimetro della provenienza polimorfa: ogni tabella (fuori lo storico) con sorgente_tipo_id e almeno una fra sorgente_id e sorgente_uid, con le colonne che ha e la sua GRAMMATICA, dal guard che monta: UNICO (script.trgfn_guard_sorgente: tipo + sorgente_id | sorgente_uid + riga + dettaglio), MODELLO_A (script.trgfn_guard_sorgente_polimorfa_tipizzata: la chiave in sorgente_riga per id, in sorgente_uid per uid), TESTUALE (nessun guard: la chiave in sorgente_uid, come id o uid, in testo o uuid). Due esenzioni dichiarate con il motivo: orfani_esclusi_perche (le tabelle dove sorgente_uid non e'' la chiave del documento, e il log dei reconcile) e guard_esente_perche (il log dei reconcile). Delle tabelle temporanee, solo quelle della sessione leggibili da chi chiede. Derivato dal catalogo di PostgreSQL, non da un elenco: una tabella nuova con la provenienza entra da sola. Lo leggono dbops.fn_sorgenti_orfane e il presidio di struttura (dbops/test-sorgenti-struttura-v1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
