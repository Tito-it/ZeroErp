{% include-markdown "it/dbzero/script/manual/fn_check_sorgente_chiudibile.md" %}
# ⚙️ Funzione `fn_check_sorgente_chiudibile`

```sql
CREATE FUNCTION fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    v_emesse  integer := 0;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di CHIUDERE (annullare)
    --   un documento che ha spinto righe in commessa.
    --   Funzione PURA: nessuna scrittura, nessun raise di
    --   dominio. Chi ferma solleva il primo motivo.
    --
    -- ⛔ LA CHIAVE. Si legge vendite.commesse_attivita, dove
    --   `sorgente_uid` porta `<testata>.uid::text` per TUTTE le
    --   sorgenti. NON e' la stessa chiave di
    --   vendite.commesse_sorgenti, che varia per sorgente (uid
    --   per il preventivo, id per l'ordine). Sbagliarla non
    --   produce un errore: produce ZERO motivi.
    -- =========================================================
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_sorgente_chiudibile',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id',
                               'valore',    p_sorgente_tipo_id),
            NULL::uuid, 'p_sorgente_tipo_id');
    END IF;

    IF p_sorgente_uid IS NULL OR btrim(p_sorgente_uid) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_sorgente_chiudibile',
            'E_RITIRO_SORGENTE_PARAMETRO_MANCANTE',
            jsonb_build_object('parametro', 'p_sorgente_uid',
                               'valore',    p_sorgente_uid),
            NULL::uuid, 'p_sorgente_uid');
    END IF;

    -- ── MOTIVO 1 — righe gia' EMESSA ─────────────────────────
    -- ⛔ Sono in volo verso una fattura: non si ritirano, e
    --    finche' ci sono la testata non si chiude.
    -- ⭐ Da L5 il rifiuto ha una via d'uscita, e il messaggio la
    --    nomina: «Riporta da emettere» le riporta a NON_EMESSA,
    --    e da li' il ritiro le prende. Prima era un vicolo cieco.
    -- ℹ️ Le ANNULLATA non si contano (sono uscite di proposito) e
    --    nemmeno le NON_EMESSA: quelle sono proprio cio' che il
    --    ritiro portera' via.
    SELECT count(*)
      INTO v_emesse
      FROM vendite.commesse_attivita ca
     WHERE ca.sorgente_tipo_id = p_sorgente_tipo_id
       AND ca.sorgente_uid     = btrim(p_sorgente_uid)
       AND ca.stato_emissione  = 'EMESSA';

    IF v_emesse > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_SORGENTE_CON_RIGHE_EMESSE',
            'reason',     'RIGHE_COMMESSA_EMESSE',
            'reason_key', 'vendite.sorgenti.azione_reason.righe_commessa_emesse',
            'dettaglio',  v_emesse::text,
            'quante',     v_emesse,
            -- ⭐ «Il documento ha %s righe di commessa gia' emesse»: ci va il
            --   CONTEGGIO. Fino al 2026-09-09 questo motivo viaggiava anche
            --   dentro fn_check_ordine_annullabile, che lo concatena, e li' la
            --   madre passava per primo il NUMERO dell'ordine: a video usciva
            --   «Il documento ha ORD-... righe». Il guard della chiusura
            --   sorgente invece passava il dettaglio, ed era corretto — due
            --   chiamanti, una frase sola, due esiti diversi.
            'valori',     jsonb_build_array(v_emesse));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_sorgente_chiudibile(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Elenca i motivi che impediscono di CHIUDERE (annullare) un documento che ha spinto righe in commessa. Funzione PURA: nessuna scrittura e nessun raise di dominio — chi ferma solleva il primo motivo, e chi disegna l''interfaccia li mostra tutti. ⭐ Oggi il motivo e'' UNO: ci sono righe di commessa gia'' EMESSA. Quelle non si ritirano — sono in volo verso una fattura — e finche'' ci sono la testata non si chiude. ⭐ E dal lotto L5 quel rifiuto ha una VIA D''USCITA, che il messaggio nomina: «Riporta da emettere» riporta la riga a NON_EMESSA, e da li'' il ritiro la prende. Prima di L5 non ce n''era una, ed e'' il motivo per cui E_PREV_ANNULLA_COMMESSA_EMESSA era un vicolo cieco. ⭐ UNA primitiva per tutte le sorgenti, non una per documento: la sorgente e'' polimorfa e la coppia (sorgente_tipo_id, sorgente_uid) e'' gia'' la chiave che tutto il dominio usa; sei copie divergerebbero. ⛔ LA CHIAVE, e non e'' un dettaglio: si legge vendite.commesse_attivita, dove sorgente_uid porta <testata>.uid::text per TUTTE le sorgenti — verificato sul contratto, cioe'' sul corpo di fn_list_ordini_da_pushare, fn_list_preventivi_da_pushare, fn_list_ddt_da_pushare, fn_list_contratti_da_pushare e fn_list_consumi_da_pushare, che compongono tutte x.uid::text. ⚠️ NON e'' la chiave di vendite.commesse_sorgenti, che VARIA per sorgente (uid per il preventivo, id::text per l''ordine): e'' la ragione per cui fn_check_preventivo_annullabile confronta v_uid::text mentre fn_check_ordine_annullabile confronta p_ordine_id::text — le due non sono in disaccordo, ognuna segue la chiave della propria sorgente. Chi chiama QUESTA funzione deve passare <testata>.uid::text, perche'' sbagliare la chiave non produce un errore: produce ZERO motivi, cioe'' un freno che lascia passare tutto. ℹ️ Non conta le righe gia'' ANNULLATA (sono uscite di proposito) ne'' le NON_EMESSA (sono proprio quelle che il ritiro portera'' via). ⚠️ E non raggiunge le righe SOURCELESS — ONERE e RETTIFICA — perche'' non hanno sorgente: e'' corretto, e va detto invece che lasciato dedurre. Piano: brief-db-lavoro-che-non-torna-indietro, L7 / Q-5'' strada A.';
```

</div>

---
{% include-markdown "signature-core.md" %}
