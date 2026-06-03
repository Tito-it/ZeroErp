# Colonne visualizzate in liste — architettura

> **Scopo di questo documento**: architettura del modulo `ui` (problema,
> 3 livelli, tabelle DB, fn `fn_resolve_lista_config`, regole) + **storia
> cronologica** degli atterraggi (Blocco A→F). Append-only: le voci
> storiche non si rimuovono.
>
> Per il **piano operativo degli sviluppi differiti** (DEF-1..DEF-10:
> stato corrente, decisioni aperte, dipendenze, sforzo) vedi
> [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md).

**Modulo:** UI / Presentazione
**Stato:** Blocchi **A+B+C+D+E+F** completati (incluso F Fase 2 / DEF-5b 2026-05-10) + **DEF-1 export CSV/Excel** + **DEF-2 banner "preset aggiornato"** + **DEF-8 liste soggetti + fornitori + contratti** atterrati 2026-05-10/11/24 e 2026-06-02. DB-1..DB-4 atterrati, Blocco F.2 (i18n + seed clienti) applicato. **DB-A `priorita`** (attributo ritiro dinamico colonne, trasversale) atterrato 2026-06-02. 4 liste migrate (clienti, soggetti, fornitori, contratti) + 9 residue. **BE/FE del ritiro dinamico** (composable `useResponsiveColumns` + migrazione `ContrattiSearchTable` a `<ListaConfigurabile>`) atterrato 2026-06-03 (commit `1cc906377`) — brief applicato e archiviato in [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md). Prossimo: **DEF-8 articoli/preventivi...** — vedi [_def.md](sviluppo-personalizzazioni-liste_def.md).
**Coerenza:** Sviluppo Concentrico — strato di presentazione che si appoggia ai domini funzionali senza modificarli
**Revisione 2026-05-06 (post-A/B)**: allineato a DB landed (tipi BIGINT, output JSONB completo), recepiti i pattern di [api.md](../api.md) (skip_area_check, Idempotency-Key, base view) e dei due cataloghi building block. Variazioni in §4.3, §4.5, §5, §10, §11. Brief al team DB raccolti in §10.

Stato cronologico:

| Data | Evento |
| ---- | ------ |
| 2026-05-06 | Blocco A (DDL schema `ui` — 6 tabelle + 4 ENUM + FK auth_user + seed fk_index_policy) atterrato su `dev/db-tid` |
| 2026-05-06 | Blocco B (2 trigger guard + `fn_resolve_lista_config` + 9 test pgTAP) atterrato su `dev/db-tid` |
| 2026-05-06 | Analisi critica post-A/B: brief DB-1..DB-4 raccolti (§10.2) |
| 2026-05-07 | Brief DB-1..DB-4 atterrati su `dev/db-tid` (changeset `20260507-01..04`, pgTAP 12/12). Deviazioni: cast GUC blindato + trigger `clear_preset_base_ts` |
| 2026-05-07 | **Blocco C** (backend `apps/ui/`) completato: 4 endpoint, 5 codici errore, 26 test verdi, doc API, refactor critico applicato |
| 2026-05-07 | **Blocco D** (frontend `core/components/` + `core/composables/` + `core/api/`) completato: 4 building block FE, 15 chiavi i18n IT/EN, vite build verde, refactor critico applicato |
| 2026-05-07 | **Blocco E — seed DB** atterrato su `dev/db-tid` (lista_definizione + lista_colonna + lista_preset + lista_preset_colonna per `anagrafiche.clienti`) |
| 2026-05-07 | **Blocco E5 — migrazione FE** atterrata: `ClientiSearchTable.vue` ora usa `<ListaConfigurabile codice="anagrafiche.clienti">`. Build vite verde, `ClientiView` invariato |
| 2026-05-07 | **Smoke test E** preparato in `backend/scripts/tests/smoke-test-ui-personalizzazioni-liste.sh` (10 scenari). **Esecuzione bloccata** dal mancato GRANT su schema `ui` per `zeroerp_app` — brief DB-5 in §10.2-bis |
| 2026-05-07 | Decisioni prese su **Blocco F** (gestione amministrazione `ui.*`): split visibilità config/amm-software, Fase 1 minimal (preset + permessi colonne). Implementazione dopo smoke test E. Promemoria 2 decisioni aperte (area azioni di processo + profilo seed) in §11/Blocco F |
| 2026-05-08 | **Blocco F Fase 1** atterrato end-to-end (DB+BE+FE+test+doc): preset + permessi colonne sotto `/config/personalizzazioni-liste`. 9 endpoint admin, 19 nuovi test (54/54 verdi totali). Decisioni operative chiuse: area azioni `config` (1A), nessun profilo seed (2B). |
| 2026-05-08 | **Blocco F.2** (i18n etichette + fix seed clienti) atterrato dal team DB: nuova colonna `ui.lista_colonna.etichetta_i18n_key` + `fn_resolve_lista_config` aggiornata + seed clienti corretto (composta `sosp_riatt`). Refactor toolbar lista standard (`<ListaConfigurabile>` + `ClientiSearchTable`). |
| 2026-05-10 | **Blocco F Fase 2 — DEF-5b** atterrato end-to-end (BE+FE+test+doc): CRUD `ui.lista_definizione` + `ui.lista_colonna` SUPER_ADMIN-only sotto `/amm-software/personalizzazioni-liste-tecniche`. 8 endpoint admin nuovi, 39 test (93/93 ui verdi totali, 590 BE complessivi). 8 decisioni operative chiuse — vedi [_def.md DEF-5b](sviluppo-personalizzazioni-liste_def.md). Helper `optional_string` estratto in `PayloadValidator` (refactor anti-duplicazione). |
| 2026-05-10 | **DEF-1 export CSV/Excel** atterrato sulla lista clienti (BE+FE+test+doc): renderer puro `ListaExportService` no-fetch (genera bytes da righe + config colonne), endpoint dedicato `GET /api/v1/anagrafiche/clienti/export/` con query param `format=csv` o `xlsx`, hard cap 10.000 righe pre-render via `total_count` window function, foglio "Filtri applicati" XLSX + header con prefisso `#` JSON dei filtri in CSV con BOM UTF-8. Composable FE riusabile `useFileDownload` (pattern Content-Disposition RFC 5987). Aggiunto `openpyxl>=3.1` a requirements (autorizzato Tid). 12 nuovi test renderer. 4 decisioni operative chiuse — vedi [_def.md DEF-1](sviluppo-personalizzazioni-liste_def.md). Refinement architetturale: il modulo `ui` espone solo il renderer (no SQL dinamico sulla `vista_sql`); ogni dominio in DEF-8 estende il proprio repository per ottenere righe e delega al renderer. |
| 2026-05-11 | **DEF-2 "preset aggiornato"** atterrato (BE+FE+brief DB+test+doc): nuova colonna `ui.lista_preferenza_utente.preset_aggiornato_ignored_at` (tombstone "Ignora"), `ui.fn_resolve_lista_config` aggiornata per esporre flag `preset_aggiornato: bool` via confronto `COALESCE(data_update,data_insert)` snapshot vs corrente, nuovo endpoint `POST /api/v1/ui/liste/<codice>/preferenza/ignore-preset-update/` con `Idempotency-Key`, banner inline `<Message severity="info">` dentro `ListaConfigurabile` (gratis per tutti i caller DEF-8). 3 decisioni operative chiuse + audit critico applicato (helper `_require_lista_id`, `MANAGE_ICONS.PERSONALIZZA` centralizzata) — vedi [_def.md DEF-2](sviluppo-personalizzazioni-liste_def.md). |
| 2026-05-11 | **DEF-8 soggetti** atterrato (BE+FE+brief DB+test+doc): `<ListaConfigurabile codice="anagrafiche.soggetti">` + endpoint `/anagrafiche/soggetti/export/` simmetrico clienti. 2 fix emersi a smoke: (a) `campo_sorgente='id_fiscale_univoco_cf_piva'` (colonna `GENERATED ALWAYS` su `anagrafiche.soggetti` che COALESCE CF/PIVA, allineato a clienti); (b) `sensibile=false` su `codice_fiscale` (la fn DB filtra fuori le colonne sensibili senza grant, anche per SUPER_ADMIN — pattern clienti = sensibile=false). Aggiornata `manage-test.sh` con override `DJANGO_API_SEARCH_THROTTLE_RATE=100000/min` per neutralizzare 429 falsi positivi nei test (LocMemCache persiste tra SimpleTestCase). 7 test nuovi BE (3 service label + 4 view smoke export). Tutta la suite Django 2494/2494 verde. — vedi [_def.md DEF-8](sviluppo-personalizzazioni-liste_def.md). |
| 2026-06-02 | **DB-A `priorita` + DEF-8 contratti** atterrati su `dev/db-tid` (solo DB; BE/FE a valle). **DB-A**: nuova colonna `ui.lista_colonna.priorita SMALLINT NOT NULL DEFAULT 50` (peso ritiro dinamico colonne, packing a somma FE) + `fn_resolve_lista_config` espone `priorita` per ogni colonna (letta fresca dal catalogo, non overridabile per preset/preferenza). **DB-B**: vista `vendite.vw_contratti_lista` (`security_invoker=on`, RLS contratti attiva — join diretto a `soggetti`, non annida `vw_soggetti_ruoli_dettaglio`) + seed `lista_definizione/colonna/preset/preset_colonna` per `vendite.contratti` (22 colonne catalogo, 13 visibili nel preset `contratti_default`, ordinamento `data desc`). Aggiunta `stato_codice` nascosta per Tag severity FE (omessa dal brief §4). **Bug latente trovato e corretto**: le sequenze IDENTITY delle 3 tabelle `ui.*` seedate con id espliciti non venivano riallineate → collisione pkey sugli INSERT auto-id (admin CRUD DEF-5b + test); fix con `90_end/20260602-17` (`runAlways setval` a `MAX(id)`). Changeset `20260602-13..17`. pgTAP: `test-fn-resolve-lista-config` 13/13 (nuovo test priorita), `test-lista-contratti-seed` 14/14. Prima lista non-`anagrafiche` migrata. — vedi [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md). |
| 2026-05-24 | **DEF-8 fornitori** atterrato (BE+FE+brief DB+test+doc): `<ListaConfigurabile codice="anagrafiche.fornitori">` + endpoint `/anagrafiche/fornitori/export/` simmetrico clienti+soggetti. Particolarita': il repo fornitori legge da vista (`vw_fornitori_dettaglio`), non da repo Python con alias → brief DB include estensione vista con `s.id_fiscale_univoco_cf_piva` (JOIN su soggetti). 15 colonne nel catalogo (7 visibili nel preset + 8 extra opt-in: codice_fiscale, partita_iva, pec_email, canale_fe, split_payment, ritenuta_acconto, regime_fiscale, data_update). Divergenza voluta vs clienti+soggetti: `codice='id_fiscale'` per la colonna unificata (invece di `codice='codice_fiscale'`) per permettere CF e P.IVA come extra separati nel catalogo. Lezioni soggetti applicate da subito (sensibile=false ovunque). 7 test nuovi BE (3 service label + 4 view smoke export). 387/387 anagrafiche test verdi. Fix preset post-seed: la riga `lista_preset_colonna` con `codice='codice_fiscale'` (CF puro, vuota per fornitori azienda) era refuso del brief originale, sostituita con `id_fiscale` via UPDATE puntuale ([brief-db-def8-fornitori-fix-preset-id-fiscale.md](../work-done/brief-db-def8-fornitori-fix-preset-id-fiscale.md)). — vedi [_def.md DEF-8](sviluppo-personalizzazioni-liste_def.md). |

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
  emittente_fiscale_id     BIGINT REFERENCES anagrafiche.emittenti_fiscali(id),
    -- usato quando ambito = 'emittente_fiscale'; l'associazione operatore↔EF
    -- è 1:1 (refactor operatore-emittenti, vedi config.user_emittenti_fiscali).
    -- ATTENZIONE: il DDL atterrato in A4 usa INTEGER mentre emittenti_fiscali.id
    -- è BIGINT — Postgres coerce ma è inconsistenza. Brief DB pendente in §10.

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

  UNIQUE (auth_user_id, lista_id),

  -- ON DELETE SET NULL: se l'admin elimina il preset di base la preferenza
  -- utente non si rompe — il riferimento storico diventa NULL.
  -- (Da consolidare in 90_end nel brief DB §10 — il DDL A6 non lo prevede.)
  CONSTRAINT fk_preferenza_preset_base
    FOREIGN KEY (preset_base_id) REFERENCES ui.lista_preset(id) ON DELETE SET NULL
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
-- Firma effettiva landed (vedi docs/it/dbzero/ui/funzioni/fn_resolve_lista_config.md):
CREATE OR REPLACE FUNCTION ui.fn_resolve_lista_config(
  p_lista_codice         VARCHAR,
  p_auth_user_id         INTEGER,
  p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE   -- BIGINT
) RETURNS JSONB
LANGUAGE plpgsql STABLE
```

Logica (sintesi — sorgente completo nei changelog Liquibase `20_code/ui/`):

1. **Risoluzione profili applicabili** via `script.fn_get_profili_accesso_applicabili(p_auth_user_id)` — la stessa chain del `PermissionResolver` Django.
2. **Cascata** preferenza utente → preset ruolo → preset emittente → preset sistema → catalogo grezzo (vedi §3).
3. **Merge nuove colonne**: le colonne del catalogo non presenti nella configurazione candidata vengono aggiunte con `visibile=false`; il contatore `colonne_nuove` è ritornato per il badge UX.
4. **Permessi effettivi per colonna** via `DISTINCT ON (colonna_codice)` ordinato per `(priorita ASC, restrittivita ASC)` con `BLOCCATO=1 > LETTURA=2 > TUTTO=3`. Significa: AD_HOC (prio 1) prevale su REPARTO (prio 2); a parità, vince il livello più restrittivo.
5. **Normalizzazione**: `tipo_colonna IN ('identificatore','azione')` forza `visibile=true` anche se la preferenza salvata dice il contrario; `identificatore` forza `fissata=true`. Colonne `sensibile=TRUE` senza grant esplicito → escluse (BLOCCATO implicito allow-list); colonne BLOCCATE → rimosse; colonne LETTURA → marcate `esportabile=false`.

**Output JSONB effettivo** (allineato al sorgente Liquibase, output completo per ogni colonna):

```jsonc
{
  "colonne": [
    {
      "codice": "ragione_sociale",
      "ordine": 1,
      "larghezza": 240,
      "visibile": true,
      "fissata": true,
      "esportabile": true,        // false se livello LETTURA
      "tipo_colonna": "identificatore"  // utile al FE per disabilitare toggle
    },
    ...
  ],
  "ordinamento":      [{"col": "ragione_sociale", "dir": "asc"}],
  "filtri":           {"attivo": true},
  "pagina_dimensione": 25,
  "colonne_nuove":     0
}
```

I campi `esportabile` e `tipo_colonna` per ogni colonna **fanno parte del contratto API** — il FE li usa per disabilitare il toggle nella modale (identificatore/azione) e per pilotare l'export.

Il campo `colonne_nuove` permette al frontend di mostrare il badge "N nuove colonne disponibili" senza fare chiamate aggiuntive.

**Risoluzione di `emittente_fiscale_id` lato backend.** Post refactor operatore-emittenti l'associazione operatore↔EF è **1:1** (vedi `script.fn_resolve_emittente_for_user` e `PermissionResolver.get_emittente_for_user`): non c'è più ambiguità di whitelist multi-EF. Il **frontend non invia** mai questo parametro — il backend lo deriva con:

```python
emittente_id = PermissionResolver.get_emittente_for_user(request.user)
# None per admin globale o istanza "0 emittenti": passa NULL alla fn
config = ui_repository.resolve_lista_config(codice, request.user.id, emittente_id)
```

Il parametro resta nella signature SQL per casi diagnostici/admin (super-admin che vuole previsualizzare il preset di un EF specifico), ma non è esposto in `GET /config`.

> **Brief DB pendenti** (vedi §10). Sulla cascata e sul filtro veste il resolver landed presenta due punti aperti:
>
> - **Preset di ruolo non ordinato per `priorita`** (Step 2b): se l'utente ha più profili applicabili con preset `is_default=TRUE` per la stessa lista, il preset scelto non è deterministico.
> - **Veste corrente non filtrata**: `fn_get_profili_accesso_applicabili(auth_user_id)` (1-arg) ritorna profili di tutte le vesti dell'utente (OPERATORE + CLIENTE_PORTALE su stessa email vengono mescolati).

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

### 10.1 Aperti generali

1. **Validare il catalogo** su un caso reale complesso (anagrafiche clienti, articoli, commesse) prima di generalizzare.
2. **Formato `filtri_default` JSONB** — il formato dei filtri nel preset DB deve essere concordato con il componente Vue filtri prima di seedare i preset. Definirlo nel Blocco C/D del piano di sviluppo (§11).
3. **Sviluppi rinviati** — export, viste nominate, admin UI, mobile: vedi [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md).

### 10.2 Brief al team DB (post-A/B, dev/db-tid) — ✅ LANDED 2026-05-07

Quattro interventi raccolti dall'analisi critica post-A/B. **Tutti applicati** dal team DB su `dev/db-tid` (changeset `20260507-01..04`); pgTAP 12/12 verdi (uno in più del previsto: test 3b separato sulla colonna sensibile).

| # | Intervento | Stato |
| - | ---------- | ----- |
| DB-1 | `ALTER TABLE ui.lista_preset ALTER COLUMN emittente_fiscale_id TYPE BIGINT` | ✅ |
| DB-2 | `fk_lista_preferenza_utente_lista_preset` → `ON DELETE SET NULL` | ✅ |
| DB-3 | `fn_resolve_lista_config` — Step 2b: cascata preset di ruolo ordinata per `pa.priorita ASC` | ✅ |
| DB-4 | `fn_resolve_lista_config` — Step 1: filtro veste corrente via GUC `app.ruolo_applicativo` | ✅ (con cast blindato, vedi sotto) |

**Deviazione #1 — DB-4 cast GUC blindato.** Invece del cast diretto `NULLIF(...)::config.ruolo_applicativo`, il team DB ha avvolto il cast in un blocco `EXCEPTION WHEN invalid_text_representation THEN NULL`. Se la GUC contiene un valore non-ENUM (corruzione, downgrade, test che setta valore arbitrario), fallback silenzioso a NULL = legacy "tutte le vesti", invece di propagare un'eccezione all'utente. Backend non vede differenza: `JwtAuditAuthentication` scrive sempre valori corretti dell'enum.

**Deviazione #2 — Trigger aggiuntivo `trg_ui_lista_preferenza_utente_z90_clear_preset_base_ts_upd`.** Non richiesto dal brief ma sensato: quando un preset viene eliminato, l'`ON DELETE SET NULL` di DB-2 azzera `preset_base_id`; il trigger azzera *anche* `preset_base_data_update` per coerenza (un timestamp di confronto senza preset di riferimento sarebbe dato fantasma).

**Impatto FE — regola obbligatoria sul badge "preset aggiornato"** (DEF-2): il confronto `preset_base_data_update < lista_preset.data_update` ha senso solo se il preset di base esiste ancora. La condizione completa:

```js
const showPresetUpdatedBadge =
  preferenza.preset_base_id !== null &&
  preferenza.preset_base_data_update !== null &&
  presetCorrente.data_update > preferenza.preset_base_data_update;
