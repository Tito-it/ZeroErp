# Colonne visualizzate in liste — architettura

**Modulo:** UI / Presentazione
**Stato:** Blocchi A (DDL) e B (codice DB) completati — 2026-05-06. Prossimo: commit `dev/db-tid` → PR → Blocco C (backend Django).
**Coerenza:** Sviluppo Concentrico — strato di presentazione che si appoggia ai domini funzionali senza modificarli

---

## 1. Il problema

In un ERP come ZeroERP ogni operatore ha un punto di vista diverso sui dati.
La stessa anagrafica clienti, vista da un amministrativo, da un tecnico o da un commerciale, ha bisogno di mettere in evidenza informazioni completamente diverse:

- l'**amministrativo** vuole vedere partita IVA, codice fiscale, condizioni di pagamento, esposizione finanziaria, ultima fattura emessa
- il **tecnico** vuole vedere indirizzi degli impianti, ultimo intervento, prossima scadenza manutenzione, contatto referente operativo
- il **commerciale** vuole vedere fatturato dell'anno, ultimo contatto, listino applicato, opportunità aperte

Una lista che mostra *tutto* a tutti diventa illeggibile, costringe l'utente a scorrere orizzontalmente e nasconde le informazioni rilevanti dietro a quelle che non servono.
Allo stesso tempo, costruire una lista diversa per ogni ruolo è una via senza fine: ogni nuova esigenza diventa un intervento sul codice.

Serve quindi un meccanismo che permetta di **catalogare** le informazioni disponibili una volta sola, e poi **comporle** in viste diverse a seconda dell'utente, mantenendo controllo centrale su cosa è permesso vedere.

---

## 2. I tre livelli da tenere distinti

Il primo errore architetturale, in problemi di questo tipo, è fondere insieme tre cose che vanno tenute separate.
Le chiamiamo **catalogo**, **autorizzazione** e **preferenza**.

### 2.1 Il catalogo — cosa esiste

Il catalogo è l'insieme **completo** delle colonne potenzialmente disponibili per una lista.
È definito dallo sviluppatore al momento della progettazione del modulo, e descrive *tutte* le informazioni che la lista è tecnicamente in grado di mostrare.

Ogni colonna ha un **tipo** (`tipo_colonna`) che ne definisce il comportamento strutturale:

- `'identificatore'` — identifica la riga (es. ragione_sociale, numero_documento): sempre visibile, non nascondibile, fissata di default
- `'informazione'` — colonna standard: personalizzabile liberamente dall'utente
- `'azione'` — pulsanti e icone UI: non esportabile per definizione, non personalizzabile in visibilità

Le colonne marcate `sensibile = TRUE` (es. esposizione finanziaria, IBAN) usano un modello di accesso **allowlist**: di default sono bloccate a tutti, si devono scrivere esplicitamente i grant. Le colonne non sensibili usano il modello **deny-list** (di default visibili, si scrivono solo le restrizioni).

Il catalogo può raggruppare le colonne in sezioni logiche (campo `gruppo`) per rendere gestibile la modale di personalizzazione quando le colonne sono molte.

L'utente finale non interagisce mai direttamente con il catalogo: non può aggiungere colonne arbitrarie, non può scrivere SQL. Può solo scegliere fra ciò che il catalogo mette a disposizione. Questa è la prima garanzia di sicurezza e di stabilità.

### 2.2 Le autorizzazioni — cosa è permesso vedere

Sopra al catalogo si appoggia il sistema dei permessi.
Una colonna del catalogo può essere *bloccata* per un certo ruolo: ad esempio la colonna "esposizione finanziaria" potrebbe essere visibile solo agli operatori amministrativi e bloccata per i tecnici.

Le autorizzazioni vivono **separate** dal catalogo perché sono una dimensione organizzativa, non tecnica.
Il catalogo dice "questa colonna esiste". I permessi dicono "tu puoi vederla / tu no".

Il filtro autorizzativo viene applicato **dopo** la scelta dell'utente: anche se l'utente ha salvato una preferenza che include una colonna riservata, al momento del rendering quella colonna viene rimossa silenziosamente. L'autorizzazione vince sempre.

Per le colonne `sensibile = TRUE` il modello si inverte: l'assenza di una riga di permesso significa accesso **negato** (non pieno). Si devono scrivere esplicitamente i grant per i ruoli autorizzati.

### 2.3 Le preferenze — cosa l'utente vuole vedere

Solo dopo aver definito catalogo e permessi entra in gioco la preferenza personale dell'utente.
Tra le colonne che il catalogo offre e che il suo ruolo gli permette di vedere, l'utente può scegliere quali mostrare, in che ordine, con che larghezza, con quali filtri preimpostati.

Le preferenze esistono a quattro livelli, in ordine di specificità crescente:

1. **Preset di sistema** — la configurazione di default, la stessa per tutti. È quella che vede un nuovo utente che non ha ancora personalizzato nulla.
2. **Preset di emittente fiscale** — configurazione predefinita per una specifica società/emittente. Sovrascrive il default di sistema per tutti gli utenti di quell'emittente.
3. **Preset di ruolo** — configurazione predefinita per uno specifico ruolo applicativo. Quando un utente con quel ruolo apre la lista, parte da qui anziché dal default di emittente o sistema.
4. **Preferenza personale** — la personalizzazione che l'utente fa per sé, salvata sul suo profilo. Ha la priorità massima.

