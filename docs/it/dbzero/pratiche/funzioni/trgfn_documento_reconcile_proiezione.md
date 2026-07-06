{% include-markdown "it/dbzero/pratiche/manual/trgfn_documento_reconcile_proiezione.md" %}
# ⚙️ Funzione `trgfn_documento_reconcile_proiezione`

```sql
CREATE FUNCTION trgfn_documento_reconcile_proiezione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_documento_reconcile_proiezione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: innesco generico dell'avanzamento su esito proiettato (GUIDA D4/G3b).
--   Da agganciare AFTER UPDATE OF <colonna_stato> alle tabelle-documento.
--   Parametri dal seed: TG_ARGV[0]=sorgente_tipo_id, TG_ARGV[1]=colonna
--   chiave ('id'|'uid'). Best-effort: documento sovrano.
DECLARE
  v_tipo   config.sorgenti.id%TYPE := TG_ARGV[0]::bigint;
  v_keycol text := TG_ARGV[1];  -- nome colonna: nessun mirror di tabella
  v_uid    pratiche.pratiche_sorgenti.sorgente_uid%TYPE;
BEGIN
  -- UID del documento dalla colonna-chiave indicata dal seed, senza
  -- SQL dinamico: estrazione per nome dal record via jsonb.
  v_uid := to_jsonb(NEW) ->> v_keycol;

  IF v_uid IS NULL THEN
    RETURN NULL;
  END IF;

  -- Sovranita' del documento (D-B7): un errore lato pratiche viene
  -- inghiottito e loggato, MAI propagato (niente rollback del cambio-stato).
  BEGIN
    PERFORM pratiche.fn_reconcile_sorgente(v_tipo, v_uid);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO pratiche.reconcile_errori
           (sorgente_tipo_id, sorgente_uid, errcode, messaggio, tx_id)
    VALUES (v_tipo, v_uid, SQLSTATE, SQLERRM,
            dbops.fn_get_or_create_session_tx_id());
  END;

  RETURN NULL;  -- AFTER trigger: valore di ritorno ignorato.
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_documento_reconcile_proiezione()
IS 'GUIDA D4/G3b: trigger-function generica AFTER UPDATE OF <colonna_stato> su tabella-documento. Innesca pratiche.fn_reconcile_sorgente(TG_ARGV[0]::tipo, to_jsonb(NEW)->>TG_ARGV[1]::uid) dopo un cambio-stato (standalone incluso). Best-effort: documento sovrano, errore loggato su pratiche.reconcile_errori senza rollback. Agganciata per-dominio (CREATE TRIGGER con args espliciti, D-B9).';
```

---
{% include-markdown "signature-core.md" %}
