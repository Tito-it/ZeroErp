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

### DB-2 — `script.fn_data_operativa()`

```sql
RETURNS date  -- STABLE
  (now() AT TIME ZONE (SELECT default_value FROM config.parameters
                        WHERE code = 'SYSTEM_FUSO_ORARIO'))::date
```

⛔ **Fail-loud** se il parametro manca o è vuoto: `E_CONFIG_MANCANTE`, mai un
fallback silenzioso a UTC — è esattamente il difetto che stiamo chiudendo.

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

### DB-9 — il codice errore

`config.codici_errore.csv` + `config.messaggi_errore.csv` (append ai CSV; primo
id libero: **988**).

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
   `DRAFT` o `EMESSA`** (la finestra oltre la quale
   `trgfn_fattura_satellite_guard_congelamento` congela tutto);
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

* `chk_registri_fatturazione_reset` → solo `'ANNUALE'`;
* `mese` fuori dal `RETURNS TABLE` di `fn_assign_numero_fattura` e
  `fn_numera_fattura_opz_emessa`, e via il `CASE WHEN v_reset = 'MENSILE'`.
  Nessun consumatore lo legge (§2): il BE drena il result set senza guardarlo.
* colonna `registri_fatturazione_progressivi.mese`: vedi **D-1**.

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

⚠️ Preambolo obbligatorio (`BEGIN`, contesto operatore,
`SET CONSTRAINTS ALL IMMEDIATE`) e baseline
(`scripts/pgtap-baseline.sh vendite`) prima di attribuirsi un rosso.

---

## 5. Ordine di applicazione

```
DB-1 ─► DB-2 ─┐
DB-3 ─────────┼─► DB-5 ─► DB-6        (la data nasce giusta)
DB-4 ─────────┘
DB-7 ─► [bonifica §6] ─► DB-8 ─► DB-9 ─► DB-10 ─► DB-11   (il cancello)
DB-12, DB-13 in coda
```

⛔ **DB-8 dopo la bonifica**, non prima: acceso sui dati attuali blocca **6
fatture `EMESSA` legittime** (§6).

---

## 6. Bonifica (via libera di Tid)

Stato al 2026-08-25 su `dbdev`:

* registro 3: **11 fatture numerate, 3 inversioni** (numeri 3, 9 e 11);
* **6 fatture `EMESSA`** ancora da numerare, date dal 31/07 al 24/08 — con
  l'ultimo numerato al 23/08, quella del 31/07 verrebbe rifiutata;
* **7 fatture su 18** con `data <> (data_insert AT TIME ZONE 'Europe/Rome')::date`
  — lo sfasamento UTC di DB-2.

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

---

## 9. Registro

### 2026-08-25 · Analisi e consegna

Analisi sui dati veri, tre inversioni misurate, tre difetti distinti isolati
(momento sbagliato · fuso UTC · nessun cancello) e un quarto emerso strada
facendo (`reset_policy` decorativa). Decisioni prese da Tid in giornata; brief
scritto e passato al team DB. Nessuna riga di DB, BE o FE ancora scritta.
