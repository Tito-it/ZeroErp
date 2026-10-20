{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_normalize`

```sql
CREATE FUNCTION trgfn_billing_account_guard_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- ⚠️ Ancorate alle colonne (AGENTS.md, linee-guida-sql §5b).
  --   Le due preesistenti erano `text` nudo: corrette qui, non
  --   e' un cambio di comportamento.
  v_cf_child   anagrafiche.soggetti.id_fiscale_univoco_cf_piva%TYPE;
  v_cf_parent  anagrafiche.soggetti.id_fiscale_univoco_cf_piva%TYPE;
  v_sog_child  anagrafiche.soggetti.id%TYPE;
  v_sog_parent anagrafiche.soggetti.id%TYPE;
BEGIN
  ------------------------------------------------------------------
  -- 1) NORMALIZE (pulizie/derive)
  ------------------------------------------------------------------
  -- (Riservato per future normalizzazioni)

  ------------------------------------------------------------------
  -- 2) GUARD (validazioni di business con errori)
  ------------------------------------------------------------------

  -- 2.0) Parent: vieta self-reference
  IF NEW.parent_account_id IS NOT NULL AND NEW.parent_account_id = NEW.id THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME, 'E_PARENT_SELF',
      jsonb_build_object('campo', 'parent_account_id', 'codice', NEW.codice, 'parent_account_id', NEW.parent_account_id),
      NULL::uuid, NEW.parent_account_id::text
    );
  END IF;

  -- 2.1) Se c'e parent, valido_dal e' obbligatorio
  IF NEW.parent_account_id IS NOT NULL AND NEW.valido_dal IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME, 'E_VALORE_MANCANTE',
      jsonb_build_object('codice', NEW.codice, 'campo', 'valido_dal'),
      NULL::uuid, 'valido_dal'
    );
  END IF;

  -- 2.2) Coerenza del SOGGETTO FISCALE fra parent e child.
  --
  --   Rev 2026-08-18 (P-3, brief §4 e §11.1). Prima confrontava
  --   solo il codice fiscale con IS DISTINCT FROM, e aveva due
  --   buchi che si sommavano:
  --
  --   a) `NULL IS DISTINCT FROM NULL` e' FALSO -> due BA
  --      entrambi senza CF passavano anche se di soggetti
  --      DIVERSI. Il classico NULL in una chiave;
  --   b) la SELECT sul padre passa dalle policy RLS (questa
  --      funzione e' SECURITY INVOKER): un padre di un altro
  --      emittente non viene trovato, v_cf_parent restava NULL
  --      e il guard sollevava E_ID_FISCALI_DIVERSI su due CF
  --      IDENTICI — un messaggio che nomina la causa sbagliata.
  --
  --   Ora: il padre non trovato ha il suo codice; e quando il
  --   codice fiscale non e' utilizzabile come prova si ripiega
  --   sul SOGGETTO, che c'e' sempre.
  IF NEW.parent_account_id IS NOT NULL THEN
    SELECT s.id, s.id_fiscale_univoco_cf_piva
      INTO v_sog_child, v_cf_child
      FROM anagrafiche.istanze_utilities iu
      JOIN anagrafiche.soggetti s ON s.id = iu.soggetto_id
    WHERE iu.id = NEW.istanza_utility_id;

    SELECT s2.id, s2.id_fiscale_univoco_cf_piva
      INTO v_sog_parent, v_cf_parent
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.istanze_utilities iu2 ON iu2.id = ba.istanza_utility_id
      JOIN anagrafiche.soggetti s2 ON s2.id = iu2.soggetto_id
    WHERE ba.id = NEW.parent_account_id;

    -- ⚠️ FOUND si riferisce all'ULTIMA SELECT INTO, che e' quella
    --   sul padre: e' il test preciso, e va fatto subito — una
    --   SELECT INTO a vuoto AZZERA le variabili, quindi piu' in
    --   basso «NULL» non direbbe piu' se il padre manca o se e'
    --   il suo CF a mancare.
    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_PARENT_NON_RAGGIUNGIBILE',
        jsonb_build_object(
          'codice', NEW.codice,
          'parent_account_id', NEW.parent_account_id,
          'campo',  'parent_account_id',
          'detail', 'parent inesistente oppure fuori dal perimetro RLS di chi scrive'
        ),
        NULL::uuid,
        NEW.parent_account_id::text
      );
    END IF;

    IF v_cf_child IS NULL OR v_cf_parent IS NULL THEN
      -- Il codice fiscale non e' utilizzabile come prova di
      -- identita': si confronta il soggetto. Due BA dello STESSO
      -- soggetto senza CF restano legittimi — ed e' il motivo per
      -- cui qui non si rifiuta e basta.
      IF v_sog_child IS DISTINCT FROM v_sog_parent THEN
        PERFORM script.fn_log_and_raise_error(
          'database', TG_NAME, 'E_PARENT_SOGGETTO_DIVERSO',
          jsonb_build_object(
            'codice', NEW.codice,
            'parent_account_id', NEW.parent_account_id,
            'campo',  'parent_account_id',
            'soggetto_id', v_sog_child,
            'parent_soggetto_id', v_sog_parent
          ),
          NULL::uuid,
          NEW.parent_account_id::text
        );
      END IF;
    ELSIF v_cf_child IS DISTINCT FROM v_cf_parent THEN
      -- Entrambi i CF presenti e diversi: il caso storico.
      -- ⚠️ Due soggetti DIVERSI con lo stesso CF continuano a
      --   passare, ed e' voluto: quella e' identita' fiscale, che
      --   e' cio' che il guard presidia.
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_ID_FISCALI_DIVERSI',
        jsonb_build_object(
          'codice', NEW.codice,
          'parent_account_id', NEW.parent_account_id,
          'campo',  'parent_account_id',
          'id_fiscale_univoco_cf_piva', v_cf_child,
          'parent_id_fiscale_univoco_cf_piva', v_cf_parent
        ),
        NULL::uuid,
        NEW.parent_account_id::text, v_cf_child, v_cf_parent
      );
    END IF;
  END IF;

  -- 2.3) Coerenza date validita
  --   rev 20260923-43: resta solo «valido_al richiede valido_dal», che e' una
  --   regola di QUESTA tabella (qui valido_dal e' nullable). L'ordine delle
  --   due date ha una sede sola: script.trgfn_guard_date_validita, montata
  --   dall'automazione DATE_VALIDITA. Il ramo tolto sollevava
  --   E_DATA_FINE_NON_MAGGIORE_DI_INIZIO, la cui frase («minore uguale»)
  --   diceva una regola piu' stretta di quella che applicava (solo <).
  IF NEW.valido_al IS NOT NULL AND NEW.valido_dal IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME, 'E_VALORE_MANCANTE',
      jsonb_build_object('codice', NEW.codice, 'column', 'valido_al_requires_valido_dal'),
      NULL::uuid, 'valido_al'
    );
  END IF;

  -- 2.4) Guard dissociazione parent: blocca la rimozione di parent_account_id
  --      quando esistono attivita_fatturabili non ancora fatturate sul BA figlio.
  --      Questo previene la corruzione della catena di fatturazione:
  --        fatture.billing_account_id (padre) → fatture_righe.dest_billing_account_id (figlio)
  IF TG_OP = 'UPDATE'
     AND OLD.parent_account_id IS NOT NULL
     AND NEW.parent_account_id IS NULL
  THEN
    IF EXISTS (
      SELECT 1
        FROM vendite.attivita_fatturabili af
       WHERE af.billing_account_id = NEW.id
         AND af.fatturato IS FALSE
    ) THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_DISSOCIAZIONE_PARENT_CON_ATTIVITA',
        jsonb_build_object(
          'billing_account_id', NEW.id,
          'codice', NEW.codice,
          'ex_parent_account_id', OLD.parent_account_id,
          'detail', 'Impossibile rimuovere parent_account_id: esistono attivita non fatturate collegate a questo billing account'
        ),
        NULL::uuid,
        NEW.id::text, OLD.parent_account_id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()
