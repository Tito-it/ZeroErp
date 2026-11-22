# Brief DB — la data del documento e la sequenza del registro

> ✅ **STATO: CANTIERE CHIUSO E COLLAUDATO** (2026-08-25). DB **18 changeSet
> applicati** e **14 consegne su 14** (§11); BE e FE **10 su 10** (§12); seed
> della colonna di lista arrivato dal team DB; **collaudo in-app superato da
> Tid** sulle due superfici che contano — la riga scelta dalla Dashboard
> Competenza e la numerazione avanzata dal drawer del lotto (§12.7).
>
> ⭐ **Spostato in `work-done/` il 2026-08-26** (decisione di Tid). ~~NON spostare
> questo file~~: il divieto che stava qui poggiava su un rischio di CI che **non
> esiste** — vedi §12.8, corretta. Restano 15 riferimenti al vecchio percorso
> dentro i `COMMENT` del database: **debito cosmetico accettato**, non un
> guasto.
>
> **Destinatario:** team DB (`dev/db-tid`), poi backend e frontend. BE e FE
> hanno atteso i prerequisiti DB prima di partire
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
> `▶ §10 V-n`. ⚠️ Quel giorno **nessuna riga era ancora scritta**: la frase resta
> perché è il fotogramma da cui il cantiere è partito, non lo stato di oggi.

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

| Lotto | # | Cartella | File | Consegna | Stato |
| --- | --- | --- | --- | --- | --- |
| **A** | 12 | `80_data` | `20260825-12-upsert-parameter-system-fuso-orario-` + CSV **dedicato** `parameters_sistema.csv` (id 54) | DB-1 | ✅ scritto |
| A | 02 | `20_code/script` | `20260825-02-create-fn-data-operativa-` | DB-2 | ✅ scritto |
| A | 03 | `00_schema/vendite` | `20260825-03-alter-registri-politica-data-documento-` | DB-3 | ✅ scritto |
| A | 04 | `00_schema/vendite` | `20260825-04-alter-fatturazione-lotti-data-documento-` | DB-4 | ✅ scritto |
| A | 05 | `80_data` | `20260825-05-seed-registri-politica-data-documento-` + CSV dedicato | seed D-2 | ✅ scritto |
| A | 06 | `20_code/vendite` | `20260825-06-create-fn-calcola-data-documento-` | DB-5 | ✅ scritto |
| A | 07 | `20_code/vendite` | `20260825-07-update-fn-get-or-create-fattura-header-data-documento-` | DB-6 | ✅ scritto |
| A | 08 | `00_schema/vendite` | `20260825-08-alter-fatture-data-default-operativa-` | DB-2 (default) | ✅ scritto |
| **0** | — | — | ~~bonifica dati~~ → **nessuna** (§6). Resta la *ripartenza dei numeratori da 100*, **dopo** il migrate | cosmesi, non prerequisito | 🟡 script pronto e collaudato |
| **B** | 09 | `00_schema/vendite` | `20260825-09-alter-registri-progressivi-ultima-data-` | DB-7 | ✅ scritto |
| B | — | `80_data` | append a `codici_errore.csv` + `messaggi_errore.csv` (id **989**) | DB-9 | ✅ scritto |
| B | 10 | `80_data` | `20260825-10-backfill-ultima-data-progressivi-` | §6 punto 2 | ✅ scritto |
| B | 11 | `20_code/vendite` | `20260825-11-recreate-fn-get-next-progressivo-cancello-` (**DROP + CREATE**) | DB-8 | ✅ scritto |
| **C** | 13 | `20_code/vendite` | `20260825-13-create-fn-get-data-minima-numerabile-` | DB-10 | ✅ scritto |
| C | 14 | `20_code/vendite` | `20260825-14-create-fn-imposta-data-documento-lotto-` | DB-11 | ✅ scritto |
| C | 15 | `20_code/vendite` | `20260825-15-create-trgfn-fatture-guard-data-numerata-` + codice **990** nei CSV | **DB-14** | ✅ scritto |
| **D** | 16 | `00_schema/vendite` | `20260825-16-alter-chk-registri-fatturazione-reset-annuale-` | DB-12 (CHECK) | ✅ scritto |
| D | 17 | `20_code/vendite` | `20260825-17-recreate-fn-numera-fattura-opz-emessa-senza-mese-` ⚠️ **prima la chiamante** | DB-12 | ✅ scritto |
| D | 18 | `20_code/vendite` | `20260825-18-recreate-fn-assign-numero-fattura-bersaglio-e-senza-mese-` (**fuso**: D-4) | DB-8 (chiamante) + DB-12 | ✅ scritto |
| D | — | `db/pgtap/` | `test-registri-progressivi` esteso (14) + **`test-data-documento-v1` nuovo** (15) | DB-13 | ✅ **verdi** |

⚠️ **DB-1 non ha un changeSet, e la numerazione e' scalata di uno rispetto al
piano di ieri.** Il mirror `20250715-01-upsert_parameters` e' gia'
`runOnChange: true` + `validCheckSums: ANY` sul CSV: appendere la riga BASTA, e
un loader nuovo sarebbe una seconda sorgente per la stessa tabella
([[feedback_messaggi_errore_no_new_loader]], stessa logica). Vale identico per
DB-9 al passo 10.

