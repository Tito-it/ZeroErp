# Analisi — Numerazione fattura: la data e la sequenza

> **Destinatari:** Tid, team DB, backend, frontend
>
> **Tipo:** analisi del processo attuale + proposta di struttura bersaglio, da
> cui è nato il brief di cantiere.
>
> ✅ **Stato: CHIUSA E COLLAUDATA** (2026-08-25). Le decisioni di §7 sono state
> prese, il cantiere è stato costruito e provato in applicazione: il riepilogo
> è in fondo, al §9.
>
> **Origine:** Tid, 2026-08-25. «Stamattina ho numerato la fattura 835 del
> 31/07/26, ha preso il numero 11 ma ci sono già fatture di agosto.»
>
> **Non siamo in produzione**: i breaking change sono ammessi e i cancelli si
> mettono restrittivi da subito ([[project_no_produzione_solo_sviluppo]]).
>
> **Seguito.** Le decisioni sono state prese da Tid il 2026-08-25 (§7) e la
> consegna è passata al team DB:
> [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md).

---

## 1. Il caso, e il fatto che non è un caso isolato

Registro 3 (`Front-office`, serie `R2`, reset `ANNUALE`), tutte le fatture
numerate, in ordine di numero:

> ⚠️ La serie di quel registro è stata poi rinominata in `VX2` e i contatori
> sono ripartiti da 100: la tabella qui sotto è il **fotogramma del difetto**,
> non lo stato di oggi.

| numero | fattura | data documento | lotto | numerata il |
| ---: | ---: | --- | ---: | --- |
| 1 | 210 | 2026-06-19 | 117 | 2026-08-05 11:45 |
| 2 | 244 | 2026-07-21 | 151 | 2026-08-05 11:45 |
| 3 | 207 | **2026-06-19** ⛔ | 106 | 2026-08-05 11:45 |
| 4 | 208 | 2026-06-19 | 107 | 2026-08-05 11:45 |
| 5 | 329 | 2026-07-27 | 245 | 2026-08-05 11:45 |
| 6 | 362 | 2026-07-28 | 278 | 2026-08-05 11:45 |
| 7 | 9916 | 2026-08-17 | 4213 | 2026-08-22 12:52 |
| 8 | 18848 | 2026-08-23 | 7133 | 2026-08-24 01:18 |
| 9 | 9914 | **2026-08-17** ⛔ | 4212 | 2026-08-24 17:08 |
| 10 | 9915 | 2026-08-17 | 4212 | 2026-08-24 17:08 |
| 11 | 835 | **2026-07-31** ⛔ | 603 | 2026-08-25 10:11 |

**Tre inversioni**, non una. Quella di stamattina è solo la più vistosa (17
giorni indietro). Il registro è già non monotòno da agosto, e nessuno se n'era
accorto perché **niente lo guarda**.

E il numero 3 dimostra che il difetto non nasce dal ritardo di un lotto: 1..6
sono stati numerati **nello stesso istante**, in un solo giro, e già lì l'ordine
delle date non è stato rispettato — perché il giro numera per **id di lotto**,
non per data documento.

---

## 2. Il processo attuale, passo per passo

### 2.1 Dove nasce la data

`vendite.fn_get_or_create_fattura_header(p_lotto_id, p_attivita_id)` — step
**DRAFT**, task `generate_fatture_righe`:

```sql
INSERT INTO vendite.fatture (registro_id, data, ...)
VALUES (v_registro_id, current_date, ...)
```

`current_date`. Punto. **Nessun'altra riga in tutto il repo scrive
`vendite.fatture.data`**: né una funzione DB, né il backend, né un endpoint, né
una schermata. Verificato con grep su `docs/it/dbzero/*/funzioni/` e su
`backend/`.

Quindi: **la data della fattura è il giorno in cui qualcuno ha premuto
«Fattura»**. Non la competenza, non una decisione, non un atto: un effetto
collaterale del momento in cui è stata generata la bozza.

### 2.2 Dove viene consumato il numero

Step **DEFINITIVA**, task `numera_fatture` →
`_handle_numera_fatture_task` ([pipeline_step_executor.py:788](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L788))
→ per fattura, in ordine di `id` crescente:

