{% include-markdown "it/dbzero/script/manual/fn_pgtap_emittente_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_emittente_operatore`

```sql
CREATE FUNCTION fn_pgtap_emittente_operatore()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_pgtap_emittente_operatore()
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dare a una fixture pgTAP l'emittente su cui l'operatore
--   corrente puo' davvero scrivere, invece di uno qualsiasi.
--   Brief: brief-db-pgtap-runner-rls-baseline §8.
-- Uso, al posto di
--   (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo LIMIT 1):
--   script.fn_pgtap_emittente_operatore()
DECLARE
    v_user_id     integer;
    v_emittente   bigint;
BEGIN
    -- 1) Se il contesto c'e', l'emittente e' quello di chi agisce.
    v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF v_user_id IS NOT NULL THEN
        SELECT uef.emittente_fiscale_id
          INTO v_emittente
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id = v_user_id;

        IF v_emittente IS NOT NULL THEN
            RETURN v_emittente;
        END IF;
        -- Operatore senza assegnazione: non e' un errore
        -- (fn_check_user_emittente_scope lo tratta come «nessuna
        -- restrizione»), ma un emittente serve lo stesso perche'
        -- la colonna e' NOT NULL sui documenti. Si ripiega sotto.
    END IF;

    -- 2) Nessun contesto — il caso di oggi, con la suite lanciata
    --    dall'owner. Si prende l'emittente di un operatore VERO,
    --    scelto in modo deterministico: e' quello su cui i dati
    --    esistono, e la scelta non cambia fra un'esecuzione e
    --    l'altra. Ordinare e' il punto: senza ORDER BY si torna
    --    a pescare a caso, che e' il difetto che si sta togliendo.
    SELECT uef.emittente_fiscale_id
      INTO v_emittente
      FROM config.user_emittenti_fiscali uef
     ORDER BY uef.auth_user_id, uef.emittente_fiscale_id
     LIMIT 1;

    IF v_emittente IS NULL THEN
        -- Ultimo ripiego: nessun operatore ha un emittente
        -- assegnato. Si prende comunque un emittente attivo, ma
        -- ORDINATO — perche' un test che sceglie a caso non
        -- verifica, scommette.
        SELECT ef.id INTO v_emittente
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.attivo IS TRUE
         ORDER BY ef.id
         LIMIT 1;
    END IF;

    IF v_emittente IS NULL THEN
        RAISE EXCEPTION
          'Nessun emittente fiscale attivo: le fixture non hanno su cosa lavorare.';
    END IF;

    RETURN v_emittente;
END;
$function$

COMMENT ON FUNCTION script.fn_pgtap_emittente_operatore()
IS 'Restituisce l''emittente fiscale su cui l''operatore corrente puo'' scrivere: quello assegnato a app.current_user_id se il contesto e'' impostato, altrimenti quello di un operatore reale scelto in modo deterministico. Sostituisce nelle fixture pgTAP il «SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo LIMIT 1», che senza ORDER BY pescava un emittente a caso — nel DB di sviluppo il 44, attivo ma senza documenti e senza operatore, che il guard trgfn_guard_emittente_scope rifiuta appena un contesto c''e''. Brief: brief-db-pgtap-runner-rls-baseline §8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