⭐ **I due `recreate` di `fn_assign_numero_fattura` sono fusi nel passo 17**
(decisione D-4, Tid 2026-08-25): la funzione si riscrive **una volta sola**,
passando `p_fattura_id` a `fn_get_next_progressivo` e togliendo `mese` dal
`RETURNS TABLE` nello stesso `DROP + CREATE`.
⚠️ Fra il passo 11 e il 18 c'è una finestra in cui l'errore del cancello esce
**senza bersaglio** (il chiamante non passa ancora l'id). Tid, 2026-08-25:
**non siamo in produzione, il punto decade**. ▶ §10.3 D-4.

⛔ **E l'ordine 17 → 18 è invertito rispetto al piano di stamattina, per una
ragione misurata.** Le due funzioni si toccano: `fn_numera_fattura_opz_emessa`
chiama `fn_assign_numero_fattura`. Togliendo `mese` prima dalla **chiamata**, ci
sarebbe un momento in cui la chiamante fa `SELECT t.mese FROM …` su una colonna
che non esiste più: **errore a runtime**. Nell'ordine giusto — prima la
chiamante, poi la chiamata — la chiamante seleziona 4 colonne su 5, che è
legittimo, e non c'è nessuna finestra rotta.
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

### ⛔ RETTIFICA (Tid, 2026-08-25, secondo giro): **la bonifica non si fa**

~~1. azzerare il registro 3 · 2. backfill · 3. sistemare le 5 EMESSA~~

La domanda di Tid — *«perché dovremmo rinumerarle? mica danno errore? i dati sono
di test»* — ha smontato la premessa, ed era giusta. **Le 11 fatture con le
inversioni non producono nessun errore**: `uq_fatture_numero` è soddisfatto,
nessuna query legge l'ordine dei numeri, nessun guard le guarda. Sono **storia
brutta, non un difetto attivo**.

⭐ **Il cancello è rivolto in avanti**: confronta la data del *prossimo*
documento con `max(ultima_data)`. Non gli importa come si è arrivati a quel
massimo.

Quindi l'unica conseguenza reale delle 11 è **una riga sola**: il pavimento si
ferma al **2026-08-23** (dalla fattura 18848, numero 8), e delle 5 `EMESSA` in
attesa le tre datate 31/07, 02/08 e 03/08 verrebbero rifiutate.

**E quelle tre date sono spazzatura comunque**: sono `current_date` in UTC
catturati alla generazione della bozza settimane fa, non decisioni. Sul registro
3 (politica `OGGI`) il nuovo modello darebbe loro la data di oggi.

### Cosa si fa, allora

**Niente sulle fatture.** Resta il **backfill** di `ultima_data`, che non è
lavoro a mano ma il changeSet `20260825-10`.

⭐ **Una sola cosa a mano, e non è una bonifica: i numeratori ripartono da 100**
(decisione di Tid, 2026-08-25 — *«che ci frega, facciamo prima»*). Nessuna
rinumerazione, nessuna cancellazione: solo uno **stacco visibile** fra il prima
e il dopo. Tutto ciò che porta 1..11 viene dal flusso rotto, tutto ciò che porta
101 e oltre viene dal cancello. In collaudo si legge a colpo d'occhio.

```sql
-- ⚠️ DOPO il migrate, non prima: il backfill (20260825-10) è runOnChange:false
--    e gira una volta durante il migrate — eseguito prima, lo sovrascriverebbe.
INSERT INTO vendite.registri_fatturazione_progressivi
       (registro_id, anno, mese, serie, last_numero, attivo)
SELECT r.id, EXTRACT(YEAR FROM CURRENT_DATE)::smallint, 0,
       COALESCE(r.serie_default, ''), 100, true
  FROM vendite.registri_fatturazione r
 WHERE r.attivo
ON CONFLICT (registro_id, anno, mese, serie) DO UPDATE SET last_numero = 100;
```

Collaudato in transazione: `INSERT 0 6`, sei registri a 100, prossimo numero
**101**, le 11 fatture intatte. Script eseguibile (con `ROLLBACK` da girare in
`COMMIT`): `/tmp/ripartenza-numeratori-da-100.sql`.

⭐ **Non tocca `ultima_data`, ed è una scelta.** Sul registro 3 resta 2026-08-23,
quindi le tre `EMESSA` anteriori **restano rifiutate** — ed è esattamente il
collaudo che serve: sono il primo caso reale di `fn_imposta_data_documento_lotto`
(DB-11), l'unica occasione di provare il cancello su dati veri. Azzerare il
pavimento renderebbe il cancello inerte fino al primo numero nuovo.
⚠️ Se un giorno servisse sbloccarle subito, basta aggiungere `ultima_data = NULL`
a quell'`UPDATE` — ma sapendo che si sta spegnendo il presidio.

⭐ Le tre bloccate diventano il **primo collaudo vero di
`fn_imposta_data_documento_lotto`** (DB-11, lotto C): la funzione riscrive la
data, **rigenera il piano rate** e salta le già numerate. È esattamente il caso
per cui esiste.

⛔ **E per questo NON si sistemano con un `UPDATE` secco su `fatture.data`.**
Cambiare la data senza rigenerare le scadenze lascia rate calcolate su una data
che il documento non porta più, e il guard D-K **non se ne accorge** — la somma
delle rate non cambia, cambiano le loro scadenze, quindi passa in silenzio. È
precisamente il difetto che DB-11 punto 4 esiste per impedire, e sarebbe
ridicolo introdurlo a mano nel cantiere che lo chiude.

⚠️ **La sola conseguenza da sapere**: fra il migrate del lotto B e l'arrivo di
DB-11, quelle tre fatture non si possono numerare. Non siamo in produzione e il
lotto C è il prossimo.

---

## 6-bis. ~~Lo script di azzeramento~~ — le alternative misurate e scartate

⛔ **Nessuna di queste si esegue** (rettifica di Tid del 2026-08-25). Restano
scritte perché sono state provate davvero, e perché il giorno in cui una
bonifica servisse su un database che non è di test, il confronto è già fatto.

Tutte e tre collaudate in transazione con `ROLLBACK`, tutte a costo trascurabile
(due o tre `UPDATE`):

| | le 11 vecchie | inversioni residue | pavimento R2 | `EMESSA` bloccate | fatture senza numero |
| --- | --- | --- | --- | --- | --- |
| **niente** (scelta) | invariate | 3, storiche | 2026-08-23 | 3 → le risolve DB-11 | 5 |
| azzeramento | perdono il numero | — | nessuno | 0 | **11 `DEFINITIVA` + 5** |
| rinumerare per data | 1..11 in ordine | 0 | 2026-08-23 | 3 | 5 |
| serie storica `R2S` | numeri invariati | 3, in una serie chiusa | nessuno | 0 | 5 |
| entrambe (`R2S` + ordine) | 1..11 in ordine su `R2S` | 0 | nessuno | 0 | 5 |

⚠️ **Perché l'azzeramento era la peggiore**, ed era quella scelta al primo giro:
lascia **11 fatture `DEFINITIVA` senza numero** dentro 10 lotti chiusi — nessun
vincolo lo impedisce e nessun trigger lo rifiuta (verificato: né i `BEFORE`, né i
`CONSTRAINT ... DEFERRED` al `COMMIT`), ma sono documenti «definitivi» senza
identificativo fiscale.

⚠️ **Perché la serie storica, pur elegante, resta una finzione**: `R2S` non
esiste in `tipi_doc_fiscale_registri` e nessuna mappatura la produrrebbe mai. È
leggibile come «sezionale chiuso prima del cantiere» solo se qualcuno lo scrive
da qualche parte — cioè è una convenzione che vive in un documento, non nel
modello.

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
* ⛔ **`DEFAULT_UTILITY` non è più scrivibile, e nessuno se n'era accorto.** La
  riga (id 12 di `config.parameters`) ha `default_value = ''`, il dispatcher
  `config.trgfn_parameters_fk_surrogate_dispatch` — entrato **dopo** — pretende un
  valore esistente in `config.utilities.codice_interno`, e la stringa vuota non
  c'è. ⚠️ E `default_value` è `NOT NULL`, mentre la descrizione della riga dice
  «NULL = nessun default»: **quella riga non ha nessun valore scrivibile**.
  Sopravvive solo perché precede il guard. Il migrate del 2026-08-25 ci è morto
  sopra. Sanarla è una **decisione di dominio** (scegliere una utility di
  default, oppure ammettere `''` nel guard, oppure togliere il `NOT NULL`) e non
  si prende dentro questo cantiere.

---

## 8. Cosa parte dopo, e per chi

> ✅ **CHIUSO il 2026-08-25.** Dieci consegne su dieci scritte, una sola in
> attesa di un prerequisito (FE-3). Dettaglio in **§12**.

### Backend (attende il DB) — ✅ fatto

| | Consegna | Stato |
| --- | --- | --- |
| BE-1 | `data_documento` facoltativa nel payload di creazione lotto | ✅ |
| BE-2 | `data_documento` facoltativa su `POST /vendite/lotti/<id>/numera` e su `POST /vendite/fatturazione/numera` → `fn_imposta_data_documento_lotto` prima di numerare, **una data per l'intero atto** (decisione 5) | ✅ |
| BE-3 | `list_lotti_numerabili`: `ORDER BY fl.id` → **ordine per data documento** (`min(f.data)` delle fatture non numerate del lotto), poi `id` (decisione 6) | ✅ |
| BE-4 | Policy del codice `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` (rigenerata, non scritta a mano) | ✅ (commit `1be23ca53`) + override `ui_action` |
| BE-5 | Endpoint di lettura per la `minDate` del dialog | ✅ `GET /vendite/fatturazione/finestra-numerazione/` |
| BE-6 | Il **backstop stampa** ora può rifiutare: l'esito va nella coda con il suo motivo, non come render fallito muto | ✅ |

### Frontend (attende il BE) — ✅ fatto, tranne una colonna

| | Consegna | Stato |
| --- | --- | --- |
| FE-1 | Campo data (facoltativo) nella creazione del lotto | ✅ |
| FE-2 | DatePicker nel dialog «Rendi definitive», singolo lotto **e** per competenza, con `minDate` da BE-5 e default dalla politica | ✅ |
| FE-3 | Colonna **data documento** nella lista lotti e nella lista fatture | 🟡 **il valore c'è nel payload, la colonna no**: serve una riga di seed in `lista_colonna.csv` per `vendite.lotti` — passata al team DB. La lista fatture ha già `data` |
| FE-4 | Messaggio del cancello con bersaglio | ✅ — non ha richiesto codice: `LOTTO` era già mappato in `core/bersagli.js`. Verificato con una chiamata vera, non dato per fatto |

⚠️ **Cosa era stato detto a BE e FE prima che partissero** (verifica del
2026-08-25). Tutti e quattro i punti hanno retto: la §12 dice come.

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

### 2026-08-25 · Lotto A applicato al repo (scritto, non migrato)

Otto consegne di file per la prima metà del cantiere — «la data nasce giusta» —
più l'append al CSV dei parametri. **Nessuna migrazione eseguita**: i changeSet
sono nel repo e aspettano l'autorizzazione a `migrate`.

| | |
| --- | --- |
| DB-1 | riga `SYSTEM_FUSO_ORARIO` (id 54) appesa a `parameters.csv`. ⭐ **Nessun changeSet**: il mirror esistente è già `runOnChange` sul file, e la numerazione del piano è scalata di uno |
| DB-2 | `script.fn_data_operativa()` — `STABLE`, fail-loud su **tre** condizioni (assente · vuoto · non in `pg_timezone_names`) |
| DB-3 | `registri_fatturazione.politica_data_documento` + CHECK + `COMMENT` |
| DB-4 | `fatturazione_lotti.data_documento`, senza default (il NULL significa «vince il registro») |
| seed | CSV **dedicato** per la politica + eredità dei registri clonati da `meta->>'clonato_da'` |
| DB-5 | `vendite.fn_calcola_data_documento` |
| DB-6 | `fn_get_or_create_fattura_header` senza `current_date` |
| DB-2b | `vendite.fatture.data` DEFAULT `script.fn_data_operativa()` |

**Tre cose emerse scrivendo**, tutte già dentro i file:

1. ⭐ **Il terzo controllo di `fn_data_operativa`.** Il brief ne chiedeva due
   (parametro assente o vuoto). Ne serve un terzo: un valore che *non è un fuso*
   (`Europe/Roma`) fa alzare a `AT TIME ZONE` un **22023 grezzo** da dentro la
   funzione — il contratto «`P0001` + `CONSTRAINT` = errore di dominio» salta e
   il guasto arriva al backend come 500 non tradotto. È la stessa forma del
   difetto già pagato sui segnaposto malformati.
2. ⭐ **Nessun `ELSE` che ingoia in `fn_calcola_data_documento`.** Il brief
   scriveva `ELSE fn_data_operativa()`: una politica non riconosciuta si
   sarebbe comportata come `OGGI`, in silenzio. Ora solleva. Il CHECK rende il
   ramo irraggiungibile *finché regge*, ed è esattamente il ragionamento già
   scritto in `fn_genera_scadenze_fattura` sulla ripartizione non gestita.
3. ⚠️ **`fn_get_or_create_fattura_header` guadagna un controllo che non aveva.**
   Legge il lotto (per competenza e data dichiarata) e quindi può non trovarlo:
   `E_LOTTO_NON_TROVATO`. Prima il lotto non lo leggeva affatto, e un
   `p_lotto_id` sbagliato produceva una fattura orfana. ⭐ La lettura sta
   **dopo** il lookup della fattura esistente: la funzione gira una volta per
   *attività* e quasi sempre esce subito.

⭐ E il codice per il chiamante rotto **non è `E_PARAMETRO_INVALIDO`**:
`E_VENDITE_CHIAMATA_NON_VALIDA` (983, `TECNICO`) esiste già ed è il gemello di
dominio di quello che il cantiere incassi ha usato stamattina. Il rubinetto
degli 88 `E_PARAMETRO_INVALIDO` di `vendite` resta chiuso.

**Verifiche eseguite** — tutte in transazione con `ROLLBACK`, nessuna scrittura
lasciata sul database:

* i tre rami di errore di `fn_data_operativa` sollevano `P0001` con la frase
  giusta, e il canale `CONSTRAINT` porta `E_CONFIG_MANCANTE`;
* ⭐ **la controprova del difetto**: con la sessione forzata in **UTC** (il fuso
  di Django), alle 00:30 del 26/08 romane `current_date` dice **25/08** e
  `fn_data_operativa()` dice **26/08**;
* `fn_calcola_data_documento` su 8 casi: OGGI, fine mese, **febbraio bisestile**
  (2028-02-29), competenza a metà mese, dichiarata che vince su entrambe le
  politiche, competenza `NULL` che sotto `FINE_MESE` solleva e sotto `OGGI` è
  legittima, registro `<= 0` e registro inesistente con **due frasi diverse**;
* il seed: i tre cloni **ereditano** dai loro originali (1360 si comporta come
  il 4);
* ⭐ **end-to-end su `fn_get_or_create_fattura_header`**, con la sessione in
  UTC: tre lotti veri, tre configurazioni, tre date scritte giuste
  (`2026-08-25` · `2026-08-10` dichiarata · `2026-06-30` fine mese), più
  l'idempotenza (una seconda chiamata non crea una seconda fattura) e il nuovo
  `E_LOTTO_NON_TROVATO`;
* `scripts/guardrail_run_on_change.py` e `guardrail_pgtap_preambolo.py`: verdi;
* i sette YAML parsano, hanno un solo changeSet e il `logicalFilePath`.

⚠️ **Una trappola incontrata e da ricordare per DB-13**: la prima stesura della
prova leggeva la data con `SELECT f.data FROM fatture WHERE f.id = fn_get_or_create...(...)`
— tutto in **una** istruzione — e riceveva `NULL`. La snapshot di statement
legge *prima* delle scritture della funzione chiamata: il verbo va invocato in
un'istruzione **separata** dall'asserzione
([[reference_pgtap_stessa_istruzione_snapshot]]). Vale identico nei pgTAP di
DB-13.

### 2026-08-25 · Lotto B applicato al repo — il cancello (scritto, non migrato)

Tre changeSet più l'append del codice errore ai due CSV. **Nessuna migrazione
eseguita.**

| | |
| --- | --- |
| DB-7 | `registri_fatturazione_progressivi.ultima_data` |
| DB-9 | `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` (`DATO_ERRATO`) + messaggio **989** — nessun changeSet: i mirror `runOnChange` dei due CSV lo ripescano |
| §6.2 | backfill di `ultima_data` dallo storico, forward-only |
| DB-8 | ⭐ **il cancello**, dentro `fn_get_next_progressivo`, sotto l'advisory lock |

⭐ **La correzione portante è nel lock, non nel cancello.** La chiave
dell'advisory lock passa da `registro|anno|serie` a **`registro|serie`**. Senza,
il cancello sarebbe stato aggirabile *proprio nel caso che dichiara di coprire*:
legge il massimo attraverso gli anni, ma con l'anno nel lock due numerazioni con
date in anni diversi avrebbero preso lock **diversi**, letto lo stesso massimo e
passato entrambe. Il `FOR UPDATE` sulla riga di contatore non salva — blocca la
riga dell'anno corrente, non le altre.

> **La regola, che vale oltre questo cantiere:** *il perimetro del lock deve
> coincidere con quello del controllo che ci sta dentro.* Un lock più stretto di
> ciò che il controllo legge non serializza niente.

**Tre scelte prese scrivendo:**

1. **Il bersaglio si cerca per DATA, non per numero** — e nel registro 3, oggi,
   la differenza si vede: «l'ultimo per numero» è la fattura 835 (31/07), la
   frase invece nomina il 23/08. Il pulsante avrebbe portato altrove.
2. **La chiave `bersaglio` si omette quando sarebbe vuota** (chiamata senza
   `p_fattura_id` e ultima non visibile): un array vuoto è malformato e
   lascerebbe un `W_BERSAGLIO_MALFORMATO` nel log per niente.
3. **I guard di parametro escono da `E_PARAMETRO_INVALIDO`.** La funzione vecchia
   ci metteva dentro `'p_registro_id e p_data obbligatori'` — nomi di variabili
   PL/pgSQL nella frase che legge una persona. Ora sono due guard separati con
   `E_VENDITE_CHIAMATA_NON_VALIDA` (TECNICO), più il `<= 0` sugli id che mancava.

**Verifiche** — in transazione con `ROLLBACK`, su un registro di prova creato e
distrutto lì dentro:

* stessa data dell'ultimo numerato → **passa** (decisione 7), data successiva →
  passa e il pavimento sale;
* data anteriore → `P0001` con la frase *«…che porta la data 23/08/2026»*, e il
  pavimento **non arretra** dopo il rifiuto;
* ⭐ **cross-anno**: numerato il 2027-01-05, il tentativo sul 2026-12-31 è
  **rifiutato** — è il caso che la vecchia chiave del lock non avrebbe protetto;
* **due serie sullo stesso registro** non si bloccano a vicenda (S2 riparte da 1
  mentre S1 è a 3);
* contratto errore completo: `CONSTRAINT` = il codice, `COLUMN` = `data_documento`,
  `DATATYPE` = `FATTURA:835`; e senza bersaglio il canale resta **vuoto**, non
  malformato;
* chiamata a **tre** argomenti (il chiamante attuale) ancora valida, e
  `pg_get_function_identity_arguments` conferma **una sola** firma: nessun
  overload;
* backfill sui contatori veri: registro 3 → 23/08/2026, registro 5 → 24/08/2026,
  gli stessi numeri calcolati a mano nell'analisi.

**Bonifica**: decisa (azzeramento del registro 3), script scritto e **collaudato
in transazione** — §6-bis. `UPDATE 11`, `DELETE 1`, zero inversioni residue,
nessun trigger che rifiuta. ⚠️ **Da eseguire prima del migrate**, e finisce in
`ROLLBACK`: va portato a `COMMIT` a mano.

⚠️ **Rilievo laterale, non di questo cantiere**: `scripts/codici-errore-baseline.sh`
segnala un **rientrato** preesistente (`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`)
che chiede un `--update` della baseline. Non è stato toccato: è debito altrui e
allineare una baseline è una decisione, non un effetto collaterale.

### 2026-08-25 · La bonifica cade, e i numeratori ripartono da 100

Tid, rileggendo: *«perché dovremmo rinumerarle? mica danno errore? i dati sono di
test»*. La domanda ha smontato la premessa di §6, ed era giusta.

**Le 11 fatture con le inversioni non producono nessun errore.**
`uq_fatture_numero` è soddisfatto, nessuna query legge l'ordine dei numeri,
nessun guard le guarda. ⭐ Il cancello è **rivolto in avanti**: confronta la data
del *prossimo* documento con `max(ultima_data)`, e non gli importa come si è
arrivati a quel massimo. Le inversioni sono storia brutta, non un difetto attivo.

L'unica conseguenza reale era **una riga sola**: il pavimento a 2026-08-23, e tre
`EMESSA` anteriori rifiutate. ⭐ E quelle tre date sono spazzatura comunque —
`current_date` in UTC catturati alla generazione della bozza settimane fa, non
decisioni.

**Deciso:** nessuna bonifica. Le tre bloccate diventano il **primo collaudo reale
di `fn_imposta_data_documento_lotto`** (DB-11), che è la funzione fatta apposta:
riscrive la data, **rigenera il piano rate**, salta le già numerate.

⛔ **E per questo non si sistemano con un `UPDATE` secco.** Cambiare
`fatture.data` senza rigenerare le scadenze lascia rate calcolate su una data che
il documento non porta più, e il guard D-K **non se ne accorge**: la somma non
cambia, cambiano le scadenze. Sarebbe ridicolo introdurre a mano il difetto che
DB-11 punto 4 esiste per impedire.

⭐ **Resta una cosa sola, e non è una bonifica: i numeratori ripartono da 100.**
Uno stacco visibile fra il flusso rotto (1..11) e il cancello (101+), leggibile a
colpo d'occhio in collaudo. Sei registri, un `INSERT ... ON CONFLICT`, collaudato.
⚠️ Va eseguito **dopo** il migrate: il backfill è `runOnChange: false` e girerebbe
dopo, sovrascrivendo.

**Le alternative sono state misurate davvero prima di scartarle** (§6-bis), tutte
a costo trascurabile: azzeramento, rinumerazione per data, serie storica `R2S`, e
le ultime due combinate. La tabella comparativa resta scritta perché il giorno in
cui una bonifica servisse su un database che non è di test, il confronto è già
fatto. ⚠️ E perché l'opzione scelta al primo giro — l'azzeramento — era **la
peggiore delle quattro**: lasciava 11 fatture `DEFINITIVA` senza numero.

### 2026-08-25 · Migrate fallito sul 09, e perché la prova non l'aveva visto

Tid ha lanciato il migrate. Applicati **02, 03, 04, 06, 07, 08**; il **09** è
morto con *«Unterminated string literal»*, e con lui si sono fermati 05, 10 e 11.

**Il difetto**: un **apostrofo singolo in una parola italiana tronca** dentro il
`COMMENT ON COLUMN` — `letto la' sotto`. In un letterale SQL a quote singole
quell'apostrofo **chiude la stringa**: tutte le forme `e'`, `gia'`, `piu'`,
`perche'`, `la'`… vanno raddoppiate, e in quel `COMMENT` tutte lo erano tranne
una. Corretto riformulando la frase invece di raddoppiare, così la trappola non
si ripresenta a chi rilegge.

⛔ **Perché la verifica non l'aveva presa, ed è la lezione vera.** Per i file
02, 06, 07 e 11 avevo **estratto** l'SQL dallo YAML e lo avevo eseguito intero.
Per 03, 04, 08 e 09 la prova **ricopiava a mano solo l'`ALTER TABLE`**, senza il
`COMMENT`. Una prova che riscrive l'SQL non prova il changeSet: prova quello che
si è ricopiato — e si ricopia sempre la DDL, saltando `COMMENT`, `GRANT` e
blocchi `DO`, cioè proprio i pezzi che non sembrano codice e che nessuno rilegge.
([[feedback_verificare_sql_estratto_non_riscritto]])

**Cosa è stato fatto adesso:**

* un **tokenizer** che cammina i blocchi `sql` di tutti i changeSet del cantiere
  tenendo conto del dollar-quoting e segnala i letterali non chiusi: **1 trovato**
  (il 09), **0 dopo la correzione**;
* la verifica **dinamica rifatta come si deve**, sull'SQL **estratto dallo YAML**:
  09, 11, 05 e 10 concatenati in ordine di dipendenza dentro `BEGIN; … ROLLBACK;`
  con `ON_ERROR_STOP=1`. Tutto eseguito — `COMMENT` e `GRANT` compresi — seed dei
  registri corretto (i tre cloni ereditano) e backfill che valorizza le due righe
  di contatore (registro 3 → 23/08, registro 5 → 24/08).

**Stato del database**: parziale e coerente. `DATABASECHANGELOG` registra 02, 03,
04, 06, 07, 08; `ultima_data` **non** esiste ancora. Il 09 non è stato registrato,
quindi il migrate riprende da lì senza conflitti di checksum: **basta rilanciarlo**.

⭐ **Candidato a guardrail**: quel tokenizer trova la classe intera senza toccare
il database ed è un `scripts/guardrail_*.py` naturale, gemello di
`guardrail_run_on_change.py`. Non è stato aggiunto — è una decisione, non un
effetto collaterale di una correzione.

### 2026-08-25 · Secondo migrate fallito — e la mina era in `parameters.csv`

Ripreso il migrate dopo la correzione del `09`: applicati **09** e **11**. Poi il
lotto `80_data` è morto su un changeSet **che non è di questo cantiere**:
`20250715-01-upsert_parameters`, con `E_PARAMETER_DEFAULT_VALUE_INVALID`.

**Cosa è successo.** DB-1 era un *append* a `parameters.csv`. L'append cambia il
checksum del file, il mirror è `runOnChange: true`, quindi si è **svegliato** e ha
ri-scritto **tutte** le righe — morendo su `DEFAULT_UTILITY` (id 12), che ha
`default_value = ''`. Il dispatcher `config.trgfn_parameters_fk_surrogate_dispatch`,
entrato **dopo** che quella riga fu scritta, pretende un valore esistente in
`config.utilities.codice_interno`, e la stringa vuota non c'è.

🔴 **E qui c'è la lezione, perché avevo verificato — con il controllo sbagliato.**
Avevo confrontato `parameters.csv` col database riga per riga, trovato tutto
allineato e concluso «append sicuro». **Il confronto non poteva vederlo**: la riga
è **identica** al database ed è **irriscrivibile lo stesso**.

> Le mine nei CSV con mirror `runOnChange` sono **due specie**:
> **stantìa** — il CSV dice il falso rispetto al DB (si trova col confronto);
> **irriscrivibile** — il CSV dice il vero, ma un guard entrato dopo lo rifiuta.
> La seconda si trova **solo rieseguendo l'upsert**.

⚠️ E `DEFAULT_UTILITY` è messa peggio di così: `default_value` è `NOT NULL` mentre
la sua descrizione dice «NULL = nessun default». **Quella riga non ha nessun
valore scrivibile.** Nominata in §7 — sanarla è una decisione di dominio.

**Cosa è stato fatto:**

* `parameters.csv` **ripristinato** (`git checkout`): il checksum torna quello di
  prima, il mirror si riaddormenta, il migrate si sblocca;
* DB-1 spostato su un **CSV dedicato** — `parameters_sistema.csv` + loader
  `20260825-12` — che apre la famiglia `SYSTEM_*`. È lo stesso pattern già in
  casa (`parameters_note_defaults.csv`, `parameters_documenti_storage.csv`,
  `parameters_vendite_defaults.csv`, `parameters_default_tipo_soggetto_dettaglio.csv`)
  e la stessa mossa già fatta per `registri_fatturazione.csv`;
* ⭐ **verificata la RIESEGUIBILITÀ dei quattro CSV toccati**, non più il confronto:
  ogni file caricato in una temp table e ri-upsertato riga per riga dentro
  `BEGIN; … ROLLBACK;`. `codici_errore.csv` (780 righe) ✅ ·
  `messaggi_errore.csv` (777) ✅ · `parameters_sistema.csv` ✅ — e con la riga a
  posto `script.fn_data_operativa()` risponde `2026-08-25` · 
  `registri_fatturazione_politica_data.csv` ✅.

⚠️ **Un effetto collaterale della prova, da sapere**: la prova di *controllo* su
`parameters.csv` è rimasta **appesa**. Nel percorso d'errore
`script.fn_log_error_only` tenta un `dblink` che può non tornare, e la sessione
resta attiva **tenendo un lock su `config.parameters`** — cioè bloccherebbe il
migrate successivo. Terminata con `pg_terminate_backend`; la transazione è tornata
indietro pulita (nessun `SYSTEM_FUSO_ORARIO` residuo). Chi rifà quella verifica
metta un timeout e controlli `pg_stat_activity` dopo.

**Stato del database**: `DATABASECHANGELOG` ha 02, 03, 04, 06, 07, 08, 09, 11.
Restano da applicare i tre di `80_data`: **05** (seed politiche), **10**
(backfill), **12** (parametro fuso). Nessuno dei tre è registrato, quindi il
migrate riprende da lì: **basta rilanciarlo**.

### 2026-08-25 · Il cancello statico sui letterali SQL

Chiesto da Tid dopo i due migrate falliti: *«prima finisci di risolvere, poi
scrivilo»*. Scritto e agganciato alla CI.

`scripts/guardrail_sql_letterali.py` cammina i blocchi `sql` di **changes** e
**rollback** di ogni changelog di `migrations_v2` e segnala i letterali `'`
aperti e mai chiusi. Tiene conto di dollar-quoting, commenti `--`, commenti
`/* … */` **annidati** e apostrofi raddoppiati. Statico, senza database.
Agganciato in `ci-validate.yaml` accanto agli altri due cancelli statici, prima
del migrate — che è proprio quello che vogliamo non far morire.

**Esito:** `2943` changelog esaminati, **verde**; la regressione ricostruita
(il `la'` rimesso nel `09`) viene **presa**.

⚠️ **E qui ho sbagliato di nuovo la stessa cosa, in piccolo.** La prima stesura
non gestiva i commenti `/* … */` — avevo scritto nel file, testualmente, che «nel
repo non compaiono nei blocchi sql». Falso, e misurato dopo tre minuti:
`20251026-01-create-fn-guard-sorgente-polimorfa` si apre con un `/* … */` che
contiene `l'esistenza`. Quell'apostrofo apriva un letterale fantasma, il
tokenizer perdeva il passo per 3900 caratteri e accusava un `COMMENT`
perfettamente sano 120 righe più in basso.

⛔ **Un cancello che sbaglia così viene spento dopo due segnalazioni**, e un
presidio spento è peggio di uno assente. Corretto e riverificato: zero falsi
positivi su tutto il repo.

⚠️ **Cosa NON prende, ed è scritto nel file perché non dia falsa sicurezza**: un
letterale chiuso ma nel **punto sbagliato**. Quello lo vede solo il parser di
PostgreSQL — cioè eseguire l'SQL estratto dallo YAML in transazione. I due
controlli sono complementari, non alternativi.

Regola documentata dove la si cerca: `docs/it/linee-guida-sql.md` **§11.3**, con
in §11.2 la parte nuova sulle **due specie di mina** nei CSV con mirror
`runOnChange`.

### 2026-08-25 · Lotti C e D scritti — restano i pgTAP

Sei changeSet più il codice errore **990**. **Nessuna migrazione eseguita.**

| | |
| --- | --- |
| DB-10 | `fn_get_data_minima_numerabile` (registro, serie) e `_lotto` |
| DB-11 | `fn_imposta_data_documento_lotto` — la madre: data + rate + conteggi |
| DB-14 | `trgfn_fatture_guard_data_numerata` + trigger + codice `E_FATTURA_DATA_NON_MODIFICABILE` (990) |
| DB-12 | CHECK `reset_policy = 'ANNUALE'`, poi le due funzioni senza `mese` |

**Quattro decisioni prese scrivendo:**

1. ⛔ **L'ordine 17 → 18 è invertito rispetto al piano**, e la ragione è
   misurata: `fn_numera_fattura_opz_emessa` chiama `fn_assign_numero_fattura`.
   Togliendo `mese` prima dalla *chiamata*, la chiamante farebbe
   `SELECT t.mese FROM …` su una colonna che non esiste più — errore a runtime.
   Prima la chiamante: selezionare 4 colonne su 5 è legittimo.
2. ⛔ **Il JOIN sul registro cade nel 17 e RESTA nel 18.** Nel 17 serviva solo a
   `reset_policy`; nel 18 porta anche `serie_default`, cioè **il punto in cui la
   serie di un documento si risolve davvero** — la stessa risoluzione che usano
   `fn_get_data_minima_numerabile` e il backfill. Se una delle tre diverge,
   cerca una riga di contatore che non esiste e risponde «nessun vincolo».
3. ⚠️ **DB-11 rigenera le rate solo dove un piano esiste già.** Su una `DRAFT`
   senza totali `fn_genera_scadenze_fattura` alzerebbe
   `E_SCADENZE_BASE_NON_PRONTA` e farebbe fallire l'intera dichiarazione su un
   caso legittimo. Se il piano non c'è, lo step EMESSA lo creerà con la data
   nuova: non c'è niente da riparare.
4. ⚠️ **DB-14 conia un codice invece di riusare `E_COLONNA_NON_MODIFICABILE`**,
   che pure esiste sulla stessa tabella: quel messaggio dice «Colonna non
   modificabile: %s» e non dice **perché** — e il perché è tutto. Nel segnaposto
   va il **numero**, non l'id: è quello che compare sul documento.
   ✅ Test esistenti verificati prima di aggiungere il trigger: l'unico pgTAP che
   scrive `fatture.data` non numera mai quella fattura.

**Verifiche** — DDL **estratta dagli YAML** (non riscritta) ed eseguita in
transazione, poi prove di comportamento:

* pavimento del registro con la serie risolta dal `serie_default`, serie
  esplicita, serie sbagliata → `NULL`, registro senza contatore → `NULL`,
  registro inesistente e id `<= 0` → due frasi distinte;
* pavimento dei 5 lotti con le `EMESSA` in attesa: **2026-08-23** su tutti;
* **DB-14**: cambiare la data della fattura numerata 18848 → `P0001`,
  *«Fattura 8 già numerata…»*, bersaglio `FATTURA:18848`; su una non numerata
  passa; e un `UPDATE` che non nomina `data` non scatta affatto;
* **DB-11**: data valida → `aggiornate 1, saltate 0, rate_rigenerate 1`, e la
  **prima rata si sposta** dal 23/09 al 10/10 — cioè il punto 4 funziona; data
  sotto il pavimento → rifiutata con `campo = data_documento` e bersaglio
  `LOTTO:7515`; sul lotto 4212 (due fatture numerate) → `0 aggiornate,
  2 saltate`, **non fallisce**;
* **DB-12**: `MENSILE` e `NESSUNA` rifiutati dal CHECK; le due funzioni tornano
  quattro colonne, `fn_get_next_progressivo` ha i suoi quattro parametri, e
  `pg_get_function_identity_arguments` conferma **nessun overload**;
* **il giro completo**: numerare una `EMESSA` passa dal cancello e prende il
  **101**, con `ultima_data` aggiornata alla data nuova;
* i tre guardrail statici: verdi (2949 changelog esaminati da quello nuovo).

⛔ **Un'incoerenza trovata nei dati, non nel codice** — vedi §6-ter.

**Resta DB-13**, i pgTAP. Si scrivono dopo il migrate di C e D: prima, non si
potrebbero **eseguire**, e una prova che non gira non è una prova.

---

## 6-ter. ⛔ Il contatore del registro 5 è rimasto sulla serie vecchia

Trovato il 2026-08-25 provando i lotti C e D, **dopo** che Tid aveva rinominato i
`serie_default` e portato i contatori a 100.

| registro | serie che userà | serie del contatore | |
| --- | --- | --- | --- |
| 3 Front-office | `VX2` | `VX2` | ok |
| 4 Back-office | `VX1` | `VX1` | ok |
| **5 NC** | **`RX1`** | **`''` (vuota)** | ⛔ |
| 1359/1360/1361 | `V2` / `V1` / `R2` | idem | ok |

**Cosa succede se resta così**: la serie effettiva di un documento è
`COALESCE(f.serie, r.serie_default, '')`, quindi la prossima nota di credito
cerca il contatore su `RX1`, **non lo trova**, ne crea uno a zero e prende il
numero **1** invece di 101. E `ultima_data` di `RX1` sarebbe `NULL`: su quel
sezionale il cancello **non avrebbe nessun pavimento** e accetterebbe qualunque
data. La riga con la serie vuota — `last_numero = 100`, `ultima_data = 2026-08-24`
— resterebbe orfana.

⭐ **È la conferma sul campo che la risoluzione della serie è il punto delicato
di tutto il cantiere**: rinominare un `serie_default` sposta il sezionale, e
tutto ciò che non lo risolve allo stesso modo smette di parlare della stessa
cosa. Le funzioni scritte oggi hanno retto proprio perché lo risolvono tutte con
lo stesso `COALESCE`.

**Rimedio**, una riga, collaudata (`UPDATE 1`, zero orfane, tutti e sei i
registri a `prossimo_numero = 101`) — script in
`/tmp/allinea-contatori-alla-serie.sql`:

```sql
UPDATE vendite.registri_fatturazione_progressivi rp
   SET serie = COALESCE(r.serie_default, '')
  FROM vendite.registri_fatturazione r
 WHERE r.id = rp.registro_id
   AND rp.serie <> COALESCE(r.serie_default, '')
   AND NOT EXISTS (SELECT 1 FROM vendite.registri_fatturazione_progressivi altra
                    WHERE altra.registro_id = rp.registro_id AND altra.anno = rp.anno
                      AND altra.mese = rp.mese AND altra.serie = COALESCE(r.serie_default, ''));
```

⚠️ Il `NOT EXISTS` c'è perché se sulla serie giusta esistesse **già** una riga le
due andrebbero **fuse a mano**: quale `last_numero` sopravvive è una decisione,
non una cosa da indovinare.

⚠️ **E le 11 fatture storiche del registro 3 restano sulla serie `R2`**, che ora
non è più quella del registro. Non è un difetto: è — arrivandoci per un'altra
strada — l'opzione «serie storica» confrontata in §6-bis, ottenuta rinominando la
serie **viva** invece di spostare i documenti vecchi. `uq_fatture_numero` regge
(chiave diversa) e il pavimento è stato riportato su `VX2`.

### 2026-08-25 · DB-13 — i pgTAP, scritti e VERDI. Il cantiere DB è chiuso.

Scritti **dopo** il migrate, per poterli eseguire: una prova che non gira non è
una prova.

| file | | |
| --- | --- | --- |
| `test-registri-progressivi.sql` | esteso da 6 a **14** asserzioni | ✅ |
| `test-data-documento-v1.sql` | **nuovo**, **15** asserzioni | ✅ |

⚠️ **Due file invece dei due che il brief nominava.** `test-numerazione-guard-coerenza-v1.sql`
non è stato toccato: è il test del guard **D-K**, che questo cantiere non ha
cambiato, e infilarci dentro la data l'avrebbe reso un file su due argomenti. La
data documento, la madre e il guard sulla colonna hanno preso un file loro.

**Cosa coprono, oltre alle nove voci del brief:**

* il **cross-anno** — numerato al 2026-01-01, il tentativo sul 2025-12-31 è
  rifiutato benché il contatore 2025 sia un'altra riga;
* ⭐ **`throws_like` sulle frasi**, non solo lo SQLSTATE: il rifiuto del cancello
  deve nominare *la data da cui ripartire* (`%15/03/2026%`) e quello di DB-14 il
  *numero del documento* (`%999001%`). Un test sul solo SQLSTATE resterebbe
  verde anche se il messaggio smettesse di dire l'unica cosa utile;
* **la serie risolta dal `serie_default`** — il punto su cui il rename di
  stamattina avrebbe potuto far saltare tutto;
* ⭐ **la controprova di DB-14**: su una fattura *non* numerata la data si
  cambia. Senza, «il guard funziona» e «il guard blocca tutto» sarebbero verdi
  allo stesso modo;
* ⭐ **la rigenerazione delle rate si misura sullo spostamento della prima
  scadenza**, non sul fatto che la funzione non sollevi. È l'unico modo di
  vedere il punto 4 di DB-11, che altrimenti è invisibile — il guard D-K
  verifica la somma, che non cambia;
* i tre rami fail-loud di `fn_data_operativa`, **con la sessione forzata in
  `UTC`** dentro il preambolo: è il fuso di Django, cioè quello che produceva il
  difetto.

⚠️ **Scritto in testa al file, e non lasciato scoprire a chi verrà dopo**: questi
test **non provano che il cancello stia sotto l'advisory lock**. pgTAP è
mono-sessione, il lock non si contende, e spostando il controllo *prima* del lock
il file resterebbe interamente verde. La posizione si presidia in review. È la
stessa lezione già scritta in `test-numerazione-guard-coerenza-v1.sql` sul D-K.

**Verifiche:**

* i due file: **29 asserzioni, tutte verdi**;
* i quattro file dell'area numerazione (`registri-progressivi`,
  `data-documento-v1`, `numerazione-guard-coerenza-v1`, `numera-fattura-opz-emessa`,
  `numera-nota-credito-riferimento-v1`): **PASS**;
