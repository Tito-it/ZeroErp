{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_normalize.md" %}
# ⚙️ Funzione `trgfn_ordini_normalize`

```sql
CREATE FUNCTION trgfn_ordini_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_fatturazione_ordini anagrafiche.billing_account.fatturazione_ordini%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizzazione campi ordine.
  --
  -- Regole:
  --   1. Imposta anno/data se numero presente e valori mancanti.
  --   2. fatturazione_trigger: la TESTATA ha la precedenza; il
  --      billing_account e' il ripiego. SOLO su INSERT.
  --   3. ruolo del cliente e utility dal billing account (BB
  --      script.fn_cliente_dal_billing_account, rev 2026-10-10):
  --      su INSERT e su un UPDATE che tocca la utility.
  --
  -- Nota (DB-ORD-LOCK 2026-06-04): billing_account_id e'
  --   immutabile su UPDATE (automation_lock_columns ->
  --   script.trgfn_lock_columns, codice E_ORD_CLIENTE_IMMUTABILE).
  --   Non esiste piu' un "cambio BA su UPDATE" da propagare, quindi
  --   il vecchio ramo UPDATE e' stato rimosso (era irraggiungibile:
  --   il lock in fase a10 scatta prima di questo trigger).
  -- =========================================================
  IF TG_OP = 'INSERT' THEN
    ----------------------------------------------------------------
    -- 1. Imposta anno/data se numero e' presente e anno/data mancanti
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '' THEN
      IF NEW.anno IS NULL OR NEW.anno = 0 THEN
        NEW.anno := EXTRACT(YEAR FROM script.fn_data_operativa())::smallint;
      END IF;
      IF NEW.data IS NULL THEN
        NEW.data := script.fn_data_operativa();
      END IF;
    END IF;
    ----------------------------------------------------------------
    -- 2. fatturazione_trigger (rev 2026-08-17): eredita dal billing
    --    account SOLO se la testata non ha scelto.
    --
    --    ⚠️ Il NULL qui e' portante e non e' un caso da difendere: e'
    --    il modo in cui il chiamante DICE «non ho scelto». Regge
    --    perche' il changeSet -02 toglie il DEFAULT dalla colonna —
    --    con il default in piedi qui non arriverebbe mai un NULL e
    --    l'eredita' dal BA non scatterebbe mai.
    --
    --    Il NOT NULL della colonna resta soddisfatto: i vincoli si
    --    valutano dopo i BEFORE ROW, e il COALESCE chiude comunque
    --    su 'CONFERMATO' (il valore che prima metteva il DEFAULT).
    IF NEW.fatturazione_trigger IS NULL
       AND NEW.billing_account_id IS NOT NULL THEN
      SELECT ba.fatturazione_ordini
        INTO v_fatturazione_ordini
        FROM anagrafiche.billing_account ba
       WHERE ba.id = NEW.billing_account_id;
    END IF;
    NEW.fatturazione_trigger := COALESCE(NEW.fatturazione_trigger,
                                         v_fatturazione_ordini,
                                         'CONFERMATO');
  END IF;
  ----------------------------------------------------------------
  -- 3. Ruolo del cliente e utility (rev 2026-10-10,
  --    brief-db-esecutivi-ba-coppia §10.2 domanda 2): sono COPIE di
  --    cio' che il billing account gia' dice. Le scrive o le rifiuta
  --    il BB, con E_DOC_CLIENTE_DIVERSO_DA_BA (prima: la utility qui,
  --    il dissenso col 23503 della FK).
  --    ⚠️ Il NOT NULL si controlla dopo i BEFORE ROW: qui il BA puo'
  --    ancora essere NULL (e l'INSERT fallira' sul NOT NULL); il BB
  --    allora rende le copie come sono.
  IF TG_OP = 'INSERT'
     OR NEW.utility_id         IS DISTINCT FROM OLD.utility_id
     OR NEW.soggetto_ruolo_id  IS DISTINCT FROM OLD.soggetto_ruolo_id
     OR NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
    SELECT f.soggetto_ruolo_id, f.utility_id
      INTO NEW.soggetto_ruolo_id, NEW.utility_id
      FROM script.fn_cliente_dal_billing_account(
               NEW.billing_account_id,
               NEW.soggetto_ruolo_id,
               NEW.utility_id,
               'Ordine ' || COALESCE(NEW.numero, '#' || NEW.id::text),
               'soggetto_ruolo_id',
               NEW.tx_id) f;
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_normalize()
IS 'Normalize: imposta anno/data se numero presente; fatturazione_trigger risolto per precedenza TESTATA -> billing_account.fatturazione_ordini -> CONFERMATO, entrambe SOLO su INSERT. rev 2026-08-17: prima l''eredita'' dal BA era una SOVRASCRITTURA incondizionata e la scelta in testata veniva scartata — con tutti i BA a CONFERMATO nessun ordine poteva nascere SPEDITO/CONSEGNATO e il ramo order-backed di fn_list_ddt_da_pushare era irraggiungibile (segnalazione BE 2026-08-16; brief-be-fan-out-isolato-e-esito-parziale.md §13.2, brief-design-fatturazione-due-lenti.md §6-quater DL-19). Il NULL in NEW e'' il modo in cui il chiamante dice «non ho scelto» e funziona solo perche'' il changeSet 20260817-02 toglie il DEFAULT dalla colonna: i due vanno letti insieme. Il cambio BA su UPDATE non e'' supportato (billing_account_id immutabile - DB-ORD-LOCK). rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-5): utility_id dal billing account se il chiamante non la dice; la colonna e'' NOT NULL dal 20261009-64. rev 2026-10-10 (stesso brief, §10.2 domanda 2, regola del 2): ruolo del cliente e utility li risolve il BB script.fn_cliente_dal_billing_account — scritti se mancano, E_DOC_CLIENTE_DIVERSO_DA_BA se dissentono (prima il 23503 di fk_ordini_ba_cliente, che resta la rete sotto) — su INSERT e su un UPDATE che tocca una delle tre colonne (BA e ruolo li ferma prima il lock E_ORD_CLIENTE_IMMUTABILE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
