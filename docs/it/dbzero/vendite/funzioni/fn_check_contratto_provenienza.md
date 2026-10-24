{% include-markdown "it/dbzero/vendite/manual/fn_check_contratto_provenienza.md" %}
# ⚙️ Funzione `fn_check_contratto_provenienza`

```sql
CREATE FUNCTION fn_check_contratto_provenienza(p_commessa_id bigint, p_contratto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_contratto_provenienza(p_commessa_id bigint, p_contratto_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_ba_contratto vendite.contratti.billing_account_id%TYPE;
    v_ba_commessa  vendite.commesse.billing_account_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   il codice del motivo per cui il contratto citato come
    --   provenienza del prezzo da una riga della commessa data
    --   non e' ammesso; NULL = ammesso.
    --   E_ATTIVITA_CONTRATTO_INCOERENTE: il contratto non e'
    --   del billing account della commessa.
    -- =========================================================
    IF p_contratto_id IS NULL THEN
        RETURN NULL;   -- nessun contratto: niente da giudicare
    END IF;

    SELECT k.billing_account_id
      INTO v_ba_contratto
      FROM vendite.contratti k
     WHERE k.id = p_contratto_id;

    SELECT c.billing_account_id
      INTO v_ba_commessa
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    -- Un contratto che non c'e' lo rifiuta la FK; qui un NULL
    -- da una parte sola e' gia' una differenza.
    IF v_ba_contratto IS DISTINCT FROM v_ba_commessa THEN
        RETURN 'E_ATTIVITA_CONTRATTO_INCOERENTE';
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_contratto_provenienza(p_commessa_id bigint, p_contratto_id bigint)
IS 'Check (richiesta BE del 2026-10-21, decisione di Tid D-1): il codice del motivo per cui il contratto citato come provenienza del prezzo (contratto_id) da una riga della commessa data non e'' ammesso; NULL = ammesso. E_ATTIVITA_CONTRATTO_INCOERENTE: il contratto non e'' del billing account della commessa. Il prezzo il contratto lo prende da vendite.fn_get_contratto_attivo(BA, utility, data): un contratto di un altro BA e'' un prezzo che il modello non sa produrre. Basta il BA: utility e istanza seguono da fk_contratti_ba_coppia, l''emittente dal legame unico del BA. ⛔ Non si confronta l''emittente: quello di un BA senza legame dipende da chi agisce. Contratto NULL: NULL. SECURITY DEFINER: contratti e commesse hanno la RLS per emittente, e letto con la RLS di chi scrive un contratto di un''altra azienda tornerebbe a vuoto. Ritorna solo un codice. Non solleva: lo fa vendite.trgfn_attivita_guard_contratto. Gemella di vendite.fn_check_listino_provenienza (l''altra meta'' della provenienza).';
```

</div>

---
{% include-markdown "signature-core.md" %}