* ⭐ **`scripts/pgtap-baseline.sh vendite` — 225 file: «Nessuna regressione,
  ogni rosso era già noto»** (5 rossi, tutti in baseline). Il trigger nuovo su
  `vendite.fatture` e le due firme cambiate non hanno rotto niente;
* i tre guardrail statici verdi, e il debito `throws_ok` **invariato a 131**: i
  test nuovi passano tutti lo SQLSTATE.

---

## 11. Stato finale del cantiere DB

**18 changeSet applicati**, 4 CSV toccati, 2 file pgTAP, 1 guardrail nuovo.
Tutte e 14 le consegne DB sono chiuse — le 13 del brief più **DB-14**, emersa
dalla verifica.

✅ **I due residui di allora sono chiusi** (aggiornato il 2026-08-25, a sera):

1. ~~`/tmp/allinea-contatori-alla-serie.sql`~~ **eseguito**: tutti e sei i
   contatori sono sulla serie che il registro usa davvero, e il registro 5 (NC)
   porta il suo pavimento al 2026-08-24. §6-ter.
2. ~~Le consegne BE-1..BE-6 e FE-1..FE-4~~ **fatte**, tranne la colonna di
   lista di FE-3 che aspetta una riga di seed. **§12**.

⚠️ E due debiti **nominati e non chiusi**, entrambi di casa d'altri: la mina in
`registri_fatturazione.csv` (§10.3 D-3) e `DEFAULT_UTILITY` che non ha nessun
valore scrivibile (§7).

