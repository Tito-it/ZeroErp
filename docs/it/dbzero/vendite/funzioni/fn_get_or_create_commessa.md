{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_commessa.md" %}
# ⚙️ Funzione `fn_get_or_create_commessa`

```sql
CREATE FUNCTION fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying DEFAULT 'AUTO'::character varying, p_policy_fatturazione character varying DEFAULT 'DA_DOCUMENTO'::character varying, p_fatturazione_immediata boolean DEFAULT false, p_priorita_operativa character varying DEFAULT 'NORMALE'::character varying, p_competenza_dal date DEFAULT NULL::date, p_competenza_al date DEFAULT NULL::date, p_meta jsonb DEFAULT '{}'::jsonb, p_force_new boolean DEFAULT false, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: recupera o crea la commessa coerente con il contesto
--        dimensionale. Da D-R la chiave comprende anche le condizioni
--        di pagamento: un documento con termine diverso NON riusa una
--        commessa esistente, ne apre una nuova — cosi' la divergenza
--        emerge al push e non a valle, in fattura.
-- Regole: la chiave vive in TRE posti (hash del lock, WHERE del riuso,
--         INSERT). ⚠️ I tre NON sono identici alla lettera, ed e'
--         voluto: l'emittente e' NOT NULL sulla colonna
--         (20260826-41), quindi il WHERE lo confronta con `=` puro,
--         mentre l'hash conserva il proprio COALESCE — cambiare la
--         stringa che si hasha cambierebbe l'IDENTITA' del lock senza
--         guadagno. Le DIMENSIONI restano le stesse in tutti e tre:
--         e' quello che va tenuto uguale, non il testo.
-- ⭐ Dal 2026-08-26 NON esiste piu' un parametro per l'emittente:
--         si deriva dal billing account e basta (decisione D-1).
DECLARE
    v_commessa_id vendite.commesse.id%TYPE;
    v_ba_utility  anagrafiche.billing_account.utility_id%TYPE;
    v_ba_found    BOOLEAN := FALSE;
    v_emittente   vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
    v_codice      vendite.commesse.codice%TYPE;
    -- ⭐ rev 2026-08-31 (C2-11): il codice non si fabbrica piu' qui, si
    --   COMPONE dal numero che consegna il registro.
    v_sigla       anagrafiche.emittenti_fiscali.codice%TYPE;
    v_registro    vendite.registri_fatturazione.id%TYPE;
    v_data        date;
    v_anno        smallint;
    -- ⚠️ Il separatore FRA I PEZZI del corpo: e' del dominio commessa,
    --   non del registro. Quello davanti al prefisso non esiste piu'.
    v_sep_dom      text := '-';
    v_ass          record;
BEGIN
    -- Guard: parametri obbligatori
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id obbligatorio e > 0'
        );
    END IF;

    IF p_competenza_dal IS NOT NULL AND p_competenza_al IS NOT NULL AND p_competenza_dal > p_competenza_al THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_DATA_AL_MINORE_DAL',
            jsonb_build_object('competenza_dal', p_competenza_dal, 'competenza_al', p_competenza_al),
            NULL::uuid, p_competenza_al::text, p_competenza_dal::text
        );
    END IF;

    -- Verifica BA
    SELECT ba.utility_id, TRUE INTO v_ba_utility, v_ba_found
      FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;

    IF NOT v_ba_found THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, concat('billing_account_id ', p_billing_account_id)
        );
    END IF;

    IF v_ba_utility IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_BILLING_ACCOUNT_UTILITY_NULL',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, p_billing_account_id::text
        );
    END IF;

    IF v_ba_utility <> p_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_CLIENTE_UTILITY_MISMATCH_BA',
            jsonb_build_object('billing_account_id', p_billing_account_id, 'ba_utility_id', v_ba_utility, 'utility_id', p_utility_id),
            NULL::uuid, p_billing_account_id::text, p_utility_id::text, v_ba_utility::text
        );
    END IF;

    -- ⭐ L'emittente si DERIVA, e non c'e' piu' nessun modo di
    --   passarlo da fuori: e' la decisione D-1 portata a termine.
    --   La funzione SOLLEVA invece di tornare NULL, quindi da qui
    --   in poi v_emittente e' valorizzato per costruzione.
    --   ⚠️ Lo stesso valore lo riscriverebbe comunque
    --   trgfn_commesse_default_emittente sulla INSERT: qui serve
    --   PRIMA, perche' entra nella chiave di riuso e nel lock.
    v_emittente := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);

    IF NOT p_force_new THEN
        -- SPECCHIO 1 — advisory lock sul contesto dimensionale.
        -- ⛔ Il COALESCE su v_emittente resta anche se il NULL non
        --    e' piu' possibile: quello che si hasha e' l'IDENTITA'
        --    del lock, e cambiarla farebbe smettere di
        --    serializzarsi a due sessioni che girassero su due
        --    revisioni diverse di questa funzione.
        PERFORM pg_advisory_xact_lock(
            hashtext('fn_get_or_create_commessa'),
            hashtext(
                p_billing_account_id::text || E'\x1F' || p_utility_id::text || E'\x1F' ||
                p_tipo_commessa || E'\x1F' || p_policy_fatturazione || E'\x1F' ||
                p_fatturazione_immediata::text || E'\x1F' || p_priorita_operativa || E'\x1F' ||
                COALESCE(v_emittente::text, '') || E'\x1F' ||
                COALESCE(p_competenza_dal::text, '') || E'\x1F' || COALESCE(p_competenza_al::text, '') || E'\x1F' ||
                COALESCE(p_termine_pagamento_id::text, '') || E'\x1F' ||
                COALESCE(p_modalita_pagamento_id::text, '')
            )
        );

        -- SPECCHIO 2 — WHERE della commessa riusabile.
        -- ⭐ L'emittente si confronta con `=` PURO: la colonna e'
        --   NOT NULL (20260826-41) e v_emittente non e' mai NULL.
        -- ⚠️ IS NOT DISTINCT FROM resta sulle quattro dimensioni
        --   davvero nullable (competenza e condizioni di pagamento).
        SELECT c.id INTO v_commessa_id
          FROM vendite.commesse c
          JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id AND sc.chiude_commessa = FALSE
         WHERE c.billing_account_id = p_billing_account_id
           AND c.utility_id = p_utility_id
           AND c.tipo_commessa = p_tipo_commessa
           AND c.policy_fatturazione = p_policy_fatturazione
           AND c.fatturazione_immediata = p_fatturazione_immediata
           AND c.priorita_operativa = p_priorita_operativa
           AND c.emittente_soggetto_ruolo_id = v_emittente
           AND c.competenza_dal IS NOT DISTINCT FROM p_competenza_dal
           AND c.competenza_al IS NOT DISTINCT FROM p_competenza_al
           AND c.termine_pagamento_id  IS NOT DISTINCT FROM p_termine_pagamento_id
           AND c.modalita_pagamento_id IS NOT DISTINCT FROM p_modalita_pagamento_id
         ORDER BY c.id DESC LIMIT 1;

        IF v_commessa_id IS NOT NULL THEN RETURN v_commessa_id; END IF;
    END IF;

    -- ═══ IL CODICE, rev 2026-08-31 (C2-11) ═══════════════════
    -- ⛔ Prima era 'CMM-' || timestamp || '-' || md5(random()): un
    --   identificatore, non un codice. Diceva quando e' nata la riga
    --   — cosa che data_insert dice gia' — e affidava l'unicita' a
    --   sei caratteri casuali SOTTO un vincolo deterministico
    --   (uq_commesse_codice): un'unicita' probabilistica, che quando
    --   fallisce esce come 23505 nudo in mezzo a un fan-out.
    -- ⭐ Ora: CMM-<sigla emittente>-<anno>-<9 cifre>, e l'unicita' e'
    --   DETERMINISTICA — la sigla e' unica, l'anno e' un fatto, il
    --   numero viene da un contatore serializzato.

    -- La sigla entra nel codice, e per questo il contatore e' PER
    -- EMITTENTE: ogni dimensione del contatore dev'essere nella
    -- stringa, o al primo cambio di periodo la UNIQUE salta.
    SELECT ef.codice INTO v_sigla
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.soggetto_ruolo_id = v_emittente;

    -- ⛔ L'INVOLUCRO, non il lettore: qui si scrive, e un emittente
    --   senza registro COMMESSA deve fermare invece di far nascere
    --   una commessa senza codice.
    -- ⭐ La commessa non ha una data documento: la sua data e' quella
    --   di CREAZIONE, e si legge da script.fn_data_operativa() —
    --   la data di oggi NEL FUSO DELL'AZIENDA, mai now() nudo.
    v_data := script.fn_data_operativa();
    v_anno := vendite.fn_get_anno_registro(v_data);

    -- ⭐ I SEI PASSI IN UNA CHIAMATA SOLA, la stessa che usano DDT,
    --   ordini e resi. La commessa ci sta dentro grazie al `corpo`:
    --   il suo codice porta sigla e anno DENTRO la stringa, ed e'
    --   l'unico dei cinque la cui IDENTITA' e' la stringa nuda.
    -- ⚠️ Il SEPARATORE fra i pezzi del corpo si scrive qui perche' e'
    --   una cosa di questo dominio; quello davanti al prefisso non
    --   esiste piu' — se serve, sta DENTRO il prefisso del registro
    --   ('CMM-'). Cosi' un prefisso vuoto non lascia piu' un
    --   separatore ORFANO in testa.
    -- ℹ️ Nessun bersaglio (p_documento_id NULL): la riga non esiste
    --   ancora, e il cancello non puo' mordere perche' la data e'
    --   sempre oggi.
    SELECT * INTO v_ass
      FROM vendite.fn_assegna_numero_documento(
               p_famiglia_documento          => 'COMMESSA',
               p_emittente_soggetto_ruolo_id => v_emittente,
               p_data                        => v_data,
               p_documento_id                => NULL,
               p_utility_id                  => p_utility_id,
               -- ⭐ IL CORPO PORTA SOLO LA SIGLA, dal 2026-09-08.
               --   L'anno lo mette ora il compositore generico, che lo
               --   aggiunge in coda al corpo quando il registro lo
               --   dichiara (anno_nel_numero): la stringa esce identica
               --   — CMM-<sigla>-<anno>-<9 cifre>, verificato byte per
               --   byte sui codici esistenti — ma la regola sta in UN
               --   POSTO SOLO.
               -- ⛔ Prima la commessa era l'unica famiglia che l'anno se
               --   lo metteva da se': una seconda sorgente di verita' per
               --   la stessa cosa, e la ragione per cui inizialmente
               --   COMMESSA doveva dichiarare `false` mentendo sul
               --   contenuto della propria stringa.
               p_corpo                       => v_sigla || v_sep_dom) v;

    v_registro := v_ass.registro_id;
    v_codice   := v_ass.numero;

    -- SPECCHIO 3 — INSERT: la commessa nasce con la chiave completa.
    -- ⭐ rev 2026-09-02: la commessa nasce con gli ASSI DEL CONTATORE nelle
    --   sue colonne, non solo dentro la stringa del codice. `registro_id` e
    --   `anno` li ha gia' restituiti il numeratore qui sopra: fino a oggi si
    --   buttavano via dopo aver composto il codice, ed era l'unica delle
    --   cinque famiglie a non tenerli.
    -- ⛔ Non e' un doppione del codice: il codice li porta DENTRO una stringa,
    --   per convenzione di chi la compone. Qui sono dato, e si interrogano.
    INSERT INTO vendite.commesse (codice, registro_id, anno,
        tipo_commessa, policy_fatturazione, fatturazione_immediata,
        priorita_operativa, billing_account_id, utility_id, emittente_soggetto_ruolo_id,
        competenza_dal, competenza_al, meta,
        termine_pagamento_id, modalita_pagamento_id)
    VALUES (v_codice, v_registro, v_anno,
            p_tipo_commessa, p_policy_fatturazione, p_fatturazione_immediata,
        p_priorita_operativa, p_billing_account_id, p_utility_id, v_emittente,
        p_competenza_dal, p_competenza_al, COALESCE(p_meta, '{}'::jsonb),
        p_termine_pagamento_id, p_modalita_pagamento_id)
    RETURNING id INTO v_commessa_id;

    RETURN v_commessa_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Trova o crea la commessa di un billing account, componendone il codice come <prefisso><sigla emittente>-<anno>-<progressivo><suffisso>. ⭐ rev 2026-08-31 (brief-db-prefisso-sul-registro-e-allineamento-contatori, P-5): chiama vendite.fn_assegna_numero_documento come DDT, ordini e resi, invece di rifare per conto proprio i sei passi della numerazione. ⭐ CI STA DENTRO GRAZIE AL PARAMETRO `corpo`: il codice commessa porta sigla e anno DENTRO la stringa — e'' l''unico dei cinque la cui IDENTITA'' e'' la stringa nuda, perche'' uq_commesse_codice guarda quella e non una quadrupla di colonne — quindi passa quei due pezzi come corpo, che per gli altri tre e'' vuoto. ⭐ PREFISSO, SUFFISSO e LUNGHEZZA vengono TUTTI dal REGISTRO (decisione di Tid, 2026-08-31: «cosi'' diventa parametrizzabile anche quello», e il suffisso «come standard» insieme agli altri); i DEFAULT con cui un registro nasce stanno in vendite.famiglie_documento, che per la commessa dichiara 9 cifre contro le 7 degli altri. ⛔ config.sistema_codici NON C''ENTRA PIU'': il 20260831-53 ne ha tolto le righe. ⚠️ ED E'' PROPRIO QUI CHE SI E'' VISTO IL DANNO: fino al 20260831-54 la funzione centrale leggeva la lunghezza da quel catalogo, e tolte le righe la trovava NULL — 7 cifre a tutti, cioe'' giusto per caso su DDT, ordini e resi e SBAGLIATO su questa commessa (CMM-ACME-2026-0000007 invece di CMM-ACME-2026-000000007), senza nessun errore. Corretto dal 20260831-55. ⚠️ IL SEPARATORE si e'' sdoppiato, ed e'' la parte che si dimentica: quello FRA I PEZZI del corpo (sigla-anno-) e'' del DOMINIO commessa e vive qui; quello davanti al prefisso NON ESISTE PIU'' — se serve si scrive dentro il prefisso del registro (''CMM-''). ⛔ Cosi'' sparisce un caso speciale che la commessa aveva e gli altri no: un prefisso vuoto le lasciava un separatore ORFANO in testa (`-ACME-2026-000000001`), che spezzato sul trattino dava un primo pezzo VUOTO. ⚠️ La data e'' quella di CREAZIONE (script.fn_data_operativa(), mai now() nudo), perche'' la commessa non ha una data documento — ed e'' il motivo per cui il cancello di monotonia non puo'' morderla. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-5 e P-16.';
```

</div>

---
{% include-markdown "signature-core.md" %}