Questa scala permette all'amministratore del cliente di predisporre configurazioni mirate senza imporle: l'utente resta libero di personalizzare ulteriormente, ma parte da una base sensata.

---

## 3. Come si compongono i quattro livelli

Quando l'utente apre una lista, il sistema risolve quale configurazione applicare. La logica è una cascata dal più specifico al più generico:

1. **Esiste una preferenza personale dell'utente per questa lista?**
   Se sì, parto da quella.
2. **Altrimenti, esiste un preset associato al ruolo attivo dell'utente?**
   Se sì, uso quello.
3. **Altrimenti, esiste un preset associato all'emittente fiscale corrente?**
   Se sì, uso quello.
4. **Altrimenti, esiste un preset di sistema (default)?**
   Se sì, uso quello.
5. **Altrimenti, uso il catalogo grezzo.**
   Tutte le colonne attive della lista, ordinate per `ordine_default`, con `larghezza_default`. Questo garantisce che una lista funzioni sempre, anche se lo sviluppatore ha definito solo il catalogo senza creare alcun preset.

A questa configurazione viene poi applicato il **filtro autorizzativo**: le colonne bloccate per il ruolo dell'utente vengono eliminate, le colonne LETTURA vengono marcate come non esportabili.

Il risultato è la configurazione **effettiva**, quella che il frontend riceve e usa per costruire la tabella.

### 3.1 Merge automatico delle nuove colonne

Se l'utente ha una preferenza personale salvata e lo sviluppatore aggiunge successivamente una nuova colonna al catalogo, quella colonna non comparirà mai nella vista dell'utente finché non resetta la preferenza — a meno che il sistema non la gestisca esplicitamente.

Comportamento corretto: quando `fn_resolve_lista_config` risolve una preferenza utente e trova nel catalogo colonne non presenti nel JSONB salvato, le **include automaticamente** con `visibile: false`. La colonna appare nella modale di personalizzazione ma non nella vista di default. L'utente può attivarla quando vuole, ed è informato della disponibilità tramite un badge "N nuove colonne disponibili" sul pannello di personalizzazione.

Lo stesso vale per colonne disattivate (`attivo = FALSE`): vengono ignorate silenziosamente senza rompere la preferenza salvata.

### 3.2 Colonne obbligatorie nella personalizzazione

Le colonne con `tipo_colonna = 'identificatore'` o `tipo_colonna = 'azione'` non possono essere nascoste dall'utente:

- nella modale di personalizzazione Vue il loro toggle è disabilitato, con tooltip esplicativo
- all'endpoint di salvataggio preferenza, eventuali `visibile: false` su queste colonne vengono ignorati silenziosamente
- in `fn_resolve_lista_config`, se una preferenza storica contiene una colonna obbligatoria marcata non visibile, viene normalizzata a visibile prima di essere restituita

---

## 4. Le tabelle

Tutte le tabelle vivono nello schema dedicato `ui` (presentazione), separato dai domini funzionali.

### 4.1 `ui.lista_definizione`

Catalogo delle liste esistenti nel sistema. Una riga per ogni lista configurabile.

```sql
CREATE TABLE ui.lista_definizione (
  id              SERIAL PRIMARY KEY,
  codice          VARCHAR(80) NOT NULL UNIQUE,
    -- convenzione: '<schema>.<entita>' (es. 'anagrafiche.clienti')
    -- per varianti di contesto: '<schema>.<entita>:<contesto>' (es. 'anagrafiche.clienti:picker')
  descrizione     VARCHAR(200) NOT NULL,
  schema_dati     VARCHAR(40) NOT NULL,           -- es. 'anagrafiche'
  vista_sql       VARCHAR(120),
    -- nome della view PostgreSQL sorgente dati
    -- validato all'INSERT/UPDATE tramite trigger su pg_catalog.pg_class
  note            TEXT,
  attivo          BOOLEAN NOT NULL DEFAULT TRUE,

  -- audit standard ZeroERP
  data_insert     TIMESTAMP NOT NULL DEFAULT now(),
  user_insert     VARCHAR(80) NOT NULL,
  data_update     TIMESTAMP,
  user_update     VARCHAR(80)
);
```

Il `codice` è l'identificatore stabile usato dal frontend (`<ListaConfigurabile codice="anagrafiche.clienti" />`).

Il suffisso `:contesto` è opzionale e serve per varianti della stessa entità in contesti diversi: la lista principale clienti, il picker clienti in una form fattura, e il widget dashboard clienti sono tre `lista_definizione` distinte con catalogo e preset separati.

La `vista_sql` va validata in fase di INSERT/UPDATE contro `pg_catalog.pg_class` per rilevare riferimenti stale prima che raggiungano l'utente.

### 4.2 `ui.lista_colonna`

Catalogo delle colonne disponibili per ciascuna lista.