---

### 11.1 · 2026-08-25 — documentazione concettuale delle sei funzioni nuove

Le pagine **auto-generate** delle sei funzioni nate in questo cantiere esistevano
già (le scrive `scripts/gen_db_docs.py` leggendo il DB vivo); mancava la metà
**manuale**, quella che le persone scrivono e che l'auto-gen non tocca mai.

| funzione | pagina |
| --- | --- |
| `script.fn_data_operativa` | `docs/it/dbzero/script/manual/fn_data_operativa.md` |
| `vendite.fn_calcola_data_documento` | `docs/it/dbzero/vendite/manual/fn_calcola_data_documento.md` |
| `vendite.fn_get_data_minima_numerabile` | `…/manual/fn_get_data_minima_numerabile.md` |
| `vendite.fn_get_data_minima_numerabile_lotto` | `…/manual/fn_get_data_minima_numerabile_lotto.md` |
| `vendite.fn_imposta_data_documento_lotto` | `…/manual/fn_imposta_data_documento_lotto.md` |
| `vendite.trgfn_fatture_guard_data_numerata` | `…/manual/trgfn_fatture_guard_data_numerata.md` |

Contenuto ricavato dai `COMMENT` sugli oggetti vivi e dal §4 di questo brief:
scopo in una frase, la regola in tabella, e — dove esiste — **la trappola**
(`current_date` che segue il fuso della sessione; la serie che si risolve
diversamente fra la targa e il cancello; il fail-open sotto RLS della targa per
lotto; le rate che vanno rigenerate perché la somma non cambia e le date sì;
`OLD.numero` e non lo stato, perché il numero arriva **mentre** la fattura è in
EMESSA).

