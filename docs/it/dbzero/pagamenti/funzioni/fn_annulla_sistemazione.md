{% include-markdown "it/dbzero/pagamenti/manual/fn_annulla_sistemazione.md" %}
# ⚙️ Funzione `fn_annulla_sistemazione`

```sql
CREATE FUNCTION fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text DEFAULT NULL::text)
 RETURNS character varying
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_override_aree.auth_user_id%TYPE;
    v_atto  pagamenti.sistemazioni%ROWTYPE;
    v_stato pagamenti.sistemazioni.stato%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scartare un atto di sistemazione, lasciandolo a registro
    --   con la ragione per cui e' stato scartato. ⭐ E, se l'atto
    --   era gia' stato ESEGUITO come RIPORTO, far cadere con lui
    --   il fondo che aveva creato: l'atto e il suo effetto cadono
    --   insieme, o il registro racconta un fatto che non e'
    --   avvenuto (G-4).
    --
    -- ⛔ NON ricontrolla lo stato: su un atto gia' terminale parla
    --   trgfn_sistemazioni_guard_transizione, che dice anche in
    --   che stato si trova. Due sedi per la stessa regola sono
    --   due sedi che prima o poi divergono. La riga si legge per
    --   sapere se c'e' un ESITO da disfare, non per rideliberare
    --   se l'annullamento sia ammesso.
    --
    -- ⭐ rev 2026-11-25 (brief-db-porte-aperte-dalla-sola-guc §13,
    --   giro 8): SECURITY DEFINER. Il permesso in prima riga e' quello
    --   dell'endpoint (risposta 3d, §4.5): il livello TUTTO sull'AREA
    --   pagamenti, senza oggetto (D-U a). Il perimetro lo rimette il
    --   verbo, sull'atto, con la risposta di prima. Il fondo cade dalla
    --   primitiva, non dal verbo pubblico: chi annulla una sistemazione
    --   non deve avere anche governa_fondo_fattura.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('pagamenti.fn_annulla_sistemazione');
    PERFORM script.fn_guard_livello_area(v_utente, 'pagamenti', 'TUTTO');

    -- Le GUC che dentro un verbo DEFINER aprirebbero una porta si
    -- spengono all'ingresso (le righe contabili, il reset del lotto).
    PERFORM set_config('zeroerp.allow_contabile_riga_delete_override', '', true);
    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', '', true);

    -- ⚠️ FOR UPDATE: due annullamenti in parallelo sullo stesso
    --   atto arriverebbero entrambi alla cancellazione del fondo,
    --   e il secondo non troverebbe piu' niente.
    SELECT * INTO v_atto
      FROM pagamenti.sistemazioni
     WHERE id = p_sistemazione_id
       FOR UPDATE;

    -- ⚠️ Due cose devono restare indistinguibili: l'atto non
    --   esiste, oppure e' fuori dal perimetro di chi chiede.
    --   Distinguerle direbbe a chi e' fuori perimetro che quell'atto
    --   c'e'. Il perimetro e' la regola della policy di
    --   pagamenti.sistemazioni (l'emittente del suo
    --   emittente_soggetto_ruolo_id), rimessa qui perche' il verbo
    --   legge da proprietario.
    IF NOT FOUND
       OR NOT COALESCE(script.fn_check_user_emittente_scope(
              v_utente,
              script.fn_resolve_emittente_fiscale_id('soggetto_ruolo', v_atto.emittente_soggetto_ruolo_id)),
              false) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_annulla_sistemazione',
            'E_SISTEMAZIONE_NON_TROVATA',
            jsonb_build_object('detail', 'sistemazione inesistente o fuori perimetro',
                               'sistemazione_id', p_sistemazione_id),
            NULL::uuid,
            p_sistemazione_id::text
        );
    END IF;

    UPDATE pagamenti.sistemazioni s
       SET stato  = 'ANNULLATA',
           -- ⭐ Il motivo si FONDE: se l'atto ne aveva gia' uno e la
           --   chiamata arriva vuota, si tiene quello che c'era.
           --   Se restano entrambi vuoti non passa — il guard dei
           --   dati lo pretende, perche' una decisione scartata
           --   senza una ragione non si ricostruisce.
           motivo = COALESCE(NULLIF(btrim(p_motivo), ''), s.motivo),
           -- ⚠️ Il composito dell'ESITO cade INTERO.
           --   chk_sistemazioni_eseguita pretende data_esecuzione e
           --   fondo_source_id NULL fuori da CONFERMATA;
           --   user_esecuzione non e' nel CHECK ma appartiene allo
           --   stesso fatto, e lasciarlo sarebbe un dato composito
           --   spostato a meta'.
           --   ℹ️ contabile_id non si tocca: su un RIPORTO e' gia'
           --   NULL per chk_sistemazioni_esito, e sugli altri due
           --   rami il guard non fa nemmeno arrivare qui.
           data_esecuzione = NULL,
           user_esecuzione = NULL,
           fondo_source_id = NULL,
           -- ⭐ La memoria di cio' che si sta azzerando. Solo se
           --   l'atto era davvero stato eseguito: su una BOZZA non
           --   c'e' nessuna esecuzione da ricordare, e una chiave
           --   con dentro tre `null` direbbe il falso.
           meta = CASE
               WHEN s.stato = 'CONFERMATA'
               THEN s.meta || jsonb_build_object(
                        'annullata_dopo_esecuzione',
                        jsonb_build_object(
                            'data_esecuzione', s.data_esecuzione,
                            'user_esecuzione', s.user_esecuzione,
                            'fondo_source_id', s.fondo_source_id,
                            'destinazione',    s.destinazione,
                            'annullata_il',    now()))
               ELSE s.meta
           END
     WHERE s.id = p_sistemazione_id
    RETURNING s.stato INTO v_stato;

    -- ── E IL FONDO CADE CON LUI ───────────────────────────
    -- ⚠️ L'ordine e' invertito rispetto a §9.6-b del brief, e non
    --   poteva essere altrimenti: fk_sistemazioni_fondo_source e'
    --   NO ACTION, quindi finche' l'atto punta il fondo il DELETE
    --   e' trattenuto — e per staccare il puntatore serve proprio
    --   l'UPDATE qui sopra.
    -- ⭐ La garanzia che il brief chiedeva («solo se la
    --   cancellazione riesce») regge lo stesso, per costruzione:
    --   siamo dentro UNA funzione, cioe' una transazione. Se
    --   la primitiva solleva, l'UPDATE non
    --   sopravvive, e il record che il brief temeva — sistemazione
    --   annullata con il suo fondo ancora vivo — non e'
    --   raggiungibile.
    -- ⚠️ Cancellare RIAPRE la rigenerazione automatica: l'«atto
    --   unico» guarda se un atto esiste in qualunque stato, quindi
    --   il giro successivo ne rifa' uno leggendo il residuo di
    --   adesso. Sul riporto e' il comportamento giusto — l'eccedenza
    --   e' tornata al suo posto — ma e' un cambio reale.
    IF v_atto.stato        = 'CONFERMATA'
       AND v_atto.destinazione = 'RIPORTO'
       AND v_atto.fondo_source_id IS NOT NULL
    THEN
        PERFORM vendite.fn_applica_cancellazione_fondo_fattura(v_atto.fondo_source_id);
    END IF;

    RETURN v_stato;
END
$function$

COMMENT ON FUNCTION pagamenti.fn_annulla_sistemazione(p_sistemazione_id bigint, p_motivo text)
IS 'Verbo SECURITY DEFINER dell''endpoint di annullo della sistemazione: in prima riga script.fn_guard_livello_area con TUTTO sull''area pagamenti (lo stesso controllo dell''endpoint, senza oggetto), poi il perimetro sull''atto (fuori, come un atto che non esiste: E_SISTEMAZIONE_NON_TROVATA); spegne all''ingresso le GUC delle porte delle righe contabili e del reset del lotto. Il fondo cade dalla primitiva, cosi'' chi annulla non deve avere anche governa_fondo_fattura (brief-db-porte-aperte-dalla-sola-guc, giro 8). Scarta un atto di sistemazione lasciandolo a REGISTRO con la ragione per cui e'' stato scartato — annullare non e'' cancellare, ed e'' il senso stesso di avere un registro: l''eccedenza continuera'' a comparire nell''elenco (e'' vera, non se n''e'' andata) e chi guarda trovera'' scritto perche'' la volta scorsa si e'' deciso di lasciarla li''. ⭐ rev 2026-08-31 (D-25 di brief-db-fondo-fattura-ricalcolo-e-governo §9.6, decisione G-4 di Tid): su un atto gia'' CONFERMATA di destinazione RIPORTO fa cadere anche il FONDO che aveva creato, chiamando la primitiva vendite.fn_applica_cancellazione_fondo_fattura — l''atto e il suo effetto cadono insieme, o il registro racconta un fatto che non e'' avvenuto. ⭐ Guida pagamenti e non vendite per tre ragioni: chi alza la bandiera la abbassa (il fondo l''ha creato fn_conferma_sistemazione), api.md vieta le chiamate laterali fra moduli di pari livello quindi la sola sede in cui i due schemi si toccano e'' il database, e l''atto sta qui mentre il fondo e'' la sua conseguenza. ⚠️ L''ORDINE e'' invertito rispetto al brief — prima si stacca e si annulla, poi si cancella — perche'' fk_sistemazioni_fondo_source e'' NO ACTION e trattiene il DELETE finche'' l''atto punta il fondo; la garanzia «solo se la cancellazione riesce» regge per costruzione, essendo tutto dentro una funzione: se la cancellazione solleva, l''UPDATE non sopravvive. ⚠️ Il composito dell''esito (data_esecuzione, user_esecuzione, fondo_source_id) cade INTERO, come pretende chk_sistemazioni_eseguita, e cio'' che il registro perderebbe finisce sotto meta->''annullata_dopo_esecuzione'' — scritta solo quando l''atto era davvero stato eseguito, perche'' su una BOZZA una chiave con dentro tre null direbbe il falso. ⚠️ Cancellare il fondo RIAPRE la rigenerazione automatica: l''«atto unico» guarda se un atto esiste in qualunque stato, e il giro successivo ne rifa'' uno leggendo il residuo di adesso. ⭐ Non e'' una madre nel senso stretto: scrive una riga e ne cancella una in un altro schema, e sta qui perche'' e'' tutto SQL. ⛔ NON ricontrolla lo stato: su un atto gia'' terminale parla trgfn_sistemazioni_guard_transizione, che dal changeSet 20260831-66 porta il varco CONFERMATA -> ANNULLATA sul solo RIPORTO e rifiuta l''annullamento degli altri due nominando la correzione guidata. La riga si legge per sapere se c''e'' un ESITO da disfare, non per rideliberare. ⭐ Il motivo si fonde e non si sovrascrive: se l''atto ne aveva gia'' uno e la chiamata arriva vuota, si tiene quello che c''era.';
```

</div>

---
{% include-markdown "signature-core.md" %}
