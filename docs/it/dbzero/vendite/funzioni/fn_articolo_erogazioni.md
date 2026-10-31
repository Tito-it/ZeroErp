# ⚙️ Funzione `fn_articolo_erogazioni`

```sql
CREATE FUNCTION fn_articolo_erogazioni(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_articolo_erogazioni(p_articolo_id uuid)
 RETURNS TABLE(tipo_erogazione character varying, fonte_quantita_attesa character varying, e_default boolean, origine text, ordine integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: come si puo' erogare un articolo su una riga di contratto o di
--   offerta — le combinazioni (erogazione, fonte) ammesse e quella di
--   default.
--   ⛔ rev 2026-10-29 (F-7 di Tid, brief-db-contratto-righe-periodiche-in-
--     commessa): non propone piu' la generazione_canone. Anticipati o
--     normali lo dice la testata del documento e la riga vuota la segue:
--     un default dall'articolo riempirebbe la riga e la staccherebbe.
--   ⛔ rev 2026-10-29 (G-9 di Tid, Lotto 2): CANONE/DURATA (la quantita' la
--     conta il sistema dal calendario) entra nel perimetro solo se l'unita'
--     di misura dell'articolo si conta dal calendario
--     (catalogo.unita_misura.conta_dal_calendario: GIORNO | MESE). Un
--     articolo a pezzi o a ore non la vede: ne' il form, ne' l'eredita',
--     e il guard la rifiuta (EROGAZIONE_FUORI_PERIMETRO).
--   ⛔ rev 2026-10-29 (F-8 di Tid): dove la durata c'e', per il canone
--     viene prima della FISSA nell'ordine e, se il default della base e'
--     un canone, e' lei il default (CTE preferenza).
-- Regola (decisioni di Tid del 2026-10-07, brief-db-offerta-emissione-ed-
--   erogazione §C.5):
--   · l'articolo con una tipologia di listino: le combinazioni della
--     tipologia (config.listini_tipologie_erogazioni) — B-R1, B-D4;
--   · senza tipologia: quelle della natura di vendita
--     (config.nature_vendita_erogazioni), che e' NOT NULL — B-D1. Vince la
--     tipologia: le due non si sommano.
--   · ⛔ rev 2026-10-21 (§I.1, I-D1 e I-D6 di Tid): il composito non ammette
--     piu' DERIVATA_COMPONENTI (B-D5 superata), e delle combinazioni della
--     base tiene le sole FISSA. I componenti si calcolano dalla quantita'
--     del padre (coeff_qta x quantita'): un kit senza quantita' sulla riga
--     nascerebbe senza componenti e con prezzo 0. Un kit si vende in N
--     pezzi. Se il default della base non e' FISSA, sul composito diventa
--     default la prima FISSA nell'ordine qui sotto; un composito di una
--     tipologia solo a consumo non ha nessuna combinazione (il motivo
--     SENZA_EROGAZIONE di script.fn_check_articolo_riga lo dice).
-- Ordine (`ordine`, §D.4 punto 1): il default per primo, poi per
--   erogazione, poi per fonte. Chi deve scegliere UNA combinazione (l'eredita') prende la
--   prima che gli serve; il form mostra la lista in quest'ordine. Cosi'
--   la prima fonte che il form propone per un'erogazione e' quella che
--   il DB scriverebbe.
-- Zero righe se l'articolo non c'e'.
-- ⭐ Sede UNICA del perimetro e del suo ordine: la leggono il trigger
--   d'eredita', la check del guard e la lettura per il form. Il default e
--   il perimetro non possono dissentire, perche' sono la stessa riga.
DECLARE
    v_tipologia catalogo.articoli.listino_tipologia_id%TYPE;
    v_natura    catalogo.articoli.natura_vendita_id%TYPE;
    v_composito catalogo.articoli.is_composito%TYPE;
    v_calendario catalogo.unita_misura.conta_dal_calendario%TYPE;
BEGIN
    SELECT a.listino_tipologia_id, a.natura_vendita_id, a.is_composito,
           um.conta_dal_calendario
      INTO v_tipologia, v_natura, v_composito, v_calendario
      FROM catalogo.articoli a
      LEFT JOIN catalogo.unita_misura um ON um.id = a.uom_id
     WHERE a.id = p_articolo_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH base AS (
        SELECT te.tipo_erogazione, te.fonte_quantita_attesa, te.e_default,
               'TIPOLOGIA'::text AS origine
          FROM config.listini_tipologie_erogazioni te
         WHERE v_tipologia IS NOT NULL
           AND te.tipologia_id = v_tipologia
        UNION ALL
        SELECT ne.tipo_erogazione, ne.fonte_quantita_attesa, ne.e_default,
               'NATURA'::text
          FROM config.nature_vendita_erogazioni ne
         WHERE v_tipologia IS NULL
           AND ne.natura_vendita_id = v_natura
    ), perimetro AS (
        -- I-D6 (2026-10-21): il composito si vende solo con la FISSA, perche'
        --   i suoi componenti si calcolano dalla quantita' della riga.
        -- G-9 (2026-10-29): la durata solo se l'unita' si conta dal
        --   calendario.
        SELECT b.*
          FROM base b
         WHERE (v_composito IS NOT TRUE
                OR b.fonte_quantita_attesa = 'FISSA')
           AND (b.fonte_quantita_attesa <> 'DURATA'
                OR v_calendario IS NOT NULL)
    ), preferenza AS (
        -- F-8 (Tid, 2026-10-29): dove la durata c'e' (l'unita' si conta dal
        --   calendario), per il canone la si propone sempre per prima, e se
        --   il default della base e' un canone diventa default la durata. Un
        --   noleggio a 30 EUR al giorno: i giorni li conta il sistema, non
        --   l'operatore. Regola scritta, non l'ordine alfabetico delle fonti.
        SELECT p.tipo_erogazione, p.fonte_quantita_attesa, p.origine,
               CASE WHEN p.tipo_erogazione = 'CANONE'
                         AND bool_or(p.fonte_quantita_attesa = 'DURATA') OVER w
                    THEN p.fonte_quantita_attesa = 'DURATA'
                         AND bool_or(p.e_default) OVER w
                    ELSE p.e_default
               END AS e_default,
               CASE WHEN p.fonte_quantita_attesa = 'DURATA' THEN 0 ELSE 1 END AS rango_fonte
          FROM perimetro p
        WINDOW w AS (PARTITION BY p.tipo_erogazione)
    )
    SELECT t.tipo_erogazione, t.fonte_quantita_attesa,
           -- Il default della base; sul composito, se quello e' stato
           --   filtrato, la prima FISSA nell'ordine: uno e uno solo.
           CASE WHEN v_composito IS TRUE
                THEN row_number() OVER (
                         ORDER BY t.e_default DESC,
                                  t.tipo_erogazione,
                                  t.rango_fonte,
                                  t.fonte_quantita_attesa) = 1
                ELSE t.e_default
           END,
           t.origine,
           (row_number() OVER (
               ORDER BY t.e_default DESC,
                        t.tipo_erogazione,
                        t.rango_fonte,
                        t.fonte_quantita_attesa))::integer
      FROM preferenza t;
END;
$function$

COMMENT ON FUNCTION vendite.fn_articolo_erogazioni(p_articolo_id uuid)
IS 'Building block: come si può erogare un articolo su una riga di contratto o di offerta. Restituisce le combinazioni (tipo_erogazione, fonte_quantita_attesa) ammesse, e_default su quella che la riga eredita quando non la indica, l''origine (TIPOLOGIA | NATURA) e l''ordine (1 = la prima: il default, poi per erogazione, poi per fonte). Regola (decisioni di Tid del 2026-10-07): con una tipologia di listino, le combinazioni della tipologia (config.listini_tipologie_erogazioni); senza, quelle della natura di vendita (config.nature_vendita_erogazioni) — vince la tipologia, le due non si sommano; il composito tiene le sole combinazioni FISSA (un kit si vende in N pezzi: i componenti si calcolano dalla quantita'' della riga), e se il default della base non e'' FISSA il suo default e'' la prima FISSA nell''ordine; senza FISSA, zero righe. Zero righe se l''articolo non c''è. Sede unica del perimetro e del suo ordine: la leggono script.trgfn_righe_default_erogazione_da_articolo (eredità, prende la prima combinazione che le serve), script.fn_check_riga_erogazione (guard) e vendite.fn_documento_riga_erogazioni (form, ordina su ordine): la prima fonte che il form propone per un''erogazione è quella che il DB scriverebbe. STABLE, SECURITY INVOKER. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.7 (B3); ordine dal 20261007-66 (§D.4 punto 1). Rev 2026-10-21 (20261021-48, §I.1, I-D1 di Tid): ritirata DERIVATA_COMPONENTI sul composito (origine DISTINTA), B-D5 superata; I-D6: il composito si eroga solo con la FISSA. Rev 2026-10-29 (20261029-17, F-7 di Tid): non restituisce più generazione_canone — anticipati o normali li dice la testata del documento (vendite.contratti.generazione_canone), e la riga vuota la segue. Rev 2026-10-29 (20261029-33, G-9 di Tid): CANONE/DURATA solo se l''unità di misura dell''articolo si conta dal calendario (catalogo.unita_misura.conta_dal_calendario); Rev 2026-10-29 (20261029-35, F-8 di Tid): dove c''è, per il canone la durata viene prima della FISSA e, se il default della base è un canone, è lei il default.';
```

</div>

---
{% include-markdown "signature-core.md" %}
