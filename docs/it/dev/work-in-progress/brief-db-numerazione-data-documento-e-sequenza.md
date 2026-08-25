# Brief DB — la data del documento e la sequenza del registro

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono**: nessuna riga
> di backend o frontend parte prima che i prerequisiti qui sotto siano applicati
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Analisi di riferimento:**
> [analisi-numerazione-fattura-data-e-sequenza.md](analisi-numerazione-fattura-data-e-sequenza.md)
> — lì ci sono le misure sui dati veri, le prove e il perché di ogni scelta.
> Questo documento è la **consegna**.
>
> **Origine:** Tid, 2026-08-25. La fattura 835 del 31/07 ha preso il numero 11
> quando il registro aveva già fatture di agosto. Le inversioni nel registro 3
> erano **tre**, non una.
>
> **Decisioni prese** (Tid, 2026-08-25): tutte quelle di §7 dell'analisi. Sono
> ricopiate in §1 qui sotto.
>
> **Bonifica dati: via libera.** Non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]): il cancello nasce restrittivo, senza
> fasi di compatibilità.
>
> ⭐ **Verifica tecnica eseguita il 2026-08-25** (team DB, sul DB vivo `dbdev` +
> doc auto-gen + `backend/` + `db/pgtap/`): **§10**. Il disegno regge; sono
> emersi **un difetto di concorrenza**, **due `DROP` non dichiarati**, **una
> premessa falsa** su un trigger, **una mina nel CSV dei registri** e cinque
> rettifiche minori. Ogni consegna toccata porta qui sotto un rimando
> `▶ §10 V-n`. **Nessuna riga di DB ancora scritta** (verificato: zero
> occorrenze dei nomi nuovi in `db/`, `backend/`, `frontend/`, `docs/it/dbzero/`).

---

## 1. Le decisioni, in una tabella

| # | Domanda | Decisione |
| --- | --- | --- |
| 1 | Bonifica dei dati esistenti | **Libera**: si sistemano, il cancello nasce restrittivo |
| 2 | `reset_policy` | **Solo `ANNUALE`**. `NESSUNA` e `MENSILE` escono dal CHECK: erano dichiarate e **non implementate** (§2) |
| 3 | Dove vive la regola della data | **Sul registro** (è il sezionale: numerazione e data stanno insieme), con una **data facoltativa sul lotto** che la scavalca |
| 4 | Quando l'operatore la vede e la corregge | **In due punti**: creazione del lotto *e* dialog «Rendi definitive» |
| 5 | Atto su N lotti | **Una data sola** per l'intero atto |
| 6 | Ordine del giro di numerazione | **Per data documento**, non per id di lotto |
| 7 | Stessa data dell'ultimo numerato | **Ammessa** (`>=`, non `>`) |

---

## 2. ⚠️ `reset_policy` non ha mai fatto niente

`vendite.registri_fatturazione.reset_policy` ammette `NESSUNA | ANNUALE |
MENSILE` (`chk_registri_fatturazione_reset`). Misurato il 2026-08-25:

* è letta in **due sole funzioni** (`fn_assign_numero_fattura`,
  `fn_numera_fattura_opz_emessa`), e **solo** per calcolare il `mese` del
  `RETURNS TABLE`;
* quel `mese` **nessuno lo legge**: il repository fa
  `cursor.execute("SELECT vendite.fn_numera_fattura_opz_emessa(%s)")` e non
  tocca il risultato; zero occorrenze di `reset_policy` in `backend/` e in
  `frontend/`;
* `fn_get_anno_registro(p_data)` **non riceve nemmeno il registro**: torna
  sempre l'anno solare. La chiave del contatore è
  `(registro, anno, mese, serie)` con `v_mese SMALLINT := 0` **fisso**, e
  `uq_fatture_numero` non contiene il mese.

Quindi oggi: `ANNUALE` funziona per come è fatta la chiave, `NESSUNA` si
comporta **come `ANNUALE`** (riparte lo stesso a gennaio) e `MENSILE` pure — e
se qualcuno la implementasse a metà finirebbe in violazione di UNIQUE.

**Un catalogo che promette tre comportamenti e ne fa uno è peggio di un catalogo
con una voce sola**: prima o poi qualcuno sceglie `MENSILE` e si aspetta che
funzioni. Si riduce il CHECK ad `ANNUALE` e si toglie il `mese` dai `RETURNS`
delle due funzioni.

❓ **Domanda al team DB** (D-1): la colonna
`registri_fatturazione_progressivi.mese`, sempre `0` e dentro la chiave del
contatore, si lascia o si toglie? Lasciarla è debito silenzioso; toglierla
significa rifare la chiave di una tabella tecnica. Propendo per **lasciarla**,
con un commento che dica che è ferma a 0 finché `MENSILE` non esiste — ma la
scelta è vostra, è casa vostra.

✅ **Risposta del team DB (2026-08-25): si lascia**, con un `COMMENT ON COLUMN`.
Toglierla significa rifare **quattro** oggetti misurati sul DB —
`uq_regprog_key (registro_id, anno, mese, serie)`,
`uq_registri_progressivi_scope (registro_id, anno, COALESCE(mese,0), COALESCE(serie,''))`,
il CHECK `chk_regprog_mese_valid` e il corpo di `fn_get_next_progressivo` — per
due byte. E il giorno in cui `MENSILE` servisse davvero, la chiave c'è già.
⚠️ Nel farlo si nota che **quei due UNIQUE sono lo stesso vincolo**: `mese` e
`serie` sono `NOT NULL`, quindi i `COALESCE` del secondo non fanno niente e
l'indice è un gemello con espressioni (linee-guida-sql §8.6). Non è di questo
cantiere, ma se si tocca la tabella per `ultima_data` è il momento di
nominarlo. ▶ §10 V-12.

⚠️ **Nessuna bonifica dati serve per il CHECK ristretto**: misurato il
2026-08-25, **tutti e 6** i registri sono già `ANNUALE`. ▶ §10 V-6.

---

## 3. Il modello bersaglio in una frase

> Il **registro** dice come si numera **e** che data porta il documento. La data
> si calcola da sola alla creazione del lotto, si vede e si può correggere al
> momento di numerare, e il **cancello** — dentro la funzione che consegna il
> numero, **sotto l'advisory lock** — rifiuta qualunque data precedente
> all'ultima già emessa in quel sezionale.

---

## 4. Le consegne

### DB-1 — parametro di fuso orario

`config.parameters` (append al CSV, mai `INSERT` a parte — AGENTS.md §80_data):

| code | default_value | description |
| --- | --- | --- |
| `SYSTEM_FUSO_ORARIO` | `Europe/Rome` | Fuso orario dell'azienda: la «data di oggi» dei documenti si calcola qui, non nel fuso della sessione. |

⭐ **Dove, in concreto** (verificato 2026-08-25): append a
`80_data/sql/config/parameters.csv`, **id 54** (`max(id)` in `config.parameters`
è 53). Quel CSV è stato confrontato riga per riga col DB ed è **allineato**:
appenderci una riga fa ri-girare il suo mirror senza regredire nulla. ▶ §10 V-8.

### DB-2 — `script.fn_data_operativa()`

```sql
RETURNS date  -- STABLE
  (now() AT TIME ZONE (SELECT default_value FROM config.parameters
                        WHERE code = 'SYSTEM_FUSO_ORARIO'))::date
```

⛔ **Fail-loud** se il parametro manca o è vuoto: `E_CONFIG_MANCANTE`, mai un
fallback silenzioso a UTC — è esattamente il difetto che stiamo chiudendo.
⭐ Verificato: `E_CONFIG_MANCANTE` esiste, classe **`TECNICO`** (500), messaggio
`Configurazione mancante: %s` — un segnaposto, e ciò che ci va dentro è
`SYSTEM_FUSO_ORARIO`, cioè una **chiave che un amministratore può creare**, non
il nome di un parametro PL/pgSQL. Su un `TECNICO` la chiave `campo` **non** si
emette. E `config.parameters.default_value` è `NOT NULL` ma **senza CHECK di non
vuoto**: il ramo «c'è ma è stringa vuota» è raggiungibile davvero, non teoria.