```

Se `preset_base_id === null` il preset di riferimento non esiste più (è stato eliminato): il badge **non va mostrato**, l'utente sta di fatto vivendo su una preferenza orfana che ha senso lasciare invariata finché l'utente non decide di resettare. La regola va recepita nel Blocco D (D2/D3) e nel doc differito [DEF-2](sviluppo-personalizzazioni-liste_def.md).

**Brief originale**: [brief-db-ui-personalizzazioni-liste.md](brief-db-ui-personalizzazioni-liste.md) (con stato LANDED in cima).

### 10.2-bis Brief DB-5 (rilevato post-E5, smoke test) — TODO

> ⚠️ **Bloccante** per smoke test E end-to-end e per Blocco F.

**Sintomo**: il backend Django solleva `ProgrammingError: permesso negato per lo schema ui` quando tenta di leggere `ui.lista_definizione`. Il ruolo runtime `zeroerp_app` non ha `USAGE` sullo schema `ui` né privilegi sulle tabelle. Verificato 2026-05-07 lanciando una query test via Django ORM.

**Causa**: la whitelist hardcoded in [`scripts/sql/provision_db_roles.sql`](../../../../scripts/sql/provision_db_roles.sql) elenca solo `public, script, dbops, config, anagrafiche, catalogo, vendite, acquisti, magazzino, pagamenti, contabilita, storico`. Mancano `ui`, `documenti`, `pratiche` (questi ultimi due forse compensati in altro modo).

**Brief DB-5**:

1. Aggiornare `provision_db_roles.sql` aggiungendo `'ui'` (e per coerenza `'documenti'`, `'pratiche'`) alle 5 whitelist `IN (...)` del file:
   - GRANT USAGE ON SCHEMA
   - GRANT SELECT/INSERT/UPDATE/DELETE ON ALL TABLES IN SCHEMA
   - GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
   - GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
   - ALTER DEFAULT PRIVILEGES per il migrator (3 statement)
2. Ri-eseguire lo script (idempotente) sul DB dev con utente admin DB:

   ```bash
   psql "host=$DB_HOST port=5432 dbname=zeroerp user=$ADMIN_DB_USER" \
     -v app_role=zeroerp_app \
     -v app_password='<password>' \
     -v migrator_role=titodb \
     -f scripts/sql/provision_db_roles.sql
   ```

3. Verificare con `scripts/sql/check_db_role_access.sql` che `zeroerp_app` legge `ui.lista_definizione`.

**Impatto**: solo provisioning, nessun cambiamento allo schema/dati. Sblocca smoke test E.

**Brief separato**: [brief-db-grants-schemi-applicativi.md](brief-db-grants-schemi-applicativi.md) (pronto da passare a `dev/db-tid`).

### 10.3 Caching della config (proposta da valutare in Blocco C)

`fn_resolve_lista_config` viene invocata ad ogni open della lista e fa fino a 5–6 round-trip. Per liste con molte colonne+permessi conviene un ETag basato su:

```text
hash(user_id, lista_codice, max(data_update di ui.lista_definizione + lista_colonna + lista_preset + lista_preset_colonna + lista_preferenza_utente + lista_colonna_permesso filtrate per la lista))
```

Il backend ritorna `ETag` su `GET /config` e accetta `If-None-Match` → 304 se nulla è cambiato. Niente cache lato Redis: la sorgente di verità sta nel DB e il calcolo è leggero quando i tag matchano.

---

## 11. Piano di sviluppo

> **Convenzioni**: Liquibase → `docs/it/liquibase-setup-workflow.md`. SQL/trigger → `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`. Backend → `docs/it/dev/api.md`.
>
> **Entità già presenti, non da creare**: `django.auth_user`, `config.profili_accesso`, `config.profili_accesso_bindings`, `anagrafiche.emittenti_fiscali`, `config.user_emittenti_fiscali`, `script.fn_get_profili_accesso_applicabili`.

### Dipendenze tra blocchi

```text
Blocco A ✅  ─►  Blocco B ✅  ──────────────────────────────►  Blocco E ✅  ─►  Blocco F (post smoke E)
                                                                Prima lista reale  Gestione admin
                 Blocco C ✅  ─►  Blocco D ✅  ──────────────►                     (config + amm-software)