```sql
CREATE TABLE ui.lista_colonna (
  id                SERIAL PRIMARY KEY,
  lista_id          INTEGER NOT NULL REFERENCES ui.lista_definizione(id),
  codice            VARCHAR(80) NOT NULL,           -- es. 'partita_iva'
  etichetta         VARCHAR(120) NOT NULL,          -- es. 'P.IVA'
  etichetta_estesa  VARCHAR(200),                   -- tooltip o intestazione export

  campo_sorgente    VARCHAR(120),
    -- nome colonna nella view PostgreSQL; NULL per colonne di tipo 'azione'
    -- validato all'INSERT/UPDATE contro pg_catalog.pg_attribute

  tipo_colonna      VARCHAR(20) NOT NULL DEFAULT 'informazione',
    -- 'identificatore': sempre visibile, non nascondibile, fissata di default
    -- 'informazione':   personalizzabile liberamente
    -- 'azione':         pulsanti/icone UI, non esportabile, non nascondibile
    CONSTRAINT chk_lista_colonna_tipo_colonna
      CHECK (tipo_colonna IN ('identificatore', 'informazione', 'azione')),

  tipo_dato         VARCHAR(20) NOT NULL,
    -- 'string' | 'numeric' | 'date' | 'datetime' | 'boolean' | 'enum'
    CONSTRAINT chk_lista_colonna_tipo_dato
      CHECK (tipo_dato IN ('string', 'numeric', 'date', 'datetime', 'boolean', 'enum')),

  formato           VARCHAR(40),
    -- es. 'currency_eur', 'date_short', 'percent_2', 'yesno'
    -- valore libero; il frontend deve gestire valori non riconosciuti con fallback

  larghezza_default INTEGER,                        -- in pixel, suggerimento
  ordine_default    INTEGER NOT NULL,               -- ordine nel catalogo (usato come fallback)
  allineamento      VARCHAR(10) DEFAULT 'left'
    CONSTRAINT chk_lista_colonna_allineamento
      CHECK (allineamento IN ('left', 'right', 'center')),

  -- raggruppamento per la modale di personalizzazione
  gruppo            VARCHAR(60),       -- es. 'Dati anagrafici', 'Dati fiscali'
  gruppo_ordine     INTEGER,           -- ordine del gruppo nella modale

  -- flag comportamentali
  filtrabile        BOOLEAN NOT NULL DEFAULT TRUE,
    -- la colonna può essere usata come criterio di filtro
  ordinabile        BOOLEAN NOT NULL DEFAULT TRUE,
  esportabile       BOOLEAN NOT NULL DEFAULT TRUE,
    -- FALSE per colonne 'azione'; impostato implicitamente dal tipo_colonna
  ricercabile_full  BOOLEAN NOT NULL DEFAULT FALSE, -- inclusa nella ricerca testuale globale

  sensibile         BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE: usa modello allowlist (default BLOCCATO per tutti i ruoli)
    -- FALSE: usa modello deny-list (default TUTTO se non ci sono restrizioni esplicite)

  attivo            BOOLEAN NOT NULL DEFAULT TRUE,

  data_insert       TIMESTAMP NOT NULL DEFAULT now(),
  user_insert       VARCHAR(80) NOT NULL,
  data_update       TIMESTAMP,
  user_update       VARCHAR(80),

  UNIQUE (lista_id, codice),

  CONSTRAINT chk_lista_colonna_azione_non_esportabile
    CHECK (tipo_colonna <> 'azione' OR esportabile = FALSE)
);
```

Note importanti:

- `campo_sorgente` è il nome della colonna nella view PostgreSQL. **Non è SQL arbitrario**: è un riferimento controllato. Va validato tramite trigger contro `pg_catalog.pg_attribute` per rilevare typo prima della messa in produzione.
- `tipo_colonna = 'azione'` implica `esportabile = FALSE`: il CHECK in tabella lo garantisce.
- `tipo_colonna = 'identificatore'` e `tipo_colonna = 'azione'` implicano colonna non nascondibile: questo è garantito dalla logica in `fn_resolve_lista_config` e dalla UI, non con un CHECK in tabella (la visibilità dipende dal contesto di risoluzione, non dal dato grezzo).
- `sensibile = TRUE` inverte il modello permessi: lo sviluppatore deve esplicitamente grants i ruoli autorizzati in `lista_colonna_permesso`.
- `gruppo` / `gruppo_ordine` organizzano la modale di personalizzazione in sezioni collassabili quando le colonne sono molte.

### 4.3 `ui.lista_preset`

Configurazioni predefinite — di sistema, di emittente fiscale o di ruolo.