⛔ **Legge il `default_value`, e questa è una scelta da scrivere nel `COMMENT`.**
Esiste già il lettore canonico dei parametri —
`script.fn_get_parameter_full(p_code, p_emittente_fiscale_id, p_django_user_id,
p_group_ids, p_session_key, p_function_name, p_categoria_cliente_id)` — che
risolve la cascata di `config.parameter_overrides` (utente → gruppo → emittente
→ default). **Qui non si usa apposta**: un override per utente o per sessione
farebbe portare alla *stessa* fattura date diverse a seconda di chi la genera,
cioè il difetto che questo cantiere chiude. Senza questa frase scritta, il
prossimo "corregge" la funzione verso il building block e riapre il buco.
▶ §10 V-9.

**Perché serve.** `current_date` segue il fuso **della sessione**, e la sessione
di Django è in **UTC** (`USE_TZ = True` senza `TIME_ZONE` in `DATABASES`;
verificato in vivo: `SHOW timezone` → `UTC`). Ogni documento generato fra la
mezzanotte e le 02:00 locali porta **la data del giorno prima** — è così che la
835 ha preso il 31/07 essendo nata l'01/08 alle 01:09. E lo stesso oggetto dà
date diverse a seconda del canale: da psql e da pgAgent il fuso è
`Europe/Rome`.

⚠️ **Perimetro.** Qui `fn_data_operativa` sostituisce `current_date` **solo**
sul percorso della data fattura (DB-5, DB-6) e nel default di colonna di
`vendite.fatture.data`. `CURRENT_DATE` è default in **25 tabelle** e compare in
**67 funzioni**: la bonifica generale è un cantiere suo, e va aperta subito
dopo. Anche l'ipotesi «metto `TIME_ZONE` in `DATABASES` e sistemo tutto con una
riga» appartiene a quel cantiere: ha un raggio d'azione su tutta
l'applicazione e vuole una verifica sua, non un effetto collaterale di questo.

### DB-3 — la politica sul registro

```sql
ALTER TABLE vendite.registri_fatturazione
  ADD COLUMN politica_data_documento varchar(32) NOT NULL DEFAULT 'OGGI';
-- CHECK: politica_data_documento IN ('OGGI', 'FINE_MESE_COMPETENZA')
```

| valore | data del documento |
| --- | --- |
| `OGGI` | `script.fn_data_operativa()` — fattura immediata |
| `FINE_MESE_COMPETENZA` | ultimo giorno di `lotto.competenza_mese` (competenza `2026-07-01` → **`2026-07-31`**) — fattura differita |

⚠️ **`FINE_MESE_COMPETENZA` e il cancello di DB-8 collidono per costruzione, e
non è un difetto: è il comportamento normale della differita in ritardo.** Un
lotto di competenza **arretrata** lavorato oggi prende la data di fine di quel
mese, che è anteriore all'ultimo numero già emesso: il cancello lo rifiuta
**sempre**, e l'operatore deve ridichiarare la data dal dialog (DB-11) ogni
volta. Non è teoria — misurato il 2026-08-25: **4 lotti** hanno competenza
giugno e fatture datate luglio/agosto (7515, 7133, 7132, 151), e il 7133 porta
la fattura **18848, già numerata** il 23/08.
⭐ Conseguenza operativa: la `minDate` di DB-10 **non è un abbellimento del
frontend**, è ciò che rende vivibile questa politica. E al collaudo il rifiuto
va spiegato come atteso, o verrà letto come un bug. ▶ §10 V-7 e **D-2**.

⭐ **Perché sul registro e non sul lotto.** Il registro *è* il sezionale: è lì
che vive la sequenza, e la regola della data deve stare accanto alla regola del
numero, altrimenti si può configurare un registro la cui data litiga con la sua
numerazione. E c'è un guadagno che la colonna sul lotto non dava: **un lotto può
contenere documenti di registri diversi** — la natura instrada la nota di
credito su un registro suo (`fn_build_fattura_key` → `fn_get_registro_id`).
Con la regola sul registro ogni documento prende la data giusta **da sé**.

❓ **Seed da confermare** (D-2). Proposta:

| registro | politica proposta |
| --- | --- |
| 3 `Front-office`, 1359 `Front-office-159` | `OGGI` |
| 4 `Back-office`, 1360 `Back-office-159` | `FINE_MESE_COMPETENZA` |
| 5 `NC`, 1361 `NC-159` | `OGGI` (una nota di credito porta la data del giorno in cui la si emette) |

⛔ **Il seed NON va in `80_data/sql/vendite/registri_fatturazione.csv`, e il
motivo è una mina.** Quel CSV contiene **solo** i registri 3/4/5 (1359/1360/1361
non ci sono: li ha creati `20260819-05` con un `INSERT ... SELECT`) e dice
`emittente_soggetto_ruolo_id = NULL`, mentre nel DB i sei registri sono
**intestati a 72 / 159** dallo stesso changeSet. Il suo mirror
(`20260127-09-upsert-registri-fatturazione`) è `runOnChange: true`: **oggi dorme
perché il file non cambia**, ma il primo che tocca quel CSV lo sveglia, e la
ri-lettura riporta i registri 3/4/5 a emittente `NULL` — cioè riapre il difetto
C-4 che `20260819-05` ha chiuso (`fn_get_registro_id` tornerebbe a risolvere sul
fallback generico). Un cantiere sulla numerazione che spegne l'intestazione dei
sezionali è il modo peggiore di sbagliare.

⭐ **La via**: un CSV **dedicato** — `80_data/sql/vendite/registri_fatturazione_politica_data.csv`
con le sole colonne `id,politica_data_documento` e sei righe, più un
`loadUpdateData` nuovo su `primaryKey: id`. È il pattern già in uso nel repo per
lo stesso scopo (`tipi_doc_fiscale_registri.csv` +
`tipi_doc_fiscale_registri_nota_credito.csv`; `parameters*.csv` su cinque file):
la sede resta un CSV — AGENTS §80_data è rispettato — non si tocca un changeSet
già mergiato, e la mina resta dov'è invece di esplodere addosso a noi.

⚠️ **La mina va comunque nominata**, perché non sparisce: `registri_fatturazione.csv`
è **stantìo su `emittente_soggetto_ruolo_id`** e gli mancano tre righe. Chiunque
lo tocchi per qualunque ragione fa saltare l'intestazione. ▶ **D-3** in §10.

### DB-4 — la data dichiarata sul lotto

```sql
ALTER TABLE vendite.fatturazione_lotti
  ADD COLUMN data_documento date NULL;
```

**Facoltativa**: vuota → vince la politica del registro; valorizzata → vince
lei, per tutti i documenti del lotto. È anche il posto dove atterra la data
digitata nel dialog «Rendi definitive» (DB-11).

### DB-5 — `vendite.fn_calcola_data_documento`

```sql
fn_calcola_data_documento(p_registro_id bigint,
                          p_competenza_mese date,
                          p_data_dichiarata date DEFAULT NULL) RETURNS date
```

```
COALESCE(
  p_data_dichiarata,
  CASE politica
    WHEN 'FINE_MESE_COMPETENZA'
      THEN (date_trunc('month', p_competenza_mese) + interval '1 month - 1 day')::date
    ELSE script.fn_data_operativa()
  END)
```

Guard sugli id secondo linee-guida (`NULL` o `<= 0` → errore, niente
normalizzazione silenziosa). ⚠️ `p_competenza_mese` è obbligatoria quando la
politica è `FINE_MESE_COMPETENZA`: senza, si solleva, non si ripiega su oggi —
un ripiego qui darebbe una data plausibile e sbagliata.

### DB-6 — `fn_get_or_create_fattura_header` smette di usare `current_date`

Oggi:

```sql
INSERT INTO vendite.fatture (registro_id, data, ...)
VALUES (v_registro_id, current_date, ...)
```

Bersaglio: leggere `competenza_mese` e `data_documento` dal lotto (la funzione
ha già `p_lotto_id`) e scrivere
`vendite.fn_calcola_data_documento(v_registro_id, v_competenza_mese, v_data_dichiarata)`.

