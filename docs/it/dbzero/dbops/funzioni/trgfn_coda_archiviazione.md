{% include-markdown "it/dbzero/dbops/manual/trgfn_coda_archiviazione.md" %}
# ⚙️ Funzione `trgfn_coda_archiviazione`

```sql
CREATE FUNCTION trgfn_coda_archiviazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_coda_archiviazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: governa la bandiera `archiviato` delle due code —
--        dbops.coda_lavori e vendite.fatture_stampa_coda.
--        1) GUARD  : una riga VIVA non si archivia;
--        2) RESET  : una riga archiviata che torna viva la
--                    riabbassa da sola;
--        3) DERIVA : `archiviato_il` e `archiviato_da` le scrive
--                    questa funzione, mai il chiamante.
-- Uso:   BEFORE UPDATE OF archiviato, stato, archiviato_il,
--        archiviato_da FOR EACH ROW, con la clausola WHEN che
--        tiene la corsia del worker fuori (vedi 20260904-04).
DECLARE
    -- ⚠️ Nessun %TYPE, e non e' una dimenticanza: questa funzione
    --    serve DUE tabelle, quindi non c'e' una colonna sola a cui
    --    ancorarsi — ancorarla a una delle due sceglierebbe una
    --    delle due come «quella vera». `v_vivo` non riflette
    --    comunque nessuna colonna: e' un predicato.
    v_vivo   boolean;
    v_utente text;
BEGIN
    -- ⭐ «Viva» ha UNA definizione, ed e' la stessa che conta il
    --    badge in topbar: PENDING oppure IN_CORSO. Scritta in
    --    NEGATIVO la regola vale su entrambe le code con la
    --    stessa parola — i loro elenchi di stati TERMINALI sono
    --    invece diversi (qui c'e' ANNULLATO, sulla coda stampa
    --    no), e un predicato scritto come elenco sarebbe gia'
    --    due predicati.
    v_vivo := NEW.stato IN ('PENDING', 'IN_CORSO');

    -- ── 1) LA RIGA E' VIVA ────────────────────────────────
    IF v_vivo AND NEW.archiviato THEN
        IF NOT OLD.archiviato THEN
            -- Qualcuno sta ARCHIVIANDO una riga viva: si rifiuta.
            -- ⚠️ Il rifiuto guarda la DIREZIONE, non la semplice
            --    menzione della colonna: `UPDATE OF archiviato`
            --    scatta anche riassegnando lo stesso valore, e un
            --    guard scritto sulla menzione rifiuterebbe scritture
            --    che non archiviano niente.
            -- ⭐ Nel VARIADIC va lo STATO, non il nome della
            --    colonna: e' la frase che una persona legge.
            PERFORM script.fn_log_and_raise_error(
                TG_TABLE_SCHEMA,
                'trgfn_coda_archiviazione',
                'E_CODA_ARCHIVIAZIONE_NON_AMMESSA',
                jsonb_build_object('riga_id', NEW.id,
                                   'stato',   NEW.stato),
                NULL::uuid,
                NEW.stato);
        END IF;

        -- ⭐ IL RESET. La riga era archiviata e TORNA al lavoro
        --    (requeue admin, reaper, retry del drainer): la
        --    bandiera si abbassa da sola. Non un rifiuto — una
        --    riga che torna al lavoro deve tornare nell'elenco,
        --    altrimenti sarebbe viva e invisibile, cioe' il
        --    difetto che il ramo qui sopra impedisce, rientrato
        --    dalla porta di servizio.
        NEW.archiviato := false;
    END IF;

    -- ── 2) LE DUE DERIVATE ────────────────────────────────
    IF NEW.archiviato AND NOT OLD.archiviato THEN
        -- Si alza la bandiera: data e nome li mette il database.
        v_utente := COALESCE(
            NULLIF(current_setting('app.jwt_user', true), ''),
            CURRENT_USER);
        NEW.archiviato_il := CURRENT_TIMESTAMP;
        NEW.archiviato_da := v_utente;
    ELSIF NOT NEW.archiviato THEN
        -- Si abbassa (ripristino esplicito o reset del ramo 1):
        -- le due colonne vengono dietro. Una riga «non
        -- archiviata, archiviata il 3 settembre» sarebbe un dato
        -- composito spostato a meta'.
        NEW.archiviato_il := NULL;
        NEW.archiviato_da := NULL;
    ELSE
        -- ⭐ La riga era archiviata e resta archiviata: le due
        --    derivate NON si toccano piu'. Ripristinare i valori
        --    vecchi le rende immutabili — chi passasse di qui con
        --    una data propria non la vedrebbe attecchire, e non
        --    ci sarebbe modo di far dire alla riga una cosa che
        --    la bandiera smentisce.
        NEW.archiviato_il := OLD.archiviato_il;
        NEW.archiviato_da := OLD.archiviato_da;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_coda_archiviazione()
IS 'Governa la bandiera `archiviato` delle due code (dbops.coda_lavori, vendite.fatture_stampa_coda): rifiuta l''archiviazione di una riga VIVA, riabbassa la bandiera quando una riga archiviata torna viva, e deriva `archiviato_il`/`archiviato_da`. ⭐ UNA funzione per DUE tabelle: le colonne sono identiche per costruzione e due copie divergerebbero al primo che tocca una sola delle due code. ⭐ «Viva» e'' PENDING|IN_CORSO — la stessa definizione che conta il badge in topbar — e il predicato e'' scritto in NEGATIVO e non come elenco dei terminali, che fra le due code sono elenchi diversi. ⭐ Il RESET (una riga che torna al lavoro torna nell''elenco) non e'' cortesia: senza, una riga archiviata e poi rimessa in coda dal requeue sarebbe viva e invisibile, cioe'' il difetto che il guard impedisce, rientrato dalla porta di servizio. ⛔ Il nome non porta `guard` perche'' la funzione scrive NEW. Errore: E_CODA_ARCHIVIAZIONE_NON_AMMESSA (CONFLITTO_STATO): non c''e'' nessun campo da correggere, c''e'' una riga ancora viva. Piano: brief-db-archiviazione-righe-code.';
```

</div>

---
{% include-markdown "signature-core.md" %}
