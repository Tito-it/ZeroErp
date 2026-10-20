{% include-markdown "it/dbzero/vendite/manual/fn_crea_famiglia_documento.md" %}
# ⚙️ Funzione `fn_crea_famiglia_documento`

```sql
CREATE FUNCTION fn_crea_famiglia_documento(p_codice_interno character varying, p_descrizione character varying, p_colonna_numero text, p_colonna_billing_account text, p_colonna_serie text, p_prefisso_default character varying, p_lunghezza_default integer, p_attivo boolean, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_crea_famiglia_documento(p_codice_interno character varying, p_descrizione character varying, p_colonna_numero text, p_colonna_billing_account text DEFAULT NULL::text, p_colonna_serie text DEFAULT NULL::text, p_prefisso_default character varying DEFAULT NULL::character varying, p_lunghezza_default integer DEFAULT 7, p_attivo boolean DEFAULT true, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(famiglia_id integer, codice_interno character varying, registri_creati integer)
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public'
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la famiglia e' quella di una sorgente (G-5): p_codice_interno e'
--   il codice della sorgente, escono p_schema_tabella e p_nome_tabella
--   (la tabella la dice la sorgente); firma e RETURNS TABLE ancorati.
DECLARE
    v_id      vendite.famiglie_documento.id%TYPE;
    v_codice  vendite.famiglie_documento.codice_interno%TYPE;
    -- un conteggio, e il NOME di un campo (non il suo valore): nessuna colonna dietro
    v_creati  integer;
    v_campo   text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare una famiglia di documento E provvisionarne i
    --   registri su tutti gli emittenti, come UNA cosa sola.
    --   Torna (id, codice_interno, registri_creati).
    --
    -- ⛔ Perche' una madre: sono due scritture. Se la seconda
    --   fallisse dopo la prima, resterebbe una famiglia senza
    --   registri — un documento promesso che non si numerera'
    --   mai, e nessun vincolo lo dice. Una sola SELECT su
    --   connessione autocommit e' atomica per costruzione
    --   (§5b delle linee guida).
    --
    -- ⭐ Cosa NON fa: non valida i riferimenti (lo fa il guard
    --   a10_guard_riferimenti), non scrive audit ne' tx_id (ci
    --   sono i trigger), non ricontrolla la serie (c'e' il guard).
    --   Fa le due scritture e le tiene insieme.
    -- =========================================================

    -- ---- I tre obbligatori ---------------------------------
    -- ⭐ rev 2026-10-20 (G-5): erano cinque. schema_tabella e
    --   nome_tabella non ci sono piu': la tabella dei documenti e'
    --   quella della sorgente, e p_codice_interno E' la sorgente
    --   (la FK fk_famiglie_documento_sorgenti la pretende).
    -- ⭐ rev 2026-09-14: colonna_billing_account NON e' piu' fra
    --   questi. Come colonna_serie, il vuoto e' una dichiarazione
    --   («questa famiglia non ha un billing account»: l'ordine di
    --   acquisto), non un campo dimenticato.
    -- ⚠️ Il NOT NULL della colonna non basta: una stringa VUOTA
    --   lo attraversa, e un codice_interno vuoto sarebbe il
    --   bersaglio di una FK — cioe' un riferimento che non si
    --   riesce piu' a nominare. Qui si guarda il VALORE.
    -- ⭐ `campo` nel contesto: e' il canale con cui il frontend
    --   accende l'input giusto. Il messaggio a catalogo resta
    --   generico di proposito — la frase utile la compone la
    --   maschera, che sa come si chiama quel campo a video.
    v_campo := CASE
        WHEN COALESCE(btrim(p_codice_interno), '')          = '' THEN 'codice_interno'
        WHEN COALESCE(btrim(p_descrizione), '')             = '' THEN 'descrizione'
        WHEN COALESCE(btrim(p_colonna_numero), '')          = '' THEN 'colonna_numero'
        ELSE NULL
    END;

    IF v_campo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_crea_famiglia_documento',
            'E_VENDITE_VALIDATION',
            jsonb_build_object('campo', v_campo),
            NULL::uuid,
            -- ⚠️ `VARIADIC ARRAY[]::text[]` e non la chiamata a
            --   cinque argomenti: senza, PostgreSQL non risolve
            --   la firma variadica e risponde «la funzione non
            --   esiste» — un errore TECNICO al posto di quello di
            --   dominio, cioe' il guard che si autoannulla.
            --   ⭐ Il messaggio a catalogo non ha segnaposti: qui
            --   non c'e' niente da passare, ma va passato lo
            --   stesso, vuoto.
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- ---- 1a scrittura: la riga di catalogo -----------------
    -- ⚠️ La stringa vuota su `colonna_serie` diventa NULL: il
    --   vuoto e' la dichiarazione che questa famiglia una serie
    --   non ce l'ha, e un '' salvato al posto di NULL la
    --   renderebbe indistinguibile da una serie che si chiama
    --   cosi'. Stesso trattamento per il prefisso e, dal
    --   2026-09-14, per il billing account.
    INSERT INTO vendite.famiglie_documento (
        codice_interno, descrizione,
        colonna_numero, colonna_billing_account, colonna_serie,
        prefisso_default, lunghezza_default, attivo, meta)
    VALUES (
        btrim(p_codice_interno), btrim(p_descrizione),
        btrim(p_colonna_numero),
        NULLIF(btrim(COALESCE(p_colonna_billing_account, '')), ''),
        NULLIF(btrim(COALESCE(p_colonna_serie, '')), ''),
        NULLIF(btrim(COALESCE(p_prefisso_default, '')), ''),
        COALESCE(p_lunghezza_default, 7),
        COALESCE(p_attivo, TRUE),
        COALESCE(p_meta, '{}'::jsonb))
    RETURNING id, vendite.famiglie_documento.codice_interno
         INTO v_id, v_codice;

    -- ---- 2a scrittura: i registri mancanti -----------------
    -- ⚠️ Su una famiglia creata SPENTA il provisioning torna 0
    --   per costruzione (il filtro `fd.attivo` sta nella
    --   primitiva). Non e' un errore: e' il caso «si semina
    --   prima, si accende dopo».
    v_creati := vendite.fn_provision_registri_famiglia(v_codice);

    RETURN QUERY SELECT v_id, v_codice, v_creati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_crea_famiglia_documento(p_codice_interno character varying, p_descrizione character varying, p_colonna_numero text, p_colonna_billing_account text, p_colonna_serie text, p_prefisso_default character varying, p_lunghezza_default integer, p_attivo boolean, p_meta jsonb)
IS 'MADRE del CRUD delle famiglie di documento: crea la riga di catalogo E le da'' i registri di numerazione su tutti gli emittenti, come una cosa sola. Torna (famiglia_id, codice_interno, registri_creati). ⛔ PERCHE'' UNA MADRE: sono DUE scritture, e fatte in sequenza da fuori un fallimento della seconda lascerebbe una famiglia senza registri — cioe'' una riga di catalogo che promette un documento che non si numerera'' mai, e che nessun vincolo segnala. Una sola SELECT su connessione autocommit e'' atomica per costruzione (§5b delle linee guida). ⭐ COSA NON FA, ed e'' deliberato: non valida i riferimenti (c''e'' il guard a10_guard_riferimenti), non scrive audit ne'' tx_id (ci sono i trigger), non ricontrolla la serie. Rifare qui quei controlli sarebbe il secondo elenco che diverge. ⛔ NON ESISTE una madre per l''update ne'' per il verbo attivo: sono scritture singole, e il backend le fa come gia'' fa sui registri. ⚠️ I CINQUE campi obbligatori (rev 2026-09-14: erano sei) si controllano sul VALORE e non sul NULL: una stringa vuota attraversa il NOT NULL, e un codice_interno vuoto sarebbe il bersaglio di una FK — un riferimento che non si riesce piu'' a nominare. Il `campo` viaggia nel contesto perche'' e'' il canale con cui il frontend accende l''input giusto. ⚠️ Su una famiglia creata SPENTA il provisioning torna 0 per costruzione: e'' il caso «si semina prima, si accende dopo», non un errore. ⚠️ Il conteggio torna al chiamante perche'' ZERO su una famiglia ATTIVA significa che non c''e'' nessun emittente, e quel documento non nascera'' comunque. ⚠️ SECURITY INVOKER: scrive su una tabella senza RLS su cui zeroerp_app ha gia'' INSERT; il provisioning che chiama e'' DEFINER per conto suo. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.7 (DB-5). ⭐ rev 2026-09-14 (P-9, brief-db-modifiche-certe-ciclo-vendita-e-articolo sezione 3-bis): p_colonna_billing_account e'' OPZIONALE come p_colonna_serie — DEFAULT NULL, stringa vuota normalizzata a NULL — perche'' esiste un documento la cui controparte non e'' un cliente: l''ordine di acquisto. Firma con le stesse posizioni e gli stessi tipi (il backend passa per posizione); il guard dei riferimenti (20260914-08) non cerca piu'' quella colonna quando e'' vuota. Rev 2026-10-20 (20261020-39, brief-db-grammatica-unica-documenti 2c, G-5): la famiglia e'' quella di una SORGENTE: p_codice_interno e'' il codice_interno di config.sorgenti (FK), e la tabella dei documenti e'' la sua target_table. Escono p_schema_tabella e p_nome_tabella: gli obbligatori sono TRE (codice, descrizione, colonna del numero). Firma con %TYPE; il backend passa per posizione e si adegua nello stesso giro.';
```

---
{% include-markdown "signature-core.md" %}
