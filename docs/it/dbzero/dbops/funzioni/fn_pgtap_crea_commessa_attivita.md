{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_commessa_attivita.md" %}
# ⚙️ Funzione `fn_pgtap_crea_commessa_attivita`

```sql
CREATE FUNCTION fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric, p_articolo_id uuid, p_listino_versione_id bigint, p_listino_riga_id bigint, p_sorgente_codice character varying, p_sorgente_uid text, p_sorgente_riga_id bigint, p_quantita numeric, p_stato_approvazione character varying, p_stato_emissione character varying, p_competenza_dal date, p_competenza_al date, p_chiave_etichetta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric DEFAULT 10, p_articolo_id uuid DEFAULT NULL::uuid, p_listino_versione_id bigint DEFAULT NULL::bigint, p_listino_riga_id bigint DEFAULT NULL::bigint, p_sorgente_codice character varying DEFAULT NULL::character varying, p_sorgente_uid text DEFAULT NULL::text, p_sorgente_riga_id bigint DEFAULT NULL::bigint, p_quantita numeric DEFAULT 1, p_stato_approvazione character varying DEFAULT 'APPROVATA'::character varying, p_stato_emissione character varying DEFAULT 'NON_EMESSA'::character varying, p_competenza_dal date DEFAULT NULL::date, p_competenza_al date DEFAULT NULL::date, p_chiave_etichetta text DEFAULT NULL::text)
 RETURNS TABLE(attivita_id bigint, articolo_id uuid, uom_id bigint, competenza_dal date, competenza_al date)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un'ATTIVITA' approvata su una
--   commessa gia' costruita, scritta dalla madre del dominio.
-- Uso:
--   CREATE TEMP TABLE tmp_a AS
--   SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
--              (SELECT commessa_id FROM tmp_c));
--   Senza sorgente la riga nasce da un consumo nuovo del billing account
--   della commessa (dbops.fn_pgtap_crea_consumo): un documento vero, senza
--   righe, con la chiave che il push dei consumi comporrebbe.
--   Con un articolo costruito prima (coi suoi flag) e il listino:
--   SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
--              p_commessa_id         => ...,
--              p_articolo_id         => ...,
--              p_listino_versione_id => ...,
--              p_listino_riga_id     => ...);
--   L'attivita' che la push di una riga di preventivo avrebbe scritto,
--   gia' EMESSA (rev 20261024-41): la chiave la compone il dominio.
--   SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
--              p_commessa_id        => ...,
--              p_sorgente_codice    => 'PREVENTIVO',
--              p_sorgente_uid       => (SELECT uid::text FROM tmp_prev),
--              p_sorgente_riga_id   => (SELECT id FROM tmp_riga),
--              p_stato_emissione    => 'EMESSA');
-- ⛔ L'emissione NON la fa: lo stato di emissione lo DICHIARA il test
--   (p_stato_emissione), il lavoro della pipeline resta fuori.
-- ⛔ La coerenza articolo / riga / versione la tiene la tabella.
-- ⚠️ Una riga di listino INVISIBILE (di un'altra azienda, sotto la
--   RLS di chi agisce) non ferma il builder se il chiamante da'
--   articolo e versione, come fa il backend: l'unita' di misura
--   viene dall'articolo, e giudica il guard (rev 2026-10-16).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_ba_id    vendite.commesse.billing_account_id%TYPE;
    v_dal      vendite.commesse_attivita.competenza_dal%TYPE;
    v_al       vendite.commesse_attivita.competenza_al%TYPE;
    v_ist_id   anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_articolo vendite.commesse_attivita.articolo_id%TYPE;
    v_uom      vendite.commesse_attivita.uom_id%TYPE;
    v_versione vendite.commesse_attivita.listino_versione_id%TYPE;
    v_attivita vendite.commesse_attivita.id%TYPE;
    v_riga_articolo vendite.listini_righe.articolo_id%TYPE;
    v_riga_uom      vendite.listini_righe.uom_id%TYPE;
    v_riga_versione vendite.listini_righe.listino_versione_id%TYPE;
    v_sorg_id  vendite.commesse_attivita.sorgente_tipo_id%TYPE;
    -- La chiave del documento in testo, come la riceve la madre (id o uid).
    v_sorg_chiave text;
    v_segment  vendite.commesse_attivita.segment_key%TYPE;
BEGIN
    SELECT c.billing_account_id,
           COALESCE(c.competenza_dal, date_trunc('month', (SELECT script.fn_data_operativa()))::date),
           COALESCE(c.competenza_al,
                    (date_trunc('month', (SELECT script.fn_data_operativa())) + interval '1 month - 1 day')::date)
      INTO v_ba_id, v_dal, v_al
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    -- ⚠️ Guard sul parametro: una commessa che non esiste
    --   farebbe morire la madre su un NULL che non la nomina.
    IF v_ba_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_commessa_attivita: nessuna commessa con id = %',
            p_commessa_id;
    END IF;

    -- Il periodo del test, se lo da' (rev 20261024-41).
    v_dal := COALESCE(p_competenza_dal, v_dal);
    v_al  := COALESCE(p_competenza_al, v_al);

    -- La sorgente. Senza: un consumo nuovo del billing account della
    -- commessa, il documento piu' leggero del modello (niente righe).
    -- Con: il documento da cui la riga viene. In tutti e due i casi la
    -- chiave la compone il dominio (script.fn_segment_key, il SOLO
    -- costruttore): la chiave del gruppo fatturabile ne legge l'uid.
    IF p_sorgente_codice IS NULL THEN
        SELECT s.id INTO v_sorg_id
          FROM config.sorgenti s
         WHERE s.codice_interno = 'ATTIVITA_CONSUMI' AND s.attivo;
        SELECT c.consumo_id::text, c.segment_key
          INTO v_sorg_chiave, v_segment
          FROM dbops.fn_pgtap_crea_consumo(v_ba_id, v_dal) c;
    ELSE
        SELECT s.id INTO v_sorg_id
          FROM config.sorgenti s
         WHERE s.codice_interno = p_sorgente_codice AND s.attivo;
        IF v_sorg_id IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_commessa_attivita: nessuna sorgente attiva con codice_interno = %',
                p_sorgente_codice;
        END IF;
        IF p_sorgente_uid IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_commessa_attivita: la sorgente % vuole la chiave del documento (p_sorgente_uid)',
                p_sorgente_codice;
        END IF;
        v_sorg_chiave := p_sorgente_uid;
        -- La chiave del push nomina il documento col suo UID, qualunque forma
        -- di chiave passi il test (come il push, che passa sempre l'uid): la
        -- chiave del gruppo fatturabile lo legge da li', e il guard della chiave
        -- lo verifica. Un documento che non si risolve lascia la chiave del test,
        -- e la madre lo rifiuta (E_SORG_NOT_FOUND).
        v_segment  := script.fn_segment_key(
                          p_sorgente_codice,
                          COALESCE((SELECT d.documento_uid::text
                                      FROM script.fn_sorgente_documento_da_chiave(v_sorg_id, p_sorgente_uid) d),
                                   p_sorgente_uid),
                          p_sorgente_riga_id);
    END IF;

    -- L'etichetta del test in coda alla chiave: righe distinte dalla stessa provenienza.
    IF p_chiave_etichetta IS NOT NULL THEN
        v_segment := (v_segment || ':' || p_chiave_etichetta)::varchar;
    END IF;

    SELECT ba.istanza_utility_id INTO v_ist_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = v_ba_id;

    v_versione := p_listino_versione_id;

    -- La riga di listino, se c'e': da lei l'unita' di misura e,
    --   se il chiamante non li da', articolo e versione.
    IF p_listino_riga_id IS NOT NULL THEN
        SELECT lr.articolo_id, lr.uom_id, lr.listino_versione_id
          INTO v_riga_articolo, v_riga_uom, v_riga_versione
          FROM vendite.listini_righe lr
         WHERE lr.id = p_listino_riga_id;

        IF FOUND THEN
            v_articolo := COALESCE(p_articolo_id, v_riga_articolo);
            v_uom      := v_riga_uom;
            v_versione := COALESCE(v_versione, v_riga_versione);
        ELSIF p_articolo_id IS NOT NULL AND p_listino_versione_id IS NOT NULL THEN
            -- ⭐ Rev 2026-10-16: la riga non si vede sotto la RLS di
            --   chi agisce (listino di un'altra azienda). Il backend
            --   in quel caso passa articolo, unita' di misura e
            --   versione, e il guard (DEFINER) giudica: qui l'unita'
            --   di misura viene dall'articolo (catalogo unico,
            --   visibile), sotto. Prima il builder si fermava qui e
            --   il guard non veniva mai raggiunto.
            v_articolo := p_articolo_id;
        ELSE
            RAISE EXCEPTION
                'fn_pgtap_crea_commessa_attivita: nessuna riga di listino con id = % visibile a chi agisce (se e'' di un''altra azienda, si passano anche p_articolo_id e p_listino_versione_id)',
                p_listino_riga_id;
        END IF;
    ELSIF p_articolo_id IS NOT NULL THEN
        v_articolo := p_articolo_id;
    ELSE
        -- L'articolo si costruisce: il catalogo, da zero, e' vuoto.
        v_articolo := dbops.fn_pgtap_crea_articolo(
            ('PGT-ATT-' || substr(md5(clock_timestamp()::text || p_commessa_id::text), 1, 12))::varchar,
            false);
    END IF;

    IF v_uom IS NULL THEN
        SELECT a.uom_id INTO v_uom
          FROM catalogo.articoli a
         WHERE a.id = v_articolo;

        -- ⚠️ Guard sul parametro: un articolo che non esiste
        --   farebbe morire la madre su uom_id, senza nominarlo.
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_commessa_attivita: nessun articolo con id = %',
                v_articolo;
        END IF;
    END IF;

    SELECT r.attivita_id INTO v_attivita
      FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => p_commessa_id,
        p_segment_key                   => v_segment,
        p_articolo_id                   => v_articolo,
        p_istanza_utility_id            => v_ist_id,
        p_data_attivita                 => v_dal,
        p_uom_id                        => v_uom,
        p_quantita                      => p_quantita,
        p_competenza_mese               => date_trunc('month', v_dal)::date,
        p_competenza_dal                => v_dal,
        p_competenza_al                 => v_al,
        p_prezzo_snapshot               => p_prezzo_snapshot,
        p_prezzo_base_snapshot          => NULL,
        p_origine_prezzo                => NULL,
        p_tipo_variazione_applicata     => NULL,
        p_valore_variazione_applicata   => NULL,
        p_promo_id                      => NULL,
        p_contratto_id                  => NULL,
        p_categoria_cliente_id_snapshot => NULL,
        p_classe_utenza_id_snapshot     => NULL,
        p_listino_versione_id           => v_versione,
        p_listino_riga_id               => p_listino_riga_id,
        p_stato_approvazione            => p_stato_approvazione,
        p_stato_emissione               => p_stato_emissione,
        p_sorgente_tipo_id              => v_sorg_id,
        p_sorgente_uid                  => v_sorg_chiave,
        p_sorgente_riga                 => p_sorgente_riga_id,
        p_tipo_movimento                => 'NORMALE',
        p_meta                          => jsonb_build_object('test_scope', 'pgtap_commessa_attivita')) r;

    -- Contratto dichiarato, non fiducia nel chiamato.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_attivita, v_articolo, v_uom, v_dal, v_al;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id bigint, p_prezzo_snapshot numeric, p_articolo_id uuid, p_listino_versione_id bigint, p_listino_riga_id bigint, p_sorgente_codice character varying, p_sorgente_uid text, p_sorgente_riga_id bigint, p_quantita numeric, p_stato_approvazione character varying, p_stato_emissione character varying, p_competenza_dal date, p_competenza_al date, p_chiave_etichetta text)
IS 'Fixture pgTAP: una riga di commessa su una commessa gia'' costruita (dbops.fn_pgtap_crea_commessa), scritta dalla madre vendite.fn_upsert_commessa_attivita: di default APPROVATA e NON_EMESSA, quantita'' 1, prezzo snapshot FIXED (secondo parametro, default 10). Il builder decide il CONTESTO: istanza dal billing account della commessa, competenza dalla commessa o il mese corrente, chiave del push. La PROVENIENZA: senza p_sorgente_codice la riga nasce da un consumo nuovo del billing account della commessa (dbops.fn_pgtap_crea_consumo; tipo ATTIVITA_CONSUMI, documento senza righe); con p_sorgente_codice viene dal documento indicato, con la sua chiave (p_sorgente_uid, l''id o l''uid in testo, la traduce la madre) e la sua riga (p_sorgente_riga_id). La chiave del push la compone script.fn_segment_key, il solo costruttore, con l''uid del documento; p_chiave_etichetta le aggiunge '':<etichetta>'' per righe distinte dalla stessa provenienza. Il chiamante sceglie l''OGGETTO e la provenienza del prezzo: p_articolo_id (assente, lo costruisce dbops.fn_pgtap_crea_articolo), p_listino_versione_id, p_listino_riga_id (da lei l''unita'' di misura e, se mancano, articolo e versione; una riga di listino invisibile sotto la RLS di chi agisce non ferma il builder se il chiamante da'' anche articolo e versione, come il backend). La coerenza fra articolo, riga e versione la tiene la tabella (vendite.trgfn_attivita_guard_listino_riga); documento e riga della provenienza li verifica script.trgfn_guard_sorgente. Non emette e non lega a una fattura: lo stato di emissione lo dichiara il test. Una commessa, un articolo, una riga di listino o una sorgente inesistenti parlano. Esce con i vincoli IMMEDIATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
