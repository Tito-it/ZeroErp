{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_filiale_bancaria.md" %}
# ⚙️ Funzione `fn_pgtap_crea_filiale_bancaria`

```sql
CREATE FUNCTION fn_pgtap_crea_filiale_bancaria(p_etichetta text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_filiale_bancaria(p_etichetta text DEFAULT 'pgTAP'::text)
 RETURNS TABLE(bank_branch_id bigint, banca_soggetto_ruolo_id bigint, banca_soggetto_id uuid)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una filiale bancaria su cui
--   agganciare un conto. `anagrafiche.bank_branches` e' dato di
--   MACCHINA: su un database ricostruito e' vuota, e pescarne una
--   e' copertura zero.
-- Uso:
--   CREATE TEMP TABLE tmp_banca AS
--   SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('enti incasso');
-- ⛔ Il CONTO non lo scrive: IBAN e titolare sono il caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_sog uuid;
    v_sr  anagrafiche.bank_branches.soggetto_ruolo_id%TYPE;
    v_br  anagrafiche.bank_branches.id%TYPE;
BEGIN
    -- ⛔ LA FINESTRA DIFFERITA: il ruolo BANK_B ha i suoi indirizzi
    --   obbligatori e un guard differito, e il preambolo dei pgTAP
    --   mette i vincoli IMMEDIATE. Senza queste righe la catena
    --   muore a meta', e l'errore parla di indirizzi a chi voleva
    --   una banca.
    SET CONSTRAINTS ALL DEFERRED;

    v_sog := dbops.fn_pgtap_crea_soggetto_pg('Banca ' || p_etichetta);
    v_sr  := dbops.fn_pgtap_crea_soggetto_ruolo(
                 v_sog, 'BANK_B'::character varying);

    -- ⚠️ I codici possono essere fissi: l'unicita' e'
    --   (soggetto_ruolo, bank_code, branch_code), e il soggetto
    --   ruolo e' nuovo a ogni chiamata.
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name, attivo)
    VALUES (v_sr, '01234', '56789',
            'Filiale pgTAP ' || p_etichetta, TRUE)
    RETURNING id INTO v_br;

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito. Senza la richiusura il ROLLBACK del test se li
    -- porterebbe via NON verificati.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY SELECT v_br, v_sr, v_sog;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_filiale_bancaria(p_etichetta text)
IS 'Fixture pgTAP: una filiale bancaria costruita — soggetto della banca, ruolo BANK_B coi suoi indirizzi obbligatori, e la filiale — dentro la finestra dei vincoli differiti, che e'' la trappola per cui questo builder esiste. ⚠️ anagrafiche.bank_branches e'' dato di MACCHINA, non seed di 80_data: su un database ricostruito e'' vuota, e i tre file di pagamenti che la pescavano morivano sul NOT NULL di bank_branch_id. ⛔ Il conto bancario NON lo scrive: IBAN e titolare sono il caso del test. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper. Brief: brief-db-fixture-che-costruiscono-giro-2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
