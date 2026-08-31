# ⚙️ Funzione `fn_pgtap_registro_fattura`

```sql
CREATE FUNCTION fn_pgtap_registro_fattura(p_emittente_sr_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_pgtap_registro_fattura(p_emittente_sr_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_emittente vendite.registri_fatturazione.emittente_soggetto_ruolo_id%TYPE;
    v_registro  vendite.registri_fatturazione.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dare a una fixture pgTAP un registro di fatturazione
    --   COERENTE con l'emittente della fattura che sta per
    --   scrivere — e crearlo se quell'emittente non ne ha.
    --
    -- Uso, al posto di «un registro qualunque»:
    --   registro_id = script.fn_pgtap_registro_fattura()
    --   registro_id = script.fn_pgtap_registro_fattura(<sr_id>)
    --
    -- ⛔ Non aggira vendite.trgfn_fatture_guard_registro_emittente:
    --   restituisce cio' che l'applicazione userebbe. Chi vuole
    --   il caso INCOERENTE se lo costruisce apposta — lo fa
    --   db/pgtap/vendite/test-fatture-guard-registro-emittente.sql.
    -- =========================================================

    -- Senza argomento: l'emittente dell'operatore di contesto,
    -- cioe' lo stesso che le fixture mettono sulla fattura.
    v_emittente := COALESCE(p_emittente_sr_id,
                            script.fn_pgtap_emittente_sr_operatore());

    IF v_emittente IS NULL THEN
        RAISE EXCEPTION
            'script.fn_pgtap_registro_fattura: nessun emittente — la fixture deve passarlo o impostare il contesto operatore';
    END IF;

    -- ⚠️ ORDER BY esplicito: un LIMIT 1 senza ordine non sceglie,
    --   scommette — e due corse darebbero registri diversi.
    SELECT r.id INTO v_registro
      FROM vendite.registri_fatturazione r
     WHERE r.emittente_soggetto_ruolo_id = v_emittente
       AND r.famiglia_documento = 'FATTURA'
       AND r.attivo IS TRUE
     ORDER BY r.id
     LIMIT 1;

    IF v_registro IS NOT NULL THEN
        RETURN v_registro;
    END IF;

    -- ⚠️ limite_emissione_giorni = 9999: le fixture datano i
    --   documenti nel passato, e un limite attivo le farebbe
    --   cadere su un presidio che non stanno provando. Chi il
    --   limite lo prova davvero si costruisce il registro da se'.
    INSERT INTO vendite.registri_fatturazione (
        codice, descrizione, reset_policy, attivo,
        emittente_soggetto_ruolo_id, limite_emissione_giorni, meta)
    VALUES (
        left('PGTAPREG_' || v_emittente::text, 32),
        'Registro di fixture pgTAP',
        'ANNUALE', TRUE,
        v_emittente, 9999,
        jsonb_build_object('test_scope', 'pgtap_registro_fattura'))
    RETURNING id INTO v_registro;

    RETURN v_registro;
END;
$function$

COMMENT ON FUNCTION script.fn_pgtap_registro_fattura(p_emittente_sr_id bigint)
IS 'Helper pgTAP: il registro di fatturazione COERENTE con l''emittente indicato — quello dell''operatore di contesto se non si passa niente — creandolo se quell''emittente non ne ha ancora uno. ⛔ Nasce il 2026-08-30 perche'' vendite.trgfn_fatture_guard_registro_emittente ha reso visibile un difetto diffuso nelle fixture: 44 file pgTAP sceglievano il registro con una pescata INDIPENDENTE da quella dell''emittente (`SELECT id FROM registri_fatturazione WHERE attivo ORDER BY data_insert DESC LIMIT 1`), e che i due coincidessero era un caso. E'' la stessa lezione che le fixture piu'' curate avevano gia'' imparato sulla terna emittente/utility/billing account — «si sceglie INSIEME, non a pescate indipendenti» — applicata a un quarto elemento che nessuno aveva legato agli altri. ⭐ Un helper e non 44 patch: l''emittente giusto si scrive in tre modi diversi a seconda della fixture, e quarantaquattro copie della stessa regola sono quarantaquattro occasioni di scriverla storta, piu'' la fixture successiva che nascerebbe di nuovo sbagliata. ⚠️ CREA il registro se manca: senza, risponderebbe NULL e la fixture morirebbe su `registro_id NOT NULL`, con un errore che parla di una colonna invece che della configurazione; la riga nasce nella transazione del test e sparisce col ROLLBACK. ⚠️ Il registro creato ha limite_emissione_giorni = 9999 — stessa scelta gia'' fatta a mano in test-registri-progressivi: le fixture datano i documenti nel passato, e un limite attivo le farebbe cadere su un presidio che non stanno provando; chi il limite lo prova davvero (test-limite-emissione-v1) si costruisce il registro da se'', e deve continuare a farlo. ⛔ NON e'' una scorciatoia per aggirare il guard: restituisce un registro coerente, cioe'' esattamente quello che l''applicazione userebbe — e chi vuole il caso INCOERENTE se lo costruisce apposta, come fa db/pgtap/vendite/test-fatture-guard-registro-emittente.sql. Compagna di script.fn_pgtap_emittente_sr_operatore. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C1-3.';
```

---
{% include-markdown "signature-core.md" %}