⚠️ **Serve un'altra passata di `scripts/gen_db_docs.py`.** La riga
`include-markdown` che aggancia il manuale alla pagina di riferimento la
scrive il generatore, e **solo se il file manuale esiste già** quando gira: la
passata del 2026-08-25 è avvenuta prima che queste sei pagine fossero scritte,
quindi al momento esistono ma non sono agganciate a niente.

### 2026-08-25 · Migrazione confermata, baseline verde, documentazione chiusa

**18/18 changeSet applicati.** `scripts/pgtap-baseline.sh vendite` su 225 file:
**nessuna regressione**.

#### La doc auto-gen si è rigenerata da sola

Il migrate ha riscritto `docs/it/dbzero/`: le sei pagine nuove esistono
(`fn_data_operativa`, `fn_calcola_data_documento`, le due
`fn_get_data_minima_numerabile*`, `fn_imposta_data_documento_lotto`,
`trgfn_fatture_guard_data_numerata`) e le quattro modificate portano il corpo
nuovo. ⛔ Quelle non si toccano a mano.

#### I manuali delle funzioni nuove erano già stati scritti

Trovati in `<schema>/manual/`, tutti e sei, completi. **Non toccati.**

#### ⛔ Quello che invece mancava: il debito sui manuali ESISTENTI

