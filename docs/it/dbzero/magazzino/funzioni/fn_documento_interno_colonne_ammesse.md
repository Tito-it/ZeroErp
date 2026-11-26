{% include-markdown "it/dbzero/magazzino/manual/fn_documento_interno_colonne_ammesse.md" %}
# ⚙️ Funzione `fn_documento_interno_colonne_ammesse`

```sql
CREATE FUNCTION fn_documento_interno_colonne_ammesse(p_famiglia text, p_parte text, p_gesto text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_documento_interno_colonne_ammesse(p_famiglia text, p_parte text, p_gesto text)
 RETURNS text[]
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: le colonne che un verbo dei documenti interni
    --   accetta, per famiglia, parte (testata | riga) e gesto
    --   (crea | modifica). NULL su una combinazione che non
    --   esiste: non ammette niente.
    SELECT CASE p_parte || '/' || p_gesto
               WHEN 'testata/crea' THEN
                   CASE p_famiglia
                       WHEN 'INVENTARIO'    THEN ARRAY['data', 'descrizione']
                       WHEN 'RETTIFICA'     THEN ARRAY['data']
                       WHEN 'TRASFERIMENTO' THEN ARRAY['data', 'magazzino_id_to']
                   END
                   || ARRAY['sorgente_tipo_id', 'sorgente_id', 'sorgente_uid', 'sorgente_riga']
               WHEN 'testata/modifica' THEN
                   CASE p_famiglia
                       WHEN 'INVENTARIO'    THEN ARRAY['data', 'descrizione']
                       WHEN 'RETTIFICA'     THEN ARRAY['data']
                       WHEN 'TRASFERIMENTO' THEN ARRAY['data']
                   END
               WHEN 'riga/crea' THEN
                   CASE p_famiglia
                       WHEN 'INVENTARIO'    THEN ARRAY['articolo_id', 'qta_contata', 'ubicazione_id',
                                                       'lotto_id', 'asset_id', 'costo_unitario']
                       WHEN 'RETTIFICA'     THEN ARRAY['articolo_id', 'qta_delta', 'motivo', 'ubicazione_id',
                                                       'lotto_id', 'asset_id', 'costo_unitario']
                       WHEN 'TRASFERIMENTO' THEN ARRAY['articolo_id', 'qta', 'lotto_id', 'asset_id',
                                                       'ubicazione_id_da', 'ubicazione_id_a']
                   END
               WHEN 'riga/modifica' THEN
                   CASE p_famiglia
                       WHEN 'INVENTARIO'    THEN ARRAY['articolo_id', 'qta_contata', 'ubicazione_id',
                                                       'lotto_id', 'asset_id', 'costo_unitario']
                       WHEN 'RETTIFICA'     THEN ARRAY['articolo_id', 'qta_delta', 'motivo', 'ubicazione_id',
                                                       'lotto_id', 'asset_id', 'costo_unitario']
                       WHEN 'TRASFERIMENTO' THEN ARRAY['articolo_id', 'qta', 'lotto_id', 'asset_id',
                                                       'ubicazione_id_da', 'ubicazione_id_a']
                   END
           END
     WHERE p_famiglia IN ('INVENTARIO', 'RETTIFICA', 'TRASFERIMENTO');
$function$

COMMENT ON FUNCTION magazzino.fn_documento_interno_colonne_ammesse(p_famiglia text, p_parte text, p_gesto text)
IS 'Le colonne che i verbi dei documenti interni di magazzino accettano, per famiglia (INVENTARIO, RETTIFICA, TRASFERIMENTO), parte (testata, riga) e gesto (crea, modifica). La leggono i verbi e il backend: una sede sola. Testata, crea: la data, la descrizione (inventario), il magazzino di arrivo (trasferimento) e la provenienza (sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, controllata da trgfn_guard_sorgente). Testata, modifica: la data e la descrizione; la provenienza e il magazzino di arrivo non cambiano dopo la nascita. Riga, crea e modifica: le colonne della riga, articolo compreso; la coerenza di articolo, lotto, seriale e ubicazione la dicono i guard della tabella. Mai: id, uid, audit, tx_id, storicizza, meta, lo stato (ha il suo verbo), il magazzino della testata e la testata della riga (identita'' della nascita), qta_sistema (la scrive la registrazione). NULL su una combinazione che non esiste: nessuna colonna ammessa. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