⚠️ **È l'unico punto in tutto il repo che scrive `vendite.fatture.data`.**
Verificato con grep su `docs/it/dbzero/*/funzioni/` e su `backend/`: nessun'altra
funzione, nessun endpoint, nessuna schermata. Cambiarlo qui cambia il
comportamento ovunque.

### DB-7 — la memoria della sequenza

```sql
ALTER TABLE vendite.registri_fatturazione_progressivi
  ADD COLUMN ultima_data date NULL;   -- data dell'ultimo numero emesso su questa riga
```

⭐ **Perché qui e non su `vendite.fatture`.**
`registri_fatturazione_progressivi` **non ha RLS** (verificato su
`pg_class.relrowsecurity`: `f`), mentre `vendite.fatture` ce l'ha, per
whitelist emittente. Un cancello che leggesse il massimo da `fatture` sotto un
perimetro ristretto riceverebbe `NULL` e direbbe **«via libera» proprio quando
non sa** ([[feedback_rls_conteggio_zero_non_e_un_dato]]). Sul contatore il dato
è sempre completo, è `O(1)`, ed è su una riga che il cancello **ha già
bloccato**.

Backfill dopo la bonifica (§6).

### DB-8 — ⭐ il cancello

**Dentro `vendite.fn_get_next_progressivo`, DOPO `pg_advisory_xact_lock`.**

```
… pg_advisory_xact_lock(registro | anno | serie)      ← già esistente
    v_max := (SELECT max(rp.ultima_data)
                FROM vendite.registri_fatturazione_progressivi rp
               WHERE rp.registro_id = p_registro_id
                 AND rp.serie       = v_serie)         ← ATTRAVERSO GLI ANNI
    IF v_max IS NOT NULL AND p_data < v_max THEN
        E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO
    END IF
… UPDATE last_numero = v_next,
         ultima_data = GREATEST(COALESCE(ultima_data, p_data), p_data)
```

⛔ **Sotto il lock, e non è un dettaglio.** Un controllo letto *prima* del lock è
soggetto a corsa: due transazioni leggono lo stesso massimo, passano entrambe,
poi si serializzano sul contatore e producono l'inversione che il cancello
doveva impedire. Sotto il lock, lettura e incremento sono lo stesso atto.

⭐ **Ed è l'unico punto non aggirabile.** Le vie che consumano un numero sono
**tre** — lotto singolo (`numera_lotto`), atto per competenza (job
`FATTURAZIONE_NUMERA`) e **il backstop del worker di stampa**
(`numera_fattura_backstop`), che numera senza nessun operatore davanti. Tutte e
tre passano di qui.

⚠️ **Il massimo si prende attraverso gli anni**, non sulla riga del contatore
dell'anno corrente: altrimenti un documento retrodatato al 31/12 dell'anno
scorso finirebbe nel contatore dell'anno scorso e passerebbe indisturbato,
aprendo un numero in un anno già chiuso.

⛔ **RETTIFICA (verifica 2026-08-25) — così com'è scritto, il cancello resta
aggirabile proprio in quel caso.** L'advisory lock esistente è
`pg_advisory_xact_lock(hashtext('registri_fatturazione_progressivi'),
hashtext(registro || '|' || anno || '|' || serie))`: **la chiave del lock porta
l'ANNO**, e il `FOR UPDATE` blocca la sola riga di contatore del proprio anno.
Il cancello invece legge il massimo **su tutti gli anni**. Due transazioni con
date in anni diversi sullo stesso `(registro, serie)` prendono quindi **lock
diversi**, leggono lo stesso massimo, passano entrambe e producono l'inversione
cross-anno — che è esattamente il caso che il ⚠️ qui sopra dichiara di
impedire. Il perimetro del lock deve coincidere col perimetro del cancello.

⭐ **Rimedio: togliere l'anno dalla chiave del lock** —
`hashtext(p_registro_id::text || '|' || v_serie)`, restando nella forma a due
argomenti (namespace + chiave). Il costo è serializzare fra anni diversi dello
stesso sezionale, cioè qualche transazione a cavallo di Capodanno; la
correttezza di `last_numero` non ne dipende comunque, perché la riga del
contatore è presa `FOR UPDATE`. È un **restringimento**, non un cambio di
semantica. ▶ §10 V-1.

⚠️ **La chiave è `(registro_id, serie)`, non il solo registro.** Il modello
ammette **due serie sullo stesso registro** — `tipi_doc_fiscale_registri` mappa
`(tipo_doc, natura) → (registro, serie)` e la sua UNIQUE lo consente apposta.
Sul solo registro, due sequenze indipendenti si bloccherebbero a vicenda.

⛔ **Firma: serve un `DROP FUNCTION` prima del `CREATE`.** L'errore deve portare
il **bersaglio** sulla fattura, e la funzione oggi non sa quale sia. La firma
diventa
`(p_registro_id bigint, p_data date, p_serie text DEFAULT NULL, p_fattura_id bigint DEFAULT NULL)`.
`CREATE OR REPLACE` non può aggiungere parametri: creerebbe una **seconda**
funzione, e con i default le due sarebbero **ambigue su tre argomenti**
([[feedback_overload_ambiguo_default]]). Il `DROP` è sicuro: il chiamante è
**uno solo**, `fn_assign_numero_fattura` (verificato).

✅ **Riverificato il 2026-08-25 su quattro fronti**, non solo su `pg_proc`:
`pg_proc` (solo `fn_assign_numero_fattura`), `backend/**.py` (zero chiamate),
`db/pgtap/` (solo `test-registri-progressivi.sql`, **con argomenti nominati** →
compatibile con la firma nuova) e le viste. Firma esatta da droppare:
`vendite.fn_get_next_progressivo(bigint, date, text)`. Dopo il `CREATE`,
verificare con `pg_get_function_identity_arguments` che non sia nato un
overload.

⚠️ **E il chiamante va aggiornato nello stesso giro**: `fn_assign_numero_fattura`
oggi chiama `fn_get_next_progressivo(v_registro_id, v_data, v_serie)` e deve
passare anche `p_fattura_id`, altrimenti il bersaglio di DB-9 è sempre `NULL` e
il pulsante «vai al documento» non nasce mai. Il brief dava per implicita questa
riga: adesso è scritta.

⭐ **Mentre la si riscrive, il messaggio esistente va sistemato** (AGENTS:
«toccando una funzione vecchia, il messaggio va guardato»). Oggi
`fn_get_next_progressivo` solleva `E_PARAMETRO_INVALIDO` con nel `VARIADIC`
la stringa `'p_registro_id e p_data obbligatori'` — cioè **nomi di parametro
PL/pgSQL dentro la frase che legge una persona**, l'antipattern che AGENTS.md
descrive per esteso. E il guard copre solo `IS NULL`, non `<= 0` come le
linee-guida pretendono sugli id. ▶ §10 V-11.

### DB-9 — il codice errore

~~`config.codici_errore.csv` + `config.messaggi_errore.csv` (append ai CSV; primo
id libero: **988**).~~

⛔ **RETTIFICA (verifica 2026-08-25).** Due errori in una riga:

1. **`config.codici_errore` non ha una colonna `id`** — la chiave è `codice`
   (colonne: `codice, classe, obsoleto_dal, note`). L'id esiste solo su
   `config.messaggi_errore`.
2. **988 è occupato**: è `E_PAGAMENTI_VALIDATION`, entrato oggi stesso col
   cantiere incassi (S5-1). `max(id)` = 988 → **il primo libero è 989**, e va
   riletto un'ultima volta prima di scrivere il file, perché due cantieri stanno
   appendendo allo stesso CSV nella stessa giornata.

Resta valido tutto il resto: append ai due CSV, **mai un loader nuovo** (i
mirror `runOnChange` esistenti ripescano il file), e i due CSV sono **allineati
col DB** (`data_update` di stamattina su tutte le righe: il loader ha girato).

