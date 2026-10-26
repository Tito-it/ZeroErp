# ⚙️ Funzione `trgfn_registri_fatturazione_set_anno_nel_numero`

```sql
CREATE FUNCTION trgfn_registri_fatturazione_set_anno_nel_numero()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_registri_fatturazione_set_anno_nel_numero()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_default vendite.famiglie_documento.anno_nel_numero_default%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolvere alla nascita se questo sezionale espone l'anno
    --   dentro il numero. Non e' una scelta di chi crea il
    --   registro: discende dalla POLITICA (azzera per anno?) e
    --   dalla FAMIGLIA (il mio numero porta l'anno?).
    --
    -- ⛔ PERCHE': con reset_policy = ANNUALE il progressivo
    --   riparte da 1 a gennaio, quindi la stringa consegnata
    --   TORNA identica su un documento diverso. L'unicita' del
    --   documento porta l'anno in colonna, quindi non fallisce
    --   NIENTE: l'ambiguita' non la vede il database, la vede
    --   chi legge una lista o cita un numero al telefono.
    --   E' l'invariante degli assi dichiarati applicata alla
    --   stringa che una persona legge.
    --
    -- ⭐ NON TOCCA `NESSUNA`, ed e' voluto: un progressivo che
    --   non riparte non si ripete, quindi la stringa e' gia'
    --   univoca senza l'anno. La derivazione e' CONDIZIONATA
    --   alla politica, non secca.
    --
    -- ⭐ E NON TOCCA CHI HA GIA' DETTO SI': se la colonna arriva
    --   gia' true — dal backend, da una migrazione, da chi
    --   scrive a mano — resta true. Qui si riempie un silenzio,
    --   non si sovrascrive una risposta.
    -- =========================================================

    IF COALESCE(NEW.anno_nel_numero, false) THEN
        RETURN NEW;
    END IF;

    IF COALESCE(NEW.reset_policy, '') <> 'ANNUALE'
       OR NEW.famiglia_documento IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT f.anno_nel_numero_default
      INTO v_default
      FROM vendite.famiglie_documento f
     WHERE f.codice_interno = NEW.famiglia_documento;

    -- ⚠️ Famiglia non trovata: si tace. In esercizio la FK
    --   garantisce la riga; il ramo esiste per la finestra del
    --   migrate di un database ricostruito da zero, dove il
    --   mirror dei registri gira prima di quello delle famiglie
    --   (includeAll ordina per nome file). SELECT INTO senza
    --   righe lascia v_default a NULL, e il COALESCE lo rende
    --   innocuo.
    IF COALESCE(v_default, false) THEN
        NEW.anno_nel_numero := true;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_registri_fatturazione_set_anno_nel_numero()
IS 'Risolutore `_a10_` in INSERT su vendite.registri_fatturazione: un sezionale che azzera il progressivo ogni anno (reset_policy = ANNUALE), di una famiglia che dichiara anno_nel_numero_default, nasce con anno_nel_numero = true. ⛔ PERCHE'': il progressivo riparte a gennaio e la stringa consegnata torna identica su un documento diverso; l''unicita'' del documento porta l''anno in colonna, quindi nessuna scrittura fallisce e l''ambiguita'' arriva intera alle liste e a chi cita il numero. ⭐ UN RISOLUTORE E NON UN GUARD: se non esiste un caso legittimo di «ANNUALE senza anno» per quelle famiglie, il valore non e'' una scelta da difendere ma una derivazione - e cosi'' l''invariante vale per costruzione invece che per rifiuto. La misura che ha deciso: sei file pgTAP creano registri DDT/ORDINE/RESO ANNUALE senza nominare la colonna, e il backend li crea con una whitelist che non la contiene. ⭐ Riempie un silenzio, non sovrascrive una risposta: un true in arrivo resta true. ⭐ Non tocca NESSUNA: un progressivo che non riparte non si ripete. ⛔ Solo INSERT: dopo il primo numero la forma non si cambia (20260901-03). Piano: brief-db-registri-numerazione-chiave-del-contatore, sezione 11.8.';
```

</div>

---
{% include-markdown "signature-core.md" %}
