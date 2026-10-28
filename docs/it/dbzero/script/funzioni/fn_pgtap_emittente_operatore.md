{% include-markdown "it/dbzero/script/manual/fn_pgtap_emittente_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_emittente_operatore`

```sql
CREATE FUNCTION fn_pgtap_emittente_operatore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
-- Rev 2026-10-21 (20261021-67): con un contesto, la risposta e'
--   quella di script.fn_resolve_emittente_for_user — anche per
--   il super admin che ha scelto l'emittente in alto.
DECLARE
    v_user_id     anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_emittente   anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- 1) Se il contesto c'e', l'emittente e' quello di chi agisce,
    --    con la regola di produzione: l'emittente scelto in alto
    --    (app.current_emittente_id) se l'utente lo puo' usare,
    --    altrimenti la sua riga in config.user_emittenti_fiscali.
    v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF v_user_id IS NOT NULL THEN
        v_emittente := script.fn_resolve_emittente_for_user(v_user_id);

        IF v_emittente IS NOT NULL THEN
            RETURN v_emittente;
        END IF;
        -- Nessun emittente risolto (super admin senza emittente
        -- scelto, o operatore senza assegnazione): non e' un
        -- errore, ma un emittente serve lo stesso perche' la
        -- colonna e' NOT NULL sui documenti. Si ripiega sotto.
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
IS 'Restituisce l''emittente fiscale su cui l''operatore corrente puo'' scrivere: con il contesto impostato (app.current_user_id) quello di script.fn_resolve_emittente_for_user — l''emittente scelto in alto (app.current_emittente_id) se l''utente lo puo'' usare, altrimenti la sua riga in config.user_emittenti_fiscali (rev 2026-10-21, 20261021-67: prima leggeva la sola configurazione, e per un super admin che ha scelto l''emittente divergeva dal legame che il trigger del BA scrive); senza contesto, o senza un emittente risolto, quello di un operatore reale scelto in modo deterministico, e in ultimo il primo emittente attivo per id. Sostituisce nelle fixture pgTAP il «SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo LIMIT 1», che senza ORDER BY pescava un emittente a caso. Brief: brief-db-pgtap-runner-rls-baseline §8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
