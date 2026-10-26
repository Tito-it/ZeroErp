{% include-markdown "it/dbzero/script/manual/fn_check_disponibilita_uscita.md" %}
# ⚙️ Funzione `fn_check_disponibilita_uscita`

```sql
CREATE FUNCTION fn_check_disponibilita_uscita(p_magazzino_id bigint, p_articolo_id uuid, p_qta_uscita numeric, p_sorgente_tipo_id bigint, p_sorgente_riga bigint, p_sorgente_uid uuid, p_lotto_id bigint, p_asset_id bigint, p_ignora_blocchi boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_disponibilita_uscita(p_magazzino_id bigint, p_articolo_id uuid, p_qta_uscita numeric, p_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_sorgente_riga bigint DEFAULT NULL::bigint, p_sorgente_uid uuid DEFAULT NULL::uuid, p_lotto_id bigint DEFAULT NULL::bigint, p_asset_id bigint DEFAULT NULL::bigint, p_ignora_blocchi boolean DEFAULT false)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono un'USCITA di p_qta_uscita
--   (positiva, in UoM base) dell'articolo dal magazzino. Funzione PURA
--   (fn_check_*): non scrive, non solleva (tranne il guard di parametro).
--   Consumatori: magazzino.fn_scrivi_movimento (dentro il lock, solleva il
--   primo motivo con fn_raise_primo_motivo_se_presente) e la UI come
--   operatore (spegne il pulsante col motivo). Una sede sola: il numero che
--   l'operatore vede e' quello con cui la primitiva rifiuta.
-- Ritorna: [] se ammessa; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio, valori}.
-- Regole (D-L2-d):
--   1) FISICO alla grana piu' fine dichiarata: asset -> posizione dell'asset
--      in questo magazzino; lotto -> somma del lotto; altrimenti vw_giacenza;
--      deve valere >= richiesta, o E_MAG_GIACENZA_INSUFFICIENTE;
--   2) BLOCCHI alla grana dell'articolo: giacenza(articolo, magazzino) +
--      somma FIRMATA degli attesi APERTA in USCITA (qta < 0) di sorgente
--      ALTRUI deve valere >= richiesta, o E_MAG_MERCE_BLOCCATA — salvo
--      p_ignora_blocchi (is_rettifica: il fatto vince sulla promessa).
--   «Altrui»: sorgente diversa (tipo + chiave) da quella di chi chiede; un
--   blocco senza sorgente e' sempre altrui; chi chiede senza sorgente li vede
--   tutti come altrui. Un atteso in entrata (in arrivo) non e' un blocco.
-- Perimetro: INVOKER sotto RLS — chi non vede il magazzino legge zero.
-- I numeri nei `valori` passano da trim_scale(): «11», non «11.000000» — la
-- frase la legge una persona; nel `dettaglio` restano numeric pieni.
DECLARE
    v_motivi         jsonb := '[]'::jsonb;
    v_articolo       catalogo.articoli.codice%TYPE;
    v_magazzino      magazzino.magazzini.codice%TYPE;
    v_grana          text;
    v_fisico         magazzino.movimenti.qta%TYPE;
    v_giacenza       magazzino.movimenti.qta%TYPE;
    v_bloccata       magazzino.movimenti_attesi.qta%TYPE;
    v_disponibile    magazzino.movimenti.qta%TYPE;
    v_n_blocchi      bigint;
BEGIN
    -- Guard di parametro: solo forme che nessuna interfaccia produce.
    IF p_magazzino_id IS NULL OR p_magazzino_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_disponibilita_uscita',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'magazzino obbligatorio e maggiore di zero',
                               'p_magazzino_id', p_magazzino_id),
            NULL::uuid,
            'script.fn_check_disponibilita_uscita',
            'p_magazzino_id (obbligatorio, maggiore di zero)');
    END IF;
    IF p_articolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_disponibilita_uscita',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'articolo obbligatorio'),
            NULL::uuid,
            'script.fn_check_disponibilita_uscita',
            'p_articolo_id (obbligatorio)');
    END IF;
    IF p_qta_uscita IS NULL OR p_qta_uscita <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_disponibilita_uscita',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'la quantita'' in uscita e'' positiva',
                               'p_qta_uscita', p_qta_uscita),
            NULL::uuid,
            'script.fn_check_disponibilita_uscita',
            'p_qta_uscita (obbligatoria, maggiore di zero: il «quanto» che vorrebbe uscire)');
    END IF;
    IF (p_lotto_id IS NOT NULL AND p_lotto_id <= 0)
       OR (p_asset_id IS NOT NULL AND p_asset_id <= 0)
       OR (p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <= 0)
       OR (p_sorgente_riga IS NOT NULL AND p_sorgente_riga <= 0) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_disponibilita_uscita',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'un identificativo passato vale zero o meno',
                               'p_lotto_id', p_lotto_id, 'p_asset_id', p_asset_id,
                               'p_sorgente_tipo_id', p_sorgente_tipo_id,
                               'p_sorgente_riga', p_sorgente_riga),
            NULL::uuid,
            'script.fn_check_disponibilita_uscita',
            'p_lotto_id / p_asset_id / p_sorgente_tipo_id / p_sorgente_riga (se passati, maggiori di zero)');
    END IF;
    IF (p_sorgente_tipo_id IS NULL AND (p_sorgente_riga IS NOT NULL OR p_sorgente_uid IS NOT NULL))
       OR (p_sorgente_tipo_id IS NOT NULL AND (p_sorgente_riga IS NOT NULL) = (p_sorgente_uid IS NOT NULL)) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_disponibilita_uscita',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'sorgente: con il tipo esattamente una chiave, senza il tipo nessuna',
                               'p_sorgente_tipo_id', p_sorgente_tipo_id,
                               'p_sorgente_riga', p_sorgente_riga,
                               'p_sorgente_uid', p_sorgente_uid),
            NULL::uuid,
            'script.fn_check_disponibilita_uscita',
            'p_sorgente_riga / p_sorgente_uid (esattamente una con p_sorgente_tipo_id, nessuna senza)');
    END IF;

    -- I codici per la frase (non per decidere): sotto RLS un magazzino fuori
    -- perimetro non si vede, e la frase porta l'id al suo posto.
    SELECT a.codice INTO v_articolo FROM catalogo.articoli a WHERE a.id = p_articolo_id;
    SELECT m.codice INTO v_magazzino FROM magazzino.magazzini m WHERE m.id = p_magazzino_id;
    v_articolo  := COALESCE(v_articolo,  p_articolo_id::text);
    v_magazzino := COALESCE(v_magazzino, p_magazzino_id::text);

    -- ============================================================
    -- MOTIVO 1 — il FISICO alla grana piu' fine dichiarata.
    -- ============================================================
    IF p_asset_id IS NOT NULL THEN
        v_grana := 'ASSET';
        SELECT COALESCE(sum(m.qta), 0) INTO v_fisico
          FROM magazzino.movimenti m
         WHERE m.magazzino_id = p_magazzino_id
           AND m.articolo_id  = p_articolo_id
           AND m.asset_id     = p_asset_id;
    ELSIF p_lotto_id IS NOT NULL THEN
        v_grana := 'LOTTO';
        SELECT COALESCE(sum(m.qta), 0) INTO v_fisico
          FROM magazzino.movimenti m
         WHERE m.magazzino_id = p_magazzino_id
           AND m.articolo_id  = p_articolo_id
           AND m.lotto_id     = p_lotto_id;
    ELSE
        v_grana := 'ARTICOLO';
        SELECT COALESCE(g.qta, 0) INTO v_fisico
          FROM magazzino.vw_giacenza g
         WHERE g.magazzino_id = p_magazzino_id
           AND g.articolo_id  = p_articolo_id;
        v_fisico := COALESCE(v_fisico, 0);   -- SELECT INTO a zero righe azzera
    END IF;

    IF v_fisico < p_qta_uscita THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_GIACENZA_INSUFFICIENTE',
            'reason',     'GIACENZA_INSUFFICIENTE',
            'reason_key', 'magazzino.disponibilita.blocco.giacenza_insufficiente',
            'dettaglio',  jsonb_build_object('grana', v_grana,
                                             'fisico', v_fisico,
                                             'richiesta', p_qta_uscita,
                                             'lotto_id', p_lotto_id,
                                             'asset_id', p_asset_id),
            -- «Giacenza insufficiente per l'articolo %s nel magazzino %s:
            --  disponibili %s, richiesti %s.»
            'valori',     jsonb_build_array(v_articolo, v_magazzino,
                                            trim_scale(v_fisico)::text,
                                            trim_scale(p_qta_uscita)::text));
    END IF;

    -- ============================================================
    -- MOTIVO 2 — i BLOCCHI alla grana dell'articolo.
    -- ============================================================
    IF NOT COALESCE(p_ignora_blocchi, false) THEN
        SELECT COALESCE(g.qta, 0) INTO v_giacenza
          FROM magazzino.vw_giacenza g
         WHERE g.magazzino_id = p_magazzino_id
           AND g.articolo_id  = p_articolo_id;
        v_giacenza := COALESCE(v_giacenza, 0);

        -- Gli attesi APERTA in USCITA (qta < 0), firmati, di sorgente altrui.
        SELECT COALESCE(sum(a.qta), 0), count(*)
          INTO v_bloccata, v_n_blocchi
          FROM magazzino.movimenti_attesi a
         WHERE a.magazzino_id = p_magazzino_id
           AND a.articolo_id  = p_articolo_id
           AND a.stato        = 'APERTA'
           AND a.qta          < 0
           AND NOT (    p_sorgente_tipo_id IS NOT NULL
                    AND a.sorgente_tipo_id = p_sorgente_tipo_id
                    AND a.sorgente_riga IS NOT DISTINCT FROM p_sorgente_riga
                    AND a.sorgente_uid  IS NOT DISTINCT FROM p_sorgente_uid);

        v_disponibile := v_giacenza + v_bloccata;   -- in COLONNE: la somma, mai «meno»

        IF v_disponibile < p_qta_uscita THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_MAG_MERCE_BLOCCATA',
                'reason',     'MERCE_BLOCCATA_PER_ALTRI',
                'reason_key', 'magazzino.disponibilita.blocco.merce_bloccata',
                'dettaglio',  jsonb_build_object('giacenza', v_giacenza,
                                                 'bloccata', v_bloccata,
                                                 'disponibile', v_disponibile,
                                                 'n_blocchi', v_n_blocchi,
                                                 'richiesta', p_qta_uscita),
                -- «L'articolo %s nel magazzino %s ha %s pezzi disponibili
                --  (%s bloccati per altri): richiesti %s.»
                'valori',     jsonb_build_array(v_articolo, v_magazzino,
                                                trim_scale(v_disponibile)::text,
                                                trim_scale(-v_bloccata)::text,
                                                trim_scale(p_qta_uscita)::text));
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_disponibilita_uscita(p_magazzino_id bigint, p_articolo_id uuid, p_qta_uscita numeric, p_sorgente_tipo_id bigint, p_sorgente_riga bigint, p_sorgente_uid uuid, p_lotto_id bigint, p_asset_id bigint, p_ignora_blocchi boolean)
IS 'Il controllo di disponibilita'' che UI e primitiva CONDIVIDONO (M-3, D-L2-d; linee-guida-sql 12.5.2): pura, STABLE, INVOKER — [] se l''uscita di p_qta_uscita (positiva, UoM base) e'' ammessa, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. 1) E_MAG_GIACENZA_INSUFFICIENTE: il fisico alla grana piu'' fine dichiarata (asset -> posizione dell''asset in questo magazzino; lotto -> somma del lotto; altrimenti vw_giacenza) e'' minore della richiesta. 2) E_MAG_MERCE_BLOCCATA: giacenza(articolo, magazzino) + somma FIRMATA degli attesi APERTA in USCITA (qta < 0) di sorgente ALTRUI (tipo + chiave diversi da quelli di chi chiede; senza sorgente = sempre altrui; un atteso in entrata non e'' un blocco) e'' minore della richiesta — salvo p_ignora_blocchi, che la primitiva passa da causali.is_rettifica (il fatto vince sulla promessa; il fisico resta). consente_stock_negativo esonera da tutto: la primitiva non la chiama. Non legge la causale: la UI puo'' chiederla senza averne una. Chiamata da un INVOKER sotto RLS legge il magazzino se lo vede (altrimenti zero); dalla DEFINER legge tutto il magazzino, che e'' di un emittente. Guard di parametro E_MAG_CHIAMATA_NON_VALIDA (TECNICO). Le due reason_key sono chiavi i18n del frontend. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