| campo | valore |
| --- | --- |
| codice | `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` |
| classe | **`DATO_ERRATO`** — la data la sceglie una persona, in un dialog, e può correggerla |
| messaggio | *«La data del documento è anteriore all'ultimo numero già emesso su questo registro, che porta la data %s.»* |
| `VARIADIC` | **la data dell'ultimo numerato** — l'unico dato che serve a scegliere quella giusta. Nessun id, nessun nome di colonna |
| `context.campo` | `data_documento` — il campo da accendere |
| `context.bersaglio` | `[{FATTURA, p_fattura_id}, {FATTURA, <ultima numerata del sezionale>}]` |
| context (diagnosi) | `registro_id`, `serie`, `ultima_data`, `data_richiesta` |

⚠️ Il secondo bersaglio si emette **solo se la fattura è visibile** a chi opera:
a un documento che non si può aprire non si manda nessuno (§4.3 del brief
bersaglio). Il primo c'è sempre.

⚠️ **«L'ultima numerata» si sceglie per DATA, non per numero.** Il contatore
tiene solo `ultima_data`, non l'id della fattura: bisogna andarla a cercare in
`vendite.fatture`. Se la si prende con `ORDER BY numero DESC LIMIT 1`, nei
registri che hanno **inversioni già scritte** — cioè il registro 3, oggi — il
pulsante punterebbe a un documento con una data **diversa** da quella che la
frase nomina, e il messaggio si contraddirebbe da solo. Va presa quella con
`data = v_max`. ⭐ E la query gira **solo nel ramo d'errore**, come già fa
`fn_numera_fattura_opz_emessa`: sul percorso felice non deve costare niente.
La RLS su `vendite.fatture` fa da sé il filtro di visibilità (la funzione è
`SECURITY INVOKER`, verificato). ▶ §10 V-10.

⚠️ **`context.campo`**: qui `data_documento`, in §6.B dell'analisi `data`. Vince
questo brief — il campo che il frontend accende è quello del dialog, non la
colonna di `vendite.fatture` — ma la divergenza va sanata **nell'analisi**, o
qualcuno la riporterà indietro.

⚠️ **Ripiego senza `%s`** da registrare insieme al codice, e policy rigenerate:
il segnaposto a catalogo è la ragione del ripiego
([[feedback_ripiego_ogni_codice_vivo]]).

### DB-10 — la data minima, in lettura

```sql
vendite.fn_get_data_minima_numerabile(p_registro_id bigint, p_serie text) RETURNS date
vendite.fn_get_data_minima_numerabile_lotto(p_lotto_id bigint)            RETURNS date
```

La seconda aggrega la prima su tutti i `(registro, serie)` toccati dalle fatture
**non ancora numerate** del lotto, e ne prende il massimo.

**A che serve:** il FE apre il DatePicker con `minDate` già giusto e l'errore di
DB-8 diventa l'eccezione, non la norma. Il cancello resta il cancello; questa è
la targa che dice quanto è alto.

⛔ **La serie va risolta come la risolve chi numera, o la targa dice il falso.**
`fn_assign_numero_fattura` cerca il contatore con
`COALESCE(f.serie, r.serie_default, '')`. Misurato il 2026-08-25: **tutte e sei**
le fatture non ancora numerate hanno `f.serie IS NULL`, e la serie effettiva
arriva dal `serie_default` del registro (`R2` sul 3, `R1` sul 4). Una funzione
di lettura scritta con `COALESCE(f.serie, '')` cercherebbe la riga di contatore
della serie vuota, **non la troverebbe**, e restituirebbe `NULL` — cioè
«nessun minimo», la risposta più permissiva possibile, proprio dove il cancello
poi rifiuta. Vale identico per il guard di DB-11. ▶ §10 V-5.

