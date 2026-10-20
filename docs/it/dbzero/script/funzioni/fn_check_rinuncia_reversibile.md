{% include-markdown "it/dbzero/script/manual/fn_check_rinuncia_reversibile.md" %}
# ⚙️ Funzione `fn_check_rinuncia_reversibile`

```sql
CREATE FUNCTION fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di RIAPRIRE una rinuncia
--   (annullare la dichiarazione di definitivita' su una quota resa).
--   Funzione PURA (fn_check_*): nessun raise di dominio, nessuna
--   scrittura. Consumatore: vendite.fn_riapri_riconsegna_reso.
--   Brief: brief-db-chiusura-riconsegna-reso-definitivo §5.1;
--   il gate NC: brief-db-note-credito-prerequisiti-be-fe §12 (P-3).
-- Ritorna: [] se reversibile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
--
-- ⭐ 2026-08-19: IL GATE SI E' SVEGLIATO. Dal 2026-07-26 questa
--   funzione ritornava sempre [] e lo dichiarava: «il ramo NC non
--   esiste ancora nel progetto […] codice da registrare allora,
--   non oggi». La slice NC e' arrivata, e il divieto e' entrato
--   qui — come previsto, senza toccare la madre, che solleva gia'
--   il primo motivo prodotto.
--
-- ⚠️ LA CONDIZIONE E' «ACCREDITATA», NON «NC EMESSA». Il commento
--   del 2026-07-26 immaginava il gate sul DOCUMENTO; la finestra
--   pericolosa si apre invece AL VERBO. Fra l'accredito e la
--   fattura la quota e' gia' impegnata e la riga e' gia' uscita
--   dalla coda: aspettare l'emissione lascerebbe scoperta la
--   parte piu' lunga del giro.
--
-- ⭐⚠️ VINCOLO RECIPROCO, ORA SU TRE POSTI (C-3): questo gate,
--   vendite.fn_annulla_accredito_riga_reso e — dal 2026-08-19 — la
--   guardia E_RESO_ANNULLO_CON_ACCREDITO di vendite.fn_annulla_reso.
--   Tutti e tre si AUTO-RIPARANO perche' l'annullo dell'accredito
--   CANCELLA le righe di ponte: annullato l'accredito la rinuncia
--   torna reversibile E il reso torna annullabile, senza che
--   nessuno dei due sappia nulla di quella. E' un pregio FRAGILE:
--   se l'annullo diventasse un soft-delete, questi rami
--   continuerebbero a vedere la riga e vieterebbero PER SEMPRE una
--   rinuncia ormai reversibile e un annullo ormai ammesso, IN
--   SILENZIO — perche' nessuno dei lati sarebbe sbagliato da solo.
--   Le TRE funzioni si cambiano INSIEME.
--
-- ⚠️ NON RIMUOVERE questa funzione: e' il punto di innesto del
--   gate. Rimuoverla riporta il problema a essere una nota in un
--   commento che nessuno cerchera'.
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_esiste boolean;
    v_accreditata boolean;
BEGIN
    IF p_resi_riga_id IS NULL OR p_resi_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script','fn_check_rinuncia_reversibile','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','resi_riga_id','valore',p_resi_riga_id),
            NULL::uuid, 'resi_riga_id obbligatorio (>0)');
    END IF;

    -- La riga deve esistere: un id inventato non e' "reversibile",
    -- e' un errore del chiamante. Si segnala come motivo (non come
    -- raise) per restare puri: la madre decide se sollevare.
    SELECT EXISTS (SELECT 1 FROM vendite.resi_righe rr
                    WHERE rr.id = p_resi_riga_id)
      INTO v_esiste;

    IF NOT v_esiste THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RESO_NOT_FOUND',
            'reason',     'RIGA_INESISTENTE',
            -- Riuso di E_RESO_NOT_FOUND: esiste a catalogo, nessun
            -- codice nuovo per un caso che e' un errore del chiamante.
            'reason_key', 'vendite.resi.rinuncia_reason.riga_inesistente',
            'dettaglio',  p_resi_riga_id,
            -- ⚠️ «Reso non trovato.» non ha segnaposto: l'array VUOTO e' il
            --   valore giusto, non una dimenticanza. Con zero valori
            --   fn_log_and_raise_error salta format() e il testo resta intero.
            'valori',     jsonb_build_array());
        RETURN v_motivi;
    END IF;

    -- === IL GATE NC ===
    -- ⚠️ DOPO «riga inesistente», che ritorna subito: quello e'
    --    l'IDENTITA' della riga, non una sua condizione. Dire
    --    «gia' accreditata» a chi ha passato un id inventato lo
    --    manderebbe a cercare un accredito che non esiste.
    -- Basta l'ESISTENZA di una riga di ponte: un accredito e' N
    -- coppie, e una sola impegna gia' la quota.
    SELECT EXISTS (SELECT 1 FROM vendite.resi_righe_accrediti a
                    WHERE a.resi_riga_id = p_resi_riga_id)
      INTO v_accreditata;

    IF v_accreditata THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO',
            'reason',     'ACCREDITO_ESEGUITO',
            'reason_key', 'vendite.resi.rinuncia_reason.accredito_eseguito',
            'dettaglio',  p_resi_riga_id,
            'valori',     jsonb_build_array(p_resi_riga_id));
    END IF;
    -- ==================

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
IS 'Funzione PURA (fn_check_*): motivi che impediscono di RIAPRIRE una rinuncia di ri-consegna (brief-db-chiusura-riconsegna-reso-definitivo S5.1). Ritorna [] se reversibile, altrimenti un array di {codice, reason, reason_key, dettaglio}. ⭐ NON E'' PIU'' DORMIENTE dal 2026-08-19 (P-3, brief note-credito §12): al ramo «riga inesistente» si e'' aggiunto il gate della nota di credito, che il commento del 2026-07-26 teneva in caldo dichiarando di non registrare ancora il codice «per non lasciare a catalogo un codice mai sollevato». ⚠️ La condizione e'' «esiste una riga in vendite.resi_righe_accrediti», NON «nota di credito emessa»: la finestra pericolosa si apre AL VERBO — fra l''accredito e la fattura la quota e'' gia'' impegnata e la riga e'' gia'' uscita dalla coda, quindi aspettare l''emissione lascerebbe scoperta la parte piu'' lunga del giro. Il ramo sta DOPO «riga inesistente», che e'' l''identita'' della riga e non una sua condizione. ⭐⚠️ VINCOLO RECIPROCO, ORA SU TRE POSTI: questo gate, vendite.fn_annulla_accredito_riga_reso e la guardia E_RESO_ANNULLO_CON_ACCREDITO di vendite.fn_annulla_reso (dal 2026-08-19). Tutti e tre si AUTO-RIPARANO perche'' l''annullo dell''accredito CANCELLA le righe di ponte — se un giorno diventasse un soft-delete, questi rami continuerebbero a vedere la riga e vieterebbero per sempre una rinuncia ormai reversibile e un annullo di reso ormai ammesso, IN SILENZIO, perche'' nessuno dei lati sarebbe sbagliato da solo. Le TRE funzioni si cambiano INSIEME. La madre vendite.fn_riapri_riconsegna_reso NON e'' stata toccata: solleva gia'' il primo motivo prodotto. reason_key da tradurre lato FE. rev 2026-08-19; stesso giorno, nota del vincolo estesa a TRE posti con la guardia di vendite.fn_annulla_reso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
