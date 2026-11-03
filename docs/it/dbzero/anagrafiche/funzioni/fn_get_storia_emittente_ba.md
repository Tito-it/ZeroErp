{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba.md" %}
# ⚙️ Funzione `fn_get_storia_emittente_ba`

```sql
CREATE FUNCTION fn_get_storia_emittente_ba(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
 RETURNS TABLE(famiglia_documento character varying, famiglia_descrizione character varying, n_documenti bigint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti, 2c G-5):
--   la tabella dei documenti di ogni famiglia e' la target_table della
--   sua sorgente (config.fn_sorgente_tabella); famiglia_documento e'
--   il codice della sorgente; firma e RETURNS TABLE ancorati.
DECLARE
    v_famiglia record;
    -- un conteggio: nessuna colonna dietro
    v_n        bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire QUANTI documenti e DI CHE SPECIE hanno gia'
    --   congelato l'emittente di questo billing account. Una
    --   riga per famiglia che ha almeno un documento numerato;
    --   nessuna riga = nessuna storia.
    --
    -- ⭐ rev 2026-08-31: prima tornava (n_fatture, n_commesse) —
    --   due colonne fisse, cioe' un elenco travestito da firma.
    --   Ora la forma segue il catalogo, e il messaggio che legge
    --   l'operatore puo' dire QUALE documento blocca: senza,
    --   «non si puo'» manda a cercare a mano in cinque tabelle.
    --
    -- ⚠️ Si chiama SOLO nel ramo d'errore. Il si'/no del guard
    --   lo da' anagrafiche.fn_ba_ha_storia_emittente.
    -- =========================================================
    IF p_billing_account_id IS NULL THEN
        RETURN;
    END IF;

    FOR v_famiglia IN
        SELECT fd.codice_interno,
               fd.descrizione,
               t.schema_tabella,
               t.nome_tabella,
               fd.colonna_numero,
               fd.colonna_billing_account
          FROM vendite.famiglie_documento fd
          -- ⭐ rev 2026-10-20: la tabella e' quella della sorgente (G-5).
          -- ⚠️ LEFT e non CROSS: una famiglia attiva senza tabella (il
          --   guard dei riferimenti non la lascia nascere) non deve
          --   SPARIRE dal presidio: il format() con NULL fallisce
          --   rumoroso, come prima una tabella che non c'era.
          LEFT JOIN LATERAL config.fn_sorgente_tabella(fd.codice_interno) t ON true
         WHERE fd.attivo
           -- ⭐ Solo le famiglie che HANNO un billing account (dal
           --   20260914-07 la colonna e' opzionale): una famiglia senza
           --   BA non puo' contribuire alla storia di nessun BA. Il
           --   salto sta QUI, nella query che sceglie, e non dentro il
           --   format(): %I con NULL solleva un errore di PostgreSQL
           --   senza codice di dominio, e %s con NULL tace.
           AND COALESCE(btrim(fd.colonna_billing_account), '') <> ''
         ORDER BY fd.id
    LOOP
        EXECUTE format(
            'SELECT count(*) FROM %I.%I d'
            || ' WHERE d.%I = $1'
            || '   AND d.%I IS NOT NULL'
            || '   AND btrim(d.%I::text) <> $2',
            v_famiglia.schema_tabella,
            v_famiglia.nome_tabella,
            v_famiglia.colonna_billing_account,
            v_famiglia.colonna_numero,
            v_famiglia.colonna_numero)
          INTO v_n
         USING p_billing_account_id, ''::text;

        -- ⚠️ Le famiglie a zero NON escono: «nessuna riga» e'
        --   la risposta «nessuna storia», e chi compone la frase
        --   non deve filtrare gli zeri.
        IF v_n > 0 THEN
            famiglia_documento   := v_famiglia.codice_interno;
            famiglia_descrizione := v_famiglia.descrizione;
            n_documenti          := v_n;
            RETURN NEXT;
        END IF;
    END LOOP;

    RETURN;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_storia_emittente_ba(p_billing_account_id bigint)
IS 'Quanti documenti e DI CHE SPECIE hanno gia'' congelato l''emittente di un billing account: una riga per famiglia con almeno un documento NUMERATO, nessuna riga se non c''e'' storia. ⭐ rev 2026-08-31 (brief-db-registri-di-numerazione-emittente-e-trasloco, C2-16): prima tornava (n_fatture, n_commesse), due colonne fisse — cioe'' un elenco travestito da firma. Ora la forma segue vendite.famiglie_documento, e il messaggio del rifiuto puo'' dire QUALE documento blocca: senza, un «non si puo''» manda a cercare a mano in cinque tabelle. ⛔ CAMBIA LA DEFINIZIONE DI STORIA, e la ragione e'' il trasloco: l''argomento che escludeva ordini e DDT — «il loro emittente ha un trgfn_*_guard_emittente_ba che glielo ricontrolla a ogni scrittura, quindi non e'' una copia stantia» — cade nel momento in cui quei documenti prendono il NUMERO dal registro di quell''emittente, perche'' il numero nessuno lo rinumera. La regola nuova e'' categorica: ogni famiglia che ha un registro e'' per costruzione per-emittente, quindi blocca. ⭐ Ed e'' DERIVATA, non elencata: il sesto documento entra nella regola il giorno in cui si registra la sua famiglia, e non esiste nessun elenco parallelo che possa restare indietro — lo stesso principio della primitiva di pulizia che scopre le figlie da pg_constraint. ⚠️ IL PERIMETRO NON SI ALLARGA SOLTANTO: entrano DDT, ordini e resi numerati, ed ESCE la fattura in BOZZA — che prima si contava perche'' il conteggio era un count(*) senza condizione sul numero. E'' voluto: una bozza non ha congelato niente (vendite.trgfn_fatture_guard_uscita_draft pretende emittente_snapshot solo per USCIRE da DRAFT), ed e'' esattamente il caso per cui la finestra di correzione esiste. ⛔ Resta scoperto un punto, e va detto: una bozza porta gia'' emittente_soggetto_ruolo_id e su vendite.fatture non c''e'' un guard che lo ricontrolli col BA, quindi spostare il BA la lascerebbe sull''emittente vecchio — ma resta una bozza, si cancella e si rifa'', e presidiarla costerebbe la finestra di correzione per intero. ⚠️ Si chiama SOLO nel ramo d''errore: il si''/no del guard lo da'' anagrafiche.fn_ba_ha_storia_emittente, che esce al primo documento. ⚠️ SQL dinamico: identificatori da %I, valori da USING; una riga di catalogo sbagliata romperebbe qui a runtime, ed e'' la ragione del guard vendite.trgfn_famiglie_documento_guard_riferimenti. ⚠️ SECURITY DEFINER per la RLS, come nella versione precedente. ℹ️ Input NULL -> nessuna riga: la riga senza billing account e'' quella del gestore globale, e la guarda anagrafiche.fn_guard_ba_gestore_globale_storia. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-16. ⭐ rev 2026-09-14 (P-9, brief-db-modifiche-certe-ciclo-vendita-e-articolo sezione 3-bis): famiglie_documento.colonna_billing_account e'' opzionale, e una famiglia senza billing account (l''ordine di acquisto) NON entra nel giro: il salto sta nella query che SCEGLIE le famiglie, non dentro il format() — un %I con NULL solleverebbe un errore di PostgreSQL senza codice di dominio, e un %s con NULL produrrebbe stringa vuota senza fiatare. Il predicato resta derivato dal catalogo. Rev 2026-10-20 (20261020-41, brief-db-grammatica-unica-documenti 2c, G-5): la tabella dei documenti di ogni famiglia e'' la target_table della sua sorgente; famiglia_documento e'' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA, RESO_VENDITA, DISTINTA_INCASSO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