⚠️ **`fn_get_data_minima_numerabile_lotto` legge sotto RLS** (`vendite.fatture`
ce l'ha; il contatore no): a un operatore con whitelist ristretta può sfuggire
un `(registro, serie)` e la `minDate` esce **più bassa** del vero. È
accettabile perché il cancello di DB-8 resta l'autorità — questa è una targa,
non un lucchetto — ma va scritto nel `COMMENT`, altrimenti il giorno in cui
qualcuno userà questa funzione *al posto* del cancello nessuno saprà che è
fail-open.

### DB-11 — dichiarare la data

```sql
vendite.fn_imposta_data_documento_lotto(p_lotto_id bigint, p_data date)
  RETURNS TABLE(aggiornate integer, saltate_numerate integer)
```

1. guard: `p_data >= fn_get_data_minima_numerabile_lotto(p_lotto_id)` →
   altrimenti **lo stesso codice di DB-8**, sollevato qui, subito, invece che a
   metà giro;
2. `UPDATE vendite.fatturazione_lotti SET data_documento = p_data`;
3. `UPDATE vendite.fatture SET data = p_data` sulle fatture del lotto **in
   `DRAFT` o `EMESSA`** ~~(la finestra oltre la quale
   `trgfn_fattura_satellite_guard_congelamento` congela tutto)~~;

   ⛔ **RETTIFICA (verifica 2026-08-25) — quella parentesi è falsa, e la falsità
   è più grave della frase.** Misurato su `pg_trigger`:
   `trgfn_fattura_satellite_guard_congelamento` è agganciata a `vendite.fatture`
   con `BEFORE UPDATE **OF emittente_snapshot, cliente_snapshot**` — e basta.
   Su `fatture_indirizzi` e `fatture_scadenze` copre tutti gli eventi, sulla
   **testata no**. Quindi oggi un `UPDATE vendite.fatture SET data = …` su una
   fattura **numerata e DEFINITIVA passa senza che nulla lo fermi**.
   Il filtro `DRAFT|EMESSA` di questo punto 3 resta giusto, ma è una regola che
   la funzione si dà da sola: **non c'è nessun cancello sotto**. ▶ **DB-14**.
4. ⛔ **rigenerare il piano rate** — `fn_genera_scadenze_fattura` per ogni
   fattura toccata;
5. le fatture **già numerate** si **saltano** e si contano.

⛔ **Il punto 4 non è opzionale.** Le scadenze si calcolano da `f.data`
(`v_data_rata := v_data + offset`) nello step **EMESSA**, cioè **prima** del
numero; e il guard D-K, prima di consumare il progressivo, verifica che
Σ rate = `totale_a_pagare`. Cambiare la data senza rigenerare le rate produce
scadenze sbagliate su un documento che il guard lascia passare o rifiuta per il
motivo sbagliato. `fn_genera_scadenze_fattura` cancella e riscrive, ed è
ammessa fino a `EMESSA`: la rigenerazione è pulita.

⚠️ **Perché saltare e non rifiutare** al punto 5: il caso «lotto numerato a
metà» **esiste nei dati** — i lotti 4212 e 4213 hanno fatture numerate in giorni
diversi. Rifiutare l'intero lotto renderebbe irrisolvibile proprio il caso per
cui questa funzione esiste. Il conteggio restituito lo dice al chiamante, che lo
mostra.

### DB-12 — `reset_policy` a una voce sola

* `chk_registri_fatturazione_reset` → solo `'ANNUALE'`. ✅ Nessuna riga da
  bonificare: i 6 registri sono già tutti `ANNUALE`.
* `mese` fuori dal `RETURNS TABLE` di `fn_assign_numero_fattura` e
  `fn_numera_fattura_opz_emessa`, e via il `CASE WHEN v_reset = 'MENSILE'`.
  Nessun consumatore lo legge (§2): il BE drena il result set senza guardarlo.

  ⛔ **RETTIFICA (verifica 2026-08-25): servono DUE `DROP FUNCTION` che il brief
  non nominava.** Togliere una colonna dal `RETURNS TABLE` **non** è un
  `CREATE OR REPLACE`: PostgreSQL risponde *«cannot change return type of
  existing function»*. Entrambe le funzioni tornano
  `TABLE(registro_id bigint, anno smallint, mese smallint, serie varchar,
  numero bigint)`, quindi entrambe vanno `DROP` + `CREATE`, con la firma esatta:
  * `vendite.fn_numera_fattura_opz_emessa(bigint, boolean, character varying)`
  * `vendite.fn_assign_numero_fattura(bigint)`

  ✅ **I consumatori reggono, verificati uno per uno** (era il presupposto di §2,
  ora è misurato): `pipeline_repository.py:1960` chiama in forma scalare e non
  legge nulla; `:2106` fa `SELECT * FROM …` e poi `cursor.fetchall()` per drenare;
  i pgTAP (`test-numera-fattura-opz-emessa.sql`,
  `test-numera-nota-credito-riferimento-v1.sql`) leggono **per nome di colonna**
  (`numero`) o fanno `PERFORM`. Nessuno legge per posizione, nessuno nomina
  `mese`.

  ⚠️ Togliendo `mese` sparisce anche l'ultimo uso di `reset_policy` dentro
  `fn_numera_fattura_opz_emessa`: la variabile `v_reset` e il `JOIN` sul registro
  che la portava vanno via con lei.
* colonna `registri_fatturazione_progressivi.mese`: vedi **D-1** — **si lascia**.

### DB-14 — ⭐ la porta di servizio: `fatture.data` non è congelata da nessuno

**Nasce dalla verifica del 2026-08-25** (▶ §10 V-3), e senza di essa questo
cantiere costruisce un cancello sull'ingresso principale lasciando aperto il
retro.

Oggi, misurato su `pg_trigger`: nessun trigger su `vendite.fatture` presidia la
colonna `data`. `trgfn_fattura_satellite_guard_congelamento` c'è, ma con
`UPDATE OF emittente_snapshot, cliente_snapshot`. Quindi un `UPDATE` diretto —
da un service, da uno script di riparazione, da una funzione futura — può
spostare la data di una fattura **già numerata**, e con essa l'anno del
sezionale, dopo che il cancello di DB-8 ha fatto il suo lavoro.

```sql
-- trigger di fase a10, BEFORE UPDATE OF data
trg_fatture_a10_guard_data_numerata_upd  →  vendite.trgfn_fatture_guard_data_numerata()
```

Regola: **se `OLD.numero IS NOT NULL` e `NEW.data IS DISTINCT FROM OLD.data`, si
rifiuta.**

⛔ **Il discriminante è il NUMERO, non lo stato**, e non è un dettaglio:
`fn_numera_fattura_opz_emessa` assegna il numero **mentre** la fattura è in
`EMESSA` (lo stato passa a `DEFINITIVA` dopo, nella finalizzazione dello step).
Una soglia scritta sugli stati `DRAFT|EMESSA` lascerebbe quindi una finestra
reale in cui la fattura ha un numero fiscale e la data è ancora scrivibile —
che è esattamente il buco da chiudere.

⚠️ **Verificare i test esistenti prima** ([[feedback_guard_breaks_existing_tests]]):
un `BEFORE UPDATE` nuovo su `vendite.fatture` entra in una tabella che ha già
**17 trigger**, e i `_a10_` girano in ordine alfabetico. Il nome sopra si
colloca fra `trg_fatture_a10_guard_actual...` e `trg_fatture_a10_guard_emittente_scope`:
nessuna sovrapposizione di colonna, ma un `grep` sui pgTAP che scrivono su
`vendite.fatture` va fatto lo stesso.

⚠️ Codice errore: **non serve conio**. `E_COLONNA_NON_MODIFICABILE` è già in uso
sulla stessa tabella (`trg_fatture_a10_lock_natura_doc_upd`) ed è la stessa
semantica. Da verificare la sua arità prima di riusarlo.

---

### DB-13 — pgTAP

Estendere `db/pgtap/vendite/test-registri-progressivi.sql` e
`test-numerazione-guard-coerenza-v1.sql`. Casi minimi:

1. data **uguale** all'ultima numerata → **passa** (è il caso più comune);
2. data **anteriore** → `throws_ok` con SQLSTATE `'P0001'` **e** `throws_like`
   sulla frase (la frase è la posta in gioco: dice la data da cui ripartire);
3. **cross-anno**: numerata al 2026-01-05, si tenta il 2025-12-31 → rifiutata,
   anche se il contatore 2025 è un altro;
4. **due serie sullo stesso registro** non si bloccano a vicenda;
5. `ultima_data` aggiornata a ogni numero emesso;
6. `FINE_MESE_COMPETENZA` su competenza `2026-07-01` → `2026-07-31`;
7. `lotto.data_documento` valorizzata **vince** sulla politica del registro;
8. `fn_imposta_data_documento_lotto` **rigenera** le scadenze (prima/dopo sulle
   date delle rate) e **salta** una fattura già numerata;
9. `fn_data_operativa` con parametro mancante → solleva, non ripiega.

⭐ **Quattro casi in più, dalla verifica del 2026-08-25** (senza di questi il
file è verde su ciò che non è mai stato il problema):

* **10)** **`fn_data_operativa` col parametro presente ma VUOTO** → solleva. Il ramo è
    raggiungibile: `config.parameters.default_value` è `NOT NULL` ma senza CHECK
    di non-vuoto, e nel CSV ci sono già due parametri a stringa vuota.
* **11)** **la serie che arriva dal `serie_default`** — una fattura con
    `f.serie IS NULL` su un registro con `serie_default = 'R2'` dev'essere
    fermata dal contatore di `R2`, non ignorata. È la forma di **tutte e sei** le
    fatture non numerate di oggi: senza questo caso, DB-10/DB-11 possono nascere
    con la `COALESCE` sbagliata e i test non se ne accorgono.
* **12)** **DB-14**: `UPDATE vendite.fatture SET data = …` su una fattura **numerata**
    → `throws_ok` con `'P0001'`. E la controprova: su una **non** numerata passa.
* **13)** **il cancello sotto lock non è verificabile con un pgTAP** — vale la stessa
    lezione già scritta in testa a `test-numerazione-guard-coerenza-v1.sql`
    (§«cosa questo file NON può provare»): la posizione rispetto all'advisory
    lock si presidia **in review**, non con un'asserzione. Va scritto nel file,
    o il prossimo crederà che sia coperta.

⚠️ Preambolo obbligatorio (`BEGIN`, contesto operatore,
`SET CONSTRAINTS ALL IMMEDIATE`) e baseline
(`scripts/pgtap-baseline.sh vendite`) prima di attribuirsi un rosso.

✅ **Stato di partenza dei file da estendere, verificato**: nessuno dei quattro
(`test-registri-progressivi`, `test-numerazione-guard-coerenza-v1`,
`test-numera-fattura-opz-emessa`, `test-numera-nota-credito-riferimento-v1`)
compare in `baseline-rossi.tsv` né in `baseline-rossi-ci.tsv`: **partono verdi**,
quindi un rosso dopo la modifica è nostro.

✅ **E il cancello non li rompe**: `test-registri-progressivi.sql` numera
`2025-12-31`, `2025-12-31`, `2026-01-01` — sequenza **monotòna**, passa. Usa
argomenti nominati (`p_registro_id =>`, `p_data =>`, `p_serie =>`), quindi
sopravvive anche al cambio di firma.

---

## 5. Ordine di applicazione

```
DB-1 ─► DB-2 ─┐
DB-3 ─────────┼─► DB-5 ─► DB-6        (la data nasce giusta)
DB-4 ─────────┘
DB-7 ─► [bonifica §6] ─► DB-8 ─► DB-9 ─► DB-10 ─► DB-11   (il cancello)
DB-12, DB-13 in coda
```

⛔ **DB-8 dopo la bonifica**, non prima: acceso sui dati attuali blocca ~~**6**~~
**3** fatture `EMESSA` legittime (§6).

### 5-bis. Il piano operativo, file per file (verifica 2026-08-25)

⚠️ **La numerazione parte da `20260825-02`**: `20260825-01` esiste già
(`recreate-fn-get-saldo-fattura-tre-numeri`). La sequenza è **globale per data
fra tutte le cartelle**, non per cartella
([[feedback_liquibase_numerazione_globale_per_data]]).

