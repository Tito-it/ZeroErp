{% include-markdown "it/dbzero/script/manual/fn_check_riga_contabile_eliminabile_su_distinta.md" %}
# ⚙️ Funzione `fn_check_riga_contabile_eliminabile_su_distinta`

```sql
CREATE FUNCTION fn_check_riga_contabile_eliminabile_su_distinta(p_contabile pagamenti.vendite_contabili)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_riga_contabile_eliminabile_su_distinta(p_contabile pagamenti.vendite_contabili)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: i motivi che impediscono di ELIMINARE una riga contabile —
--        attivo = false, o DELETE — giudicati sulla sua DISTINTA, gia'
--        letta dal chiamante. Funzione PURA (fn_check_*): nessuna
--        scrittura, nessun raise di dominio (salvo il guard di chiamata).
-- Consumatori: script.fn_check_riga_contabile_eliminabile (la firma
--        per id: guard e dettaglio) e il backend, in LATERAL sulle
--        liste delle righe, con l'alias della testata.
-- Ritorna: [] se la riga si puo' eliminare — la distinta e' MANUALE e
--        in BOZZA — altrimenti array ORDINATO di
--        {codice, reason, reason_key, dettaglio, valori}.
-- ⭐ Nessuna lettura sotto perimetro: si giudica la distinta RICEVUTA.
--    Chi la passa l'ha letta sotto la sua policy, una volta per
--    istruzione; rileggerla qui ricalcolerebbe il perimetro per riga
--    (linee-guida-sql §13.2). Si legge solo il catalogo degli stati.
-- ⚠️ I motivi sono tutti sulla TESTATA: una riga POSTATA sta per
--    costruzione sotto una CHIUSA, e la ferma il motivo 1.
--    Brief: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §2.2;
--    brief-db-righe-distinta-annullata-fuori-dalle-code §4.2.
DECLARE
    -- NUDO di proposito: l'array dei motivi non riflette nessuna colonna.
    v_motivi           jsonb := '[]'::jsonb;
    v_stato            pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_is_final         pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_righe_lavorabili pagamenti.vendite_contabili_stati.righe_lavorabili%TYPE;
BEGIN
    -- ⛔ Guard di PARAMETRO, e solleva: una distinta senza id non la
    --    produce nessuna lettura — e' il chiamante a essere rotto (un
    --    LEFT JOIN alla testata che non trova niente). TECNICO, come la
    --    firma per id.
    IF p_contabile.id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_riga_contabile_eliminabile_su_distinta',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_contabile',
                               'valore',    NULL),
            NULL::uuid,
            'script.fn_check_riga_contabile_eliminabile_su_distinta',
            'distinta contabile assente');
    END IF;

    -- Le bandiere sono del CATALOGO: catalogo senza row security,
    -- per chiave. ⚠️ Se lo stato non si trovasse le tre restano NULL
    -- e la risposta e' il motivo 1a, cioe' il rifiuto (fail-closed).
    SELECT s.codice_interno, s.is_final, s.righe_lavorabili
      INTO v_stato, v_is_final, v_righe_lavorabili
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.id = p_contabile.stato_id;

    -- MOTIVO 1a — le righe di questa distinta NON SI LAVORANO PIU'
    --    (righe_lavorabili = false: l'ANNULLATA). Rev 2026-09-30, D-2/D-3.
    -- ⭐ La domanda si fa al CATALOGO, non a is_final: CHIUSA e
    --    ANNULLATA sono entrambe finali e opposte per le righe.
    -- ⚠️ IS NOT TRUE: la colonna e' NOT NULL, ma se lo stato non
    --    si leggesse la risposta resta il rifiuto (fail-closed).
    -- ⭐ Codice proprio (D-2): il rimedio e' diverso da quello di una
    --    chiusa — sotto un'annullata non c'e' niente da fare.
    IF v_righe_lavorabili IS NOT TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
            'reason',     'DISTINTA_ANNULLATA',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_annullata',
            'dettaglio',  jsonb_build_object('contabile_id',   p_contabile.id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(p_contabile.codice));

    -- MOTIVO 1b — la distinta e' FINALE ma le sue righe si lavorano
    --    ancora (oggi: la CHIUSA — tardiva, «Riprendi»): eliminare no.
    -- ⭐ Riuso di E_RIGA_CONTABILE_DISTINTA_FINALE con gli STESSI due
    --    valori del guard d'ingresso: e' la stessa condizione da una
    --    porta in piu', non un accumulo. Vale per ogni origine, e
    --    copre da sola la riga POSTATA (sta sotto una CHIUSA per
    --    costruzione): nessun motivo «riga registrata».
    -- ⚠️ ELSIF e non IF: sotto un'annullata il motivo 1a ha gia'
    --    detto la cosa giusta, e questo aggiungerebbe un rimedio
    --    sbagliato al `motivi` del contesto.
    ELSIF v_is_final IS TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_FINALE',
            'reason',     'DISTINTA_FINALE',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_finale',
            'dettaglio',  jsonb_build_object('contabile_id',   p_contabile.id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(
                              p_contabile.codice,
                              CASE WHEN v_stato = 'ANNULLATA'
                                   THEN 'annullata' ELSE 'chiusa' END));
    END IF;

    -- MOTIVO 2 — la distinta NON e' compilata a mano.
    -- Eliminare e' il rimedio a un errore di DIGITAZIONE, e su una
    -- GENERATA o una AUTOMATICA nessuno ha digitato: la generata la
    -- governa il giro che l'ha prodotta (fn_cancella_fondo_fattura,
    -- fn_annulla_sistemazione), l'automatica e' la copia di un file.
    -- ⚠️ Le due frasi sono le stesse di E_CONTABILE_RIAPERTURA_NON_MANUALE:
    --    un vocabolario solo per dire «da dove viene» la distinta.
    IF p_contabile.origine IS DISTINCT FROM 'MANUALE' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_NON_MANUALE',
            'reason',     'DISTINTA_NON_MANUALE',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_non_manuale',
            'dettaglio',  jsonb_build_object('contabile_id', p_contabile.id,
                                             'origine',      p_contabile.origine),
            'valori',     jsonb_build_array(
                              p_contabile.codice,
                              CASE p_contabile.origine
                                  WHEN 'AUTOMATICA' THEN 'arrivata da un file'
                                  WHEN 'GENERATA'   THEN 'prodotta dal sistema'
                                  ELSE p_contabile.origine
                              END));
    END IF;

    -- MOTIVO 3 — la MANUALE non e' piu' in BOZZA (D18).
    -- «Ho finito di inserire» congela il contenuto: si riapre, si
    -- elimina, si rivalida. ⚠️ Scritto SOLO per la manuale: su una
    -- generata «torna in bozza» e' un rimedio che non esiste, e il
    -- motivo 2 ha gia' detto la cosa giusta. ⚠️ Whitelist (= BOZZA) e
    -- non blacklist (<> VALIDATA): uno stato nuovo non finale cade
    -- nel rifiuto, non nel silenzio. ⚠️ E' la STESSA condizione che
    -- il guard applica sull'INSERT e sui fatti (porta 2 di
    -- trgfn_vendite_contabili_righe_guard_contenuto): li' non c'e'
    -- una riga da passare, quindi la scrive lui — il pgTAP le lega.
    IF p_contabile.origine = 'MANUALE'
       AND v_is_final IS NOT TRUE
       AND v_stato IS DISTINCT FROM 'BOZZA'
    THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_CONTABILE_DISTINTA_VALIDATA',
            'reason',     'DISTINTA_VALIDATA',
            'reason_key', 'pagamenti.righe.elimina_reason.distinta_validata',
            'dettaglio',  jsonb_build_object('contabile_id',   p_contabile.id,
                                             'stato_distinta', v_stato),
            'valori',     jsonb_build_array(p_contabile.codice));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_riga_contabile_eliminabile_su_distinta(p_contabile pagamenti.vendite_contabili)
IS 'Pure check (§12.5.1): i motivi che impediscono di ELIMINARE una riga contabile — attivo = false, oppure DELETE — giudicati sulla sua DISTINTA, gia'' letta dal chiamante. Ritorna [] se si puo'' (la distinta e'' MANUALE e in BOZZA), altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. ⭐ SEDE UNICA del predicato: script.fn_check_riga_contabile_eliminabile (la firma per id, che chiamano il guard del contenuto e il dettaglio) legge riga e testata sotto RLS e delega qui; il backend la chiama in LATERAL sulle liste delle righe passando l''alias della testata (fn_check_riga_contabile_eliminabile_su_distinta(c)). ⭐ Nessuna lettura sotto perimetro: chi passa la distinta l''ha letta sotto la sua policy, una volta per istruzione; rileggerla qui ricalcolerebbe il perimetro dell''utente per ogni riga della lista (linee-guida-sql §13.2). Si legge solo il catalogo degli stati (senza RLS), perche'' le bandiere is_final e righe_lavorabili sono sue. Nessun 404 qui: non c''e'' niente da nascondere, si giudica un valore ricevuto — il no-leak e'' della firma per id. ⚠️ L''ORDINE e'' il contratto: (1a) DISTINTA_ANNULLATA — righe_lavorabili = false, E_RIGA_CONTABILE_DISTINTA_ANNULLATA; (1b) in ALTERNATIVA DISTINTA_FINALE — le altre finali, oggi la CHIUSA, riusa E_RIGA_CONTABILE_DISTINTA_FINALE e copre da sola la riga POSTATA; (2) DISTINTA_NON_MANUALE — GENERATA o AUTOMATICA; (3) DISTINTA_VALIDATA — la MANUALE non piu'' in BOZZA (D18), scritto SOLO per la manuale. ⛔ Guard di parametro: una distinta senza id (un LEFT JOIN che non ha trovato la testata) solleva E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO). ⛔ Il reason non porta il prefisso E_. Origine: nota del BE del 2026-10-21 sulla coda righe di pagamenti. Brief: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §2.2; brief-db-righe-distinta-annullata-fuori-dalle-code §4.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
