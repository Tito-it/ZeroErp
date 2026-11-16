{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_protect_snapshot.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_protect_snapshot`

```sql
CREATE FUNCTION trgfn_documenti_generati_protect_snapshot()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_protect_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Blocca l'UPDATE dei campi snapshot di una stampa.
--
-- Regole:
--   Campi immutabili (snapshot):
--     - id, uid
--     - tipo_documento_output_id, template_documento_id,
--       template_versione_id, sorgente_tipo_id, sorgente_id,
--       sorgente_uid, sorgente_riga, progressivo_sorgente,
--       emittente_fiscale_id
--     - context_json, context_hash, template_hash, pdf_hash
--     - titolo, nome_file
--     - generato_at, generato_da_user_id
--   Campo libero: meta. Lo stato ha un solo valore
--   (chk_documenti_generati_stato).
--
--   La stampa e' l'istantanea di una generazione: se cambiano il
--   modello, il tipo, la sorgente, i dati o l'identita' della riga,
--   l'istantanea non e' piu' quella.
--   ⚠️ Le due chiavi della sorgente (sorgente_id, sorgente_uid), la
--      riga e l'utente possono essere NULL: si confrontano con
--      IS DISTINCT FROM.
--
-- Errore:
--   E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE
BEGIN
  IF  (NEW.id                            != OLD.id                            OR
       NEW.tipo_documento_output_id      != OLD.tipo_documento_output_id      OR
       NEW.template_documento_id         != OLD.template_documento_id         OR
       NEW.template_versione_id          != OLD.template_versione_id          OR
       NEW.sorgente_tipo_id              != OLD.sorgente_tipo_id              OR
       NEW.sorgente_id                   IS DISTINCT FROM OLD.sorgente_id     OR
       NEW.sorgente_uid                  IS DISTINCT FROM OLD.sorgente_uid    OR
       NEW.sorgente_riga                 IS DISTINCT FROM OLD.sorgente_riga   OR
       NEW.progressivo_sorgente          != OLD.progressivo_sorgente          OR
       NEW.emittente_fiscale_id          != OLD.emittente_fiscale_id          OR
       NEW.context_json                  != OLD.context_json                  OR
       NEW.context_hash                  != OLD.context_hash                  OR
       NEW.template_hash                 != OLD.template_hash                 OR
       NEW.pdf_hash                      != OLD.pdf_hash                      OR
       NEW.titolo                        != OLD.titolo                        OR
       NEW.nome_file                     != OLD.nome_file                     OR
       NEW.uid                           != OLD.uid                           OR
       NEW.generato_at                   != OLD.generato_at                   OR
       NEW.generato_da_user_id           IS DISTINCT FROM OLD.generato_da_user_id) THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_protect_snapshot',
      'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
      jsonb_build_object(
        'documento_generato_id', OLD.id,
        'uid', OLD.uid::text
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_protect_snapshot()
IS 'Tiene ferma la fotografia di una stampa: identita'' (id, uid), modello e versione, tipo, sorgente con le sue due chiavi e la riga, azienda, dati e hash, titolo, nome del file, chi e quando l''ha generata. Resta libero solo meta; lo stato ha un valore solo. Le colonne che possono essere NULL si confrontano con IS DISTINCT FROM. Solleva E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE, da qualunque ruolo: non ha porte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