| Lotto | # | Cartella | File (proposto) | Consegna |
| --- | --- | --- | --- | --- |
| **0** | — | — | *bonifica dati a mano* (§6) | prerequisito del lotto B |
| **A** | 02 | `80_data` | `…-seed-parameter-system-fuso-orario-` + append a `parameters.csv` (id 54) | DB-1 |
| A | 03 | `20_code` | `…-create-fn-data-operativa-` | DB-2 |
| A | 04 | `00_schema` | `…-alter-registri-politica-data-documento-` (colonna + CHECK + `COMMENT`) | DB-3 |
| A | 05 | `00_schema` | `…-alter-fatturazione-lotti-data-documento-` | DB-4 |
| A | 06 | `80_data` | CSV **dedicato** `registri_fatturazione_politica_data.csv` + loader nuovo | seed D-2 |
| A | 07 | `20_code` | `…-create-fn-calcola-data-documento-` | DB-5 |
| A | 08 | `20_code` | `…-update-fn-get-or-create-fattura-header-data-documento-` | DB-6 |
| A | 09 | `00_schema` | `…-alter-fatture-data-default-fn-data-operativa-` | DB-2 (default di colonna) |
| **B** | 10 | `00_schema` | `…-alter-registri-progressivi-ultima-data-` | DB-7 |
| B | 11 | `80_data` | append a `codici_errore.csv` + `messaggi_errore.csv` (id **989**) | DB-9 |
| B | 12 | `80_data` | `…-backfill-ultima-data-progressivi-` (forward-only, `runOnChange: false`) | §6 punto 2 |
| B | 13 | `20_code` | `…-recreate-fn-get-next-progressivo-cancello-` (**DROP + CREATE**) | DB-8 |
| **C** | 14 | `20_code` | `…-create-fn-get-data-minima-numerabile-` (le due funzioni) | DB-10 |
| C | 15 | `20_code` | `…-create-fn-imposta-data-documento-lotto-` | DB-11 |
| C | 16 | `20_code` | `…-create-trgfn-fatture-guard-data-numerata-` + trigger | **DB-14** |
| **D** | 17 | `00_schema` | `…-alter-chk-registri-fatturazione-reset-annuale-` | DB-12 (CHECK) |
| D | 18 | `20_code` | `…-recreate-fn-assign-numero-fattura-fattura-id-e-senza-mese-` (**DROP + CREATE**, ⭐ **fuso**: D-4) | DB-8 (chiamante) + DB-12 |
| D | 19 | `20_code` | `…-recreate-fn-numera-fattura-opz-emessa-senza-mese-` (**DROP + CREATE**) | DB-12 |
| D | — | `db/pgtap/` | estensione dei 4 file | DB-13 |

