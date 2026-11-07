# ⚙️ Funzione `fn_gruppo_fatturabile_key_di_attivita`

```sql
CREATE FUNCTION fn_gruppo_fatturabile_key_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying, p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_gruppo_fatturabile_key_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying, p_commessa_id bigint)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT vendite.fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id, vendite.fn_documento_uid_di_attivita(p_sorgente_tipo_id, p_segment_key), p_commessa_id) AS fn_build_gruppo_fatturabile_key;
END

COMMENT ON FUNCTION vendite.fn_gruppo_fatturabile_key_di_attivita(p_sorgente_tipo_id bigint, p_segment_key character varying, p_commessa_id bigint)
IS 'La chiave del gruppo fatturabile di una riga di commessa (vendite.commesse_attivita), dai suoi tipo, segment_key e commessa: ''<codice_interno del tipo>:<uid del documento>'' per una riga con documento, ''MAN:<commessa_id>'' per una senza (oneri, rettifiche). L''uid lo da'' vendite.fn_documento_uid_di_attivita, dalla chiave del push; la forma la decide vendite.fn_build_gruppo_fatturabile_key, l''unico costruttore. La usano le viste di emissione e di competenza, i lotti e i filtri p_gruppi: ognuna passa ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id, e cosi'' la chiave e'' la stessa ovunque. Solleva quello che solleva il costruttore: una riga con tipo e una chiave senza uid e'' E_PARAMETRO_INVALIDO. BEGIN ATOMIC: le dipendenze stanno in pg_depend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