IS 'Guard/normalize: valida parent e date; normalizza codice se presente.
Include guard dissociazione parent: blocca la rimozione di parent_account_id
quando esistono attivita_fatturabili non fatturate sul BA figlio.
Rev 2026-08-18 (P-3, brief perimetro-emittente §4 e §11.1): il §2.2 non
confronta piu'' il solo codice fiscale con IS DISTINCT FROM. Il padre non
raggiungibile (inesistente o fuori dal perimetro RLS: la funzione e''
SECURITY INVOKER) ha ora un codice suo, E_PARENT_NON_RAGGIUNGIBILE, invece
di cadere su E_ID_FISCALI_DIVERSI con i due CF identici. E quando almeno un
codice fiscale manca, il confronto ripiega sul SOGGETTO
(E_PARENT_SOGGETTO_DIVERSO): chiude il fail-open di NULL IS DISTINCT FROM
NULL senza rifiutare due BA dello stesso soggetto privo di CF.
Rev 20260923-43: l''ordine delle date (valido_al non precede valido_dal) non e'' piu'' qui: ha una sede sola, script.trgfn_guard_date_validita (automazione DATE_VALIDITA). Resta la regola propria di questa tabella: valido_al richiede valido_dal.';
```

</div>

---
{% include-markdown "signature-core.md" %}