E due di essi **dicevano il falso**, non erano semplicemente incompleti:

| file | stato prima | |
| --- | --- | --- |
| `fn_assign_numero_fattura.md` | «`mese` valorizzato solo se `reset_policy = MENSILE`» + `mese` nell'Output | ⛔ **falso** |
| `fn_numera_fattura_opz_emessa.md` | `mese` nell'Output | ⛔ **falso** |
| `fn_get_next_progressivo.md` | zero occorrenze di *cancello*, *monotonia*, `ultima_data` | ⚠️ muto sulla modifica più importante |
| `fn_get_or_create_fattura_header.md` | nessuna traccia della data | ⚠️ |
| `registri_fatturazione.md` | nessuna traccia di `politica_data_documento` | ⚠️ |
| `registri_fatturazione_progressivi.md` | nessuna traccia di `ultima_data` | ⚠️ |
| `fatturazione_lotti.md` | nessuna traccia di `data_documento` | ⚠️ |
| `fatture.md` | nessuna traccia del guard né del nuovo default | ⚠️ |

**Tutti e otto aggiornati**, ciascuno con una sezione `🔄 rev 2026-08-25` nello
stile che quei file già usavano (`rev 2026-08-18`, `rev 2026-08-21`), e le due
falsità corrette **in linea**, dove stavano — non solo smentite in fondo.