```

A+B+C+D+E atterrati 2026-05-07. F (gestione admin tabelle `ui.*`) pianificato dopo lo smoke test E
end-to-end con operatore reale; decisioni architetturali in §11.F.0, 2 decisioni operative aperte
nel callout dedicato di §11/Blocco F.

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

### Blocco C — Backend ✅ COMPLETATO (2026-05-07)

Struttura atterrata in `backend/apps/ui/` (allineata a `apps/documenti/`):

```text
apps/ui/
├── __init__.py
├── apps.py                        # AppConfig, name = 'apps.ui'
├── urls.py                        # urlpatterns per /api/v1/ui/
├── db/
│   └── ui_repository.py           # query dirette verso schema ui (cursor)
├── services/
│   ├── ui_service.py              # facade lettura: get_lista_config, get_catalogo
│   └── lista_preferenza_service.py # write: save/delete preferenza utente, valida JSONB
├── api/
│   ├── views.py                   # 4 view DRF + @extend_schema inline
│   └── urls.py                    # route locali
└── tests/
    ├── api/
    └── services/
```

Aggiungere `'apps.ui'` in `INSTALLED_APPS` ([backend/zeroerp_backend/settings.py:73-98](../../../../backend/zeroerp_backend/settings.py)) e includere il router locale.

#### C0 — Codici errore in `apps/core/services/error_policies.py` (PRIMA di scrivere le view)

Cfr. [api.md §Tassonomia errori](../api.md) e [Checklist nuovo endpoint](../api.md#checklist-nuovo-endpoint). Da registrare:

| Codice | HTTP | UI action | Quando |
| ------ | ---- | --------- | ------ |
| `E_UI_LISTA_NON_TROVATA` | 404 | show_error_banner | `fn_resolve_lista_config` con `codice` inesistente o `attivo=FALSE` |
| `E_UI_VISTA_SQL_NON_TROVATA` | 400 | show_error_banner | Trigger B1 — solo errori admin (seed/import); l'utente finale non li vede |
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | show_error_banner | Trigger B2 — idem |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | show_error_banner | Service C3 — payload preferenza con campi non whitelistati o tipi sbagliati |

I tre `E_UI_*_NON_TROVATA/_NON_TROVATO` sono già seedati in [messaggi_errore.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv) (ID 427–429). `E_UI_PREFERENZA_VALIDAZIONE` è solo Python.

#### Base view e permessi

`/api/v1/ui/*` è **meta-API trasversale** (consumata da tutti i domini): non è un'area funzionale di business e lo schema `ui` **non è registrato** in `config.aree_funzionali`. La via corretta è `DomainAPIView` con `skip_area_check = True`, coerente con il pattern dei lookup cross-dominio (cfr. `BillingAccountLookupView`, `IstanzaUtilityLookupView` in [catalogo-building-block-backend.md §Anagrafiche — Billing Account](../backend/catalogo-building-block-backend.md#anagrafiche--billing-account-appsanagrafiche)).

I dati comunque restano per-utente: il `GET /config` proietta solo le colonne ammesse all'utente; il `GET /catalogo` ritorna metadati di struttura non sensibili; le preferenze sono sempre filtrate per `request.user.id`.

```python
# apps/ui/api/views.py — pattern
class ApiListaConfigView(DomainAPIView):
    skip_area_check = True
    is_search_endpoint = False  # config non è search

    @extend_schema(...)
    def get(self, request, codice):
        emittente_id = PermissionResolver.get_emittente_for_user(request.user)
        config = ui_service.get_lista_config(codice, request.user.id, emittente_id)
        return success_response(config)
```

#### Endpoint atterrati

| Step | Endpoint | Stato | Note |
| ---- | -------- | ----- | ---- |
| C1 | `GET /api/v1/ui/liste/{codice}/config/` | ✅ | Deriva `emittente_fiscale_id` via `PermissionResolver.get_emittente_for_user`; invoca `ui.fn_resolve_lista_config`; ritorna JSONB completo (incluso `esportabile` + `tipo_colonna` per ogni colonna). ETag rinviato a evoluzione (§10.3). |
| C2 | `GET /api/v1/ui/liste/{codice}/catalogo/` | ✅ | Catalogo arricchito (etichetta, gruppo, formato, ecc.) via `JOIN lista_definizione` in `list_colonne_by_codice`. Filtra colonne BLOCCATE riusando `get_lista_config()` come single source of truth permessi (no duplicazione logica). |
| C3 | `PUT /api/v1/ui/liste/{codice}/preferenza/` | ✅ | `handle_post_json` con `require_idempotency_key=True`. `PayloadValidator` whitelist `{colonne[], ordinamento[], filtri{}, pagina_dimensione}`; per ogni colonna `{codice, ordine, larghezza, visibile, fissata}`. UPSERT con snapshot preset di base (cascata simmetrica a fn DB Step 2b/c/d). `pagina_dimensione` cap a `MAX_LIMIT=200` da `apps/core/api/constants.py`. |
| C4 | `DELETE /api/v1/ui/liste/{codice}/preferenza/` | ✅ | Idempotente: ritorna `{deleted: bool}` (200 anche se non esisteva). |

**Test 26/26 verdi**:

- 17 service test (`UiService` 7 + `ListaPreferenzaService` 10) — repository mockato (`SimpleTestCase`)
- 6 API test (`JwtMockedApiTest` con `PermissionResolver` mockato + service mockati)
- Suite globale invariata: 2199/2199 verdi.

**Codici errore** registrati in [`apps/core/services/error_policies.py`](../../../../backend/apps/core/services/error_policies.py):

| Codice | HTTP | UI action |
| ------ | ---- | --------- |
| `E_UI_LISTA_NON_TROVATA` | 404 | `show_empty_state` |
| `E_UI_VISTA_SQL_NON_TROVATA` | 400 | `show_error_banner` |
| `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | `show_error_banner` |
| `E_UI_PREFERENZA_VALIDAZIONE` | 400 | `highlight_form_fields` |
| `E_UI_GENERIC_FAILED` | 400 | `show_error_banner` (fallback DatabaseError ignote, allineato al pattern `E_VENDITE_PRICING_FAILED`) |

**Doc API**: [`docs/it/backend/ui/manual/api_ui_liste.md`](../../backend/ui/manual/api_ui_liste.md) — contratto completo dei 4 endpoint, building block usati, regole multi-veste, dipendenze DB.

**Refactor critico applicato** (review post-implementazione):

- P1 — `get_catalogo` ridotto da 3 → 2 round-trip riusando `get_lista_config()` come single source of truth permessi
- P2 — `_raise_db_error` parametrizzato con `function_name` per logging DB corretto
- P3 — `pagina_dimensione` cap a `MAX_LIMIT` invece di `200` hardcoded
- P4 — `_raise_db_error` annotato `-> NoReturn`
- P5 — drift risk in `get_preset_base_snapshot` documentato (cascata duplicata della fn DB)
- P6 — `list_colonne_by_codice` con JOIN unificato (rimosso `list_colonne_catalogo` + `get_lista_id` separati)

#### Building block backend riusabili

Da [catalogo-building-block-backend.md](../backend/catalogo-building-block-backend.md):

- `handle_post_json` + `success_response` + `exception_to_error_response` (envelope uniforme)
- `PayloadValidator` per la whitelist JSONB del PUT
- `PermissionResolver.get_emittente_for_user` (1:1 user→EF)
- `script.fn_log_and_raise_error` lato DB per gli errori della fn
- `EmittenteFiscaleScopeMixin` non serve qui (la fn applica già lo scope)

Test in `apps/ui/tests/api/` e `apps/ui/tests/services/` con `unittest.TestCase` + cursor DB mockato (vincoli CI senza DB — vedi [AGENTS.md §Test](../../../.codex/AGENTS.md)).

---

### Blocco D — Frontend ✅ COMPLETATO (2026-05-07)

Componenti trasversali in `frontend/src/core/`.

#### Pattern: estendere i building block esistenti, non duplicarli

Prima di scrivere composable nuovi, vedi [catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md). I tre building block che `<ListaConfigurabile>` deve **comporre**, non sostituire:

- **`useSearchTable`** — già gestisce ricerca + paginazione + ordinamento server-side con debounce. Lo `<ListaConfigurabile>` lo invoca passando `pagina_dimensione`, `ordinamento` e `filtri` derivati dalla config risolta.
- **`useGlobalLookup`** — cache modulo-level per il `GET /catalogo` (chiave = `ui.lista.<codice>`): la modale di personalizzazione si apre senza round-trip se il catalogo è già stato fetched in sessione.
- **`useDirtyState`** — la toolbar `[Configurazione salvata]` vs `[Temporanea — non salvata]` (§7) si appoggia su `useDirtyState` invece di costruire un confronto custom.

Niente prop `emittenteFiscaleId` sul componente: il backend lo deriva (vedi §5).

#### Steps atterrati

| Step | File | Stato | Note implementazione |
| ---- | ---- | ----- | -------------------- |
| D1 | [`src/core/api/ui-api.js`](../../../../frontend/src/core/api/ui-api.js) | ✅ | 4 endpoint client axios (`getListaConfig`, `getListaCatalogo`, `putListaPreferenza`, `deleteListaPreferenza`). `Idempotency-Key` passata dal caller, generata via `crypto.randomUUID()` in `useListaConfig.save()`. |
| D1 | [`src/core/composables/useListaConfig.js`](../../../../frontend/src/core/composables/useListaConfig.js) | ✅ | Stato per-istanza (no cache modulo-level): `config`, `catalogo` (lazy), `dirty`, `colonneNuove`, `loading`. Metodi `load`, `ensureCatalogo`, `applyChange`, `save`, `reset`. Whitelist payload `_PAYLOAD_ROOT_KEYS`/`_COLONNA_KEYS` allineata a `ListaPreferenzaService` BE (drift risk documentato in commento). ETag rinviato a evoluzione (§10.3). |
| D2 | [`src/core/components/ListaConfigurabile.vue`](../../../../frontend/src/core/components/ListaConfigurabile.vue) | ✅ | Wrapper PrimeVue DataTable. Prop `codice` + `rows`/`total`/`loading`/`page`/`sortField`/`sortOrder` controllati dal caller (no fetch dati interno: il caller mantiene il proprio store + `useSearchTable`). Toolbar con `Tag` stato salvata/temporanea + `Button` personalizza con `Badge` `colonne_nuove`. Slot dinamico `cell-{codice}` per body custom + slot `actions`/`filters`/`actions-extra`. Fallback formatter built-in da `formato` (`date_short`, `currency_eur`, `percent_2`, `yesno`). Colonna "Azioni" renderizzata solo se `slots.actions` e' fornito (no celle vuote silenti). `pageSize`/`firstOffset` computed con fallback a `PAGINATION.DEFAULT_ROWS`; `firstOffset=0` finche' config null per evitare salti visivi. |
| D3 | [`src/core/components/ListaColonneModal.vue`](../../../../frontend/src/core/components/ListaColonneModal.vue) | ✅ | PrimeVue Drawer right `DRAWER_WIDTH.SIMPLE` (480px). Lavora su copia locale `localColonne` — propaga al genitore solo a "Salva" (emit `apply` con `{colonne}`). Toggle disabilitato per `tipo_colonna IN ('identificatore','azione')` con tooltip esplicativo. Riordino tramite ▲/▼ (zero dipendenze drag&drop esterne); ▲ disabled sulla prima colonna globale, ▼ disabled sull'ultima (simmetria UX). Edit larghezza inline via `InputNumber` con limiti `_LARGHEZZA_LIMITS` (40-800 px, step 20). Reset preferenza tramite `useConfirmAction.confirmAction({danger: true, onAccept})`. Colonne raggruppate per `gruppo`/`gruppo_ordine` del catalogo. |
| D4 | (incluso in D2) | ✅ | Indicatore stato nella toolbar: `Tag warning` "Temporanea — non salvata" se `dirty`, `Tag success` "Configurazione salvata" altrimenti. |

**i18n**: 15 chiavi nuove sotto `lista_config.*` in [`it.json`](../../../../frontend/src/locales/it.json) e [`en.json`](../../../../frontend/src/locales/en.json) (`modal_title`, `stato_salvata`, `stato_temporanea`, `colonne_nuove_tooltip`, `colonna_obbligatoria`, `larghezza_tooltip`, `sposta_su`/`sposta_giu`, `tag_sensibile`, `gruppo_altro`, `reset_preferenza`, `reset_confirm_header`/`reset_confirm_message`, ecc.).

**Build verde**: `vite build` 1.05s, niente regressioni nei chunk.

**Refactor critico applicato** (review post-implementazione):

- FP1 — `:rows` paginator usa `pageSize` computed con `PAGINATION.DEFAULT_ROWS` (no `?? 25` magic duplicato)
- FP2 — `:first` 0 finche' config null per evitare salto visivo paginator al caricamento
- FP3 — Colonna "Azioni" renderizzata solo se `slots.actions` esiste (no celle vuote)
- FP4 — Width Drawer da `520px` hardcoded a `DRAWER_WIDTH.SIMPLE`
- FP5 — Limiti larghezza in costante locale `_LARGHEZZA_LIMITS`
- FP6 — Pulsante ▼ disabled simmetrico (ultima colonna globale)
- FP7 — Drift risk whitelist FE/BE documentato in `useListaConfig.save()`
- FP8 — Comportamento errore di rete su reload post-save documentato

**Cose riusate da building block esistenti** (no duplicazione):

- `useApiHandler` per error handling automatico + toast
- `useConfirmAction` per la conferma reset
- `app-datatable` CSS class globale per il DataTable compatto
- `PAGINATION.DEFAULT_ROWS` / `DRAWER_WIDTH.SIMPLE` da `core/constants.js`

**Limitazione MVP nota**: il BE espone solo il conteggio aggregato `colonne_nuove`, non un flag `is_new` per-colonna. La modale mostra il badge globale ma non evidenzia singolarmente le nuove colonne. Evoluzione futura: brief team DB per arricchire lo Step 3 di `fn_resolve_lista_config` con `is_new: true` per colonna.

---

### Blocco E — Prima lista reale (dipende da A+B+C+D)

Scopo: validare l'intera catena su un caso reale prima di replicare. Lista candidata: **anagrafiche clienti** (`codice = 'anagrafiche.clienti'`).

> **Vincolo**: eseguire i brief DB-1..DB-4 (§10.2) **prima** del seed E1, altrimenti il preset di emittente fiscale rischia di basarsi su tipi/comportamenti scorretti che andranno re-seedati.

**Seed dati** ✅ atterrati su `dev/db-tid` 2026-05-07:

| Step | File | Stato |
| ---- | ---- | ----- |
| E1 | `80_data/sql/ui/lista_definizione.csv` + YAML changelog | ✅ |
| E2 | `80_data/sql/ui/lista_colonna.csv` + YAML changelog | ✅ |
| E3 | `80_data/sql/ui/lista_preset.csv` + YAML changelog | ✅ |
| E4 | `80_data/sql/ui/lista_preset_colonna.csv` + YAML changelog | ✅ |

Convenzione naming YAML (cfr. [AGENTS.md §Liquibase v2 Workflow](../../../.codex/AGENTS.md)): `YYYYMMDD-NN-seed-ui-<descrizione>-mctit.yaml` in `80_data/changelog/`.

**Migrazione componente** ✅ atterrato 2026-05-07:

| Step | File frontend | Stato |
| ---- | ------------- | ----- |
| E5 | [src/anagrafiche/components/ClientiSearchTable.vue](../../../../frontend/src/anagrafiche/components/ClientiSearchTable.vue) | ✅ DataTable statico sostituito da `<ListaConfigurabile codice="anagrafiche.clienti">`. Toolbar filtri + `PageActionsBar` esposti via slot `filters` / `actions-extra`. Slot `cell-{codice}` per le 6 colonne con render custom (codice_fiscale fallback partita_iva, date, sosp/riatt composta, stato_descrizione tag). Allineamento `store.filters.limit` con `pagina_dimensione` BE via handler `@config-loaded`. `ClientiView.vue` invariato (emit-contract identico). Build vite verde. |

Dopo E5, smoke test manuale:

- Apertura senza preferenza → catalogo grezzo del preset di sistema atterrato in E3
- Personalizzazione colonne → salvataggio → ricarica → preferenza persistita
- Reset → torna al preset di sistema
- Badge "N nuove colonne" su aggiornamento catalogo
- Operatore con scope EF specifico vede solo i clienti del suo emittente (lo scope è applicato dalla `vista_sql`, non da `fn_resolve_lista_config` — la fn governa solo presentazione)

---

### Blocco F — Gestione amministrazione personalizzazioni (post-E)

Scopo: esporre via UI il CRUD delle 6 tabelle `ui.*` per consentire ai tenant admin di creare preset e permessi colonna senza richiedere un seed CSV/deploy. Decisioni prese 2026-05-07 (vedi §11.F.0 sintesi):

> ⚠️ **Promemoria — decisioni aperte da chiudere PRIMA di iniziare F**
>
> Bloccanti per il brief team DB e per il seed iniziale, non bloccanti per il design generale:
>
> 1. **Area associata alle nuove azioni di processo** `ui_preset_manage` / `ui_permesso_manage`:
>    - opzione A: `area = config` (la pagina vive in config, riusa l'area esistente)
>    - opzione B: nuova area `ui_admin` in `config.aree_funzionali` (separazione semantica, livelli area dedicati)
>    - opzione C: `area = amm_software` (azioni gestite solo da super-admin, ma allora la pagina non puo' essere accessibile a tenant admin via config)
> 2. **Profilo che riceve di default le 2 nuove azioni**:
>    - opzione A: profilo gia' seedato di "Tenant admin" (verificare se esiste in `config.profili_accesso`)
>    - opzione B: nessun seed di default, assegnazione manuale caso per caso da SUPER_ADMIN
>
> Influenzano solo il seed CSV iniziale di `config.azioni_processo` + eventuale `profili_accesso_azioni`. Modello DB invariato.

#### F.0 — Decisioni architetturali

| Tema | Decisione |
| ---- | --------- |
| **Split per natura** | Tabelle tecniche (`lista_definizione`, `lista_colonna`) → `amm-software` (SUPER_ADMIN). Tabelle operative (`lista_preset`, `lista_preset_colonna`, `lista_colonna_permesso`) → `config` (azione di processo dedicata, accessibile a tenant admin) |
| **App Django** | Estendere `apps.ui` con sotto-namespace admin (no nuova app — coerente con `apps.documenti.template_admin_service.py`). Endpoint sotto `/api/v1/ui/admin/...` |
| **Permessi** | Niente registrazione `ui` in `aree_funzionali` (decisione del Blocco C confermata). Per le 2 tabelle tecniche: `IsAdminZeroERP` (SUPER_ADMIN binding). Per le 3 operative: nuove azioni di processo `ui_preset_manage` + `ui_permesso_manage` in `config.azioni_processo` |
| **UI** | Pagina `gestione-personalizzazioni-liste` accessibile da entrambe le sidebar (config + amm-software). Render condizionale dei tab in base ai permessi: amm-software vede tutti e 4 i tab, config vede solo "Preset" + "Permessi colonne" |
| **Pattern** | Master-detail a la `ConfigurazioneDocumentiView`: header con `<Select>` "Lista corrente" (lookup `ui.lista_definizione`); i tab successivi sono filtrati su quella lista. TabView lazy PrimeVue |
| **Fase 1 minimal** | Implementare solo i 2 CRUD operativi (`lista_preset` + `lista_colonna_permesso`). Le 2 tabelle tecniche restano gestite via seed CSV in Fase 1 — passano a CRUD UI in Fase 2 quando emergerà l'esigenza concreta |
| **Lookup generico** | Aggiungere `ui.lista_definizione` a `_REL_CONSENTITE` in `apps/core/db/dbops_repository.py`. La fn `dbops.fn_get_lookup_codici` ammette tabelle senza `codice_interno` (fallback automatico — verificato in [docs/it/dbzero/dbops/funzioni/fn_get_lookup_codici.md](../../dbzero/dbops/funzioni/fn_get_lookup_codici.md)). `ui.lista_preset` no: serve filtro `lista_id` non supportato dal lookup generico → endpoint dedicato |

#### F.1 — Brief team DB (`dev/db-tid`)

Una micro-tranche seed:

1. **Azioni di processo** in `config.azioni_processo`:
    - `ui_preset_manage` (codice_interno) — area associata: `config` (perché la pagina vive in config; alternativa: una nuova area `ui_admin`, ma seguiamo il pattern delle azioni esistenti che si appoggiano ad aree esistenti)
    - `ui_permesso_manage` — idem
2. **Whitelist lookup**: aggiunta `ui.lista_definizione` in `_REL_CONSENTITE` lato Python (no SQL change — `fn_get_lookup_codici` già ammette il pattern).

Brief separato sarà scritto al momento dell'implementazione di F.

#### F.2 — Backend (`apps.ui` esteso)

Struttura attesa post-F1:

```text
apps/ui/
├── services/
│   ├── ui_service.py                        ✅ (Blocco C, runtime FE)
│   ├── lista_preferenza_service.py          ✅ (Blocco C, runtime FE)
│   ├── lista_preset_admin_service.py        🆕 F1 (CRUD preset + composizione)
│   └── lista_colonna_permesso_admin_service.py 🆕 F1 (CRUD permessi colonna)
└── api/
    ├── views.py                             ✅ (Blocco C, 4 endpoint runtime)
    └── views_admin.py                       🆕 F1 (CRUD admin endpoint)
```

Endpoint Fase 1:

| Endpoint | Permission | Scopo |
| -------- | ---------- | ----- |
| `GET /api/v1/ui/admin/liste/` | qualsiasi tenant admin con azione `ui_preset_manage` o `ui_permesso_manage` (pre-popola il Select header) | Lista delle `lista_definizione` attive (read-only, non protette: solo metadata) |
| `GET /api/v1/ui/admin/liste/<id>/preset/` | `ui_preset_manage` | Lista preset di una lista |
| `POST /api/v1/ui/admin/liste/<id>/preset/` | `ui_preset_manage` | Crea preset (ambito sistema/emittente/ruolo, FK condizionali validate dal CHECK DB) |
| `PATCH /api/v1/ui/admin/preset/<id>/` | `ui_preset_manage` | Modifica testata preset |
| `DELETE /api/v1/ui/admin/preset/<id>/` | `ui_preset_manage` | Elimina preset (ON DELETE SET NULL su `lista_preferenza_utente.preset_base_id` — DB-2 landed) |
| `PUT /api/v1/ui/admin/preset/<id>/colonne/` | `ui_preset_manage` | Sostituisce composizione `lista_preset_colonna` per il preset (atomico) |
| `GET /api/v1/ui/admin/liste/<id>/permessi/` | `ui_permesso_manage` | Lista permessi colonna per la lista |
| `POST /api/v1/ui/admin/permessi/` | `ui_permesso_manage` | Crea/aggiorna permesso (UPSERT su UNIQUE(colonna_id, profilo_accesso_id)) |
| `DELETE /api/v1/ui/admin/permessi/<id>/` | `ui_permesso_manage` | Elimina permesso (torna al default deny-list/allow-list) |

Tutti su `DomainAPIView` con `skip_area_check = True` + `post_permission` o `IsAdminZeroERP` secondo il caso.

#### F.3 — Frontend (`config` + `amm-software`)

Pagina condivisa `gestione-personalizzazioni-liste` (file: `src/config/views/GestionePersonalizzazioniListeView.vue`), inclusa nel router due volte:

- `/config/personalizzazioni-liste` (sidebar config, visibile con azione `ui_preset_manage` o `ui_permesso_manage`)
- `/amm-software/personalizzazioni-liste` (sidebar amm-software, visibile con SUPER_ADMIN)

La view legge `auth.isActionAllowed('ui_preset_manage')`, `auth.isActionAllowed('ui_permesso_manage')`, `auth.isAdmin` e renderizza i tab condizionalmente:

```text
TabView lazy
├── [SUPER_ADMIN]            "Definizione"      (Fase 2)
├── [SUPER_ADMIN]            "Catalogo colonne" (Fase 2)
├── [ui_preset_manage]       "Preset"           ← Fase 1
└── [ui_permesso_manage]     "Permessi colonne" ← Fase 1
```

Componenti previsti:

- `ListaCorrenteSelect.vue` — wrapper `LookupSelect rel="ui.lista_definizione"` con label "Lista corrente"
- `ListaPresetPanel.vue` — DataTable preset filtrata per lista_id + drawer create/edit + sub-drawer composizione colonne
- `ListaPresetDrawer.vue` — drawer testata preset (codice, descrizione, ambito + FK condizionali, pagina_dimensione, ordinamento_default, filtri_default)
- `ListaPresetColonneDrawer.vue` — sub-drawer per `lista_preset_colonna` (riordino, visibile, fissata, larghezza)
- `ListaColonnaPermessoPanel.vue` — DataTable permessi filtrata + drawer create/edit
- `ListaColonnaPermessoDrawer.vue` — drawer testata (colonna_id, profilo_accesso_id, livello_accesso enum)

#### F.4 — Out of scope per Fase 1

- CRUD `lista_definizione` e `lista_colonna` via UI: ~~rinviato a Fase 2~~ → **atterrato 2026-05-10 (DEF-5b)** sotto `/amm-software/personalizzazioni-liste-tecniche` come pagina tecnica SUPER_ADMIN-only. Vedi sezione `_def.md` DEF-5b per sintesi delivery + decisioni operative chiuse e `api_ui_admin_personalizzazioni.md` §12-§21 per il contratto endpoint.
- Validazione runtime di `vista_sql` / `campo_sorgente` lato BE Python: i trigger DB B1/B2 sono già la guardia finale; non servono validazioni Python aggiuntive.
- Versionamento dei preset: rinviato (ogni modifica sovrascrive; lo snapshot `preset_base_data_update` lato preferenza utente è già sufficiente per il badge "preset aggiornato" DEF-2).

---

### Sviluppi rinviati

Vedi documento separato: [sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md). DEF-5 ("Admin UI per gestione preset e catalogo") **viene assorbito dal Blocco F**: aggiornare DEF-5 quando F atterra.
