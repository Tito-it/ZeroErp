# ⚙️ Funzione `fn_sorgente_documento_da_chiave`

```sql
CREATE FUNCTION fn_sorgente_documento_da_chiave(p_sorgente_tipo_id bigint, p_chiave text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_documento_da_chiave(p_sorgente_tipo_id bigint, p_chiave text)
 RETURNS TABLE(documento_id bigint, documento_uid uuid, documento_numero text)
 LANGUAGE sql
 STABLE ROWS 1
BEGIN ATOMIC
 SELECT d.documento_id,
     d.documento_uid,
     d.documento_numero
    FROM script.fn_sorgente_documento(fn_sorgente_documento_da_chiave.p_sorgente_tipo_id, script.fn_sorgente_chiave_id(fn_sorgente_documento_da_chiave.p_chiave), script.fn_sorgente_chiave_uuid(fn_sorgente_documento_da_chiave.p_chiave)) d(documento_id, documento_uid, documento_numero);
END

COMMENT ON FUNCTION script.fn_sorgente_documento_da_chiave(p_sorgente_tipo_id bigint, p_chiave text)
IS 'Il ponte del BB che risolve la provenienza, per le tabelle che scrivono ancora la chiave del documento come testo (id::text o uuid::text) o l''uid dove il tipo dice id. Riconosce la forma CANONICA con script.fn_sorgente_chiave_id / _uuid e risolve con script.fn_sorgente_documento: stesso risultato, una riga sempre, mai un errore. Una chiave che non e'' in forma canonica (zeri davanti, spazi, maiuscole) non si risolve. Si svuota lotto per lotto, man mano che le tabelle passano alle colonne sorgente_id / sorgente_uid.';
```

</div>

---
{% include-markdown "signature-core.md" %}