```sql
CREATE TABLE ui.lista_preset (
  id                       SERIAL PRIMARY KEY,
  lista_id                 INTEGER NOT NULL REFERENCES ui.lista_definizione(id),
  codice                   VARCHAR(80) NOT NULL,
  descrizione              VARCHAR(200) NOT NULL,

  ambito                   VARCHAR(20) NOT NULL,
    -- 'sistema'           -> default globale
    -- 'emittente_fiscale' -> default per una specifica società/emittente
    -- 'ruolo'             -> default per un ruolo applicativo
    CONSTRAINT chk_lista_preset_ambito
      CHECK (ambito IN ('sistema', 'emittente_fiscale', 'ruolo')),

  profilo_accesso_id       INTEGER REFERENCES config.profili_accesso(id),
    -- usato quando ambito = 'ruolo': il profilo di accesso (config.profili_accesso)
    -- di cui l'utente deve essere titolare perché questo preset sia applicabile.
    -- La risoluzione usa fn_get_profili_accesso_applicabili(auth_user_id),
    -- la stessa chain usata dal PermissionResolver Django — nessuna logica duplicata.
  emittente_fiscale_id     INTEGER REFERENCES anagrafiche.emittenti_fiscali(id),
    -- usato quando ambito = 'emittente_fiscale'; l'associazione operatore↔EF
    -- è in config.user_emittenti_fiscali (whitelist opzionale).

  is_default               BOOLEAN NOT NULL DEFAULT FALSE,

  -- configurazione di default del preset
  pagina_dimensione        INTEGER DEFAULT 25,
  ordinamento_default      JSONB,
    -- es. [{"col": "ragione_sociale", "dir": "asc"}]
  filtri_default           JSONB,
    -- filtri preimpostati; il formato JSONB deve corrispondere alla struttura
    -- usata dal componente Vue per i filtri della lista

  attivo                   BOOLEAN NOT NULL DEFAULT TRUE,

  data_insert              TIMESTAMP NOT NULL DEFAULT now(),
  user_insert              VARCHAR(80) NOT NULL,
  data_update              TIMESTAMP,
  user_update              VARCHAR(80),

  UNIQUE (lista_id, codice),

  -- coerenza ambito/riferimenti
  CONSTRAINT chk_lista_preset_ambito_refs
  CHECK (
    (ambito = 'sistema'              AND profilo_accesso_id IS NULL     AND emittente_fiscale_id IS NULL)
    OR (ambito = 'ruolo'             AND profilo_accesso_id IS NOT NULL AND emittente_fiscale_id IS NULL)
    OR (ambito = 'emittente_fiscale' AND emittente_fiscale_id IS NOT NULL AND profilo_accesso_id IS NULL)
  )
);

-- un solo preset di default per ciascuna combinazione lista + ambito + profilo + emittente
CREATE UNIQUE INDEX ui_lista_preset_default_uq
  ON ui.lista_preset (lista_id, ambito, COALESCE(profilo_accesso_id, 0), COALESCE(emittente_fiscale_id, 0))
  WHERE is_default = TRUE;
```

### 4.4 `ui.lista_preset_colonna`

Composizione del preset: quali colonne, in che ordine, con che larghezza.

```sql
CREATE TABLE ui.lista_preset_colonna (
  preset_id    INTEGER NOT NULL REFERENCES ui.lista_preset(id) ON DELETE CASCADE,
  colonna_id   INTEGER NOT NULL REFERENCES ui.lista_colonna(id),
  ordine       INTEGER NOT NULL,
  larghezza    INTEGER,                  -- in pixel; NULL = usa default colonna
  visibile     BOOLEAN NOT NULL DEFAULT TRUE,
    -- FALSE significa: la colonna è nel pool disponibile all'utente
    -- (appare nella modale di personalizzazione) ma non è mostrata di default.
    -- Permette preset che dichiarano il catalogo completo ma mostrano solo
    -- le colonne più rilevanti, lasciando le altre attivabili dall'utente.
  fissata      BOOLEAN NOT NULL DEFAULT FALSE,  -- frozen column (non scrolla)
  PRIMARY KEY (preset_id, colonna_id)
);
```

Il flag `visibile = FALSE` a livello di preset ha un significato preciso: la colonna è **disponibile** ma non **attiva di default**. Questo distingue il "pool del preset" dalla "vista del preset". Un preset può dichiarare 30 colonne disponibili e mostrarne 8 di default: l'utente può attivarne altre dalla modale senza dover cercare cosa esiste.

### 4.5 `ui.lista_preferenza_utente`

Personalizzazione dell'utente finale.

```sql
CREATE TABLE ui.lista_preferenza_utente (
  id                        SERIAL PRIMARY KEY,
  auth_user_id              INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
  lista_id                  INTEGER NOT NULL REFERENCES ui.lista_definizione(id),
  preset_base_id            INTEGER REFERENCES ui.lista_preset(id),
    -- preset da cui è partita la personalizzazione

  preset_base_data_update   TIMESTAMP,
    -- timestamp di data_update del preset al momento del salvataggio.
    -- Permette di rilevare se il preset di base è stato modificato dopo
    -- che l'utente ha salvato la sua preferenza ("preset aggiornato, vuoi vedere le novità?")

  configurazione            JSONB NOT NULL,
    -- struttura:
    -- {
    --   "colonne": [
    --     {"codice": "ragione_sociale", "ordine": 1, "larghezza": 240, "visibile": true, "fissata": true},
    --     {"codice": "partita_iva",     "ordine": 2, "larghezza": 130, "visibile": true},
    --     {"codice": "citta",           "ordine": 3, "larghezza": 160, "visibile": false}
    --   ],
    --   "ordinamento":    [{"col": "ragione_sociale", "dir": "asc"}],
    --   "filtri":         {"attivo": true},
    --   "pagina_dimensione": 50
    -- }
    -- Il riferimento per codice (non per colonna_id) protegge da cambi di ID
    -- e permette di ignorare silenziosamente colonne disattivate.

  data_insert               TIMESTAMP NOT NULL DEFAULT now(),
  data_update               TIMESTAMP,

  UNIQUE (auth_user_id, lista_id)
);
```

La scelta di JSONB per la configurazione utente è deliberata: la preferenza si legge sempre intera, non servono query relazionali su di essa. Il JSONB rende la struttura resiliente all'aggiunta di nuove proprietà future (raggruppamenti, vista compatta, ecc.) senza cambiare la tabella.

`preset_base_data_update` registra lo snapshot del preset al momento del salvataggio. Se il preset viene aggiornato in seguito, il confronto con `lista_preset.data_update` permette all'applicazione di segnalare: *"la configurazione di base del tuo ruolo è stata aggiornata — vuoi vedere le novità?"*.

### 4.6 `ui.lista_colonna_permesso`

Filtro autorizzativo. Si appoggia al sistema di ruoli applicativi esistente.

