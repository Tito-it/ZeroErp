{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_default_guard.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_default_guard`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_default_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- due conteggi (count(*)): nessuna colonna dietro
    v_count     bigint;
    v_emittenti bigint;
BEGIN
    -- =========================================================
    -- Scopo: con almeno un'azienda, il collegamento predefinito
    --   (la riga di emittenti_fiscali_billing_account con
    --   is_default e senza billing account) e' uno e uno solo.
    --   CONSTRAINT TRIGGER differito su ogni INSERT, UPDATE e
    --   DELETE del collegamento: si giudica a transazione finita.
    --
    -- ⚠️ Dove parla: il secondo predefinito lo ferma prima
    --   uq_emittenti_fiscali_ba_default, e la riga predefinita
    --   non si cancella ne' si sposta (a05_block_delete,
    --   a05_block_sposta). Qui resta «nessuna predefinita», che
    --   solo una via di servizio raggiunge: e' la rete.
    -- =========================================================
    SELECT count(*)
      INTO v_emittenti
      FROM anagrafiche.emittenti_fiscali;

    SELECT count(*)
      INTO v_count
      FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE is_default = true;

    -- Installazione vuota: nessuna azienda, nessuna predefinita.
    IF v_emittenti = 0 AND v_count = 0 THEN
        RETURN NULL;
    END IF;

    IF v_count <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'trgfn_emittenti_fiscali_default_guard',
            'E_EMITTENTE_DEFAULT_SINGLETON',
            jsonb_build_object(
                'found', v_count,
                'emittenti_fiscali', v_emittenti,
                'trigger', TG_NAME
            ),
            NULL::uuid,
            v_count::text
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()
IS 'Guard differito (CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED, AFTER INSERT, UPDATE e DELETE) su anagrafiche.emittenti_fiscali_billing_account: con almeno un''azienda, il collegamento predefinito (is_default, senza billing account) e'' uno e uno solo, altrimenti E_EMITTENTE_DEFAULT_SINGLETON col numero trovato. Un''installazione senza aziende e senza predefinita passa. Il secondo predefinito lo ferma prima l''indice uq_emittenti_fiscali_ba_default; la riga predefinita non si cancella e non si sposta (script.trgfn_prevent_modification_generic, senza porte): il guard parla per la predefinita che manca, che solo una via di servizio raggiunge, ed e'' la rete. La prima azienda creata diventa predefinita da sola (anagrafiche.trgfn_emittenti_fiscali_default_bootstrap).';
```

</div>

---
{% include-markdown "signature-core.md" %}
