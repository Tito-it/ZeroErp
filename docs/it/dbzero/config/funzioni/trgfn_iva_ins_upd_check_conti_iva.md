{% include-markdown "it/dbzero/config/manual/trgfn_iva_ins_upd_check_conti_iva.md" %}
# ⚙️ Funzione `trgfn_iva_ins_upd_check_conti_iva`

### 🎯 Scopo Principale
* **Validazione contestuale**: eseguire controlli sui campi contabili prima di inserire o aggiornare un record in `config.iva`.
* **Coerenza dei dati**: evitare associazioni errate tra codici IVA e conti di tipo sbagliato.

---

```sql
CREATE FUNCTION trgfn_iva_ins_upd_check_conti_iva()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_iva_ins_upd_check_conti_iva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_acq CHAR(1);
  v_tipo_ven CHAR(1);
BEGIN
  -- 
  -- Constraint trigger per validare i conti IVA in config.iva
  --    conto_iva_acquisti deve riferirsi a un conto di tipo A
  --    conto_iva_vendita deve riferirsi a un conto di tipo V
  -- Usa messaggi centralizzati in config.messaggi_errore
  -- Schema: config
  -- 
  
  -- Validazione conto acquisti
  IF NEW.conto_iva_acquisti_id IS NOT NULL THEN
    SELECT tipo_conto INTO v_tipo_acq
      FROM config.conti_contabili
     WHERE id = NEW.conto_iva_acquisti_id;
    IF v_tipo_acq IS DISTINCT FROM 'A' THEN
      RAISE EXCEPTION '%', config.fn_get_messaggio('E_IVA_CONTO_ACQ_ERR');
    END IF;
  END IF;

  -- Validazione conto vendita
  IF NEW.conto_iva_vendita_id IS NOT NULL THEN
    SELECT tipo_conto INTO v_tipo_ven
      FROM config.conti_contabili
     WHERE id = NEW.conto_iva_vendita_id;
    IF v_tipo_ven IS DISTINCT FROM 'V' THEN
      RAISE EXCEPTION '%', config.fn_get_messaggio('E_IVA_CONTO_VEN_ERR');
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```