```sql
CREATE TABLE ui.lista_colonna_permesso (
  id                   SERIAL PRIMARY KEY,
  colonna_id           INTEGER NOT NULL REFERENCES ui.lista_colonna(id) ON DELETE CASCADE,
  profilo_accesso_id   INTEGER NOT NULL REFERENCES config.profili_accesso(id),
    -- Il profilo di accesso a cui si applica questa restrizione/concessione.
    -- Usa config.profili_accesso — la stessa entità del sistema permessi principale.
    -- La risoluzione (quale profilo è applicabile all'utente) usa
    -- fn_get_profili_accesso_applicabili(auth_user_id), identica al PermissionResolver.
    -- UO e identità digitale specifiche si raggiungono via profili_accesso_bindings:
    -- non serve duplicare quella logica qui.

  livello_accesso      VARCHAR(20) NOT NULL,
    -- 'TUTTO'    -> visibile e esportabile
    -- 'LETTURA'  -> visibile a video ma non esportabile
    -- 'BLOCCATO' -> nascosta completamente

  data_insert          TIMESTAMP NOT NULL DEFAULT now(),
  user_insert          VARCHAR(80) NOT NULL,
  data_update          TIMESTAMP,
  user_update          VARCHAR(80),

  UNIQUE (colonna_id, profilo_accesso_id)
);
```

**Modello deny-list (colonne non sensibili):**
L'assenza di una riga di permesso significa accesso pieno (`TUTTO`). Si scrivono solo le restrizioni. Questo evita di dover popolare la tabella per ogni combinazione profilo × colonna.

**Modello allowlist (colonne `sensibile = TRUE`):**
L'assenza di una riga di permesso significa accesso negato (`BLOCCATO`). Lo sviluppatore deve scrivere esplicitamente le righe con `livello_accesso = 'TUTTO'` o `'LETTURA'` per i profili autorizzati. Questo protegge da dimenticanze: aggiungere una colonna sensibile al catalogo non la espone a nessuno finché non viene esplicitamente concessa.

Il livello `LETTURA` è utile per dati che si vogliono mostrare a video ma non consentire l'estrazione massiva — comune per dati personali o finanziariamente sensibili.

**Coerenza con il sistema permessi principale:**
`profilo_accesso_id` referenzia la stessa entità (`config.profili_accesso`) usata da `profili_accesso_aree` e `profili_accesso_azioni`. La risoluzione di quale profilo è applicabile all'utente avviene tramite `fn_get_profili_accesso_applicabili(auth_user_id)` — la stessa funzione usata dal `PermissionResolver` Django. Non ci sono due sistemi di risoluzione: c'è uno solo, riutilizzato.

---

## 5. La funzione di risoluzione

Il punto in cui i quattro livelli si fondono è una funzione PostgreSQL che restituisce la configurazione effettiva.

```sql
CREATE OR REPLACE FUNCTION ui.fn_resolve_lista_config(
  p_lista_codice           VARCHAR,
  p_auth_user_id           INTEGER,
  p_emittente_fiscale_id   INTEGER    -- emittente fiscale corrente della sessione
) RETURNS JSONB
LANGUAGE plpgsql STABLE
AS $$
DECLARE
  v_config       JSONB;
  v_profili_ids  INTEGER[];  -- profili_accesso applicabili all'utente
BEGIN
  -- risoluzione profili applicabili: stessa chain del PermissionResolver Django
  SELECT ARRAY(
    SELECT id FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id)
  ) INTO v_profili_ids;

  -- cascata configurazione:
  -- 1. cerca preferenza personale utente (lista_preferenza_utente)
  -- 2. se non c'è, cerca preset di ruolo con is_default=TRUE
  --    dove profilo_accesso_id = ANY(v_profili_ids)
  -- 3. se non c'è, cerca preset di emittente fiscale con is_default=TRUE
  --    dove emittente_fiscale_id = p_emittente_fiscale_id
  -- 4. se non c'è, cerca preset di sistema (is_default=TRUE, ambito='sistema')
  -- 5. se non c'è, costruisce configurazione dal catalogo grezzo
  --    (tutte le colonne attive ordinate per ordine_default con larghezze_default)

  -- merge automatico: aggiunge al JSONB le colonne del catalogo non presenti
  -- nella preferenza salvata, con visibile=false (nuove colonne post-salvataggio)

  -- normalizzazione colonne obbligatorie: imposta visibile=true per
  -- tipo_colonna IN ('identificatore', 'azione') anche se salvate a false

  -- filtro autorizzativo colonne non sensibili (deny-list):
  --   rimuove colonne con livello BLOCCATO in lista_colonna_permesso
  --   per ANY(v_profili_ids)
  -- filtro autorizzativo colonne sensibili (allow-list):
  --   rimuove colonne sensibili senza riga TUTTO/LETTURA in lista_colonna_permesso
  --   per ANY(v_profili_ids)

  -- marca colonne LETTURA come non esportabili nel JSONB risultante

  -- ritorna JSONB con struttura finale pronta per il frontend:
  -- {
  --   "colonne": [...],
  --   "ordinamento": [...],
  --   "filtri": {...},
  --   "pagina_dimensione": N,
  --   "colonne_nuove": N    -- quante colonne del catalogo non erano nella preferenza salvata
  -- }
  ...
END;
$$;
```

Il campo `colonne_nuove` nel risultato permette al frontend di mostrare il badge "N nuove colonne disponibili" senza fare chiamate aggiuntive.

