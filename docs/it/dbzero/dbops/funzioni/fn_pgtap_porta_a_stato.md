{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_porta_a_stato.md" %}
# ⚙️ Funzione `fn_pgtap_porta_a_stato`

```sql
CREATE FUNCTION fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: portare una testata di fixture nello stato voluto per
--   le transizioni della sua matrice, dopo che il test le ha
--   scritto in bozza cio' che i passaggi pretendono (righe,
--   indirizzi, prezzi…).
-- Uso:
--   SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO')
--     FROM tmp_ordine o;
-- rev 2026-10-24 (20261024-22, brief-modello-documento-vendita
--   N-1): tutte le testate con una matrice, non piu' solo ordine
--   e preventivo. Un documento nasce in bozza (trigger della
--   nascita) e si porta avanti da qui.
-- rev 2026-10-24 (20261024-30, R-4): anche il lotto di
--   fatturazione, VUOTO (con fatture si muove col verbo
--   vendite.fn_sync_lotto_fatture_stato).
-- rev 2026-10-25 (20261025-19, §7): la mappa da
--   script.fn_doc_stato_modello; dove c'e' la porta ogni passo e'
--   il verbo del documento, sui soli passaggi manuali, con l'azione
--   del passaggio concessa all'utente del contesto.
-- rev 2026-10-25 (20261025-48, §8): il preventivo ha la porta
--   (verbo vendite.fn_cambia_stato_preventivo); lo stato voluto
--   da script.fn_doc_stato_id.
-- rev 2026-10-25 (20261025-82, §9): l'ordine ha la porta (verbo
--   vendite.fn_cambia_stato_ordine). L'evasione (EVASO,
--   PARZIALMENTE_EVASO) e' di processo: non e' nel percorso, si
--   costruisce evadendo (dbops.fn_pgtap_crea_ddt_da_ordine).
-- rev 2026-10-26 (20261026-12, §11): il contratto ha la porta
--   (verbo vendite.fn_cambia_stato_contratto). CESSATO vuole
--   valido_al arrivata: la scrive il test prima di chiederlo.
-- rev 2026-10-26 (20261026-28, §13): l'offerta ha la porta (verbo
--   vendite.fn_cambia_stato_offerta). Dove la riga del passaggio
--   chiede la motivazione (rifiuto, annulli) la fixture ne passa una
--   sua. SUPERATA e' di processo: si costruisce creando una revisione
--   (vendite.fn_crea_revisione_offerta). L'annullo con legami (la
--   revisione precedente che torna emessa) passa da
--   vendite.fn_annulla_offerta, non da qui.
-- rev 2026-10-26 (20261026-36, §14): la commessa ha la porta (verbo
--   vendite.fn_cambia_stato_commessa, firma senza p_user). Lo stato
--   emittibile della push si costruisce anche da qui, dal passaggio
--   manuale «rendi pronta» (il test scrive prima le righe approvate).
-- rev 2026-10-28 (20261028-24, §16): la versione di listino ha la
--   porta. ATTIVA dal verbo vendite.fn_attiva_versione_listino (chiude
--   anche le precedenti); CHIUSA, di processo, da
--   vendite.fn_chiudi_versioni_listino_scadute: il test scrive prima
--   valido_al passata (la versione ATTIVA la accetta).
-- rev 2026-10-27 (20261027-20, §15): fattura e lotto hanno la porta. Per
--   loro il percorso comprende anche i passaggi di PROCESSO (la pipeline li
--   scrive tutti): il lotto passa dal suo verbo sui passaggi manuali
--   (vendite.fn_cambia_stato_lotto) e dal verbo di processo sugli altri
--   (vendite.fn_lotto_proietta_stato_step); la fattura dal suo verbo
--   (vendite.fn_fattura_proietta_stato).
DECLARE
    v_col       text;       -- colonna di stato della testata
    v_stati     regclass;   -- catalogo degli stati
    v_matrice   regclass;   -- matrice delle transizioni
    v_col_da    text;       -- colonna «da» della matrice
    v_col_a     text;       -- colonna «a» della matrice
    v_col_vivo  text;       -- colonna «passaggio ammesso» della matrice
    v_filtro    text;       -- condizione in piu' sui passaggi, letterale della mappa
    v_porta     boolean;    -- la testata ha la porta: i passi sono verbi
    -- Id e codici di stato di uno qualunque dei
    -- vocabolari della mappa: bigint e testo in tutti, nessuna
    -- colonna comune a cui ancorarli (%TYPE[] non e' sintassi valida).
    v_target    bigint;
    v_corrente  bigint;
    v_percorso  bigint[];
    v_passo     bigint;
    v_da        bigint;
    v_codice    text;
    v_utente    config.user_override_azioni.auth_user_id%TYPE;
    v_azione    config.azioni_processo.permission_codename%TYPE;
    v_n         integer;    -- righe toccate (ROW_COUNT): un conteggio
    v_manuale   boolean;    -- il passaggio e' manuale (script.fn_doc_passaggio)
BEGIN
    -- ── Il documento: errore del CHIAMANTE, non un dato ────────
    -- ⚠️ La fattura: la matrice ha anche i passaggi del LOTTO
    --   (solo_lotto = true), che il guard della fattura singola
    --   (vendite.trgfn_fatture_guard_stato) non ammette. Il
    --   filtro della mappa li toglie.
    SELECT m.colonna_stato, m.vocabolario, m.matrice, m.colonna_da, m.colonna_a,
           m.colonna_vivo, m.filtro
      INTO v_col, v_stati, v_matrice, v_col_da, v_col_a, v_col_vivo, v_filtro
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: documento non gestito: % (noti: le testate della mappa script.fn_doc_stato_modello)',
            p_testata;
    END IF;

    IF p_id IS NULL OR p_id <= 0 THEN
        RAISE EXCEPTION 'fn_pgtap_porta_a_stato: id testata non valido: %', p_id;
    END IF;

    -- La porta: dal catalogo, non da un elenco.
    v_porta := EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger t
         WHERE t.tgrelid = p_testata
           AND t.tgfoid  = 'script.trgfn_doc_stato_solo_dal_verbo()'::regprocedure
           AND NOT t.tgisinternal);
    IF v_porta THEN
        -- Il percorso, sotto la porta: i soli passaggi manuali. Fattura,
        -- lotto (rev 2026-10-27) e versione di listino (rev 2026-10-28)
        -- anche quelli di processo: ogni passo ha il suo verbo.
        IF p_testata NOT IN ('vendite.fatture'::regclass, 'vendite.fatturazione_lotti'::regclass,
                             'vendite.listini_versioni'::regclass) THEN
            v_filtro := v_filtro || ' AND COALESCE((t.meta ->> ''manuale'')::boolean, true)';
        END IF;
        IF p_testata NOT IN ('vendite.ddt'::regclass, 'vendite.resi'::regclass,
                             'vendite.preventivi'::regclass, 'vendite.ordini'::regclass,
                             'vendite.contratti'::regclass, 'vendite.offerte_commerciali'::regclass,
                             'vendite.commesse'::regclass, 'vendite.fatture'::regclass,
                             'vendite.fatturazione_lotti'::regclass,
                             'vendite.listini_versioni'::regclass) THEN
            RAISE EXCEPTION
                'fn_pgtap_porta_a_stato: % ha la porta ma la fixture non conosce il suo verbo',
                p_testata;
        END IF;
    END IF;

    -- ── Lo stato voluto, per codice_interno ──────────────────
    v_target := script.fn_doc_stato_id(p_testata, p_stato);
    IF v_target IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: nessuno stato attivo con codice_interno = % in %',
            p_stato, v_stati;
    END IF;

    -- ── Lo stato corrente: la testata deve esserci e vedersi ──
    EXECUTE format('SELECT t.%I FROM %s t WHERE t.id = $1', v_col, p_testata)
       INTO v_corrente USING p_id;
    IF v_corrente IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: % id = % non esiste o non e'' visibile',
            p_testata, p_id;
    END IF;

    -- ── Il percorso piu' corto nella matrice attiva ──────────
    -- ⚠️ Niente cicli: uno stato gia' visitato non si rivisita.
    --   A parita' di lunghezza, gli id minori: un ordine scelto.
    EXECUTE format($q$
        WITH RECURSIVE p(stato, percorso) AS (
            SELECT $1::bigint, ARRAY[$1::bigint]
            UNION ALL
            SELECT t.%2$I::bigint, p.percorso || t.%2$I::bigint
              FROM p
              JOIN %3$s t ON t.%1$I = p.stato AND t.%4$I IS TRUE %6$s
              JOIN %5$s s ON s.id = t.%2$I AND s.attivo IS TRUE
             WHERE NOT (t.%2$I = ANY (p.percorso))
        )
        SELECT p.percorso FROM p
         WHERE p.stato = $2
         ORDER BY cardinality(p.percorso), p.percorso
         LIMIT 1$q$, v_col_da, v_col_a, v_matrice, v_col_vivo, v_stati, v_filtro)
       INTO v_percorso USING v_corrente, v_target;

    IF v_percorso IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: nessun percorso nella matrice % da stato id % a %',
            v_matrice, v_corrente, p_stato;
    END IF;

    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- ── Il cammino: un passo alla volta, dai guard veri ──────
    v_da := v_corrente;
    FOREACH v_passo IN ARRAY v_percorso[2:] LOOP
        IF v_porta THEN
            -- L'azione del passaggio (M-3) all'utente del contesto:
            -- la fixture porta lo stato, non prova il permesso.
            SELECT p.azione_processo_codename, p.manuale INTO v_azione, v_manuale
              FROM script.fn_doc_passaggio(p_testata, v_da, v_passo) p;
            IF v_azione IS NOT NULL AND v_utente IS NOT NULL THEN
                PERFORM dbops.fn_pgtap_concedi_azione(v_utente, v_azione);
            END IF;

            EXECUTE format('SELECT s.codice_interno FROM %s s WHERE s.id = $1', v_stati)
               INTO v_codice USING v_passo;

            IF p_testata = 'vendite.ddt'::regclass THEN
                PERFORM 1 FROM vendite.fn_cambia_stato_ddt(p_id, v_codice);
            ELSIF p_testata = 'vendite.preventivi'::regclass THEN
                PERFORM 1 FROM vendite.fn_cambia_stato_preventivo(p_id, v_codice);
            ELSIF p_testata = 'vendite.ordini'::regclass THEN
                PERFORM 1 FROM vendite.fn_cambia_stato_ordine(p_id, v_codice);
            ELSIF p_testata = 'vendite.contratti'::regclass THEN
                PERFORM 1 FROM vendite.fn_cambia_stato_contratto(p_id, v_codice);
            ELSIF p_testata = 'vendite.commesse'::regclass THEN
                PERFORM 1 FROM vendite.fn_cambia_stato_commessa(p_id, v_codice);
            ELSIF p_testata = 'vendite.fatturazione_lotti'::regclass THEN
                -- Manuale: il verbo del lotto; di processo: il giro.
                IF v_manuale IS TRUE THEN
                    PERFORM 1 FROM vendite.fn_cambia_stato_lotto(p_id, v_codice);
                ELSE
                    PERFORM vendite.fn_lotto_proietta_stato_step(p_id, v_passo);
                END IF;
            ELSIF p_testata = 'vendite.fatture'::regclass THEN
                PERFORM vendite.fn_fattura_proietta_stato(p_id, v_passo);
            ELSIF p_testata = 'vendite.listini_versioni'::regclass THEN
                -- Manuale: l'attivazione (con la chiusura delle precedenti);
                -- di processo: la chiusura a scadenza, che vuole valido_al
                -- passata (rev 2026-10-28).
                IF v_codice = 'ATTIVA' THEN
                    PERFORM 1 FROM vendite.fn_attiva_versione_listino(p_id);
                ELSIF v_codice = 'CHIUSA' THEN
                    PERFORM vendite.fn_chiudi_versioni_listino_scadute();
                ELSE
                    RAISE EXCEPTION
                        'fn_pgtap_porta_a_stato: nessun verbo della versione di listino porta a %', v_codice;
                END IF;
            ELSIF p_testata = 'vendite.offerte_commerciali'::regclass THEN
                -- La motivazione dove la riga del passaggio la chiede.
                PERFORM 1 FROM vendite.fn_cambia_stato_offerta(
                    p_id, v_codice,
                    (SELECT CASE WHEN COALESCE((t.meta ->> 'requires_motivazione')::boolean, false)
                                 THEN 'Fixture pgTAP' END
                       FROM config.stati_doc_offerte_transizioni t
                      WHERE t.stato_da_id = v_da AND t.stato_a_id = v_passo AND t.attivo IS TRUE));
            ELSIF v_codice = 'CONFERMATO' THEN
                PERFORM vendite.fn_conferma_reso(p_id);
            ELSIF v_codice = 'ANNULLATO' THEN
                PERFORM vendite.fn_annulla_reso(p_id);
            ELSE
                RAISE EXCEPTION
                    'fn_pgtap_porta_a_stato: nessun verbo del reso porta a %', v_codice;
            END IF;
        ELSE
            EXECUTE format('UPDATE %s SET %I = $1 WHERE id = $2', p_testata, v_col)
              USING v_passo, p_id;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> 1 THEN
                RAISE EXCEPTION
                    'fn_pgtap_porta_a_stato: UPDATE di % id = % verso stato id % ha toccato % righe',
                    p_testata, p_id, v_passo, v_n;
            END IF;
        END IF;
        v_da := v_passo;
    END LOOP;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    -- Lo stato raggiunto si confronta con quello chiesto, per ogni
    -- testata: un verbo che non porta dove deve (la chiusura delle
    -- versioni scadute non tocca una versione che non e' scaduta, e
    -- non dice niente) e' un errore del test, non uno stato da
    -- restituire come se fosse quello voluto.
    EXECUTE format('SELECT s.codice_interno FROM %s t JOIN %s s ON s.id = t.%I WHERE t.id = $1',
                   p_testata, v_stati, v_col)
       INTO v_codice USING p_id;
    IF v_codice IS DISTINCT FROM p_stato THEN
        RAISE EXCEPTION
            'fn_pgtap_porta_a_stato: % id = % chiesta in %, e'' rimasta in % — il passaggio non e'' avvenuto (per CHIUSA della versione di listino il test scrive prima valido_al passata)',
            p_testata, p_id, p_stato, coalesce(v_codice, 'NULL');
    END IF;
    RETURN v_codice;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_porta_a_stato(p_testata regclass, p_id bigint, p_stato text)
IS 'Fixture pgTAP: porta una testata di vendita dallo stato corrente allo stato p_stato (codice_interno) per il percorso piu'' corto della sua matrice dei passaggi, sotto i guard veri: le condizioni d''uscita dalla bozza (righe, indirizzi, prezzi…) le scrive prima il test. La mappa delle testate (colonna di stato, vocabolario, matrice, filtro) la legge da script.fn_doc_stato_modello; lo stato voluto da script.fn_doc_stato_id. Testate senza la porta: un UPDATE per passo, tutti i passaggi della matrice. Testate con la porta (script.trgfn_doc_stato_solo_dal_verbo montato, letto dal catalogo): ogni passo e'' il verbo del documento, sui soli passaggi manuali, con l''azione del passaggio (script.fn_doc_passaggio) concessa all''utente del contesto da dbops.fn_pgtap_concedi_azione: la fixture porta lo stato, non prova il permesso. I verbi: bolla vendite.fn_cambia_stato_ddt; preventivo vendite.fn_cambia_stato_preventivo; ordine vendite.fn_cambia_stato_ordine; contratto vendite.fn_cambia_stato_contratto (CESSATO vuole valido_al arrivata, che scrive il test); offerta vendite.fn_cambia_stato_offerta, con una motivazione della fixture dove il passaggio la chiede; commessa vendite.fn_cambia_stato_commessa; reso vendite.fn_conferma_reso e vendite.fn_annulla_reso. Fattura, lotto e versione di listino percorrono anche i passaggi di processo, ognuno col suo verbo: la fattura vendite.fn_fattura_proietta_stato; il lotto vendite.fn_cambia_stato_lotto sui manuali e vendite.fn_lotto_proietta_stato_step sugli altri (un lotto con fatture si muove invece col giro, vendite.fn_sync_lotto_fatture_stato); la versione di listino ATTIVA da vendite.fn_attiva_versione_listino e CHIUSA da vendite.fn_chiudi_versioni_listino_scadute, che chiude ogni versione scaduta e vuole valido_al passata, scritta prima dal test. Gli stati di processo che nascono da un altro documento (EVASO e PARZIALMENTE_EVASO dell''ordine, SUPERATA dell''offerta) non si raggiungono da qui: si costruiscono evadendo o creando una revisione. Restituisce il codice_interno dello stato raggiunto, che e'' sempre p_stato: se il passaggio non e'' avvenuto solleva. Un documento nasce solo nello stato iniziale (script.trgfn_doc_stato_iniziale): una fixture che vuole un documento avanti lo crea e lo porta avanti da qui. Errori del chiamante (testata non gestita, id, stato o percorso inesistenti, porta senza verbo noto, stato non raggiunto): RAISE EXCEPTION. ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
