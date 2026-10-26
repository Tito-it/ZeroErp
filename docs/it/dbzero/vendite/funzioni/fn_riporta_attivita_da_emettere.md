{% include-markdown "it/dbzero/vendite/manual/fn_riporta_attivita_da_emettere.md" %}
# ⚙️ Funzione `fn_riporta_attivita_da_emettere`

```sql
CREATE FUNCTION fn_riporta_attivita_da_emettere(p_attivita_fatturabili_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riporta_attivita_da_emettere(p_attivita_fatturabili_ids bigint[])
 RETURNS TABLE(riportate integer, riemesse_attivita integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_motivi     jsonb;
    v_bersaglio  jsonb;
    v_prima      jsonb;
    v_riportate  integer := 0;
    v_riemesse   integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Madre DB di «Riporta da emettere». Rimette in coda di
    --   fatturazione un elenco di attivita' RESIDUE: le libera e
    --   riporta a NON_EMESSA le righe di commessa passate a
    --   EMESSA per causa loro.
    --   Il lavoro ricompare in «Da emettere» e segue il giro
    --   normale: nessun lotto rigenerato, nessuna fattura
    --   ricreata.
    --
    -- ⭐ Non inventa logica: sono le stesse due scritture della
    --   pulizia, e vivono nella primitiva condivisa
    --   vendite.fn_libera_attivita_fatturabili.
    --
    -- ⛔ NON imposta zeroerp.maintenance_reset_lotto_draft. Su
    --   un'attivita' orfana fattura_riga_id e' gia' NULL, quindi
    --   trgfn_attivita_fatturabili_guard_fatturato lascia passare
    --   da se'. Impostare la GUC sarebbe l'unico modo di
    --   trasformare questo verbo in un modo per SCOLLEGARE UNA
    --   FATTURA VIVA.
    --
    -- ⭐ Q-8: vale anche sulle attivita' di RETTIFICA, e NON c'e'
    --   whitelist su tipo_movimento. La distinzione ORIGINE /
    --   NATURA ha gia' morso il dominio il 2026-08-20 su
    --   fn_annulla_commessa_attivita, dove la risposta e' stata
    --   OPPOSTA (whitelist su ONERE): li' il verbo DISTRUGGE.
    --   Qui no — rimettere in coda una rettifica orfana rigenera
    --   la nota di credito al giro successivo, che e' gia' il
    --   comportamento dichiarato nella guida.
    --
    -- ⚠️ SINCRONO: due scritture, una transazione, nessun job.
    --   Accodarlo per simmetria con «Rendi definitive»
    --   importerebbe il problema della dedup, che qui non esiste.
    -- =========================================================

    -- ── 1. Lock PRIMA dei motivi ─────────────────────────────
    -- ⚠️ FOR UPDATE serializza i concorrenti sulle stesse righe:
    --    due riporti simultanei scriverebbero altrimenti due
    --    eventi di log per un solo riporto. Sotto READ COMMITTED
    --    chi aspetta ri-legge la versione aggiornata e cade sul
    --    motivo corretto («gia' da emettere»).
    -- ⚠️ ORDER BY id: due selezioni che si intersecano in ordine
    --    opposto si bloccherebbero a vicenda.
    -- ℹ️ Con l'array NULL o vuoto questo passo non tocca niente e
    --    il guard di parametro scatta al passo 2, dov'e' scritto.
    PERFORM 1
       FROM vendite.attivita_fatturabili af
      WHERE af.id = ANY(p_attivita_fatturabili_ids)
      ORDER BY af.id
        FOR UPDATE;

    -- ── 2. I motivi: sede unica, e si solleva il PRIMO ───────
    -- Il context porta l'elenco completo, cosi' il backend puo'
    -- mostrarli tutti; la frase che legge l'operatore e' il
    -- `dettaglio` del primo, cioe' «commessa <codice>, competenza
    -- <MM/AAAA>» — mai un id tecnico.
    v_motivi := script.fn_check_attivita_riportabile_da_emettere(
                    p_attivita_fatturabili_ids);

    IF jsonb_array_length(v_motivi) > 0 THEN
        -- ⭐ Il BERSAGLIO: dove portare l'operatore. Prima la cosa
        --    SU CUI l'errore e' successo (la commessa, che e'
        --    l'unico posto dove quella riga si vede), poi quella
        --    DA SISTEMARE (la fattura che la tiene ancora).
        -- ⛔ Solo se c'e' davvero dove andare: sul motivo
        --    aggregato «non trovata» non ci sono id, e un
        --    bersaglio verso una riga che l'operatore non vede
        --    sarebbe un pulsante in un vicolo cieco.
        v_bersaglio := COALESCE(
            (CASE WHEN v_motivi -> 0 ->> 'commessa_id' IS NOT NULL
                  THEN jsonb_build_array(jsonb_build_object(
                           'tipo', 'COMMESSA',
                           'id',   v_motivi -> 0 ->> 'commessa_id'))
                  ELSE '[]'::jsonb END)
          ||
            (CASE WHEN v_motivi -> 0 ->> 'fattura_id' IS NOT NULL
                  THEN jsonb_build_array(jsonb_build_object(
                           'tipo', 'FATTURA',
                           'id',   v_motivi -> 0 ->> 'fattura_id'))
                  ELSE '[]'::jsonb END),
            '[]'::jsonb);

        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_riporta_attivita_da_emettere',
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object(
                'attivita_fatturabili_ids', to_jsonb(p_attivita_fatturabili_ids),
                'motivi',                   v_motivi)
            || CASE WHEN jsonb_array_length(v_bersaglio) > 0
                    THEN jsonb_build_object('bersaglio', v_bersaglio)
                    ELSE '{}'::jsonb END,
            NULL::uuid,
            v_motivi -> 0 ->> 'dettaglio');
    END IF;

    -- ── 3. Lo snapshot, PRIMA di liberare ────────────────────
    -- ⚠️ lock_batch_id e stato_esecuzione sono cio' che il log
    --    deve raccontare, e la primitiva li azzera: si
    --    fotografano finche' esistono. E' la stessa disciplina
    --    che il difetto di questo cantiere aveva violato un
    --    livello piu' in giu' — si legge il legame finche' e'
    --    vivo.
    SELECT jsonb_agg(jsonb_build_object(
               'attivita_fatturabile_id', af.id,
               'commessa_attivita_id',    af.commessa_attivita_id,
               'commessa_id',             af.commessa_id,
               'lock_batch_id',           af.lock_batch_id,
               'stato_esecuzione',        af.stato_esecuzione,
               'competenza_mese',         af.competenza_mese)
               ORDER BY af.id)
      INTO v_prima
      FROM vendite.attivita_fatturabili af
     WHERE af.id = ANY(p_attivita_fatturabili_ids);

    -- ── 4. Le due scritture, nella primitiva condivisa ───────
    SELECT l.updated_attivita, l.riemesse_attivita
      INTO v_riportate, v_riemesse
      FROM vendite.fn_libera_attivita_fatturabili(p_attivita_fatturabili_ids) AS l;

    -- ── 5. La traccia, riga per riga ─────────────────────────
    -- ⭐ Q-2: nessun motivo richiesto (il verbo non distrugge:
    --    si rifattura e si e' al punto di prima), ma il log e'
    --    OBBLIGATORIO. «Il lavoro e' sparito da un lotto» non
    --    deve poter essere indistinguibile da un difetto — che e'
    --    esattamente il male da cui nasce questo cantiere.
    -- ℹ️ La colonna `evento` non ha CHECK ne' tabella-vocabolario:
    --    nessun seed da estendere (precedente:
    --    RIGA_MANUALE_ANNULLATA).
    -- ℹ️ Non e' attivita_fatturabili_log: quello e' il log del
    --    flusso consumi, con FK su attivita_consumi_id.
    INSERT INTO vendite.commesse_attivita_log
                (commessa_attivita_id, evento, dettaglio)
    SELECT (e ->> 'commessa_attivita_id')::bigint,
           'RIGA_RIPORTATA_DA_EMETTERE',
           jsonb_build_object(
               'attivita_fatturabile_id',  e -> 'attivita_fatturabile_id',
               'commessa_id',              e -> 'commessa_id',
               'competenza_mese',          e -> 'competenza_mese',
               'lock_batch_id_precedente', e -> 'lock_batch_id',
               'stato_precedente',         e -> 'stato_esecuzione')
      FROM jsonb_array_elements(COALESCE(v_prima, '[]'::jsonb)) AS e;

    RETURN QUERY SELECT v_riportate, v_riemesse;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riporta_attivita_da_emettere(p_attivita_fatturabili_ids bigint[])
IS 'Verbo «Riporta da emettere»: rimette in coda di fatturazione un elenco di vendite.attivita_fatturabili RESIDUE. Le libera (lucchetto, timbro, legame con la riga di fattura, stato di esecuzione) e riporta a NON_EMESSA le vendite.commesse_attivita che erano passate a EMESSA per causa loro; il lavoro ricompare in «Da emettere» e segue il giro normale — nessun lotto viene rigenerato, nessuna fattura viene ricreata. ⭐ Non inventa logica: sono le STESSE due scritture della pulizia, e vivono nella primitiva condivisa vendite.fn_libera_attivita_fatturabili. I motivi ostativi stanno in script.fn_check_attivita_riportabile_da_emettere, che li compone tutti; qui si solleva il PRIMO, con il contesto che porta l''elenco completo per il backend. ⛔ NON imposta la GUC zeroerp.maintenance_reset_lotto_draft, ed e'' il presidio: su un''attivita'' ORFANA fattura_riga_id e'' gia'' NULL e trgfn_attivita_fatturabili_guard_fatturato lascia passare da se''; impostarla sarebbe l''unico modo di trasformare questo verbo in un modo per SCOLLEGARE UNA FATTURA VIVA. Il guard di dominio e quello di riga dicono cosi'' la stessa cosa da due livelli diversi: se il primo si rompesse, il trigger tiene. ⚠️ Il lock (FOR UPDATE, ORDER BY id) viene PRIMA dei motivi: due riporti concorrenti scriverebbero altrimenti due eventi di log per un solo riporto, e l''ORDER BY evita il deadlock fra selezioni che si intersecano in ordine opposto. ⚠️ E lock_batch_id e stato_esecuzione si fotografano PRIMA di liberare, perche'' sono cio'' che il log deve raccontare e la primitiva li azzera. ⭐ Q-2 (Tid, 2026-08-26): NESSUN motivo richiesto — a differenza di fn_annulla_commessa_attivita, qui non si distrugge niente: se il riporto era sbagliato si rifattura e si e'' al punto di prima. Ma il log e'' SEMPRE scritto (evento RIGA_RIPORTATA_DA_EMETTERE su vendite.commesse_attivita_log): serve il FATTO, non la RAGIONE, perche'' «il lavoro e'' sparito da un lotto» non deve poter essere indistinguibile da un difetto. ⭐ Q-8 (Tid, 2026-08-26): vale ANCHE sulle attivita'' di RETTIFICA, e NON c''e'' whitelist su tipo_movimento. ⚠️ La distinzione ORIGINE/NATURA ha gia'' morso il dominio il 2026-08-20 su fn_annulla_commessa_attivita, dove la risposta e'' stata OPPOSTA (whitelist su ONERE): li'' il verbo DISTRUGGE e lasciar passare una riga di nota di credito lasciava l''accredito senza documento. Qui il verbo NON distrugge — rimettere in coda una rettifica orfana rigenera la nota di credito al giro successivo, che e'' gia'' il comportamento dichiarato nella guida operativa. ⚠️ E'' SINCRONO: due scritture, una transazione, nessun job. Accodarlo per simmetria con «Rendi definitive» importerebbe il problema della dedup, che qui non esiste. Permesso: riporta_da_emettere (config.azioni_processo id 33), presidiato dal backend. Piano: brief-db-lavoro-che-non-torna-indietro, L5 / D-4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