Il contratto è chiaro: input = chi sei + quale emittente fiscale; output = configurazione completa già filtrata per i permessi, già normalizzata per le colonne obbligatorie, già arricchita delle colonne nuove.

La firma non riceve il `ruolo_applicativo_id` come parametro esplicito: la funzione lo risolve internamente tramite `fn_get_profili_accesso_applicabili(p_auth_user_id)`, esattamente come fa il `PermissionResolver` Django. Un unico meccanismo di risoluzione, nessuna duplicazione.

L'`emittente_fiscale_id` viene passato esplicitamente perché è una scelta di sessione dell'operatore (quale emittente sta lavorando in questo momento), non derivabile dai GUC in modo univoco quando l'operatore ha whitelist con più emittenti.

---

## 6. Esportazione CSV/Excel

L'export non è un meccanismo separato: è la stessa configurazione, applicata in modo diverso.

Quando l'utente esporta una lista:

1. il backend recupera la **stessa configurazione effettiva** della lista a video
2. esclude le colonne con `tipo_colonna = 'azione'` (non esportabili per definizione)
3. esclude le colonne con `esportabile = FALSE` nel catalogo
4. esclude le colonne con permesso `LETTURA` (visibili a video ma non esportabili)
5. esclude le colonne marcate `visibile: false` nella configurazione effettiva
6. genera il file con le sole colonne sopravvissute, nell'ordine della configurazione

In questo modo è impossibile aggirare i permessi attraverso l'export.

**Metadati filtri nel file esportato:**
Se la lista ha filtri attivi al momento dell'export, questi devono essere visibili nel file generato — altrimenti il CSV appare come una lista completa quando è in realtà un sottoinsieme. Soluzione: aggiungere un foglio `Filtri applicati` (in Excel) o righe di intestazione commentate (in CSV) che descrivono i criteri attivi. Chi riceve il file sa esattamente cosa contiene e può riprodurre o contestare il sottoinsieme.

---

## 7. Stato non salvato — indicatore UX

Il salvataggio della preferenza è esplicito e opzionale: l'utente può modificare colonne, ordinamento e filtri senza salvare, e le modifiche vivono solo nella sessione corrente. Al prossimo accesso ricomincia dal preset di ruolo (o di sistema/catalogo grezzo).

Questo comportamento va comunicato all'utente in modo chiaro. Il componente Vue `<ListaConfigurabile>` deve mostrare lo **stato della configurazione corrente** in modo visibile:

- `[Configurazione salvata]` — la vista corrente corrisponde alla preferenza salvata sul server
- `[Configurazione temporanea — non salvata]` — la vista è stata modificata ma non salvata; andrà persa alla chiusura

L'indicatore deve essere visibile nella toolbar della lista, vicino al controllo di personalizzazione colonne. Non deve essere intrusivo (niente modale), ma deve essere inequivocabile: l'utente che non salva deve sapere che sta lavorando su una vista temporanea.

Il frontend distingue questi due stati confrontando la configurazione corrente con quella ricevuta all'apertura dal server: se differiscono, la configurazione è non salvata.

---

## 8. Cosa lasciamo fuori (per ora)

- **Viste salvate multiple per utente**: l'utente ha una sola preferenza personale per lista. Più avanti si potrà estendere a "viste nominate" (es. "Clienti morosi", "Clienti TOP"), ma è un livello aggiuntivo.
- **Condivisione di viste fra utenti**: rinviato.
- **Calcoli su colonne** (totali, sub-totali, raggruppamenti dinamici): tema diverso, va trattato nel modulo reportistica, non nelle liste operative.
- **Layout responsive su mobile**: serve uno strato dedicato di adattamento; qui ci concentriamo sul desktop.
- **Colonne calcolate lato client**: colonne derivate (es. "giorni alla scadenza" = oggi - data_scadenza) non presenti nella view SQL. Il campo `campo_sorgente = NULL` su `lista_colonna` lascia la porta aperta, ma la logica di calcolo richiede un contratto frontend separato.

---

## 9. Riepilogo del flusso

Apertura della lista da parte dell'utente:

1. il frontend chiama `GET /api/ui/liste/<codice>/config`
2. il backend invoca `ui.fn_resolve_lista_config(codice, user_id, emittente_fiscale_id)`
3. la funzione risolve i profili applicabili via `fn_get_profili_accesso_applicabili`, poi applica la cascata: preferenza → preset ruolo → preset emittente → preset sistema → catalogo grezzo
4. la funzione applica il merge automatico delle nuove colonne (da catalogo, `visibile: false`)
5. la funzione normalizza le colonne obbligatorie (tipo_colonna identificatore/azione → visibile: true)
6. la funzione applica il filtro autorizzativo (deny-list per non sensibili, allow-list per sensibili)
7. ritorna la configurazione effettiva come JSONB, con il campo `colonne_nuove`
8. il frontend costruisce il DataTable PrimeVue con le colonne ricevute
9. il frontend mostra l'indicatore di stato: `[Configurazione salvata]` o `[Temporanea — non salvata]`
10. se `colonne_nuove > 0`, il frontend mostra il badge "N nuove colonne disponibili"
11. quando l'utente modifica colonne/ordinamento/filtri, lo stato passa a `[Temporanea — non salvata]`
12. il salvataggio avviene con `PUT /api/ui/liste/<codice>/preferenza`, che valida la struttura e registra `preset_base_data_update`
13. quando l'utente esporta, il backend riusa la stessa configurazione effettiva e aggiunge i metadati filtri