```
fn_numera_fattura_opz_emessa(fattura_id)
  ├─ ritorno idempotente se già numerata
  ├─ guard E_FATTURA_RETTIFICATA_SENZA_NUMERO (nota di credito → padre numerato)
  └─ fn_assign_numero_fattura(fattura_id)
        ├─ guard D3  — niente righe → E_FATTURA_SENZA_RIGHE
        ├─ guard D-K — 7 condizioni di coerenza del documento
        ├─ anno   := fn_get_anno_registro(f.data)            ← la data decide l'anno
        ├─ numero := fn_get_next_progressivo(registro, f.data, serie)
        │              └─ pg_advisory_xact_lock(registro|anno|serie)
        │                 UPDATE registri_fatturazione_progressivi.last_numero += 1
        └─ UPDATE fatture SET anno, serie, numero
```

**Fra i guard non ce n'è nessuno che guardi la data.** `f.data` viene usata solo
per *derivare* l'anno e la chiave del contatore, mai per *verificare* qualcosa.

`uq_fatture_numero` — `(registro_id, anno, COALESCE(serie,''), numero) WHERE
numero IS NOT NULL` — garantisce l'unicità del numero, e **null'altro**: sulle
date non dice niente.

### 2.3 Chi fa scattare la numerazione, e in che ordine

| Via | Endpoint / punto | Ordine |
| --- | --- | --- |
| Singolo lotto | `POST /vendite/lotti/<id>/numera` (`numera_lotto`) | scelto dall'operatore, un lotto per volta |
| Per competenza | `POST /vendite/fatturazione/numera` → job `FATTURAZIONE_NUMERA` | `list_lotti_numerabili` → **`ORDER BY fl.id`** |
| Backstop stampa | `numera_fattura_backstop` nel worker `coda-stampa` | nessuno: numera al volo prima del render |

Nessuna di queste tre vie guarda la data documento. La terza numera perfino
**senza un operatore davanti**.

### 2.4 Cosa dipende dalla data, e quando viene calcolato

| Cosa | Funzione | Quando gira |
| --- | --- | --- |
| Piano rate (`fatture_scadenze`) | `fn_genera_scadenze_fattura` → `v_data_rata := f.data + offset` | step **EMESSA**, cioè **prima** della numerazione |
| `fatture.anno` | `fn_get_anno_registro(f.data)` | alla numerazione |
| Chiave del contatore | `fn_get_next_progressivo(registro, data, serie)` | alla numerazione |
| Payload SDI | `fn_prepare_sdi_payload` | dopo |
| PDF | `stampa_documenti_lotto` (accoda) | dopo |

⚠️ **Il piano rate si calcola prima del numero.** E il guard D-K, prima di
consumare il progressivo, verifica che Σ rate = `totale_a_pagare`. Quindi
**data e rate sono legate**: cambiare la data dopo aver generato le rate senza
rigenerarle produce scadenze sbagliate; cambiarla dopo la numerazione non si può
affatto (§2.5).

### 2.5 La finestra in cui la data è ancora modificabile

`trgfn_fattura_satellite_guard_congelamento` blocca ogni scrittura su testata e
satelliti quando lo stato **non è** `DRAFT` o `EMESSA`. Stessa soglia in
`fn_genera_scadenze_fattura` (`E_SCADENZE_FATTURA_BLOCCATA`).

Quindi la data si può ancora cambiare **fino all'istante prima della
numerazione**, rate comprese — e mai più dopo. È esattamente la finestra dentro
cui deve entrare l'atto di dichiarare la data.

---

## 3. I difetti che producono l'inversione, e sono tre

### D1 — La data è decisa nel momento sbagliato

È un `current_date` catturato alla **generazione della bozza**, cioè giorni o
settimane prima dell'atto fiscale. Se un lotto resta indietro, la sua data resta
indietro con lui. Nessuno la può correggere: non c'è una schermata, non c'è un
endpoint, non c'è un parametro.

