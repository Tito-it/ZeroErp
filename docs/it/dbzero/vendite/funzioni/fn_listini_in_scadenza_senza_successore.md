# ⚙️ Funzione `fn_listini_in_scadenza_senza_successore`

```sql
CREATE FUNCTION fn_listini_in_scadenza_senza_successore(p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listini_in_scadenza_senza_successore(p_data date DEFAULT NULL::date)
 RETURNS TABLE(listino_id bigint, versione_id bigint, valido_al date, giorni_rimanenti integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
#variable_conflict use_column
-- Scopo: le versioni di listino in vigore alla data che scadono entro N
--   giorni senza un successore, coi giorni rimanenti. Sede unica della
--   regola: la leggono il filtro della lista listini, la colonna della
--   lista versioni e il badge dell'alert scadenze.
--   N = LISTINI_SCADENZA_PREAVVISO_GIORNI, con la cascata degli override
--   della sessione. Regola completa nell'intestazione del changeSet
--   20261031-27 (brief-db-liste-datatable-grezze-secondo-giro §3.1).
-- Nasce il 2026-10-31 (20261031-27) dalla query del backend
--   listini_repository.listini_in_scadenza.
DECLARE
  v_data   vendite.listini_versioni.valido_al%TYPE :=
             COALESCE(p_data, script.fn_data_operativa());
  -- nudo: e' il ritorno di script.fn_intero_positivo_da_testo
  v_giorni integer;
BEGIN
  v_giorni := script.fn_intero_positivo_da_testo(
      script.fn_get_parameter_di_sessione(
          'LISTINI_SCADENZA_PREAVVISO_GIORNI',
          'vendite.fn_listini_in_scadenza_senza_successore'),
      'LISTINI_SCADENZA_PREAVVISO_GIORNI',
      'vendite.fn_listini_in_scadenza_senza_successore');

  RETURN QUERY
  SELECT v.listino_id,
         v.id,
         v.valido_al,
         (v.valido_al - v_data)::integer
    FROM vendite.listini_versioni v
    JOIN vendite.listini l ON l.id = v.listino_id
   WHERE l.attivo IS TRUE
     AND v.attivo IS TRUE
     AND v.valido_al IS NOT NULL
     AND v.valido_al <= v_data + v_giorni
     AND v.id = vendite.fn_listino_versione_in_vigore(v.listino_id, v_data)
     AND NOT EXISTS (
         SELECT 1
           FROM vendite.listini_versioni succ
           JOIN config.stati_doc_listino_versioni ss
             ON ss.id = succ.stato_doc_listino_versione_id
          WHERE succ.listino_id = v.listino_id
            AND succ.id <> v.id
            AND succ.attivo IS TRUE
            -- il successore contiguo nasce il giorno dopo la fine
            AND succ.valido_dal > v.valido_al
            -- in preparazione (lo stato iniziale, oggi BOZZA), oppure
            -- operativo dal giorno dopo la fine in poi
            AND (ss.iniziale IS TRUE
                 OR succ.validita && daterange(v.valido_al + 1, NULL, '[)')));
END;
$function$

COMMENT ON FUNCTION vendite.fn_listini_in_scadenza_senza_successore(p_data date)
IS 'Le versioni di listino in vigore alla data (default: la data operativa) che scadono entro N giorni senza un successore, coi giorni rimanenti: una riga per versione. N = LISTINI_SCADENZA_PREAVVISO_GIORNI (cascata degli override della sessione; assente o non intero positivo = E_CONFIG_MANCANTE). Successore = una versione attiva dello stesso listino che nasce dopo la fine e che e'' nello stato iniziale (in preparazione) o ha una validita'' dal giorno dopo la fine in poi. La versione in vigore la dice vendite.fn_listino_versione_in_vigore. Sede unica della regola: la leggono il filtro della lista listini, la colonna giorni_alla_scadenza della lista versioni e il badge dell''alert scadenze, una volta per query. Nasce il 2026-10-31 (20261031-27, brief-db-liste-datatable-grezze-secondo-giro §3.1) dalla query del backend listini_repository.listini_in_scadenza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
