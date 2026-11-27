{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_filiale_bancaria.md" %}
# ⚙️ Funzione `fn_pgtap_crea_filiale_bancaria`

```sql
CREATE FUNCTION fn_pgtap_crea_filiale_bancaria(p_etichetta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
--   e l'IBAN del conto con dbops.fn_pgtap_iban(bank_branch_id, '<seme>').
-- ⛔ Il CONTO non lo scrive: IBAN e titolare sono il caso del test.
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_sog     anagrafiche.soggetti.id%TYPE;
    v_sr      anagrafiche.bank_branches.soggetto_ruolo_id%TYPE;
    v_br      anagrafiche.bank_branches.id%TYPE;
    v_stato   anagrafiche.soggetti.stato_id%TYPE;
    v_banca   CONSTANT anagrafiche.bank_branches.bank_code%TYPE := '01234';
    v_filiale anagrafiche.bank_branches.branch_code%TYPE;
    v_n       integer;  -- un contatore, non una colonna
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
    SELECT s.stato_id INTO v_stato FROM anagrafiche.soggetti s WHERE s.id = v_sog;
    -- Lo sportello e' unico nel paese (E_FILIALE_DUPLICATA): il
    --   codice della filiale e' il primo libero a partire dal
    --   ruolo nuovo, nella stessa ricerca dei guard.
    v_n := (v_sr % 100000)::integer;
    LOOP
        v_filiale := lpad(v_n::text, 5, '0');
        EXIT WHEN anagrafiche.fn_filiale_stessi_codici(
                      NULL, v_banca, v_filiale, v_stato) IS NULL;
        v_n := (v_n + 1) % 100000;
    END LOOP;
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name, attivo)
    VALUES (v_sr, v_banca, v_filiale,
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
IS 'Fixture pgTAP: una filiale bancaria costruita (soggetto della banca, ruolo BANK_B coi suoi indirizzi obbligatori, e la filiale) dentro la finestra dei vincoli differiti, che e'' la trappola per cui questo builder esiste. Codice della banca 01234, codice della filiale il primo libero nel paese del soggetto (lo sportello e'' unico nel paese): due chiamate danno due filiali diverse. ⚠️ anagrafiche.bank_branches e'' dato di MACCHINA, non seed di 80_data: su un database ricostruito e'' vuota, e un test che la pescasse morirebbe sul NOT NULL di bank_branch_id. ⛔ Il conto bancario non lo scrive: IBAN e titolare sono il caso del test; l''IBAN coerente con la filiale lo da'' dbops.fn_pgtap_iban. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