---

## 10. Note architetturali aperte

1. **Validare il catalogo** su un caso reale complesso (anagrafiche clienti, articoli, commesse) prima di generalizzare.
2. **Formato `filtri_default` JSONB** — il formato dei filtri nel preset DB deve essere concordato con il componente Vue filtri prima di seedare i preset. Definirlo nel Blocco C/D del piano di sviluppo (§11).
3. **Sviluppi rinviati** — export, viste nominate, admin UI, mobile: vedi [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md).

---

## 11. Piano di sviluppo

> **Convenzioni**: Liquibase → `docs/it/liquibase-setup-workflow.md`. SQL/trigger → `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`. Backend → `docs/it/dev/api.md`.
>
> **Entità già presenti, non da creare**: `django.auth_user`, `config.profili_accesso`, `config.profili_accesso_bindings`, `anagrafiche.emittenti_fiscali`, `config.user_emittenti_fiscali`, `script.fn_get_profili_accesso_applicabili`.

### Dipendenze tra blocchi

```text
Blocco A — DDL schema ui
│
├──► Blocco B — Codice DB  ──────────────────────────────────────────► Blocco E
│                                                                       Prima lista reale
└──► Blocco C — Backend base ──► Blocco D — Frontend base ─────────►┘
```

Blocchi B e C sono **indipendenti** tra loro: possono procedere in parallelo dopo A.
Blocco D può iniziare non appena il contratto degli endpoint C è definito (§ C1–C4), anche prima che siano testabili end-to-end.

---

### Blocco A — DDL schema `ui` ✅ COMPLETATO (2026-05-06)

Percorso: `db/changelog/migrations_v2/00_schema/ui/`.
`changelog-autogen.yaml` già aggiornato. Liquibase applicato.

| Step | File | Oggetto | Stato |
| ---- | ---- | ------- | ----- |
| A1 | `20260506-01-ddl-schema-ui-mctit.yaml` | `CREATE SCHEMA ui` + 4 ENUM: `ambito_preset`, `tipo_colonna`, `tipo_dato`, `allineamento_colonna` | ✅ |
| A2 | `20260506-02-ddl-ui-lista-definizione-mctit.yaml` | `CREATE TABLE ui.lista_definizione` | ✅ |
| A3 | `20260506-03-ddl-ui-lista-colonna-mctit.yaml` | `CREATE TABLE ui.lista_colonna` | ✅ |
| A4 | `20260506-04-ddl-ui-lista-preset-mctit.yaml` | `CREATE TABLE ui.lista_preset` + CHECK ambito + UNIQUE INDEX default | ✅ |
| A5 | `20260506-05-ddl-ui-lista-preset-colonna-mctit.yaml` | `CREATE TABLE ui.lista_preset_colonna` | ✅ |
| A6 | `20260506-06-ddl-ui-lista-preferenza-utente-mctit.yaml` | `CREATE TABLE ui.lista_preferenza_utente` | ✅ |
| A7 | `20260506-07-ddl-ui-lista-colonna-permesso-mctit.yaml` | `CREATE TABLE ui.lista_colonna_permesso` | ✅ |
| A8 | `90_end/20260506-08-fk-ui-preferenza-auth-user-mctit.yaml` | FK `auth_user_id → django.auth_user` ON DELETE CASCADE | ✅ |
| A9 | `80_data/changelog/20260506-09-upsert-dbops-fk-index-policy-ui-mctit.yaml` | Seed `dbops.fk_index_policy` per schema `ui` (8 FK) | ✅ |
| — | `80_data/sql/config/messaggi_errore.csv` | Messaggi errore ID 427–429 (`E_UI_LISTA_NON_TROVATA`, `E_UI_VISTA_SQL_NON_TROVATA`, `E_UI_CAMPO_SORGENTE_NON_TROVATO`) | ✅ |

---

### Blocco B — Codice DB ✅ COMPLETATO (2026-05-06)

Percorso: `db/changelog/migrations_v2/20_code/ui/`.

| Step | File | Oggetto | Stato |
| ---- | ---- | ------- | ----- |
| B1 | `20260506-10-code-trgfn-ui-lista-def-valida-vista-mctit.yaml` | `trgfn_ui_lista_definizione_a10_valida_vista_sql()` — guard `vista_sql` su `pg_catalog.pg_class` | ✅ |
| B2 | `20260506-11-code-trgfn-ui-lista-col-valida-campo-mctit.yaml` | `trgfn_ui_lista_colonna_a10_valida_campo_sorgente()` — guard `campo_sorgente` su `pg_catalog.pg_attribute`; skip se `tipo_colonna='azione'` | ✅ |
| B3 | `20260506-12-code-fn-ui-resolve-lista-config-mctit.yaml` | `ui.fn_resolve_lista_config(VARCHAR, INTEGER, INTEGER) RETURNS JSONB` — cascata preset + permessi + merge | ✅ |

**Test pgTAP** — `db/pgtap/ui/test-fn-resolve-lista-config.sql`:

| Scenario | Stato |
| -------- | ----- |
| Nessuna preferenza, nessun preset → catalogo grezzo ordinato per `ordine_default` | ✅ |
| Preset di sistema applicato | ✅ |
| Preset di profilo prevale su preset di sistema | ✅ |
| Preferenza utente prevale su tutto | ✅ |
| Colonna sensibile senza grant → assente dalla risposta | ✅ |
| Colonna sensibile con grant → presente con livello corretto | ✅ |
| Colonna `identificatore` con `visibile:false` → normalizzata a `true` | ✅ |
| Nuova colonna non in preferenza → aggiunta con `visibile:false`, `colonne_nuove++` | ✅ |
| Lista inesistente → errore `E_UI_LISTA_NON_TROVATA` | ✅ |

