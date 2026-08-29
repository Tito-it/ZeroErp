{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_righe_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_fatture_righe_guard_normalize`

```sql
CREATE FUNCTION trgfn_fatture_righe_guard_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_righe_guard_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
/*
  vendite.trgfn_fatture_righe_guard_normalize()

  Scopo:
    - Eredita BA di destinazione dalla testata fattura se non valorizzato.
    - Congela sulla riga il TRATTAMENTO IVA preso dal master:
        * `iva_natura`  (dal 2025)
        * `aliquota_iva` (dal 2026-08-29, D19)
    - NON gestisce assoggettamento.

  Note:
    - Se l'IVA master ha aliquota > 0, per design natura_iva_id e' NULL:
      lo snapshot di natura risulta NULL. L'aliquota invece c'e'.
    - Se l'IVA master ha aliquota = 0, natura_iva_id puo' essere presente
      e viene copiato il codice corrispondente.
    - Nessun iva_id: entrambi gli snapshot restano com'erano. In bozza una
      riga senza codice IVA e' legittima (D3).
*/
DECLARE
  -- ⚠️ %TYPE: prima era `integer` mentre billing_account.id e' bigint.
  --   Non ha mai morso, ma era un troncamento in attesa.
  v_parent_ba    anagrafiche.billing_account.id%TYPE;
  v_natura_code  config.iva_natura.codice%TYPE;
  v_stato_id     anagrafiche.soggetti.stato_id%TYPE;
  v_aliquota     vendite.fatture_righe.aliquota_iva%TYPE;
  v_split_sogg   anagrafiche.soggetti.split_payment%TYPE;
BEGIN
  -- 1) Eredita BA dalla testata se non fornito
  IF NEW.dest_billing_account_id IS NULL THEN
    SELECT f.billing_account_id
      INTO v_parent_ba
    FROM vendite.fatture f
    WHERE f.id = NEW.fattura_id;

    NEW.dest_billing_account_id := v_parent_ba;
  END IF;

  -- 2) Snapshot del trattamento IVA dal master.
  --    ⚠️ Tutto dentro questo ramo: config.fn_get_aliquota_iva
  --    SOLLEVA su un id nullo, quindi la chiamata non deve mai
  --    poterlo incontrare.
  IF NEW.iva_id IS NOT NULL THEN
    SELECT n.codice
      INTO v_natura_code
    FROM config.iva i
    LEFT JOIN config.iva_natura n
          ON n.id = i.natura_iva_id
    WHERE i.id = NEW.iva_id;

    -- Se la natura in master e' NULL (es. aliquota > 0), resta NULL
    NEW.iva_natura := v_natura_code;

    -- ⚠️ Lo stato dell'EMITTENTE, con lo stesso identico percorso di
    --   vendite.fn_ricalcola_riepilogo_iva_fattura: se i due
    --   divergessero, riga e riepilogo dello stesso documento
    --   porterebbero aliquote diverse e nessuno se ne accorgerebbe
    --   finche' non quadrasse un totale.
    SELECT s.stato_id
      INTO v_stato_id
    FROM vendite.fatture f
    JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
    JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
    WHERE f.id = NEW.fattura_id;

    v_aliquota := config.fn_get_aliquota_iva(NEW.iva_id, v_stato_id);
    NEW.aliquota_iva := v_aliquota;
  END IF;

  -- 2-bis) ⭐ SCISSIONE DEI PAGAMENTI ed ESIGIBILITA' (I5 / D8).
  --   Fino al 2026-08-29 queste due colonne esistevano, erano nel
  --   raggruppamento del riepilogo, ed erano NULL su TUTTE le
  --   righe: non le riempiva nessuno. Il brief lo chiamava «voce
  --   corta» proprio per questo — mancava solo lo scrittore.
  --
  -- ⭐ La sede e' questo trigger e non il chiamante, per lo stesso
  --   motivo per cui ci sta gia' lo snapshot del trattamento IVA:
  --   cosi' il valore non dipende da QUALE percorso ha scritto la
  --   riga. E c'e' un secondo motivo, piu' stringente: il riepilogo
  --   RAGGRUPPA per (iva, natura, esigibilita, split). Se due
  --   righe della stessa fattura portassero valori diversi, la
  --   stessa aliquota si spezzerebbe in due riepiloghi — e la
  --   fattura direbbe due cose sul suo stesso regime.
  --
  -- ⚠️ La domanda e' del CLIENTE, non dell'emittente: la scissione
  --   e' una proprieta' di chi riceve (D8), quindi il percorso
  --   passa dal billing_account della testata e non da
  --   `emittente_soggetto_ruolo_id`, che serve al blocco 2 per un
  --   altro scopo (lo stato dell'emittente per l'override).
  SELECT s.split_payment
    INTO v_split_sogg
  FROM vendite.fatture f
  JOIN anagrafiche.billing_account ba  ON ba.id = f.billing_account_id
  JOIN anagrafiche.soggetti_ruoli sr   ON sr.id = ba.soggetto_ruolo_id
  JOIN anagrafiche.soggetti s          ON s.id  = sr.soggetto_id
  WHERE f.id = NEW.fattura_id;

  -- ⛔ Se il soggetto non si risolve NON si scrive niente, e le due
  --   colonne restano NULL. E' la stessa disciplina di D32 sul
  --   risolutore: «non scissa» e' un'AFFERMAZIONE, e non e' la
  --   risposta prudente su un documento che potrebbe andare a una
  --   PA. Il nullo dice «non determinato», ed e' vero.
  IF v_split_sogg IS NOT NULL THEN
    -- `split_payment` e' una DERIVAZIONE PURA: non esiste una
    -- scelta legittima per riga, quindi si riscrive sempre. Una
    -- riga che dissentisse dal proprio cliente sarebbe un errore,
    -- non un'eccezione.
    NEW.split_payment := (v_split_sogg = 'S');

    -- ⚠️ L'esigibilita' invece NON e' una derivazione pura, e qui
    --   le due meta' si comportano DIVERSAMENTE apposta:
    --     * con la scissione, 'S' e' IMPOSTA: non c'e' scelta;
    --     * senza, restano 'I' (immediata) e 'D' (DIFFERITA), e la
    --       differita e' una SCELTA del documento che nessuna
    --       colonna sa dedurre.
    --   Percio' fuori dalla scissione il trigger riempie solo il
    --   VUOTO: sovrascrivere cancellerebbe in silenzio una
    --   'D' scelta da qualcuno.
    IF NEW.split_payment THEN
      NEW.esigibilita := 'S';
    ELSIF NEW.esigibilita IS NULL THEN
      NEW.esigibilita := 'I';
    END IF;
  END IF;

  -- 3) Protezione soft su UPDATE:
  --    Se qualcuno cambia solo iva_natura manualmente lasciando invariato
  --    iva_id, riallineiamo comunque allo snapshot da master per evitare
  --    derive manuali.
  --    ℹ️ Ridondante rispetto al blocco 2, che riscrive gia' a ogni
  --    INSERT/UPDATE con iva_id valorizzato. Si lascia com'era: toglierlo
  --    e' un'altra modifica.
  IF TG_OP = 'UPDATE'
    AND NEW.iva_id IS NOT NULL
    AND OLD.iva_id = NEW.iva_id
    AND NEW.iva_natura IS DISTINCT FROM OLD.iva_natura
  THEN
    SELECT n.codice
      INTO v_natura_code
    FROM config.iva i
    LEFT JOIN config.iva_natura n
          ON n.id = i.natura_iva_id
    WHERE i.id = NEW.iva_id;

    NEW.iva_natura := v_natura_code;
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_righe_guard_normalize()
IS 'Eredita il billing account di destinazione dalla testata, e CONGELA sulla riga il trattamento IVA preso dal master: il codice di natura (dal 2025) e, dal 2026-08-29, l''ALIQUOTA APPLICATA (D19 del cantiere IVA). ⭐ Le due colonne sono la stessa specie — snapshot — ed e'' per questo che `iva_natura` sopravvisse alla potatura che nel 2025 tolse `iva_perc`: quella era una denormalizzazione su un documento vivo, queste sono memoria. 🔴 L''aliquota serve sulla RIGA e non solo sul riepilogo perche'' vendite.fn_ricalcola_riepilogo_iva_fattura ricostruisce i riepiloghi DALLE RIGHE: senza, una rigenerazione dopo un cambio di aliquota produrrebbe numeri diversi dall''originale e niente potrebbe smentirla. ⚠️ L''aliquota non e'' config.iva.aliquota_iva e basta: config.iva_stati puo'' sovrascriverla per lo stato dell''emittente, e lo stato si ricava con lo STESSO identico percorso di fn_ricalcola_riepilogo_iva_fattura (fattura -> soggetti_ruoli -> soggetti) — se i due divergessero, riga e riepilogo dello stesso documento porterebbero aliquote diverse e nessuno se ne accorgerebbe finche'' non quadrasse un totale. ⚠️ La chiamata sta DENTRO il ramo «iva_id valorizzato» che gia'' esisteva: config.fn_get_aliquota_iva solleva su un id nullo, e il difetto §R-3 su quel fronte non si chiude qui. ⚠️ Su un documento vivo il valore si riallinea a ogni scrittura della riga, ed e'' voluto; dal congelamento in poi le righe non si toccano piu'' (trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt), quindi resta fermo per costruzione senza un secondo presidio. ℹ️ Sistemato passando: v_parent_ba era `integer` mentre billing_account.id e'' bigint — ora ancorata con %TYPE. ℹ️ Il blocco 3 e'' ridondante rispetto al 2 e si lascia com''era: toglierlo e'' un''altra modifica. ⭐ rev 2026-08-29 ter (I5 / D8): riempie anche esigibilita e split_payment, che esistevano da sempre, erano nel raggruppamento del riepilogo ed erano NULL su TUTTE le righe - non le scriveva nessuno. La sede e'' qui e non il chiamante per lo stesso motivo dello snapshot IVA (il valore non deve dipendere da quale percorso ha scritto la riga) e per uno piu'' stringente: il riepilogo RAGGRUPPA per (iva, natura, esigibilita, split), quindi due righe della stessa fattura con valori diversi spezzerebbero la stessa aliquota in due riepiloghi. ⚠️ La domanda e'' del CLIENTE (D8): il percorso passa dal billing_account della testata, non da emittente_soggetto_ruolo_id. ⛔ Se il soggetto non si risolve non si scrive nulla e le colonne restano NULL: «non scissa» sarebbe un''affermazione, non la risposta prudente (stessa disciplina di D32). ⚠️ Le due meta'' si comportano diversamente apposta: split_payment e'' una derivazione pura e si riscrive sempre, mentre l''esigibilita'' fuori dalla scissione ammette ''I'' e ''D'' - e la differita e'' una SCELTA che nessuna colonna deduce, quindi li'' il trigger riempie solo il vuoto.';
```

---
{% include-markdown "signature-core.md" %}
