{% include-markdown "it/dbzero/vendite/manual/fn_libera_attivita_fatturabili.md" %}
# ⚙️ Funzione `fn_libera_attivita_fatturabili`

```sql
CREATE FUNCTION fn_libera_attivita_fatturabili(p_attivita_fatturabili_ids bigint[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_libera_attivita_fatturabili(p_attivita_fatturabili_ids bigint[])
 RETURNS TABLE(updated_attivita integer, riemesse_attivita integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ca_ids            bigint[];
    v_updated_attivita  integer := 0;
    v_riemesse_attivita integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rimettere in coda di fatturazione un insieme di
    --   attivita_fatturabili: le libera (lucchetto, timbro,
    --   legame con la riga di fattura, stato di esecuzione) e
    --   riporta a NON_EMESSA le commesse_attivita che erano
    --   passate a EMESSA per causa loro.
    --
    -- ⭐ PERCHE' E' UNA PRIMITIVA e non due UPDATE copiate.
    --   Sono le due scritture che compongono UN SOLO fatto —
    --   «questo lavoro torna disponibile» — e vivono su due
    --   livelli diversi. Se divergono, un livello torna in coda
    --   e l'altro no, IN SILENZIO: nessun errore, nessun
    --   contatore fuori posto, e il lavoro esce dal giro.
    --   E' la stessa ragione per cui RD-4 aveva messo il ritorno
    --   a NON_EMESSA dentro la pulizia invece che nei suoi tre
    --   chiamanti.
    --
    -- ⛔ NON imposta zeroerp.maintenance_reset_lotto_draft, ed e'
    --   la parte portante. trgfn_attivita_fatturabili_guard_fatturato
    --   rifiuta l'UPDATE quando OLD.fattura_riga_id e'
    --   valorizzato: se la GUC la impostasse questa funzione,
    --   diventerebbe il modo di SCOLLEGARE UNA FATTURA VIVA.
    --   Impostarla resta una decisione del chiamante, e ne ha
    --   diritto solo chi la fattura la sta cancellando.
    --
    -- Regole:
    --   - array NULL o vuoto: nessuna scrittura, contatori a
    --     zero. Non e' un errore di dominio, e' l'insieme vuoto
    --     — e la pulizia la chiama cosi' quando una fattura non
    --     ha righe. Il guard sull'array vuoto e' un dovere del
    --     VERBO che questa primitiva serve, non suo;
    --   - stato_esecuzione torna a NULL: l'attivita' non e' piu'
    --     dentro nessun giro di fatturazione;
    --   - solo le commesse_attivita in EMESSA tornano a
    --     NON_EMESSA: le ANNULLATA sono state annullate di
    --     proposito e non tornano in coda per una pulizia.
    -- =========================================================
    IF p_attivita_fatturabili_ids IS NULL
       OR array_length(p_attivita_fatturabili_ids, 1) IS NULL THEN
        RETURN QUERY SELECT 0, 0;
        RETURN;
    END IF;

    -- Le righe di commessa da riportare in coda si raccolgono
    -- PRIMA della UPDATE qui sotto: quella azzera il legame e il
    -- lucchetto, e dopo l'insieme non sarebbe piu' ricostruibile.
    -- ℹ️ commessa_attivita_id e' NOT NULL: il filtro non toglie
    --    righe oggi, tiene fuori il NULL dall'array_agg se un
    --    giorno la colonna diventasse nullable.
    SELECT array_agg(DISTINCT af.commessa_attivita_id)
      INTO v_ca_ids
      FROM vendite.attivita_fatturabili af
     WHERE af.id = ANY(p_attivita_fatturabili_ids)
       AND af.commessa_attivita_id IS NOT NULL;

    IF v_ca_ids IS NULL THEN
        v_ca_ids := ARRAY[]::bigint[];
    END IF;

    -- ── livello 1: l'attivita' fatturabile torna disponibile ──
    UPDATE vendite.attivita_fatturabili
       SET lock_in_fatturazione = false,
           lock_batch_id        = NULL,
           -- ⛔ `fatturato` NON si scrive piu' (20260826-33): e' una colonna
           --    GENERATA su `fattura_riga_id IS NOT NULL`, e nominarla in un
           --    SET sarebbe un errore, non un no-op.
           -- ⭐ E il ripristino non ci perde niente: azzerando il puntatore
           --    qui sotto il timbro cade DA SOLO. E' il punto della strada B —
           --    le due colonne non possono piu' dire cose diverse, perche' una
           --    sola esiste davvero.
           fattura_riga_id      = NULL,
           stato_esecuzione     = NULL,
           data_update          = now(),
           user_update          = current_user
     WHERE id = ANY(p_attivita_fatturabili_ids);
    GET DIAGNOSTICS v_updated_attivita = ROW_COUNT;

    -- ── livello 2: la riga di commessa torna emettibile ───────
    -- 🔴 RD-4 — il livello che mancava. Senza, le attivita'
    -- restano marcate come emesse: fn_emit_attivita_fatturabili_da_commessa
    -- filtra su stato_emissione = 'EMESSA' e non le riprende mai
    -- piu', e il cruscotto competenza continua a contarle
    -- lavorate.
    -- ⚠️ Due statement e due GET DIAGNOSTICS distinti, non una
    --    CTE con RETURNING: i due livelli restano misurabili
    --    separatamente, ed e' cio' che permette al chiamante di
    --    accorgersi se uno dei due non ha fatto niente.
    UPDATE vendite.commesse_attivita ca
       SET stato_emissione = 'NON_EMESSA',
           data_update     = now(),
           user_update     = current_user
     WHERE ca.id = ANY(v_ca_ids)
       AND ca.stato_emissione = 'EMESSA';
    GET DIAGNOSTICS v_riemesse_attivita = ROW_COUNT;

    RETURN QUERY SELECT v_updated_attivita, v_riemesse_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_libera_attivita_fatturabili(p_attivita_fatturabili_ids bigint[])
IS 'Rimette in coda di fatturazione un insieme di attivita_fatturabili: le libera (lock_in_fatturazione, lock_batch_id, fattura_riga_id, stato_esecuzione) e riporta a NON_EMESSA le commesse_attivita che erano passate a EMESSA per causa loro. Torna i due contatori separati. ⭐ E'' UNA PRIMITIVA e non due UPDATE copiate perche'' le due scritture compongono UN SOLO fatto — «questo lavoro torna disponibile» — su due livelli diversi: se divergono, un livello torna in coda e l''altro no, in silenzio. Consumata da vendite.fn_cleanup_fatture_by_ids e dal verbo vendite.fn_riporta_attivita_da_emettere. ⛔ Dal 20260826-33 NON scrive piu'' `fatturato`: quella colonna e'' GENERATA su `fattura_riga_id IS NOT NULL`, e nominarla in un SET sarebbe un errore, non un no-op. ⭐ Il ripristino non ci perde niente — azzerando il puntatore il timbro cade DA SOLO: e'' il punto della strada B, le due colonne non possono piu'' dire cose diverse perche'' una sola esiste davvero, e lo stato «timbrata senza fattura» smette di essere rappresentabile. ⚠️ Il LUCCHETTO invece resta scritto a mano, e deve: non e'' un doppione e non si puo'' generare, perche'' e'' vero legittimamente DURANTE il giro, quando la riga di fattura non esiste ancora. E'' il motivo per cui togliere il timbro NON basta e il riordino di fn_cleanup_fatture_by_ids resta necessario: senza, cancellare una riga di fattura toglierebbe il timbro da solo e lascerebbe il lavoro fuori dal giro per un''ALTRA colonna. ⛔ NON imposta la GUC zeroerp.maintenance_reset_lotto_draft: trgfn_attivita_fatturabili_guard_fatturato rifiuta l''UPDATE quando OLD.fattura_riga_id e'' valorizzato, quindi una primitiva che si aprisse la strada da se'' diventerebbe il modo di SCOLLEGARE UNA FATTURA VIVA. Impostarla resta una decisione del chiamante, e ne ha diritto solo chi la fattura la sta cancellando. ⛔ Array NULL o vuoto: nessuna scrittura e contatori a zero — e'' l''insieme vuoto, non un errore; il guard sull''array vuoto e'' un dovere del VERBO. ℹ️ Le commesse_attivita si raccolgono PRIMA della UPDATE; solo le EMESSA tornano a NON_EMESSA. ℹ️ SECURITY INVOKER. Piano: brief-db-lavoro-che-non-torna-indietro, L1 / Q-6, rivisto in L3b / Q-7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