⭐ Il pezzo più lungo è `fn_get_next_progressivo.md`: è la funzione più cambiata
del cantiere e il suo manuale non sapeva niente del cancello. Ora dice dove sta
il controllo e perché lì, perché il lock ha perso l'anno, da dove viene il
pavimento e perché non da `vendite.fatture`, e **cosa i pgTAP non possono
provare**.

✅ Tutti i link `/dbzero/...` aggiunti puntano a pagine che esistono (verificato
file per file: il guardrail «riferimenti morti» gira dopo il migrate in CI).

---

### ✅ ~~Resta una sola azione, ed è sui dati~~ — fatta il 2026-08-25

`/tmp/allinea-contatori-alla-serie.sql` **eseguito**. Verificato dopo:
tutti e sei i contatori sono sulla serie che il registro usa davvero, e il
registro 5 (NC) porta il suo pavimento.

| registro | serie | `last_numero` | `ultima_data` |
| --- | --- | ---: | --- |
| 3 Front-office | `VX2` | 100 | 2026-08-23 |
| 4 Back-office | `VX1` | 100 | — |
| **5 NC** | **`RX1`** | 100 | **2026-08-24** |
| 1359 · 1360 · 1361 | `V2` · `V1` · `R2` | 100 | — |

Prima era così, ed è quello che si evitava — la prossima nota di credito avrebbe
preso il numero **1** invece di 101, e su quel sezionale il cancello non avrebbe
avuto **nessun pavimento**:

| registro | serie che userà | serie del contatore | |
| --- | --- | --- | --- |
| 3 · 4 · 1359 · 1360 · 1361 | VX2 · VX1 · V2 · V1 · R2 | idem | ok |
| **5 NC** | **`RX1`** | **`''`** | ⛔ |

Finché resta così, la prossima nota di credito prende il numero **1** invece di
101 e su quel sezionale **il cancello non ha pavimento**. §6-ter.

---

## 12. Il cantiere BE/FE — 2026-08-25

**Dieci consegne su dieci scritte**, una in attesa di un seed (FE-3). 4058 test
backend verdi, guard i18n pulito, build frontend senza errori, lint coi soli tre
errori preesistenti. 23 file toccati e 3 nuovi.

### 12.1 Quello che è nato

| Dove | Cosa |
| --- | --- |
| `db/_data_documento_sql.py` *(nuovo)* | I due frammenti SQL condivisi: «la data che i documenti da numerare portano oggi» e «quali lotti l'atto toccherebbe». Stesso pattern di `_coda_documento_filtro.py` |
| `pipeline_repository.py` | `get_data_minima_numerabile_lotto` · `get_data_minima_numerabile_competenza` · `get_data_documento_corrente` · `imposta_data_documento_lotto` |
| `pipeline_service.py` | `finestra_numerazione` (BE-5) · `_get_lotto_visibile` (estratto) · `numera_lotto(data_documento=…)` |
| `views.py` / `urls_v1.py` | `GET /vendite/fatturazione/finestra-numerazione/` · `data_documento` sui tre POST · `_payload_con_data_documento` |
| `NumerazioneDataDialog.vue` *(nuovo)* | Un componente, due modi (`MODO_DATA_DOCUMENTO.NUMERA` / `.CREAZIONE`), tre punti d'uso |
| `test_lotto_row_mapping.py` *(nuovo)* | Il presidio della proiezione di riga del lotto (§12.3) |

⭐ **Il pavimento si legge dal DB una volta per lotto, mai ricopiato.**
`get_data_minima_numerabile_competenza` chiama
`fn_get_data_minima_numerabile_lotto` dentro **una sola istruzione** invece di
riscriverne la regola in un JOIN: «max(ultima_data) sui sezionali delle fatture
senza numero», con la serie risolta come la risolve chi numera, vive in un posto
solo.

### 12.2 ⛔ Due difetti trovati per strada, che non erano di questo cantiere

**`riaperto` leggeva la colonna sbagliata** (`vendite_repository._map_lotto_row`):
`bool(row[20])`, cioè `totale_documenti`, invece di `row[22]`. Nessun errore —
prendeva un NUMERIC e lo passava a `bool()`, quindi il flag valeva *«questo lotto
ha un totale diverso da zero»*. Misurato sui dati veri **prima** di correggere,
ed era **invertito proprio sul caso che conta**:

| lotto | `riaperto_il` | totale | il flag diceva |
| ---: | --- | ---: | --- |
| 6034 | **sì** | 0 | `false` ⛔ |
| 7132 · 7133 · 7515 · 4213 | no | ≠ 0 | `true` ⛔ |

⚠️ È esattamente il difetto che il commento di quella colonna dice di voler
impedire: su un lotto riaperto il prossimo giro **rifà** lo step, e chiamarlo
«Avanza step» dice una cosa falsa.

**La whitelist di ordinamento dei resi** non aveva `fase` e `pratica_numero`,
accese `ordinabile = t` dal seed dell'**arco S**: la freccia a video avrebbe
risposto 400. L'ha trovato il presidio del seed
(`test_liste_configurabili_seed`), non una lettura a occhio — ed è la ragione
per cui quel presidio esiste.

### 12.3 ⭐ Il presidio nuovo, e la prova che serve

Un mapper posizionale **non fallisce mai** quando l'indice è sbagliato: legge
un'altra colonna e va avanti. `test_lotto_row_mapping.py` costruisce una riga
finta in cui ogni posizione porta un valore riconoscibile, più i due casi veri
del §12.2.

⛔ **Provato che sia rosso sul codice rotto**: rimesso `row[20]` → due
fallimenti; rimesso `row[22]` → verde. Un test che passa anche sul difetto che
dice di presidiare non è un presidio.

### 12.4 Il difetto che stavo per introdurre

`parse_competenza_mese` fa `.replace(day=1)` — perché una competenza **è** un
mese. Riusarla per la data documento avrebbe trasformato un **25/08 dichiarato
dall'operatore in un 01/08**, senza sollevare niente: cioè avrebbe scritto sui
documenti una data che nessuno ha scelto, nel cantiere che nasce per togliere le
date che nessuno ha scelto.

Nato `parse_data_iso` (nessun `.replace`, nessun default) e un test che presidia
il caso in negativo: `assertNotEqual(passata.day, 1)`.

### 12.5 La revisione critica del proprio codice (stesso giorno)

Nove correzioni, tutte su codice scritto poche ore prima:

| | Cosa | Perché contava |
| --- | --- | --- |
| bug | `get_data_documento_corrente` senza guard sul perimetro, con `int(stato or 0)` | Una chiamata sbagliata rispondeva `None` = «niente da numerare»: un errore di chiamante che esce come un dato |
| bug | Il dialog con `{ silent: true }` | Lettura **fallita** e perimetro **vuoto** erano indistinguibili: annunciava «niente da numerare» su una chiamata che non aveva risposto |
| bug | `defineProps` riferiva una costante dello scope `setup` | Vue issa le props: le costanti sono passate in `vendite/constants.js`, con `validator` — un refuso ricadeva **in silenzio** sul modo `numera`, la direzione pericolosa |
| dup | Il frammento «data corrente» in due moduli, il perimetro in tre | Il dialog avrebbe raccontato un ordine diverso da quello con cui il giro numera |
| dup | Il guard di visibilità del lotto scritto due volte | → `_get_lotto_visibile` |
| dup | La normalizzazione di `data_documento` in due endpoint | → `_payload_con_data_documento` |
| dup | Il costruttore della riga di coda diviso fra i due `except` | Il ramo `ServiceError` **perdeva campo e bersagli**: la stessa riga raccontava due storie a seconda di quale `except` l'avesse presa |
| morto | Il ramo `confirmAction` di `avvia`, `messageParams`, sei `keys.*`, quattro stringhe i18n | Tutti e tre i verbi passano dal dialog: un percorso morto accanto a uno vivo non si distingue leggendo |
| nome | `data_minima_numerabile` tornava quattro cose | → `finestra_numerazione`, fatto quando ancora nessuno la consumava |

⚠️ E una cosa **documentata invece che corretta**: `numera_lotto` dichiara la
data e poi numera in **due transazioni**. Se la numerazione fallisce, la data e
le rate rigenerate restano. Non si corregge avvolgendo tutto in un `atomic` — il
runner tiene apposta il lavoro parziale degli step già fatti — ed è il motivo per
cui l'esito porta `aggiornate`/`rate_rigenerate` **anche quando il giro si
ferma**.

### 12.6 Come è stato verificato

Con **chiamate vere**, non coi mock (i mock non vedono il binding):

```
imposta_data_documento_lotto(1278, 25/08) → aggiornate 1, rate rigenerate 1
  rate PRIMA 03/08 → rate DOPO 25/08                    (in transazione, rollback)
imposta_data_documento_lotto(1278, 01/08) → rifiutato
  code     E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO
  campo    data_documento
  bersagli [{'type': 'LOTTO', 'id': '1278'}]
  frase    «…che porta la data 23/08/2026.»
finestra_numerazione(1278)  prima: corrente 03/08, minima 23/08
                            dopo:  corrente 25/08, dichiarata 25/08
```

I tre guard nuovi provati uno per uno; il mapper confrontato riga per riga con
la tabella; l'endpoint interrogato via HTTP dopo il reload di gunicorn (401 =
c'è ed è protetto).

### 12.7 ✅ Il collaudo in-app, e la chiusura (2026-08-25)

**Tid, in applicazione:** *«ora chiede le date correttamente, sia quando scelgo
la riga da competenza fatturazione, sia quando dal lotto avanzo la
numerazione»*. Sono **le due superfici che contano**, ed erano quelle a rischio
per ragioni diverse: la prima perché il dialog ha **preso il posto** della
conferma secca (se avesse perso il testo del peso dell'operazione si sarebbe
visto lì), la seconda perché passa dal composable condiviso col kebab della
lista, cioè da uno stato che vive in una sede sola per due consumatori.

**FE-3 è completo**: la riga di seed è arrivata dal team DB
(`ui.lista_colonna` id 552), il payload la porta da BE-1 e la whitelist di
ordinamento la accetta. ⚠️ La colonna sarà **vuota** su tutti i lotti finora
esistenti, e non è un difetto: `data_documento` è la **dichiarazione**, e nessuno
dei lotti già chiusi ne ha una. Si riempirà dal primo giro fatto col dialog.

🟡 **Non collaudato, e non blocca**: il **rifiuto del cancello** su una delle tre
`EMESSA` datate prima del pavimento. È il primo caso reale di
`fn_imposta_data_documento_lotto`, ed è l'unica occasione di vedere il messaggio
del cancello con il suo bersaglio su dati veri. Provato in transazione (§12.6),
mai a video.

### 12.8 ⛔ Perché questo brief NON si sposta in `work-done/`

Chiuso non vuol dire trasferito. **15 `COMMENT` dentro il database** citano
`docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md`:

| oggetto | |
| --- | --- |
| `script.fn_data_operativa()` · `vendite.fn_calcola_data_documento` · `fn_get_data_minima_numerabile[_lotto]` · `fn_imposta_data_documento_lotto` · `fn_get_next_progressivo` · `fn_assign_numero_fattura` · `fn_numera_fattura_opz_emessa` · `fn_get_or_create_fattura_header` · `trgfn_fatture_guard_data_numerata` | funzioni |
| `fatture` · `fatturazione_lotti` · `registri_fatturazione` (×2) · `registri_fatturazione_progressivi` | tabelle |

⚠️ Quei percorsi **non stanno nei file**: stanno nei `COMMENT ON`, e
`scripts/gen_db_docs.py` li riscrive nella doc auto-generata a ogni migrate.
Spostare il brief non li corregge. Rimediare vorrebbe dire **15 changeSet** per
riscrivere altrettanti `COMMENT`.

#### 🔴 RETTIFICA 2026-08-26 — il rischio di CI non esiste, e il file si è spostato

~~Il file resta quindi in `work-in-progress/`…~~

La conclusione qui sopra poggiava su una premessa **sbagliata**: che «il
guardrail *riferimenti morti* li troverebbe dopo, in CI, su una PR che non
c'entra nulla». **Non è così.**

`scripts/sql/guardrail_riferimenti_morti.sql` — e la sua intestazione lo dice
nella prima riga — presidia i **riferimenti morti nelle funzioni plpgsql**:
compila i corpi con `plpgsql_check` e cerca **tabelle e funzioni** che non si
risolvono, più le righe di configurazione che nominano per stringa una tabella
inesistente. Non legge `pg_description`, non guarda i `COMMENT`, non sa cosa sia
un percorso `.md`. In `ci-validate.yaml` il passo si chiama, alla lettera,
*«Guardrail riferimenti morti (funzioni plpgsql + dati di config)»*.

✅ E in CI **non c'è nessun altro controllo sui link dei documenti**: la build
Zensical ha `normalize_source_file_links`, che i link verso file sorgente li
**neutralizza**, non li fa fallire.

**Quindi:** il fatto (15 `COMMENT` col vecchio percorso) è vero; la conseguenza
(una CI rossa altrove) no. Il costo reale è che chi legge un `COMMENT` o la doc
auto-gen cerca il brief in `work-in-progress/` e lo trova in `work-done/`.

⭐ **Deciso da Tid il 2026-08-26: il brief si sposta**, e con lui l'analisi. Il
debito dei 15 riferimenti è **accettato e nominato qui**. Si pagherà da sé: ogni
volta che una di quelle funzioni verrà toccata per un motivo suo, il `COMMENT`
si riscrive col percorso giusto — e nel frattempo la convenzione nuova
([[feedback_no_path_wip_negli_yaml]]) impedisce che il caso si ripeta.

### 2026-08-25 · Il brief chiude e si sposta in `work-done`

Cantiere DB completo, migrato, collaudato e pushato. Il documento passa in
`work-done/`.

⚠️ **Il brief e l'analisi si linkavano per NOME NUDO**, essendo nella stessa
cartella: spostandone uno solo si rompevano entrambe le direzioni. Corretti i
**5** link (1 dal brief verso l'analisi, 4 dall'analisi verso il brief) con i
percorsi relativi `../work-done/` e `../work-in-progress/`.
⭐ L'analisi resta in `work-in-progress`: se un giorno la si sposta, i due link
tornano a essere nomi nudi.

#### ⛔ Convenzione adottata da qui in avanti (richiesta di Tid)

> Negli YAML dei changeSet si cita il documento **per nome**, mai col percorso
> `docs/it/dev/work-in-progress/…`.

Il motivo immediato è che a cantiere chiuso il path muore e costringe a toccare
changeSet già mergiati — fattibile (sono commenti, e i file portano
`validCheckSums: ANY`) ma è churn che non doveva esistere.

⭐ **Il costo vero però non sta nello YAML: sta nel DATABASE.** Lo stesso
riferimento è dentro i `COMMENT ON FUNCTION` / `COMMENT ON COLUMN`, quindi vive
in `pg_description` e **riappare nella doc auto-gen**. Misurato su questo
cantiere: **32 occorrenze negli YAML e 16 nella doc auto-gen**, cioè nei commenti
vivi di dieci funzioni.

#### Cosa NON è stato fatto, e perché

I 32 riferimenti esistenti **restano com'erano**. Correggerli a metà — YAML sì,
database no — creerebbe una divergenza peggiore del path sbagliato; correggerli
davvero vorrebbe dire **dieci changeSet nuovi per riscrivere dei commenti**, su
oggetti appena collaudati.

⭐ Il danno residuo è che chi legge un `COMMENT ON` cerca il brief in
`work-in-progress` e lo trova in `work-done`: un secondo di attrito, e si
risolve da sé. La regola vale **per il prossimo cantiere**, dove costa zero.