⭐ **Passi 14 e 19 del piano originale fusi nel 18** (decisione D-4, Tid
2026-08-25): `fn_assign_numero_fattura` si riscrive **una volta sola**, passando
`p_fattura_id` a `fn_get_next_progressivo` e togliendo `mese` dal `RETURNS TABLE`
nello stesso `DROP + CREATE`.
⚠️ Fra il passo 13 e il 18 c'è una finestra in cui l'errore del cancello esce
**senza bersaglio** (il chiamante non passa ancora l'id): accettabile solo
perché i lotti si applicano nello stesso giro. ▶ §10.3 D-4.
⛔ Ciò che **non** si può fare è invertire la numerazione fra chi droppa e chi
ricrea: l'autogen ordina `00_schema` e `20_code` per NN
([[reference_liquibase_autogen_ordina_per_numero]]).

⚠️ **Tutti i changeSet di `00_schema` e `20_code` nascono `runOnChange: false`**,
e con `validCheckSums` **al plurale** se serve. È un cancello di CI, non una
preferenza.

---

## 6. Bonifica (via libera di Tid)

Stato al 2026-08-25 su `dbdev`:

* registro 3: **11 fatture numerate, 3 inversioni** (numeri 3, 9 e 11); ✅
  riconfermato il 2026-08-25 con una query a finestra su `(registro, serie)`;
* ~~**6 fatture `EMESSA`** ancora da numerare, date dal 31/07 al 24/08 — con
  l'ultimo numerato al 23/08, quella del 31/07 verrebbe rifiutata;~~
  ⛔ **RETTIFICA**: le 6 non sono tutte del registro 3. Sono **5 sul registro 3**
  (632→31/07, 2263→02/08, 2457→03/08, 18847→23/08, 20025→24/08) e **1 sul
  registro 4** (836→31/07). Il registro **4 non ha nemmeno una riga di
  contatore** (`registri_fatturazione_progressivi` ne ha due sole: registro 3
  serie `R2`, registro 5 serie vuota), quindi dopo il backfill la sua
  `ultima_data` è `NULL` e la fattura 836 **passa comunque**.
  Con `ultima_data(3, 'R2') = 2026-08-23` (il massimo delle numerate, non
  l'ultimo numero: il numero 11 porta il 31/07), il cancello ne rifiuterebbe
  **tre** — 632, 2263, 2457 — non «almeno una». ▶ §10 V-6;
* **7 fatture su 18** con `data <> (data_insert AT TIME ZONE 'Europe/Rome')::date`
  — lo sfasamento UTC di DB-2. ✅ riconfermato.
* ⚠️ **Tutte e sei le `EMESSA` hanno `serie IS NULL`**: la serie effettiva viene
  dal `serie_default` del registro. È il caso su cui DB-10 e DB-11 possono
  sbagliare in silenzio (▶ §10 V-5), ed è anche il caso su cui va provata la
  bonifica.

Da fare, nell'ordine:

1. riallineare a mano `vendite.fatture.data` delle numerate perché la sequenza
   torni monotòna per `(registro, serie)` — oppure azzerare il registro 3, se
   Tid preferisce ripartire pulito;
2. **backfill** di `registri_fatturazione_progressivi.ultima_data` =
   `max(f.data)` delle numerate di quella riga di contatore;
3. sistemare la data delle 6 `EMESSA` (o lasciarle: dopo DB-11 si ridichiarano
   dal dialog).

---

## 7. Cosa NON è in questo cantiere

* La bonifica generale di `CURRENT_DATE` (25 tabelle, 67 funzioni) e l'ipotesi
  `TIME_ZONE` in `DATABASES`: cantiere suo, subito dopo.
* L'implementazione di `MENSILE`: se un giorno serve, mese nel contatore **e**
  nella UNIQUE, con il CHECK riaperto.
* Un vincolo che leghi `fatture.emittente_soggetto_ruolo_id` all'emittente del
  suo registro: oggi nulla lo garantisce (nei dati coincidono su tutte e 18 le
  fatture). Va nominato, non chiuso qui.
* Un guard «la nota di credito non può avere data anteriore alla fattura che
  rettifica»: fiscalmente sensato, ma è un secondo cancello con una sua
  discussione.
* ⛔ **Il riallineamento di `registri_fatturazione.csv`** (decisione D-3, Tid
  2026-08-25): il CSV resta stantìo sull'emittente e senza le tre righe del
  secondo emittente, e il suo mirror `runOnChange` resta una **trappola armata**
  per chiunque tocchi quel file. Nominato in §10.3 D-3 con il rimedio già
  scritto; il cantiere ci gira intorno usando un CSV dedicato.
* I due UNIQUE gemelli su `registri_fatturazione_progressivi` (§10 V-12):
  nominati, non tolti.

---

## 8. Cosa parte dopo, e per chi

### Backend (attende il DB)

| | Consegna |
| --- | --- |
| BE-1 | `data_documento` facoltativa nel payload di creazione lotto |
| BE-2 | `data_documento` facoltativa su `POST /vendite/lotti/<id>/numera` e su `POST /vendite/fatturazione/numera` → `fn_imposta_data_documento_lotto` prima di numerare, **una data per l'intero atto** (decisione 5) |
| BE-3 | `list_lotti_numerabili`: `ORDER BY fl.id` → **ordine per data documento** (`min(f.data)` delle fatture non numerate del lotto), poi `id` (decisione 6) |
| BE-4 | Policy del codice `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` (rigenerata, non scritta a mano) |
| BE-5 | Endpoint di lettura per la `minDate` del dialog (`fn_get_data_minima_numerabile_lotto`) |
| BE-6 | Il **backstop stampa** ora può rifiutare: l'esito va nella coda con il suo motivo, non come render fallito muto |

### Frontend (attende il BE)

| | Consegna |
| --- | --- |
| FE-1 | Campo data (facoltativo) nella creazione del lotto |
| FE-2 | DatePicker nel dialog «Rendi definitive», singolo lotto **e** per competenza, con `minDate` da BE-5 e default dalla politica |
| FE-3 | Colonna **data documento** nella lista lotti e nella lista fatture |
| FE-4 | Messaggio del cancello con bersaglio (due pulsanti: il documento e l'ultimo numerato) |

⚠️ **Da dire a BE e FE prima che partano** (dalla verifica del 2026-08-25):

* **BE-5 / FE-2 salgono di rango.** Con il seed confermato (D-2), sul registro
  Back-office ogni lotto di **competenza arretrata** viene rifiutato dal cancello
  *per costruzione* (§10 V-7). La `minDate` non è un abbellimento: senza, il
  dialog «Rendi definitive» propone una data che il DB rifiuta ogni volta.
* **BE-4**: la policy si **rigenera** (`genera_error_policies`), non si scrive a
  mano — `error_policies_generated.py` è un file generato da
  `config.vw_codici_errore_identita`, e il `--check` gira in CI.
* **FE-4**: la `reason_key`/i testi nuovi vanno chiesti **nello stesso giro**;
  `scripts/check_i18n_keys.py` fallisce su una chiave emessa dal DB e assente
  dai locales.
* **BE-6**: il backstop stampa chiama `fn_numera_fattura_opz_emessa` da
  `numera_fattura_backstop` (`pipeline_repository.py`), **senza operatore
  davanti**. Da lì il nuovo codice esce come `DATO_ERRATO` (400) su una coda: va
  scritto nella riga di coda col suo motivo, non lasciato come render fallito
  muto.

---

## 9. Registro

### 2026-08-25 · Analisi e consegna

Analisi sui dati veri, tre inversioni misurate, tre difetti distinti isolati
(momento sbagliato · fuso UTC · nessun cancello) e un quarto emerso strada
facendo (`reset_policy` decorativa). Decisioni prese da Tid in giornata; brief
scritto e passato al team DB. Nessuna riga di DB, BE o FE ancora scritta.

### 2026-08-25 · Verifica tecnica del piano (team DB)

Il piano è stato riletto contro il **DB vivo** (`dbdev`), la doc auto-gen,
`backend/`, `db/pgtap/` e i CSV di `80_data`. Confermato tutto l'impianto;
corrette **13 cose**, di cui quattro portanti. Aggiunta la consegna **DB-14**.
Nessuna riga di DB, BE o FE ancora scritta. Dettaglio in §10.

Nella stessa giornata Tid ha chiuso le tre domande aperte dalla verifica:
**D-2** seed confermato com'era proposto (accettando la conseguenza V-7 sulla
differita in ritardo), **D-3** la mina di `registri_fatturazione.csv` si
**nomina e resta armata** — non si disinnesca qui —, **D-4** i due `recreate` di
`fn_assign_numero_fattura` si **fondono** in uno. Piano di §5-bis riscritto di
conseguenza: **18 changeSet**, da `20260825-02` a `20260825-19`, più i pgTAP.

---

## 10. Verifica tecnica — 2026-08-25

> **Metodo.** Ogni affermazione qui sotto è misurata su `dbdev` (`pg_proc`,
> `pg_trigger`, `pg_constraint`, `pg_policies`, `pg_class`, i dati), oppure
> letta nella doc auto-gen `docs/it/dbzero/` (che riflette l'oggetto **vivo**),
> oppure `grep`-ata su `backend/`, `db/pgtap/` e `db/changelog/`. **Niente è
> stato dedotto da uno YAML di migration** (AGENTS.md: un singolo YAML è quasi
> sempre stantìo).
>
> ⚠️ **I dati di sviluppo sono di TEST**: la gravità qui sotto risponde a «può
> succedere?», non a «è successo?».

### 10.1 Cosa il piano dice giusto (verificato, non ricopiato)

| | Affermazione del brief | Esito |
| --- | --- | --- |
| C-1 | `fn_get_next_progressivo` è il punto non aggirabile, e l'advisory lock c'è già | ✅ confermato: lock a **due argomenti** (namespace + chiave), poi `SELECT … FOR UPDATE`, poi l'incremento |
| C-2 | il chiamante è **uno solo** | ✅ confermato su quattro fronti: `pg_proc`, `backend/**.py`, `db/pgtap/`, viste. `DROP` sicuro |
| C-3 | `fn_get_or_create_fattura_header` è l'**unico** scrittore di `vendite.fatture.data` | ✅ confermato: nessuna funzione fa `SET data =` su `vendite.fatture`, nessun `INSERT` fuori da lì. La colonna ha default `CURRENT_DATE`, `NOT NULL` |
| C-4 | `registri_fatturazione_progressivi` **non ha RLS**, `vendite.fatture` sì | ✅ `relrowsecurity` = `f` sul contatore e sui registri; `t` su `fatture`, `fatture_scadenze`, `fatturazione_lotti`. La scelta di DB-7 regge, ed è il motivo per cui regge |
| C-5 | il `mese` del `RETURNS TABLE` non lo legge nessuno | ✅ confermato riga per riga: BE drena, pgTAP legge per nome |
| C-6 | `reset_policy` è decorativa | ✅ e in più: **tutti e 6** i registri sono già `ANNUALE` → restringere il CHECK non richiede bonifica |
| C-7 | il modello ammette due serie sullo stesso registro | ✅ `tipi_doc_fiscale_registri` lo consente; oggi **nessuno lo usa** (tutte le mappature hanno `serie` vuota), ma il registro 5 riceve già **due** mappature. La chiave `(registro, serie)` è giusta e a costo zero |
| C-8 | `competenza_mese` c'è sempre | ✅ `NOT NULL`, e su 49 lotti è **sempre** il primo del mese: zero eccezioni |
| C-9 | 3 inversioni, 7/18 fatture sfasate UTC | ✅ riconfermati entrambi |
| C-10 | storicizzazione | ✅ **non è un problema**: `storico.registri_fatturazione` e `storico.fatturazione_lotti` sono a **snapshot JSONB**, quindi aggiungere colonne non le tocca |
| C-11 | i pgTAP da estendere partono verdi | ✅ nessuno dei quattro è in `baseline-rossi.tsv` né in `baseline-rossi-ci.tsv` |
| C-12 | il cancello non rompe i test esistenti | ✅ `test-registri-progressivi.sql` numera 2025→2025→2026, sequenza monotòna, e usa **argomenti nominati** |

### 10.2 I difetti, in ordine di gravità

#### V-1 — ⛔ Il cancello resta aggirabile nel caso che dichiara di coprire

L'advisory lock esistente ha la chiave `registro|**anno**|serie`; il cancello di
DB-8 legge il massimo **attraverso gli anni**, e il `FOR UPDATE` blocca la sola
riga del proprio anno. Due transazioni con date in anni diversi sullo stesso
`(registro, serie)` prendono lock **diversi** e possono passare entrambe. È
esattamente il caso «documento retrodatato al 31/12 dell'anno scorso» che il
brief nomina.
**Rimedio**: togliere l'anno dalla chiave del lock. ▶ DB-8.

#### V-2 — ⛔ DB-12 richiede due `DROP FUNCTION` che il brief non nominava

`RETURNS TABLE` non si modifica con `CREATE OR REPLACE`. Servono `DROP` +
`CREATE` per `fn_assign_numero_fattura(bigint)` e
`fn_numera_fattura_opz_emessa(bigint, boolean, character varying)`, con verifica
`pg_get_function_identity_arguments` a valle. ▶ DB-12.

#### V-3 — ⛔ `fatture.data` non è congelata da nessun trigger: la premessa di DB-11 è falsa

`trgfn_fattura_satellite_guard_congelamento` è agganciata a `vendite.fatture`
**solo** su `UPDATE OF emittente_snapshot, cliente_snapshot`. Un
`UPDATE vendite.fatture SET data = …` su una fattura numerata e `DEFINITIVA`
oggi **passa**. Il cantiere costruirebbe un cancello lasciando aperto il retro.
▶ nuova consegna **DB-14**.

#### V-4 — ⛔ La mina nel CSV dei registri

`80_data/sql/vendite/registri_fatturazione.csv` dice
`emittente_soggetto_ruolo_id = NULL` per i registri 3/4/5, mentre il DB dice
**72** (glielo ha scritto `20260819-05`); e i tre registri del secondo emittente
(1359/1360/1361) **non ci sono affatto**. Il mirror
`20260127-09-upsert-registri-fatturazione` è `runOnChange: true`: **dorme finché
il file non cambia**. Chi tocca quel CSV — per qualunque motivo — lo sveglia e
riporta i registri a emittente `NULL`, riaprendo il difetto C-4 chiuso a agosto.
▶ DB-3 (via: CSV dedicato) e **D-3** qui sotto.

#### V-5 — ⚠️ La serie va risolta come la risolve chi numera

`fn_assign_numero_fattura` usa `COALESCE(f.serie, r.serie_default, '')`. **Tutte
e sei** le fatture non numerate hanno `f.serie IS NULL`. Una lettura scritta con
`COALESCE(f.serie,'')` non troverebbe il contatore e risponderebbe `NULL` =
«nessun minimo»: la risposta più permissiva, proprio dove il cancello rifiuta.
▶ DB-10, DB-11, DB-13 caso 11.

#### V-6 — ⚠️ Il conto della bonifica è sbagliato

Le 6 `EMESSA` sono **5 sul registro 3 + 1 sul registro 4**; il registro 4 non ha
riga di contatore, quindi passa comunque. Il cancello ne rifiuterebbe **tre**
(632, 2263, 2457), non «almeno una». ▶ §6.

#### V-7 — ⚠️ `FINE_MESE_COMPETENZA` + cancello: la collisione è strutturale, e nei dati c'è già

Su un registro con politica `FINE_MESE_COMPETENZA`, un lotto di **competenza
arretrata** lavorato in ritardo prende la data di fine di quel mese e il cancello
lo rifiuta **per costruzione**. Non è un difetto — è il comportamento voluto —
ma è la modalità **normale** della differita in ritardo, non un caso di bordo.

Misurato: **4 lotti** hanno competenza giugno e fatture datate luglio/agosto
(7515, 7133, 7132, 151), e il 7133 porta la fattura **18848, già numerata** il
23/08. Se il registro 3 fosse `FINE_MESE_COMPETENZA`, quelle fatture nascerebbero
al 30/06 e non si numererebbero più senza ridichiarare la data ogni volta.

⭐ Va scritto nel brief e detto al FE: **la `minDate` di DB-10 non è un
abbellimento, è ciò che rende vivibile la politica differita.** Senza, il primo
collaudo leggerà il cancello come un bug.

#### V-8 — ⚠️ Dove va, in concreto, ogni seed

* `parameters.csv`: **allineato col DB** riga per riga → append sicuro, **id 54**.
* `codici_errore.csv` / `messaggi_errore.csv`: allineati (loader girato stamattina)
  → append sicuro, ma **`config.codici_errore` non ha `id`** e su
  `messaggi_errore` il primo libero è **989**, non 988.
* `registri_fatturazione.csv`: **stantìo** → non toccare (V-4).

#### V-9 — ⚠️ DB-2 scavalca un building block, e va detto

`script.fn_get_parameter_full(...)` è il lettore canonico dei parametri con la
cascata di override. DB-2 legge il `default_value` diretto. **La scelta è
giusta** — un override per utente o sessione darebbe alla stessa fattura date
diverse a seconda di chi la genera — ma se non è scritta nel `COMMENT`, il
prossimo la "corregge" verso il BB e riapre il buco.

#### V-10 — ⚠️ Il bersaglio si sceglie per data, non per numero

Il contatore non tiene l'id della fattura. Prendendo «l'ultima numerata» con
`ORDER BY numero DESC`, nei registri con inversioni già scritte — cioè il
registro 3, **oggi** — il pulsante punta a un documento con una data diversa da
quella che la frase nomina. ▶ DB-9.

#### V-11 — ⚠️ `fn_get_next_progressivo` porta un messaggio da bonificare

Solleva `E_PARAMETRO_INVALIDO` con `'p_registro_id e p_data obbligatori'` nel
`VARIADIC`: nomi di parametro PL/pgSQL dentro la frase che legge una persona. E
il guard sugli id copre `IS NULL` ma non `<= 0`. Dato che DB-8 riscrive comunque
la funzione, è il giro in cui si sistema.

#### V-12 — ⚠️ Due UNIQUE gemelli sul contatore

`uq_regprog_key (registro_id, anno, mese, serie)` e
`uq_registri_progressivi_scope (registro_id, anno, COALESCE(mese,0), COALESCE(serie,''))`
sono lo stesso vincolo: `mese` e `serie` sono `NOT NULL`, i `COALESCE` non fanno
niente. Non è di questo cantiere; è il momento di nominarlo perché la tabella si
tocca comunque.

#### V-13 — ⚠️ `context.campo` diverge fra brief e analisi

`data_documento` qui, `data` in §6.B dell'analisi. Vince il brief; l'analisi va
sanata o qualcuno la riporta indietro.

### 10.3 Le domande aperte

**D-1 — colonna `mese`** → ✅ **risposta data**: si lascia, con `COMMENT`. Vedi §2.

**D-2 — seed delle politiche** → ✅ **DECISO da Tid, 2026-08-25: si conferma la
proposta.** 3/1359 `OGGI` · 4/1360 `FINE_MESE_COMPETENZA` · 5/1361 `OGGI`.
⚠️ Consegnato via **CSV dedicato**, non via `registri_fatturazione.csv` (V-4).
⚠️ E si accetta consapevolmente la conseguenza della **V-7**: sul Back-office
ogni lotto di competenza arretrata chiederà all'operatore di ridichiarare la
data dal dialog. **Non è un difetto da correggere in collaudo** — è la scelta.
Va detto al FE (la `minDate` di BE-5/DB-10 è ciò che la rende vivibile) e va
scritto nel messaggio di collaudo, o il primo che lo incontra aprirà un bug.

**D-3 — la mina di `registri_fatturazione.csv`** → ✅ **DECISO da Tid,
2026-08-25: si nomina e basta, non si disinnesca in questo cantiere.**
Il cantiere procede lo stesso perché il seed della politica va in un CSV
dedicato e quel file **non si tocca**.

⛔ **La mina resta armata, e questo è il posto in cui è scritta.**
`80_data/sql/vendite/registri_fatturazione.csv` è **stantìo su
`emittente_soggetto_ruolo_id`** (dice `NULL`, il DB dice `72`) e gli mancano le
righe 1359/1360/1361. Il suo mirror `20260127-09-upsert-registri-fatturazione`
è `runOnChange: true`: **il primo che edita quel file per qualunque motivo lo
sveglia**, e i registri 3/4/5 tornano senza emittente — cioè `fn_get_registro_id`
torna a risolvere sul fallback generico e il difetto C-4 chiuso da
`20260819-05` si riapre. Il rimedio, quando si deciderà di applicarlo: CSV
riallineato (emittente 72/159 + le tre righe) e **mirror ri-ancorato** con
numerazione nuova, pattern `20260806-13`/`-14` — mai modificando il changeSet
mergiato.

**D-4 — i due `recreate` di `fn_assign_numero_fattura`** → ✅ **DECISO da Tid,
2026-08-25: si fondono.** Un solo `DROP + CREATE` che passa `p_fattura_id` a
`fn_get_next_progressivo` **e** toglie `mese` dal `RETURNS TABLE`. Il piano di
§5-bis è stato riscritto di conseguenza: il passo 14 sparisce e il 19 fa
entrambe le cose.

⚠️ **Conseguenza sull'ordine, e non è un dettaglio**: fondendo, la riscrittura di
`fn_assign_numero_fattura` finisce **in coda** (lotto D) mentre il cancello di
DB-8 sta nel lotto B. Fra i due c'è una finestra in cui `fn_get_next_progressivo`
ha il parametro `p_fattura_id` e il suo unico chiamante **non glielo passa**:
il cancello funziona, ma l'errore esce **senza bersaglio**. È accettabile solo
perché i due lotti si applicano nello stesso giro. ⛔ Se si dovesse fermarsi in
mezzo, il file fuso va anticipato subito dopo DB-8.
