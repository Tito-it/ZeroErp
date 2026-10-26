{% include-markdown "it/dbzero/dbops/manual/trgfn_prevent_deactivate_if_children.md" %}
# ⚙️ Funzione `trgfn_prevent_deactivate_if_children`

```sql
CREATE FUNCTION trgfn_prevent_deactivate_if_children()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_prevent_deactivate_if_children()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_child_schema       text;
  v_child_table        text;
  v_fk_col             text;
  v_ref_col            text;     -- colonna del padre referenziata dalla FK (default 'id')
  v_parent_attivo_col  text;     -- colonna attivo del padre (rispetta override; default 'attivo')

  v_parent_ref_val_text text;
  v_fk_type             text;

  v_old_attivo boolean;
  v_new_attivo boolean;

  v_child_attivo_col text;
  v_child_has_attivo boolean;

  v_exists boolean;
  v_sql    text;
BEGIN
  /*
    Scopo
    -----
    Trigger function (ATTIVO/BLOCK): impedisce la disattivazione
    (attivo TRUE -> FALSE) del padre se esistono figli collegati.
    Se il figlio ha colonna attivo, il blocco scatta solo se esistono
    figli attivi.

    Argomenti attesi (TG_ARGV)
    --------------------------
    [0] child_schema       - schema della tabella figlia
    [1] child_table        - nome tabella figlia
    [2] fk_col             - colonna FK sul figlio
    [3] ref_col            - colonna del padre referenziata dalla FK
                             (puo' essere UNIQUE diversa da PK).
                             Se omesso, fallback 'id' (DEPRECATO).
    [4] parent_attivo_col  - nome colonna attivo del padre
                             (default 'attivo' se omesso, DEPRECATO).
                             Necessario per supportare override
                             via dbops.automation_overrides_cols.
  */

  IF array_length(TG_ARGV, 1) < 3 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_BLOCK_ARGS',
      jsonb_build_object(
        'trigger', TG_NAME,
        'table',   TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'tg_argv', TG_ARGV
      ),
      NULL::uuid,
      'Attesi: child_schema, child_table, fk_col [, ref_col, parent_attivo_col]'
    );
  END IF;

  v_child_schema := TG_ARGV[0];
  v_child_table  := TG_ARGV[1];
  v_fk_col       := TG_ARGV[2];

  IF array_length(TG_ARGV, 1) >= 4 AND TG_ARGV[3] IS NOT NULL THEN
    v_ref_col := TG_ARGV[3];
  ELSE
    v_ref_col := 'id';
    PERFORM script.fn_log_error_only(
      'database',
      'trgfn_prevent_deactivate_if_children',
      'E_ATTIVO_BLOCK',
      jsonb_build_object(
        'parent_table', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'ref_col',      v_ref_col,
        'note',         'Usata colonna di default id'
      ),
      NULL::uuid,
      'Passa ref_col come 4° parametro per evitare ambiguita'''
    );
  END IF;

  -- 5° arg: nome colonna attivo del padre (rispetta override)
  v_parent_attivo_col := COALESCE(TG_ARGV[4], 'attivo');

  IF TG_ARGV[4] IS NULL THEN
    PERFORM script.fn_log_error_only(
      'database',
      'trgfn_prevent_deactivate_if_children',
      'E_ATTIVO_BLOCK',
      jsonb_build_object(
        'parent_table',      TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'parent_attivo_col', v_parent_attivo_col,
        'note',              'Usata colonna attivo di default'
      ),
      NULL::uuid,
      'Passa parent_attivo_col come 5° parametro per supportare override'
    );
  END IF;

  -- Estrai dinamicamente OLD/NEW.parent_attivo_col via to_jsonb
  -- (no EXECUTE per riga, supporta override del nome colonna)
  v_old_attivo := (to_jsonb(OLD)->>v_parent_attivo_col)::boolean;
  v_new_attivo := (to_jsonb(NEW)->>v_parent_attivo_col)::boolean;

  -- Controlliamo solo transizione TRUE -> FALSE
  IF TG_OP = 'UPDATE'
    AND COALESCE(v_old_attivo, FALSE) IS TRUE
    AND COALESCE(v_new_attivo, FALSE) IS FALSE
  THEN
    -- Estrai valore della colonna referenziata dal record OLD via to_jsonb
    v_parent_ref_val_text := to_jsonb(OLD)->>v_ref_col;

    IF v_parent_ref_val_text IS NULL THEN
      -- rev 2026-08-05: TRE difetti in questa sola chiamata.
      --   1) mancavano i valori variadici -> `fn_log_error_only` non si
      --      risolveva e SOLLEVAVA, in una funzione il cui contratto e'
      --      «logga senza sollevare»: una disattivazione legittima
      --      falliva. E' il piu' grave dei 16 perche' non sporca un
      --      messaggio, cambia il comportamento — ed e' armato su 96
      --      tabelle.
      --   2) il codice era `E_ATTIVO_BLOCK`, il cui messaggio e'
      --      «Errore generazione regola ATTIVO_block. Sqlerrm: %s»: parla
      --      della GENERAZIONE della regola da parte del framework di
      --      automazione, non di questo salto a runtime. Ora
      --      `E_ATTIVO_BLOCK_REF_NULL` (id 840), coerente con la famiglia
      --      `E_ATTIVO_BLOCK_*` che ha messaggio `%s` pass-through.
      --   3) quel messaggio ha un segnaposto: un array vuoto avrebbe
      --      stampato «%s» alla lettera. Si passa la nota vera.
      PERFORM script.fn_log_error_only(
        'database',
        'trgfn_prevent_deactivate_if_children',
        'E_ATTIVO_BLOCK_REF_NULL',
        jsonb_build_object(
          'parent_table', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
          'ref_col',      v_ref_col,
          'note',         'Colonna referenziata NULL: controllo figli saltato'
        ),
        NULL::uuid,
        format('%s.%s: colonna referenziata %s NULL, controllo figli saltato',
               TG_TABLE_SCHEMA, TG_TABLE_NAME, v_ref_col)
      );
      RETURN NEW;
    END IF;

    -- Ricava tipo della FK del figlio (per cast corretto)
    SELECT a.atttypid::regtype::text
      INTO v_fk_type
      FROM pg_attribute a
      JOIN pg_class c     ON c.oid = a.attrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = v_child_schema
      AND c.relname = v_child_table
      AND a.attname = v_fk_col
      AND a.attnum > 0
      AND NOT a.attisdropped;

    IF v_fk_type IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_ATTIVO_BLOCK_FKCOL_NOT_FOUND',
        jsonb_build_object(
          'parent_table', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
          'child_table',  v_child_schema||'.'||v_child_table,
          'fk_col',       v_fk_col,
          'ref_col',      v_ref_col
        ),
        NULL::uuid,
        'Colonna FK del figlio non trovata in catalogo',
        v_child_schema, v_child_table, v_fk_col
      );
    END IF;

    -- Se il figlio ha una colonna attivo, blocca solo se esistono figli attivi
    v_child_attivo_col := dbops.fn_get_override_col(v_child_schema, v_child_table, 'ATTIVO_COL', 'attivo');
    v_child_has_attivo := dbops.fn_col_exists(v_child_schema, v_child_table, v_child_attivo_col);

    IF v_child_has_attivo THEN
      v_sql := format(
        'SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = ($1)::%s AND %I IS DISTINCT FROM FALSE)',
        v_child_schema, v_child_table, v_fk_col, v_fk_type, v_child_attivo_col
      );
    ELSE
      v_sql := format(
        'SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = ($1)::%s)',
        v_child_schema, v_child_table, v_fk_col, v_fk_type
      );
    END IF;

    EXECUTE v_sql INTO v_exists USING v_parent_ref_val_text;

    IF v_exists THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        -- ⭐ 2026-08-20 (secondo giro): DUE CODICI, NON DUE SFUMATURE.
        --    Il blocco ha due rami, e non sono due modi di dire la
        --    stessa cosa: sono due situazioni con DUE RIMEDI DIVERSI.
        --      · figlia CON colonna attivo -> bloccano solo le righe
        --        ATTIVE, e il rimedio e' DISATTIVARLE (il pattern
        --        «figli prima, padre poi»);
        --      · figlia SENZA colonna attivo -> blocca QUALUNQUE riga,
        --        e il rimedio e' TOGLIERLE: spegnerle non si puo',
        --        quello stato li' non esiste.
        --    Misurato il 2026-08-20 con le stesse funzioni che usa
        --    questo trigger (fn_get_override_col + fn_col_exists):
        --    168 trigger su 349 nel primo ramo (77 tabelle figlie),
        --    181 nel secondo (88). ⚠️ NON e' un caso di nicchia contro
        --    uno normale: e' meta' e meta'.
        --    Fino a stamattina il messaggio era UNO e diceva «attive»:
        --    falso per 181 trigger su 349, che mandavano l'operatore a
        --    cercare una colonna inesistente. Toglierla (20260820-01)
        --    ha reso la frase vera per tutti e imprecisa per 168. Una
        --    frase sola non puo' dire due cose: da qui i due codici.
        --    ⛔ Qui si sceglie il CODICE, non si compone una frase: il
        --    testo resta a catalogo. Comporlo qui e' esattamente il
        --    difetto da cui questa funzione e' uscita stamattina.
        CASE WHEN v_child_has_attivo
             THEN 'E_ATTIVO_BLOCK_CHILDREN_ACTIVE'
             ELSE 'E_ATTIVO_BLOCK_CHILDREN_EXIST'
        END,
        jsonb_build_object(
          'parent_table',     TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
          'child_table',      v_child_schema||'.'||v_child_table,
          'ref_col',          v_ref_col,
          'ref_val',          v_parent_ref_val_text,
          'fk_col',           v_fk_col,
          'fk_type',          v_fk_type,
          'child_attivo_col', v_child_attivo_col,
          'child_has_attivo', v_child_has_attivo
        ),
        NULL::uuid,
        -- ⭐ 2026-08-20: LA FRASE NON VIAGGIA PIU' QUI.
        --    Fino a ieri il primo valore era «Non e' possibile
        --    disattivare il padre: esistono righe figlio attive
        --    collegate» e il messaggio a catalogo era un `%s` NUDO:
        --    gli altri cinque valori — padre, figlia, colonna
        --    referenziata, suo valore, colonna FK — arrivavano fin qui
        --    e venivano BUTTATI VIA, perche' un solo segnaposto ne
        --    consuma uno solo. Un centinaio di trigger di questa
        --    famiglia dicevano tutti la stessa frase cieca, senza mai
        --    nominare la tabella che stava bloccando.
        --
        -- ⚠️ E la frase era anche IMPRECISA: diceva «attive» anche
        --    quando la figlia NON ha una colonna attivo — e in quel
        --    caso blocca qualunque riga, non le attive. Il caso non e'
        --    teorico: anagrafiche.emittenti_fiscali_billing_account e'
        --    cosi', e mandava a cercare una colonna che non esiste.
        --    ⭐ La distinzione vive ora nei DUE CODICI qui sopra. Al
        --    mattino era finita nella `causa` del catalogo, ed era un
        --    ripiego che non bastava: la `causa` si legge dopo, mentre
        --    quello che cambia fra i due rami e' il RIMEDIO — cioe' la
        --    prima cosa che serve a chi ha appena letto il rifiuto.
        --
        --    Il testo sta a catalogo (id 125 per il ramo «qualunque
        --    riga», id 934 per «attive») e qui viaggiano solo i DATI,
        --    nell'ORDINE che il messaggio consuma: padre, colonna
        --    referenziata, suo valore, figlia.
        --    ⛔ I due messaggi hanno UNA SOLA lista di valori, quindi
        --    devono avere gli STESSI segnaposti nello STESSO ordine.
        --    Presidio: test 13 di
        --    db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql. ⚠️ Cambiare quest'ordine senza cambiare
        --    il CSV scambia due nomi di tabella in una frase che
        --    resta grammaticalmente perfetta: i due vanno letti
        --    insieme.
        --    Il quinto (fk_col) e' passato IN PIU' di proposito, cosi'
        --    arricchire il messaggio non costa un changeSet di codice:
        --    format() ignora i valori che avanzano, ma non perdona
        --    quelli che mancano (W_MESSAGGIO_ARITA).
        TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        v_ref_col,
        v_parent_ref_val_text,
        v_child_schema||'.'||v_child_table,
        v_fk_col
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_prevent_deactivate_if_children()
IS 'Trigger function (ATTIVO/BLOCK): impedisce la disattivazione del padre se esistono figli collegati. TG_ARGV: child_schema, child_table, fk_col [, ref_col, parent_attivo_col]. Il 4° arg e'' la colonna del padre referenziata dalla FK (puo'' essere UNIQUE non-PK). Il 5° arg e'' la colonna attivo del padre (rispetta override via dbops.automation_overrides_cols). ⭐ rev 2026-08-20 — DUE REVISIONI NELLO STESSO GIORNO, entrambe SOLO sul messaggio: il blocco, le condizioni e il momento sono identici da mesi. (1) la FRASE e'' uscita dagli argomenti e sta a catalogo, cosi'' i valori identificativi che questa funzione passa — padre, colonna referenziata, suo valore, figlia, colonna FK — smettono di essere scartati da un `%s` nudo e la tabella che blocca viene finalmente NOMINATA. (2) il codice non e'' piu'' uno solo: si sceglie fra E_ATTIVO_BLOCK_CHILDREN_ACTIVE (id 934) e E_ATTIVO_BLOCK_CHILDREN_EXIST (id 125) leggendo v_child_has_attivo. ⚠️ Perche'' i due rami hanno RIMEDI DIVERSI: se la figlia ha la colonna attivo bloccano solo le righe attive e si DISATTIVANO (figli prima, padre poi); se non ce l''ha blocca qualunque riga e si TOLGONO, perche'' spegnerle non si puo''. Misurato il 2026-08-20: 168 trigger su 349 nel primo ramo, 181 nel secondo — meta'' e meta''. Il messaggio unico diceva «attive» ed era falso per 181, poi (per un mattino) non lo diceva piu'' ed era impreciso per 168. ⛔ I due messaggi condividono UNA sola lista di valori: devono avere gli stessi segnaposti nello stesso ordine, e cambiare l''ordine qui senza cambiare il CSV scambierebbe due nomi di tabella in una frase che resta grammaticalmente perfetta. Presidio: test 13 di db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql.';
```

</div>

---
{% include-markdown "signature-core.md" %}