Fiscalmente la data documento è una **decisione** (per la differita, tipicamente
l'ultimo giorno del mese di competenza), non l'orario di un batch.

### D2 — La data è in UTC, non nel fuso dell'azienda

`backend/zeroerp_backend/settings.py`: `USE_TZ = True`, `TIME_ZONE =
'Europe/Rome'`, e **nessun `TIME_ZONE` dentro `DATABASES`**. Django imposta
allora il fuso della **sessione PostgreSQL a UTC**. Verificato:

```
tz sessione Django: UTC
current_date = 2026-08-25 | now() = 2026-08-25 08:37 UTC | (now() AT TIME ZONE 'Europe/Rome')::date = 2026-08-25
```

Conseguenza: **ogni fattura generata fra la mezzanotte e le 02:00 locali porta
la data del giorno prima.** Non è teoria — è come la 835 ha preso il 31/07:

| fattura | creata (Europe/Rome) | `data` scritta |
| ---: | --- | --- |
| 210 | 2026-06-20 **00:31** | 2026-06-19 |
| 835 | 2026-08-01 **01:09** | 2026-07-31 |
| 18848 | 2026-08-24 **01:11** | 2026-08-23 |

**7 fatture su 18** hanno oggi `data <> (data_insert AT TIME ZONE
'Europe/Rome')::date`.

⚠️ E il fuso della sessione dipende **da chi chiama**: da Django è UTC, da
psql/pgAgent è `Europe/Rome` (il default del server). La stessa funzione dà due
date diverse a seconda del canale. Il difetto **non è solo delle fatture**:
`CURRENT_DATE` è il default di colonne `data` in **25 tabelle** (ddt, ordini,
preventivi, resi, contratti, inventari, rettifiche…) e compare in **67
funzioni**. Questa analisi lo nomina, ma la bonifica generale è un cantiere suo.

### D3 — Non esiste nessun cancello sulla sequenza

Il numero si consuma senza che nessuno confronti la data documento con quella
dell'ultimo numero emesso nello stesso sezionale. Con tre vie di innesco
(§2.3), due delle quali ordinano per id di lotto e una che non ordina affatto,
**l'inversione non è un incidente: è il comportamento atteso del sistema**.

---

## 4. Il quarto difetto: `reset_policy` non ha mai fatto niente

`vendite.registri_fatturazione.reset_policy` ammette `NESSUNA | ANNUALE |
MENSILE` (CHECK). Misurato:

* è letta in **due sole funzioni** (`fn_assign_numero_fattura`,
  `fn_numera_fattura_opz_emessa`), e **solo** per calcolare il `mese` del
  `RETURNS TABLE`;
* quel `mese` **nessuno lo legge**: il repository esegue
  `SELECT vendite.fn_numera_fattura_opz_emessa(%s)` e non tocca il risultato.
  Zero occorrenze di `reset_policy` in `backend/` e in `frontend/`;
* `fn_get_anno_registro(p_data)` **non riceve nemmeno il registro**: torna
  sempre l'anno solare, e la chiave del contatore porta l'anno **sempre**.
  `fn_get_next_progressivo` tiene `v_mese SMALLINT := 0` fisso, e
  `uq_fatture_numero` non contiene il mese.

Quindi: `ANNUALE` funziona per come è fatta la chiave, `NESSUNA` si comporta
**come `ANNUALE`** (riparte lo stesso a gennaio) e `MENSILE` pure — e
implementarla a metà finirebbe in violazione di UNIQUE.

**Il catalogo promette tre comportamenti e ne fa uno.** Decisione presa: si
riduce il CHECK ad `ANNUALE` e il `mese` esce dai `RETURNS`.

---

## 5. Cosa NON è rotto — per non inseguire fantasmi

* **Il numero non lascia buchi.** `fn_get_next_progressivo` non usa `nextval`:
  è `pg_advisory_xact_lock` + `UPDATE last_numero`, quindi transazionale. Un
  rifiuto dopo il numero fa rollback anche del numero (già rettificato nella
  guida, §«Perché prima del progressivo»).
* **L'unicità del numero regge.** `uq_fatture_numero` è parziale su `numero IS
  NOT NULL` e copre registro/anno/serie.
* **La concorrenza sul contatore regge.** L'advisory lock serializza per
  `(registro, anno, serie)`.
* **La separazione fattura / nota di credito regge.** Registro e serie si
  risolvono da `(tipo_doc, natura)` con fallback su utility ed emittente: la NC
  ha il suo sezionale e la sua sequenza.

---

## 6. La struttura bersaglio

Due pezzi, e **servono entrambi**: il cancello da solo creerebbe vicoli ciechi
(un lotto rimasto indietro non si potrebbe più numerare *e* non si potrebbe
correggere), la data dichiarata da sola non impedirebbe di dichiararla
all'indietro.

### 6.A — La data documento la decide il registro

**A1. La regola vive sul registro.** Nuova colonna
`vendite.registri_fatturazione.politica_data_documento`, due valori:

| politica | data del documento |
| --- | --- |
| `OGGI` | la data operativa corrente (§6.C) — fattura immediata |
| `FINE_MESE_COMPETENZA` | ultimo giorno di `lotto.competenza_mese` (competenza 2026-07 → **31/07**) — fattura differita |

⭐ Il registro **è** il sezionale: la regola della data deve stare accanto alla
regola del numero, o si configura un registro la cui data litiga con la sua
numerazione. E c'è un guadagno che una colonna sul lotto non darebbe: **un lotto
può contenere documenti di registri diversi** (la natura instrada la nota di
credito su un registro suo), e con la regola sul registro ogni documento prende
la data giusta **da sé**.

**A2. Il lotto può scavalcarla.** Colonna **facoltativa**
`vendite.fatturazione_lotti.data_documento`: vuota → vince la politica del
registro; valorizzata → vince lei. È anche il posto dove atterra la data
digitata nel dialog di numerazione.

**A3. `fn_get_or_create_fattura_header` smette di usare `current_date`** e
scrive `fn_calcola_data_documento(registro, lotto.competenza_mese,
lotto.data_documento)`.

**A4. L'atto di numerazione può ridichiararla**, in due tempi:

1. riscrive `fatture.data` sulle fatture **non ancora numerate** del perimetro
   (finestra `DRAFT|EMESSA`, §2.5);
2. **rigenera il piano rate**;
3. poi numera.

⛔ Il punto 2 non è opzionale: senza, il guard D-K rifiuterebbe subito dopo
(Σ rate ≠ totale) oppure — peggio — passerebbe con scadenze calcolate su una
data che il documento non porta più.

### 6.B — Il cancello di monotonia

**Dove.** Dentro `fn_get_next_progressivo`, **dopo l'advisory lock**.

Non in `fn_assign_numero_fattura`, e non è un dettaglio: il controllo letto
*prima* del lock è soggetto a corsa — due transazioni leggono lo stesso massimo,
passano entrambe, poi si serializzano sul contatore e producono l'inversione che
il cancello doveva impedire. Sotto il lock, invece, la lettura e l'incremento
sono lo stesso atto. Ed è anche l'unico punto **non aggirabile**: chiunque
consumi un numero passa di lì.

**Con che chiave.** Tid dice «per registro»; l'unità di numerazione è però
**registro + serie** — il modello ammette due serie sullo stesso registro
(`tipi_doc_fiscale_registri` mappa `(tipo_doc, natura) → (registro, serie)`, e
la UNIQUE lo consente apposta). Guardare il solo registro farebbe bloccare a
vicenda due sequenze indipendenti. Chiave del cancello = **chiave del
contatore** = `(registro_id, serie)`, **attraverso gli anni** (così una data
retrodatata all'anno precedente viene fermata anche quando il suo contatore è
un altro).

**Con che dato.** Nuova colonna
`vendite.registri_fatturazione_progressivi.ultima_data date`, aggiornata a ogni
numero emesso. La regola:

```
data_documento >= max(ultima_data) su (registro_id, serie)   -- uguale ammesso
```

⭐ `registri_fatturazione_progressivi` **non ha RLS** (verificato su
`pg_class.relrowsecurity`): il massimo si legge sempre completo, per chiunque.
Se il cancello leggesse invece `vendite.fatture` — che la RLS ce l'ha, per
whitelist emittente — un perimetro ristretto restituirebbe `NULL` e il cancello
direbbe «via libera» proprio quando non sa
([[feedback_rls_conteggio_zero_non_e_un_dato]]). La colonna sul contatore
elimina il problema alla radice, ed è O(1) su una riga già bloccata.

**Con che errore.** Codice nuovo (non `E_PARAMETRO_INVALIDO`), classe
`DATO_ERRATO`, con:

* frase che nomina **la data dell'ultimo numero emesso** — il dato che serve a
  scegliere la data giusta;
* `context.campo = 'data'` per accendere il campo nel dialog;
* **bersaglio** = la fattura da numerare + l'ultima fattura numerata del
  sezionale (§ brief bersaglio-errore).

**Precheck in lettura.** La stessa regola esposta come funzione di sola lettura
(`fn_get_data_minima_numerabile(registro, serie)`), così il FE apre il
DatePicker con `minDate` già giusto e l'errore diventa l'eccezione, non la
norma.

### 6.C — La data operativa smette di dipendere dal fuso del chiamante

Helper `script.fn_data_operativa()` = `(now() AT TIME ZONE <fuso azienda>)::date`,
con il fuso da `config.parameters` (mai hardcoded — [[feedback_no_hardcoded_ids]]).
Nel perimetro di questo cantiere lo usano il default `OGGI` di A2 e il default
di colonna di `vendite.fatture.data`. La sostituzione delle altre 24 tabelle e
67 funzioni è un cantiere separato, da aprire subito dopo.

---

## 7. Le decisioni, prese il 2026-08-25

| # | Domanda | Decisione di Tid |
| --- | --- | --- |
| 1 | Bonifica dei dati esistenti | **Libera** — il cancello nasce restrittivo, niente fasi di compatibilità |
| 2 | `reset_policy` | **Solo `ANNUALE`**: `NESSUNA` e `MENSILE` escono dal CHECK (§4) |
| 3 | Dove vive la regola della data | **Sul registro**, con la data **facoltativa** sul lotto che la scavalca |
| 4 | Quando l'operatore la vede e la corregge | **In due punti**: creazione del lotto *e* dialog «Rendi definitive» |
| 5 | Atto su N lotti | **Una data sola** per l'intero atto |
| 6 | Ordine del giro | **Per data documento**, non per id di lotto |
| 7 | Stessa data dell'ultimo numerato | **Ammessa** (`>=`, non `>`) |

Consegna al team DB:
[brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md).

---

## 8. Bonifica dei dati esistenti

Oggi in `dbdev`:

* **11 fatture numerate** nel registro 3 con **3 inversioni** già scritte;
* **6 fatture EMESSA** ancora da numerare, con date da 2026-07-31 a 2026-08-24 —
  di cui almeno una (31/07) che **il nuovo cancello rifiuterebbe subito**,
  perché l'ultimo numerato porta il 23/08;
* **7 fatture** con la data sfasata di un giorno per D2.

**Via libera di Tid**: si sistemano a mano, niente codice di riparazione
(`.codex/AGENTS.md`, Workflow Safety: «i fix software per problemi di dati
creano strati di codice inutili»). Due strade equivalenti — azzerare il registro
3, oppure riallineare `fatture.data` delle numerate perché la sequenza torni
monotòna.

⛔ **Prima del cancello, non dopo**: acceso su questi dati blocca 6 fatture
`EMESSA` legittime. E subito dopo va fatto il **backfill** di
`registri_fatturazione_progressivi.ultima_data`.

---

## 9. Ripartizione del lavoro

| Lato | Cosa | Chi |
| --- | --- | --- |
| **DB** | 13 consegne, dettagliate nel brief: parametro fuso + `fn_data_operativa`; politica su `registri_fatturazione`; `fatturazione_lotti.data_documento`; `fn_calcola_data_documento`; `fn_get_or_create_fattura_header` senza `current_date`; `registri_fatturazione_progressivi.ultima_data`; **cancello in `fn_get_next_progressivo`**; codice errore; `fn_get_data_minima_numerabile`; `fn_imposta_data_documento_lotto`; `reset_policy` a una voce; pgTAP | team DB — [brief](brief-db-numerazione-data-documento-e-sequenza.md) ✅ scritto |
| **BE** | `data_documento` nei payload di creazione lotto e dei due verbi di numerazione; ordine del giro per data documento; policy del nuovo codice errore; il backstop stampa che ora può rifiutare | backend — ✅ 6/6 |
| **FE** | campo data nella creazione lotto; DatePicker nel dialog «Rendi definitive» con `minDate` dalla finestra di numerazione; colonna data documento nella lista lotti; messaggio del cancello con bersaglio | frontend — ✅ 4/4 |

> ✅ **CHIUSO E COLLAUDATO il 2026-08-25.** DB applicato (18 changeSet), BE e FE
> 10 consegne su 10, seed della colonna di lista arrivato, e **collaudo in-app
> superato**: le date vengono chieste su entrambe le superfici — la riga scelta
> dalla Dashboard Competenza e la numerazione avanzata dal drawer del lotto.
> Consuntivo, difetti trovati per strada, revisione critica e collaudo: **§12
> del [brief](brief-db-numerazione-data-documento-e-sequenza.md)**.
>
> ⛔ Il brief **resta in `work-in-progress/`**: 15 `COMMENT` dentro il database
> ne citano il percorso e si rigenerano a ogni migrate (§12.8 del brief).

⛔ Le azioni DB non erano partite da qui: il brief è passato al team DB su
`dev/db-tid`, e i prerequisiti sono stati applicati prima di toccare BE/FE
([[feedback_db_actions_passaggio_team]], [[feedback_be_fe_attende_prerequisiti_db]]).
