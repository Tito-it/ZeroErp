{% include-markdown "it/dbzero/anagrafiche/manual/fn_nature_proponibili_soggetto.md" %}
# ⚙️ Funzione `fn_nature_proponibili_soggetto`

```sql
CREATE FUNCTION fn_nature_proponibili_soggetto(p_soggetto_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_nature_proponibili_soggetto(p_soggetto_id uuid)
 RETURNS TABLE(tipo_soggetto_dettaglio_id bigint, ammessa boolean, motivo_codice text, motivi jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT tsd.id,
     (jsonb_array_length(m.motivi) = 0),
     ((m.motivi -> 0) ->> 'codice'::text),
     m.motivi
    FROM ((anagrafiche.soggetti s
      CROSS JOIN config.tipi_soggetto_dettaglio tsd)
      CROSS JOIN LATERAL ( SELECT anagrafiche.fn_check_cambio_natura_soggetto(s.id, tsd.id, s.partita_iva, s.cliente_pa, s.split_payment) AS motivi) m)
   WHERE (s.id = fn_nature_proponibili_soggetto.p_soggetto_id)
   ORDER BY (jsonb_array_length(m.motivi) = 0) DESC, tsd.codice_interno;
END

COMMENT ON FUNCTION anagrafiche.fn_nature_proponibili_soggetto(p_soggetto_id uuid)
IS 'Le nature di dettaglio che si possono proporre per il soggetto, una riga per natura (l''attuale compresa): ammessa se anagrafiche.fn_check_cambio_natura_soggetto non ha motivi, altrimenti il codice del primo motivo e tutti i motivi. Contesto: la riga salvata del soggetto (P.IVA, cliente_pa, split_payment); una natura spenta da quei campi si accende correggendoli nello stesso salvataggio. Prima le ammesse, poi le altre, per codice. E'' la stessa check del guard anagrafiche.trgfn_soggetti_guard_cambio_natura: il picker propone cio'' che il guard accetta. Soggetto inesistente: nessuna riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
