{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_guard_emittente_ba.md" %}
# ⚙️ Funzione `trgfn_commesse_guard_emittente_ba`

```sql
CREATE FUNCTION trgfn_commesse_guard_emittente_ba()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_guard_emittente_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_emittente_atteso vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'emittente della commessa non e' un attributo: e' la
    --   sua chiave di perimetro (RLS, scope delle viste del
    --   cruscotto, giornale degli eventi). Qui si verifica che
    --   coincida con quello risolto dal billing account.
    --
    -- Regole:
    --   - vale per OGNI scrittore, non solo per
    --     fn_get_or_create_commessa: il vincolo non sa chi lo
    --     scrive;
    --   - il trigger e' montato UPDATE OF sulle due sole colonne
    --     che possono romperlo, cosi' una modifica di stato non
    --     rivalida niente e un mapping cambiato non congela le
    --     commesse esistenti (quello e' l'altro cantiere).
    --
    -- ⚠️ Puo' PROPAGARE E_EMITTENTE_DEFAULT_MISSING dal
    --   risolutore: non e' un verdetto di dominio ma un difetto
    --   di configurazione, e mascherarlo qui lo renderebbe
    --   invisibile.
    -- =========================================================
    v_emittente_atteso :=
        anagrafiche.fn_get_emittente_fiscale_id(NEW.billing_account_id);

    IF NEW.emittente_soggetto_ruolo_id IS DISTINCT FROM v_emittente_atteso THEN
        -- ⛔ TECNICO: niente `campo` (su un 500 non c'e' nessun
        --    campo da accendere) e niente `bersaglio` (nessun
        --    gesto da offrire). Nel VARIADIC va la frase che
        --    legge una persona: il CODICE della commessa e i due
        --    emittenti, non i nomi delle colonne.
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_commesse_guard_emittente_ba',
            'E_COMMESSA_EMITTENTE_BA_INCOERENTE',
            jsonb_build_object(
                'commessa_id',                 NEW.id,
                'codice',                      NEW.codice,
                'billing_account_id',          NEW.billing_account_id,
                'emittente_soggetto_ruolo_id', NEW.emittente_soggetto_ruolo_id,
                'emittente_atteso_id',         v_emittente_atteso),
            NULL::uuid,
            NEW.codice,
            COALESCE(NEW.emittente_soggetto_ruolo_id::text, '<nessuno>'),
            NEW.billing_account_id::text,
            v_emittente_atteso::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_guard_emittente_ba()
IS 'Guard BEFORE INSERT / UPDATE OF (billing_account_id, emittente_soggetto_ruolo_id) su vendite.commesse: verifica che emittente_soggetto_ruolo_id coincida con anagrafiche.fn_get_emittente_fiscale_id(billing_account_id). Solleva E_COMMESSA_EMITTENTE_BA_INCOERENTE. ⭐ Sta nel TRIGGER e non dentro vendite.fn_get_or_create_commessa perche'' quella e'' UNO solo degli scrittori: nel repository ci sono 22 file pgTAP che fanno INSERT diretta in vendite.commesse senza passarci, e il vincolo non sa chi lo scrive. ⚠️ UPDATE OF e non UPDATE nudo, ed e'' la riga che evita di congelare le commesse: con un UPDATE generico ogni modifica di stato o di competenza rivaliderebbe l''emittente contro il BA, e nel momento in cui il mapping del billing account cambia tutte le commesse di quel cliente diventerebbero non piu'' modificabili con un errore che parla di una colonna che nessuno stava toccando. La fotografia stantia resta un problema di brief-db-billing-account-cambio-emittente, dove ha il suo rimedio. ⛔ La CLASSE del codice diverge di proposito dai sei fratelli documento (E_ORDINE_/E_PREV_/E_DDT_/E_CONTRATTO_/E_OFFERTA_EMITTENTE_BA_INCOERENTE, tutti DATO_ERRATO): li'' il valore lo fornisce una persona in un form, qui non ci arriva nessuno — la commessa nasce dal push, derivata dal BA — quindi solo un chiamante rotto o una INSERT a mano puo'' produrre un valore diverso, ed e'' TECNICO. Ne discende che nel contesto NON c''e'' la chiave `campo` (su un 500 non c''e'' nessun campo da accendere) e non c''e'' il `bersaglio` (nessun gesto da offrire). ⛔ E non si riusa E_PARAMETRO_INVALIDO: quel codice e'' un debito con lo split rimandato, non una sede. ⚠️ Puo'' PROPAGARE E_EMITTENTE_DEFAULT_MISSING dal risolutore — difetto di configurazione, non verdetto di dominio: stessa scelta gia'' dichiarata in anagrafiche.fn_check_ba_coppia_emittente_omogenea. ⚠️ Il nome del trigger e'' scelto per l''ordine: i BEFORE ROW scattano in ordine alfabetico e `default_` precede `guard_`, quindi il riempitore gira prima del giudice. Piano: brief-db-emittente-commessa-invariante, L2.';
```

---
{% include-markdown "signature-core.md" %}
