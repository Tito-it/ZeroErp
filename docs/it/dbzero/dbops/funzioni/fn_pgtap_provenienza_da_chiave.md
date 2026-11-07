# ⚙️ Funzione `fn_pgtap_provenienza_da_chiave`

```sql
CREATE FUNCTION fn_pgtap_provenienza_da_chiave(p_segment_key character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_provenienza_da_chiave(p_segment_key character varying)
 RETURNS TABLE(sorgente_tipo_id bigint, sorgente_chiave text, sorgente_riga bigint)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT s.id,
     script.fn_segment_key_uid(fn_pgtap_provenienza_da_chiave.p_segment_key) AS fn_segment_key_uid,
     script.fn_segment_key_riga(fn_pgtap_provenienza_da_chiave.p_segment_key) AS fn_segment_key_riga
    FROM config.sorgenti s
   WHERE ((s.codice_interno)::text = (script.fn_segment_key_sorgente(fn_pgtap_provenienza_da_chiave.p_segment_key))::text);
END

COMMENT ON FUNCTION dbops.fn_pgtap_provenienza_da_chiave(p_segment_key character varying)
IS 'Fixture pgTAP: la provenienza che una chiave del push nomina, per scrivere una riga di commessa con la madre: il tipo (config.sorgenti dal codice, script.fn_segment_key_sorgente), la chiave del documento in testo come la riceve vendite.fn_upsert_commessa_attivita (l''uid, script.fn_segment_key_uid) e la riga (script.fn_segment_key_riga, NULL senza :R:). E'' il verso inverso del push. Serve ai test che scrivono righe di commessa con la chiave di un documento vero (una bolla, un ordine) per i lettori che lo leggono dalla chiave: la provenienza della riga deve nominare lo stesso documento (trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd). Nessuna riga per una chiave senza documento (MAN:...). Il documento e la riga li verifica il guard unico.';
```

</div>

---
{% include-markdown "signature-core.md" %}
