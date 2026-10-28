{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_righe_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_fatture_righe_guard_normalize`

```sql
CREATE FUNCTION trgfn_fatture_righe_guard_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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

  -- 2-bis) ⭐ SCISSIONE DEI PAGAMENTI ed ESIGIBILITA' (I5 / D8),
  --   rev 2026-10-01: DERIVAZIONE PURA (D-7) e regime dell'emittente.
  --
  -- ⭐ La sede resta questo trigger e non il chiamante: il valore non
  --   deve dipendere da QUALE percorso ha scritto la riga, e il
  --   riepilogo RAGGRUPPA per (iva, natura, esigibilita, split) — due
  --   righe della stessa fattura con valori diversi spezzerebbero la
  --   stessa aliquota in due riepiloghi.
  --
  -- ⭐ La REGOLA pero' non sta qui: sta in script.fn_esigibilita_iva,
  --   e le parti (regime congelato o vivo, cliente) le risolve
  --   vendite.fn_esigibilita_iva_fattura. Le stesse due funzioni le usa
  --   il ricalcolo del riepilogo (vendite.fn_ricalcola_riepilogo_iva_fattura),
  --   che riallinea le righe prima di aggregarle (D-8).
  --
  -- ⛔ Fino al 2026-09-30 fuori dalla scissione si riempiva solo il VUOTO,
  --   perche' l'unico valore che il sistema deduceva era 'I' e una 'D'
  --   poteva arrivare solo da una persona. Con l'IVA per cassa anche la
  --   'D' e' DEDOTTA, e una colonna non sa dire chi l'ha scritta: la
  --   regola «solo il vuoto» lasciava 'I' su una fattura di un emittente
  --   passato a RF17 in bozza, e 'D' su una riga il cui cliente era
  --   tornato privato. Ora le due colonne si RISCRIVONO SEMPRE, come
  --   gia' faceva split_payment. Una differita scelta a mano, se mai
  --   servira', avra' una colonna sua (brief, sezione 8.1).
  --
  -- ⛔ Cliente non risolto: la coppia esce NULL/NULL, «non determinato»
  --   (D32). Codice IVA assente su un emittente per cassa verso un
  --   soggetto IVA: esigibilita NULL, la natura non e' nota.
  SELECT e.esigibilita, e.split_payment
    INTO NEW.esigibilita, NEW.split_payment
    FROM vendite.fn_esigibilita_iva_fattura(NEW.fattura_id, NEW.iva_id) e;

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
IS 'Eredita il billing account di destinazione dalla testata, e CONGELA sulla riga il trattamento IVA preso dal master: il codice di natura (dal 2025) e, dal 2026-08-29, l''ALIQUOTA APPLICATA (D19 del cantiere IVA). ⭐ Le due colonne sono la stessa specie — snapshot — ed e'' per questo che `iva_natura` sopravvisse alla potatura che nel 2025 tolse `iva_perc`: quella era una denormalizzazione su un documento vivo, queste sono memoria. 🔴 L''aliquota serve sulla RIGA e non solo sul riepilogo perche'' vendite.fn_ricalcola_riepilogo_iva_fattura ricostruisce i riepiloghi DALLE RIGHE: senza, una rigenerazione dopo un cambio di aliquota produrrebbe numeri diversi dall''originale e niente potrebbe smentirla. ⚠️ L''aliquota non e'' config.iva.aliquota_iva e basta: config.iva_stati puo'' sovrascriverla per lo stato dell''emittente, e lo stato si ricava con lo STESSO identico percorso di fn_ricalcola_riepilogo_iva_fattura (fattura -> soggetti_ruoli -> soggetti) — se i due divergessero, riga e riepilogo dello stesso documento porterebbero aliquote diverse e nessuno se ne accorgerebbe finche'' non quadrasse un totale. ⚠️ La chiamata sta DENTRO il ramo «iva_id valorizzato» che gia'' esisteva: config.fn_get_aliquota_iva solleva su un id nullo, e il difetto §R-3 su quel fronte non si chiude qui. ⚠️ Su un documento vivo il valore si riallinea a ogni scrittura della riga, ed e'' voluto; dal congelamento in poi le righe non si toccano piu'' (trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt), quindi resta fermo per costruzione senza un secondo presidio. ℹ️ Sistemato passando: v_parent_ba era `integer` mentre billing_account.id e'' bigint — ora ancorata con %TYPE. ℹ️ Il blocco 3 e'' ridondante rispetto al 2 e si lascia com''era: toglierlo e'' un''altra modifica. ⭐ rev 2026-08-29 ter (I5 / D8): riempie anche esigibilita e split_payment, che esistevano da sempre, erano nel raggruppamento del riepilogo ed erano NULL su TUTTE le righe - non le scriveva nessuno. La sede e'' qui e non il chiamante per lo stesso motivo dello snapshot IVA (il valore non deve dipendere da quale percorso ha scritto la riga) e per uno piu'' stringente: il riepilogo RAGGRUPPA per (iva, natura, esigibilita, split), quindi due righe della stessa fattura con valori diversi spezzerebbero la stessa aliquota in due riepiloghi. ⚠️ La domanda e'' del CLIENTE (D8): il percorso passa dal billing_account della testata, non da emittente_soggetto_ruolo_id. ⛔ Se il soggetto non si risolve non si scrive nulla e le colonne restano NULL: «non scissa» sarebbe un''affermazione, non la risposta prudente (stessa disciplina di D32). ⭐ rev 2026-10-01 (D-7, D-8 di brief-db-esigibilita-iva-per-cassa-emittente): la coppia esigibilita/split_payment e'' una DERIVAZIONE PURA e si riscrive a ogni scrittura, da vendite.fn_esigibilita_iva_fattura (regime dell''emittente congelato nello snapshot se c''e'', vivo altrimenti; cliente dal billing account) sulla regola unica script.fn_esigibilita_iva. Fino al 2026-09-30 fuori dalla scissione si riempiva solo il vuoto, perche'' una ''D'' poteva venire solo da una persona: con l''IVA per cassa anche la ''D'' e'' dedotta, e il «solo il vuoto» lasciava valori stantii quando cambiavano regime o cliente. Cliente non risolto -> NULL/NULL (D32).';
```

</div>

---
{% include-markdown "signature-core.md" %}