---

### Blocco C — Backend (dipende da A; parallelo con B)

Struttura da creare in `backend/apps/ui/`:

```text
apps/ui/
├── __init__.py
├── apps.py                        # AppConfig, name = 'apps.ui'
├── urls.py                        # router locale
├── db/
│   └── ui_repository.py           # query dirette verso schema ui
├── services/
│   └── ui_service.py              # orchestrazione; chiama fn_resolve_lista_config
└── api/
    └── lista_config_api.py        # views DRF + @extend_schema
```

Aggiungere `'apps.ui'` in `INSTALLED_APPS` (`settings.py`) e includere `apps/ui/urls.py` nel router principale.
Seguire i pattern di `docs/it/dev/api.md`: `handle_post_json`, `ErrorManager`, `@extend_schema` su ogni metodo pubblico.

| Step | Endpoint | Note |
|------|----------|------|
| C1 | `GET /api/v1/ui/liste/{codice}/config` | Legge `emittente_fiscale_id` dal JWT/sessione; invoca `fn_resolve_lista_config`; ritorna JSONB |
| C2 | `GET /api/v1/ui/liste/{codice}/catalogo` | Elenco completo `lista_colonna` per la modale (con `gruppo`, `gruppo_ordine`, `tipo_colonna`); non applica permessi — è il catalogo grezzo per uso UI interno |
| C3 | `PUT /api/v1/ui/liste/{codice}/preferenza` | Valida struttura JSONB in ingresso; upsert `lista_preferenza_utente`; registra `preset_base_data_update` |
| C4 | `DELETE /api/v1/ui/liste/{codice}/preferenza` | Elimina preferenza utente → al prossimo `GET config` parte dal preset |

Test in `apps/ui/tests/api/` e `apps/ui/tests/services/`. Mockare il cursore DB (test CI senza DB — pattern `docs/it/dev/api.md`).

---

### Blocco D — Frontend (dipende da C)

Componenti trasversali in `frontend/src/core/`.

| Step | File | Descrizione |
|------|------|-------------|
| D1 | `src/core/composables/useListaConfig.js` | Fetch `GET .../config`; gestione stato locale (config da server vs config corrente); fetch `GET .../catalogo` per modale; `save()` → `PUT .../preferenza`; `reset()` → `DELETE .../preferenza` |
| D2 | `src/core/components/ListaConfigurabile.vue` | Wrapper PrimeVue DataTable: riceve `codice` + `emittenteFiscaleId` come prop; usa `useListaConfig`; costruisce colonne dinamicamente; gestisce ordinamento e filtri locali |
| D3 | `src/core/components/ListaColonneModal.vue` | Modale personalizzazione: toggle visibilità, drag&drop ordine, colonne raggruppate per `gruppo`, colonne `identificatore`/`azione` non togglabili (disabled con tooltip), badge "N nuove colonne" |
| D4 | (incluso in D2) | Indicatore stato nella toolbar: testo `Configurazione salvata` / `Temporanea — non salvata`; confronto config locale vs config da server al mount |

Costanti UI (durata toast, larghezze default colonne) in `src/core/constants.js`.
Tutti i testi visibili via `$t()` (vue-i18n) — nessuna stringa hardcoded nei template.

---

### Blocco E — Prima lista reale (dipende da A+B+C+D)

Scopo: validare l'intera catena su un caso reale prima di replicare. Lista candidata: **anagrafiche clienti** (`codice = 'anagrafiche.clienti'`).

**Seed dati** — file CSV + YAML in `80_data/`:

| Step | File | Contenuto |
|------|------|-----------|
| E1 | `80_data/sql/ui/lista_definizione.csv` + YAML changelog | Una riga: `codice='anagrafiche.clienti'`, `vista_sql='<nome view clienti>'` |
| E2 | `80_data/sql/ui/lista_colonna.csv` + YAML changelog | Colonne del catalogo clienti: `ragione_sociale` (identificatore), poi colonne informazione con gruppo, ordine, tipo_dato, formato |
| E3 | `80_data/sql/ui/lista_preset.csv` + YAML changelog | Un preset di sistema (`is_default=TRUE, ambito='sistema'`) con le colonne più rilevanti |
| E4 | `80_data/sql/ui/lista_preset_colonna.csv` + YAML changelog | Colonne del preset di sistema: quali visibili di default, quali nel pool ma non visibili |

Verificare che ogni `campo_sorgente` in E2 esista nella view SQL prima del deploy — il trigger B2 lo valida automaticamente all'INSERT.

**Migrazione componente**:

| Step | File frontend | Descrizione |
|------|---------------|-------------|
| E5 | `src/anagrafiche/views/ClientiListView.vue` | Sostituire il DataTable statico con `<ListaConfigurabile codice="anagrafiche.clienti" />` |

Dopo E5, testare manualmente:
- Apertura senza preferenza → catalogo grezzo
- Personalizzazione colonne → salvataggio → ricarica → preferenza persistita
- Reset → torna al preset di sistema
- Badge "N nuove colonne" su aggiornamento catalogo

---

### Sviluppi rinviati

Vedi documento separato: [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md)
