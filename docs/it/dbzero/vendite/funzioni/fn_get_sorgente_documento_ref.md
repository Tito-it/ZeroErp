{% include-markdown "it/dbzero/vendite/manual/fn_get_sorgente_documento_ref.md" %}
# ⚙️ Funzione `fn_get_sorgente_documento_ref`

```sql
CREATE FUNCTION fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS TABLE(documento_id bigint, documento_numero text)
 LANGUAGE sql
 STABLE ROWS 1
BEGIN ATOMIC
 SELECT d.documento_id,
     d.documento_numero
    FROM script.fn_sorgente_documento_da_chiave(fn_get_sorgente_documento_ref.p_sorgente_tipo_id, fn_get_sorgente_documento_ref.p_sorgente_uid) d(documento_id, documento_uid, documento_numero);
END

COMMENT ON FUNCTION vendite.fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Il documento di origine di una riga a sorgente polimorfa che scrive la chiave come testo: documento_id (per l''azione «apri documento sorgente») e documento_numero (il numero che l''operatore legge, dalla colonna che config.sorgenti dichiara in label_selector). Passa al ponte script.fn_sorgente_documento_da_chiave, che riconosce l''id o l''uid in forma canonica e risolve con script.fn_sorgente_documento: stessa regola per tutti i lettori. Restituisce SEMPRE una riga, anche tutta NULL, e non solleva: una sorgente non risolta fa solo sparire l''azione, come per le voci manuali, gli oneri e le rettifiche, che un documento a monte non ce l''hanno. INVOKER: NULL vuol dire anche «non visibile a chi chiede».';
```

</div>

---
{% include-markdown "signature-core.md" %}
