{% include-markdown "it/dbzero/script/manual/fn_check_attivita_riportabile_da_emettere.md" %}
# ⚙️ Funzione `fn_check_attivita_riportabile_da_emettere`

```sql
CREATE FUNCTION fn_check_attivita_riportabile_da_emettere(p_attivita_fatturabili_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_attivita_riportabile_da_emettere(p_attivita_fatturabili_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di riportare «da
    --   emettere» un insieme di attivita_fatturabili. Funzione
    --   PURA: nessuna scrittura, nessun raise di dominio.
    -- Ritorna:
    --   [] se si puo' fare su tutte; altrimenti un array
    --   ordinato di {codice, reason, reason_key, dettaglio,
    --   attivita_fatturabile_id, commessa_id, fattura_id}.
    -- Consumatori:
    --   vendite.fn_riporta_attivita_da_emettere (solleva il
    --   codice del PRIMO motivo) e il backend, per spiegare
    --   invece di far fallire.
    -- =========================================================

    -- ⛔ Guard di PARAMETRO, e solleva. Un elenco assente o
    --    vuoto e' un errore di chiamante, non una condizione di
    --    dominio: se uscisse come «nessun motivo» diventerebbe
    --    poi «zero righe riportate», cioe' indistinguibile da
    --    un'operazione riuscita che non ha trovato niente da
    --    fare. TECNICO: nessuna persona sceglie questo valore.
    IF p_attivita_fatturabili_ids IS NULL
       OR array_length(p_attivita_fatturabili_ids, 1) IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script',
            'fn_check_attivita_riportabile_da_emettere',
            'E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA',
            jsonb_build_object(
                'parametro', 'p_attivita_fatturabili_ids',
                'valore',    to_jsonb(p_attivita_fatturabili_ids)),
            NULL::uuid,
            'fn_check_attivita_riportabile_da_emettere');
    END IF;

    WITH sel AS (
        SELECT DISTINCT u.id
          FROM unnest(p_attivita_fatturabili_ids) AS u(id)
    ),
    -- ⛔ IL PERIMETRO. Il JOIN su commesse_attivita non serve a
    --    leggere una colonna: e' il cancello di scope. La tabella
    --    attivita_fatturabili NON ha row level security, quella
    --    delle commesse si' — quindi e' quel JOIN a decidere cosa
    --    chi chiede ha diritto di vedere. Senza, la funzione
    --    direbbe «si puo' fare» su un emittente altrui.
    vis AS (
        SELECT s.id                                    AS attivita_fatturabile_id,
               af.commessa_id,
               af.fattura_riga_id,
               COALESCE(af.lock_in_fatturazione, false) AS lucchettata,
               af.stato_esecuzione,
               -- ⭐ rev 2026-09-12 — I DUE LIVELLI. La riga di commessa dice
               --    se il lavoro e' ancora «consegnato» (EMESSA); il marchio
               --    del giro dice A CHI, e vw_lotti_fase se quel giro e' vivo.
               --    Un'attivita' libera con la riga EMESSA e' DIVERGENTE:
               --    nessun giro la riprende (il pull la vede EMESSA, la
               --    select di un altro lotto non trova il suo marchio).
               --    Divergente e marchio di un lotto in gioco = in transito
               --    (fra pull e select); divergente e lotto morto o senza
               --    marchio = orfana, riportabile. Lotto fuori dal perimetro
               --    RLS di chi chiede → NULL → «morto»: chi vede la commessa
               --    vede il suo lotto, e' lo stesso emittente.
               ca.stato_emissione::text AS stato_emissione_riga,
               EXISTS (SELECT 1
                         FROM vendite.vw_lotti_fase f
                        WHERE f.lotto_id = vendite.fn_lotto_da_emit_batch(af.emit_batch_id)
                          AND f.pre_fiscale)               AS marchio_pre_fiscale,
               fr.fattura_id,
               -- L'etichetta che l'operatore riconosce sulla
               -- card: commessa e competenza, mai un id tecnico.
               format('commessa %s, competenza %s',
                      c.codice,
                      to_char(af.competenza_mese, 'MM/YYYY')) AS etichetta
          FROM sel s
          JOIN vendite.attivita_fatturabili af ON af.id = s.id
          JOIN vendite.commesse_attivita ca    ON ca.id = af.commessa_attivita_id
          JOIN vendite.commesse c              ON c.id  = af.commessa_id
          -- LEFT: se chi chiede non vede la riga di fattura, il
          -- motivo deve uscire lo stesso — senza bersaglio.
          LEFT JOIN vendite.fatture_righe fr   ON fr.id = af.fattura_riga_id
    ),
    -- ── MOTIVO 1 — non esiste, o e' fuori perimetro ──────────
    -- ⚠️ AGGREGATO, non per riga: di una riga che non si vede non
    --    si puo' dire niente che l'operatore riconosca — nemmeno
    --    la commessa. L'unica informazione onesta e' QUANTE sono,
    --    e il rimedio (aggiorna l'elenco) e' lo stesso per tutte.
    m1 AS (
        SELECT CASE WHEN count(*) > 0
                    THEN jsonb_build_array(jsonb_build_object(
                             'codice',                  'E_ATTIVITA_FATTURABILE_NON_TROVATA',
                             'reason',                  'ATTIVITA_NON_TROVATA',
                             'reason_key',              'vendite.attivita.azione_reason.non_trovata',
                             'dettaglio',               count(*)::text,
                             'attivita_fatturabile_id', NULL::bigint,
                             'commessa_id',             NULL::bigint,
                             'fattura_id',              NULL::bigint))
                    ELSE '[]'::jsonb END AS j
          FROM sel s
         WHERE NOT EXISTS (SELECT 1 FROM vis v
                            WHERE v.attivita_fatturabile_id = s.id)
    ),
    -- ── MOTIVO 2 — e' ancora dentro una fattura ──────────────
    -- ⛔ E' il guard che impedisce al verbo di diventare un modo
    --    per SCOLLEGARE UNA FATTURA VIVA. Il trigger di riga
    --    trgfn_attivita_fatturabili_guard_fatturato dice gia' la
    --    stessa cosa da un altro livello; qui si dice con una
    --    frase che nomina il documento, perche' un
    --    E_RIGA_GIA_FATTURATA generico non dice all'operatore
    --    COSA stava tentando.
    m2 AS (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
                   'codice',                  'E_ATTIVITA_ANCORA_IN_FATTURA',
                   'reason',                  'ATTIVITA_IN_FATTURA',
                   'reason_key',              'vendite.attivita.azione_reason.ancora_in_fattura',
                   'dettaglio',               v.etichetta,
                   'attivita_fatturabile_id', v.attivita_fatturabile_id,
                   'commessa_id',             v.commessa_id,
                   'fattura_id',              v.fattura_id)
                   ORDER BY v.attivita_fatturabile_id), '[]'::jsonb) AS j
          FROM vis v
         WHERE v.fattura_riga_id IS NOT NULL
    ),
    -- ── MOTIVO 3 — non c'e' niente da riportare ──────────────
    -- Senza lucchetto E con la riga di commessa gia' NON_EMESSA
    -- l'attivita' e' davvero disponibile: il giro successivo la
    -- prende da se'. Dirlo e' diverso dal motivo 2, e il rimedio e'
    -- «non fare niente».
    -- ⛔ rev 2026-09-12: «senza lucchetto» da solo NON bastava. Con
    --    la riga ancora EMESSA il pull non la vede e nessun giro la
    --    riprende: quello stato era irraggiungibile da ogni verbo,
    --    e questo motivo lo chiamava «gia' disponibile». Verificato
    --    il 12-09 sul lotto 13338 (E_ATTIVITA_GIA_DA_EMETTERE su due
    --    attivita' che nessuno avrebbe mai ripreso).
    m3 AS (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
                   'codice',                  'E_ATTIVITA_GIA_DA_EMETTERE',
                   'reason',                  'ATTIVITA_GIA_DISPONIBILE',
                   'reason_key',              'vendite.attivita.azione_reason.gia_da_emettere',
                   'dettaglio',               v.etichetta,
                   'attivita_fatturabile_id', v.attivita_fatturabile_id,
                   'commessa_id',             v.commessa_id,
                   'fattura_id',              NULL::bigint)
                   ORDER BY v.attivita_fatturabile_id), '[]'::jsonb) AS j
          FROM vis v
         WHERE v.fattura_riga_id IS NULL
           AND NOT v.lucchettata
           AND v.stato_emissione_riga <> 'EMESSA'
    ),
    -- ── MOTIVO 5 — EMESSA e non ancora lockata, dentro un giro VIVO ──
    -- ⭐ rev 2026-09-12. E' la finestra fra il pull e la select di un
    --    lotto che sta girando: la riga e' EMESSA, l'attivita' porta il
    --    marchio di un lotto in gioco, nessun lucchetto ancora. Non e'
    --    orfana: e' in transito. Liberarla da qui la farebbe prendere
    --    da due giri — stessa ragione del motivo 4, letta dal marchio
    --    invece che dal lucchetto. Stesso codice e stessa classe
    --    (CONFLITTO_STATO, rimedio «aspetta»); `reason` suo, perche'
    --    la diagnosi distingua i due transiti.
    -- ⭐ Quando il marchio e' di un lotto MORTO (o non c'e'), la stessa
    --    coppia «libera + EMESSA» non e' un motivo: e' la divergenza, e
    --    il verbo la riallinea con fn_libera_attivita_fatturabili.
    m5 AS (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
                   'codice',                  'E_ATTIVITA_IN_LAVORAZIONE',
                   'reason',                  'ATTIVITA_EMESSA_IN_GIRO_VIVO',
                   'reason_key',              'vendite.attivita.azione_reason.in_lavorazione',
                   'dettaglio',               v.etichetta,
                   'attivita_fatturabile_id', v.attivita_fatturabile_id,
                   'commessa_id',             v.commessa_id,
                   'fattura_id',              NULL::bigint)
                   ORDER BY v.attivita_fatturabile_id), '[]'::jsonb) AS j
          FROM vis v
         WHERE v.fattura_riga_id IS NULL
           AND NOT v.lucchettata
           AND v.stato_emissione_riga = 'EMESSA'
           AND v.marchio_pre_fiscale
    ),
    -- ── MOTIVO 4 — e' dentro un giro VIVO ────────────────────
    -- ⛔ Lucchettata e non COMPLETED vuol dire che un lotto la sta
    --    lavorando ADESSO. Liberarla da qui la farebbe prendere da
    --    due giri insieme. E' la condizione che separa l'orfana
    --    dal transito legittimo, ed e' il motivo per cui la card
    --    «Emesse non fatturate» non e' un perimetro: contiene due
    --    popolazioni strutturalmente diverse.
    m4 AS (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
                   'codice',                  'E_ATTIVITA_IN_LAVORAZIONE',
                   'reason',                  'ATTIVITA_IN_GIRO_VIVO',
                   'reason_key',              'vendite.attivita.azione_reason.in_lavorazione',
                   'dettaglio',               v.etichetta,
                   'attivita_fatturabile_id', v.attivita_fatturabile_id,
                   'commessa_id',             v.commessa_id,
                   'fattura_id',              NULL::bigint)
                   ORDER BY v.attivita_fatturabile_id), '[]'::jsonb) AS j
          FROM vis v
         WHERE v.fattura_riga_id IS NULL
           AND v.lucchettata
           AND v.stato_esecuzione IS DISTINCT FROM 'COMPLETED'
    )
    -- L'ordine di concatenazione E' la priorita': la mutazione
    -- solleva il primo motivo, e il primo dev'essere quello che
    -- spiega di piu'.
    SELECT m1.j || m2.j || m3.j || m5.j || m4.j
      INTO v_motivi
      FROM m1, m2, m3, m5, m4;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_attivita_riportabile_da_emettere(p_attivita_fatturabili_ids bigint[])
IS 'Elenca i motivi che impediscono di riportare «da emettere» un insieme di vendite.attivita_fatturabili. Funzione PURA: nessuna scrittura e nessun raise di dominio — la mutazione vendite.fn_riporta_attivita_da_emettere solleva il codice del PRIMO motivo, mentre il backend li mostra tutti. Ritorna [] se si puo'' fare su tutte. ⛔ IL PERIMETRO NON USA `fatturato`, ed e'' deliberato: con la colonna generata prevista dal lotto L3b il predicato «fatturato IS TRUE AND fattura_riga_id IS NULL» diventerebbe sempre falso e il verbo smetterebbe di funzionare IN SILENZIO. Le tre condizioni vere sono fattura_riga_id IS NULL (non e'' in nessuna fattura), lock_in_fatturazione (e'' ancora lucchettata, nessun giro la riprende) e stato_esecuzione = COMPLETED (il giro che la lucchettava ha dichiarato di aver finito) — ⭐ e la terza e'' cio'' che separa l''ORFANA dal GIRO VIVO: PENDING/RUNNING vuol dire lotto in corso, e quello non si tocca. E'' anche il motivo per cui la card «Emesse non fatturate» non e'' il perimetro del verbo: contiene due popolazioni strutturalmente diverse. ⛔ E LO SCOPE STA SULLA COMMESSA: vendite.attivita_fatturabili non ha row level security, vendite.commesse_attivita si'' — quindi l''attivita'' si risolve passando per quel JOIN, che E'' il cancello. Leggere la sola attivita_fatturabili sarebbe fail-open, e il danno non sarebbe un permesso concesso a vuoto: la mutazione libererebbe l''attivita'' (tabella senza RLS) e NON riporterebbe la riga di commessa a NON_EMESSA (tabella con RLS, zero righe toccate), cioe'' lo stato SPEZZATO che la primitiva condivisa di L1 esiste per impedire. Chi non vede la riga riceve «non trovata», che dal suo punto di vista e'' la verita''. ℹ️ Il primo motivo e'' AGGREGATO (quante mancano) e gli altri sono PER ATTIVITA'': di una riga che non si vede non si puo'' dire niente che l''operatore riconosca, mentre delle altre si nomina «commessa <codice>, competenza <MM/AAAA>», che e'' come le vede sulla card. I campi attivita_fatturabile_id, commessa_id e fattura_id non servono all''interfaccia: servono alla mutazione per comporre il bersaglio dell''errore senza rileggersi le stesse righe. Piano: brief-db-lavoro-che-non-torna-indietro, L5 / D-4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
