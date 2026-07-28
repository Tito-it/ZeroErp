# Brief BE/FE — Importi e aggregazione righe fattura, dopo il land DB

> **Tipo**: brief operativo **BE + FE** · **Target**: `dev/backend-tid` ·
> **Data**: 2026-07-28 · **Owner**: Tid · **Stato**: 🔴 **APERTO** ·
> **Priorità**: 🔴 **ALTA** — la generazione PDF delle fatture è **ferma** (due
> voci in coda in `ERRORE` con i tentativi esauriti) e i requisiti **D4** e
> **D5** appena landati sul DB **non hanno effetto** sul percorso che gira.
>
> **Origine**: sostituisce §5 e §6 di
> [brief-fix-importi-riga-fattura-zero.md](brief-fix-importi-riga-fattura-zero.md),
> scritte prima della 2ª analisi DB e ferme al perimetro iniziale (allora: solo
> B0 + B1 + «FE: nulla da fare»). Il perimetro DB è poi cresciuto con **D4**
> (aggregazione) e **D5** (kit/esposizione), che hanno conseguenze BE che quelle
> due sezioni non contengono.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.
>
> **Come leggere**: §1 è lo **stato reale** rilevato sul DB vivo, §2 è il **fatto
> che cambia il piano** (leggere per primo), §3 la **verifica su quale
> implementazione tenere**, §4-§9 il lavoro, §10 l'ordine, §11 le decisioni
> aperte.

---

## ⚡ Stato in testa

| # | Voce | Impatto | Stato |
|---|---|---|---|
| **B0** | Colonne `imposta_riga`/`totale_riga` rimosse dalla `SELECT` | sbloccava la stampa PDF | ✅ **FATTO** — verificato su DB reale (fatture 329/362/244) |
| **B1** | Nomi di contratto nel context stampa (`quantita`, `importo_riga`) | Q.tà e Importo stampavano `-` | ✅ **FATTO** + test di contratto |
| **B2** ⭐ | **D4 + D5 portati nel servizio Python**, l'implementazione in esercizio | perimetro esatto in **§3-bis** | ✅ **FATTO** — aggregazione, snapshot kit, R11, R10, `sorgente_*` NULL, `riga_nr` deterministico |
| **B3** | Il context stampa legge `vw_fattura_righe_esposte` | R17: PDF/XML/portale con dettagli divergenti | ✅ **FATTO** — + `tipo_riga`/`livello` per il template |
| **B4** | `visibilita_componenti` fuori dal BE (pronto per `-18`) | breaking su `pipeline_repository` + `types` + service | ✅ **FATTO** |
| **B5** | Coda stampa: 2 voci in `ERRORE`, tentativi esauriti | — | ⏭️ **non necessario** (Tid, 2026-07-28) |
| **B6** | `stato_esecuzione`: RUNNING all'avvio, COMPLETED alla fine | 8 attività su 8 erano ferme a `PENDING` (§3.4) | ✅ **FATTO** |
| **B7** | Ritirare la funzione DB gemella | è la trappola che ha causato questo giro | ✅ **brief pronto** → [brief-db-ritiro-generatore-righe-fattura-sql.md](../work-done/brief-db-ritiro-generatore-righe-fattura-sql.md) |
| **B8** | Template: dettaglio kit + `sconto_percentuale` | | ✅ **FATTO** — Fattura v2 (id 73) e Ordini vendita v2 (id 74), PUBBLICATE dal 2026-07-28 |
| **T** | Test BE | **3393 verdi** sull'intera suite; +11 casi nuovi su aggregazione e kit | ✅ **FATTO** (integrazione DB: §10.2 casi 7-8 ⬜) |
| **FE** | Frontend | ✅ **nessuna modifica** — verificato (§8) | ✅ |

> ✅ **Prerequisito DB soddisfatto**: `-17` e `-18` sono stati applicati il
> 2026-07-28 alle 14:30 e alle 16:57. `articolo_regole_fatturazione.visibilita_componenti`
> non esiste più e `fn_group_attivita_fatturabili` non la espone. Le tre query BE
> che la leggevano erano già state ripulite (B4) e sono state riprovate sul DB
> reale dopo il `DROP`: nessuna rottura.
>
> ⚠️ **I file YAML dei changeset `-17`/`-18` non risultano nel repo** (`fc41e80e1`
> si ferma a `-16`), insieme ai nuovi `-19`/`-20`
> (`fn_annulla_commessa_attivita`, `fn_get_commessa_stato_esclude_annullate`,
> dell'altro brief). Applicati sul DB ma non ancora pushati: da allineare, o un
> ambiente che riparte da zero non ci arriva.

---

## 1. Stato del DB — cosa è davvero applicato

Rilevato sul DB vivo `dbdev` il 2026-07-28, **non** letto dal brief.

### Applicato ✅

| Oggetto | Verifica |
|---|---|
| `imponibile_riga` valorizzato | **8 righe su 8**, prima erano 0 su 7 |
| Trigger `trg_fatture_righe_a20_importo_ins_upd` | presente e armato |
| Guard `trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt` | presente |
| `imposta_riga`, `totale_riga` | **rimosse** dalla tabella |
| Colonne kit: `kit_key`, `kit_esposto_in_fattura`, `kit_articolo_padre_id`, `kit_descrizione_padre` | presenti |
| `vendite.vw_fattura_righe_esposte` | presente (17 colonne, con `tipo_riga` / `livello` / `ordinamento`) |
| `script.fn_arrotonda_importo` | presente |
| `vw_dash_competenza_attivita` con quota proporzionale | presente — `valore_fatturato` ora valorizzato (attività 192 → 500,00; 190 → 200,00) |
| `fn_generate_fatture_righe` riscritta con aggregazione + snapshot kit | presente ⚠️ **ma non è la funzione in esercizio** (§2) |

### NON applicato ⬜

| Changeset | Contenuto | Conseguenza |
|---|---|---|
| `-17` | `fn_group_attivita_fatturabili` smette di trasportare `visibilita_componenti` | — |
| `-18` | **DROP** `articolo_regole_fatturazione.visibilita_componenti` | ⚠️ breaking BE quando verrà applicato (§6) |

Verificato: la colonna `visibilita_componenti` **esiste ancora**. Il BE non è
ancora rotto da questo, ma lo sarà.

---

## 2. ⭐ Il fatto che cambia il piano

> **Il task `generate_fatture_righe` della pipeline non esegue
> `vendite.fn_generate_fatture_righe`.** Esegue il **servizio Python**, che è
> l'implementazione in esercizio (§3) e che nessuno ha aggiornato. D4 e D5 sono
> stati scritti e applicati sulla funzione SQL, che **non viene chiamata**.

### 2.1 La catena, verificata

[`pipeline_step_executor.py:454`](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L454):

```python
action=lambda: self.fatture_righe_service.generate_fatture_righe(
    lotto_id, dry_run=dry_run,
),
```

Il nome della funzione SQL nel registry è dichiarato, testualmente, come
decorativo — [`pipeline_repository.py:143`](../../../../backend/apps/vendite/db/pipeline_repository.py#L143):

```python
# `fn` nei JSON task e` mantenuto come token di compatibilita` SQL legacy.
ALLOWED_TASK_FUNCTIONS = {
    "generate_fatture_righe": "vendite.fn_generate_fatture_righe",   # ← validato, mai eseguito
```

Il nome viene **validato** da `_validate_task_function_name`, poi ignorato: si
esegue l'`action`. Da fuori sembra che giri la funzione SQL. Non gira.

### 2.2 Cosa manca al servizio Python

[`fatture_righe_service.py:174-193`](../../../../backend/apps/vendite/services/fatture_righe_service.py#L174):

| Requisito | Servizio Python (in esercizio) | Funzione SQL (aggiornata oggi) |
|---|---|---|
| **D4** — una riga per **gruppo**, `qta` = somma esatta | ❌ `for attivita in attivita_list` → una riga per attività | `GROUP BY` + `SUM(t.quantita)` |
| **D4** — `sorgente_*` a `NULL` sulla riga aggregata | ❌ scrive la sorgente della singola attività | `NULL, NULL, NULL` |
| **D4** — `riga_nr` con ordinamento deterministico | ❌ contatore nell'ordine delle attività | `ORDER BY` su articolo/competenza/prezzo/uom/kit |
| **D4** — `meta` con `n_attivita` e `attivita_ids` | ❌ solo `group_key` | sì |
| **D5** — snapshot kit (4 colonne) | ❌ **non scrive nessuna colonna kit** | congelato dal `meta` dell'attività |
| **R11** — fail-loud se manca `componente_di` | ❌ assente | `fn_log_and_raise_error` |
| **D1** — importo di riga | ✅ **funziona su entrambi** — è del trigger, indipendente da chi inserisce | ✅ |

L'ultima riga spiega perché la verifica di land del brief DB (§11, fattura 362 →
imponibile 200,00) è risultata **verde pur girando sul percorso non aggiornato**:
il trigger fa il suo lavoro qualunque sia lo scrittore. **D1 ha mascherato che D4
e D5 non erano attivi.**

### 2.3 La prova nei dati

```
id | fattura_id | riga_nr |    qta     | prezzo | imponibile | sorgente_tipo_id | kit_key |      data_insert
 98 |       362 |       1 |   2.000000 | 100.00 |    200.000 |               13 |  (null) | 2026-07-28 11:33:05
```

La riga **98** è nata alle 11:33 di oggi, **dopo** l'applicazione dei changeset
D4/D5. Ha `sorgente_tipo_id = 13` e `sorgente_uid` valorizzato: il criterio di
accettazione D4 n. 6 chiede che sulla riga aggregata siano **NULL**.

Controprova sull'effetto mancato — fattura **244**, cinque righe:

```
63 | 244 | 1 | 5.000000 | 80.00 | 400.000
64 | 244 | 2 | 5.000000 | 80.00 | 400.000
65 | 244 | 3 | 5.000000 | 80.00 | 400.000
66 | 244 | 4 | 5.000000 | 80.00 | 400.000
67 | 244 | 5 | 5.000000 | 80.00 | 400.000
```

Stesso articolo, stesso prezzo, stessa uom, stessa IVA: **stessa chiave di
gruppo**. Con D4 attivo sarebbe **una riga** con `qta = 25` e imponibile 2.000,00.
Sono cinque. È esattamente il caso che D4 esiste per risolvere.

---

## 3. B2 — verifica: quale delle due implementazioni deve sopravvivere

> **Esito: resta il servizio Python.** La verifica conferma il ricordo di Tid.
> Una prima stesura di questo brief raccomandava l'opposto (instradare il task
> sulla funzione SQL): era basata sul principio DB-first senza aver trovato il
> documento della decisione, e su un presupposto sbagliato sulla copertura di
> test (§3.3). Le sezioni che seguono riportano le evidenze, non la conclusione.

### 3.1 La decisione era stata presa, ed è documentata

Commit **`ece04a5ff`**, 3 febbraio 2026: *«Iniziato sviluppi python — base per
architettura futura. **Riscritto funzioni sql fatturazione in Python**»*.

Il manuale backend
[`docs/it/backend/vendite/manual/fn_generate_fatture_righe.md`](../../backend/vendite/manual/fn_generate_fatture_righe.md)
lo dice senza margini:

> *«La logica di `vendite.fn_generate_fatture_righe()` **è stata portata in**
> `apps/vendite/services/fatture_righe_service.py`…»*
> *«Stato attuale: **migrazione logica completata lato Python**.»*
> *«La funzione SQL **può restare per compatibilità storica/transitoria**.»*

Con una matrice di responsabilità esplicita: **Python** = loop applicativo,
metadati riga, `dry_run`, policy errori; **DB** = locking/selezione, header
fattura, persistenza, integrità.

Non è una deriva né una dimenticanza: è l'architettura scelta. La funzione SQL è
il residuo dichiarato.

### 3.2 Cosa il servizio Python fa meglio — verificato, non asserito

| Capacità | Python | Funzione SQL |
|---|---|---|
| **`dry_run` senza effetti collaterali** | ritorna il conteggio **prima** di creare qualsiasi cosa | ❌ chiama `fn_get_or_create_fattura_header` dentro il loop **prima** del `RETURN` di dry-run — e quella funzione fa `INSERT INTO vendite.fatture` **e** `INSERT INTO vendite.fatturazione_lotti_fatture`. **Un dry-run crea le testate.** Difetto preesistente, non introdotto oggi |
| **Policy errori applicativa** | `ErrorManager` con codici di dominio (`E_GROUP_ATTIVITA_NOT_FOUND`, `E_GROUP_ATTIVITA_INVALID_DATA`), mappabili in `error_policies.py` su HTTP + azione UI | solo `fn_log_and_raise_error`, tradotto genericamente dal middleware |
| **Validazione per-attività prima di scrivere** | valida tutti i group input, poi scrive | valida implicitamente, riga per riga, mentre scrive |
| **Round-trip di rete** | 4 fissi, indipendenti da *N* | 1 |

Sul `dry_run`: oggi il difetto è **latente**, perché `_run_validated_task` ritorna
prima dell'`action` quando `dry_run` è vero, e l'entrypoint
`pipeline_service.fn_generate_fatture_righe` **non ha chiamanti**. Ma è la
differenza di cura fra le due implementazioni, e va messa a verbale: promuovere
la funzione SQL avrebbe portato dentro quel difetto.

Sui round-trip: la funzione SQL ne fa 1, il servizio 4 — ma la SQL esegue
comunque *N×2* chiamate a funzione lato server (header + group key per attività),
quindi il vantaggio è di rete, non di lavoro. **Non è un argomento decisivo in
nessuna delle due direzioni**, e la prima stesura di questo brief lo aveva
sopravvalutato.

### 3.3 ⚠️ Correzione: il pgTAP **non** copre la funzione SQL generatrice

La prima stesura sosteneva che la funzione SQL fosse «già coperta da 19 casi
pgTAP verdi». **È falso, verificato**: il file
`db/pgtap/vendite/test-fatture-righe-importo-e-kit-v1.sql` **non invoca mai**
`fn_generate_fatture_righe` (zero occorrenze). I 19 casi coprono il **trigger**
dell'importo (1-7), la **pulizia del modello** (8-10), il **congelamento**
(11-14), la **numerazione** (15), la **vista di esposizione** (16-18) e il
**vocabolario di arrotondamento** (19). I casi 17-18 popolano le righe a mano.

Due conseguenze, entrambe utili:

- **cadeva l'argomento più forte a favore della funzione SQL**: non è più
  testata dell'altra, non è testata affatto sul suo comportamento nuovo;
- **la copertura landata sopravvive intatta** alla scelta Python, perché
  verifica invarianti di database — trigger, CHECK, guard, vista — che valgono
  qualunque sia lo scrittore. Il lavoro del team DB **non va buttato**.

Resta scoperto un solo punto, **in entrambe le implementazioni**:
l'aggregazione D4. Nessun test, da nessuna parte, verifica che due attività con
la stessa chiave producano una riga sola (§9.2, casi 4-5).

### 3.4 Il servizio Python ha però un buco suo, e va chiuso nello stesso giro

La funzione SQL porta le attività da `PENDING` → `RUNNING` → `COMPLETED`. **Il
servizio Python non tocca mai `stato_esecuzione`**: `batch_insert_righe_and_mark`
scrive `fattura_riga_id` e `fatturato = TRUE`, e basta.

Rilevato sui dati:

```
 stato_esecuzione | fatturato | count |     da     |     a
 PENDING          | t         |     8 | 2026-06-20 | 2026-07-28
```

**Tutte** le attività mai fatturate sono ferme a `PENDING`. Il ciclo di vita
progettato è `fn_select_attivita_fatturabili` → `PENDING`, generazione →
`RUNNING`/`COMPLETED`, `fn_cleanup_fatture_by_ids` → `NULL`: il passo centrale
non avviene mai.

**Gravità: latente, non attiva.** Verificato che nessun consumatore vivo lo
legge — il BE filtra `stato_esecuzione` su `fatturazione_lotti_fatture`, che è
un'altra tabella, e nessuna vista usa quella di `attivita_fatturabili`. Ma è una
macchina a stati dichiarata e non implementata: la stessa famiglia del difetto
che ha aperto questo brief. Diventa la voce **B6**.

### 3.5 Conclusione operativa

**Si porta D4 + D5 nel servizio Python**, e la funzione SQL si **ritira** (§7,
voce B7). Non si lascia «per compatibilità storica»: è precisamente quella nota
nel manuale che ha permesso a un giorno di lavoro del team DB di finire su
codice non eseguito. Un residuo che sembra vivo è peggio di un residuo assente.

---

## 3-bis. Matrice di conservazione — cosa NON si perde, e cosa Python deve implementare

> Richiesta di Tid: *«la cosa importante è che sia chiaro tutto il processo di
> fatturazione su cui abbiamo lavorato stamattina e che non si deve perdere
> nell'utilizzo della funzione Python»*.
>
> Passati in rassegna **tutti e 18 i changeset** di `fc41e80e1` e le **18 regole
> R1-R18** del brief DB §4.7-ter, uno per uno, verificando **dove vive il
> presidio**. Il criterio è netto: un presidio che sta su **tabella, trigger,
> CHECK, vincolo o vista** vale per *qualunque* scrittore — Python compreso, senza
> una riga di codice. Un presidio che sta **dentro la funzione generatrice** vive
> solo lì, e va portato.
>
> **Esito in una riga: 13 changeset su 18 sono salvi da soli. Si perde solo ciò
> che il generatore SQL fa e quello Python no — più un caso che degrada in
> silenzio (§3-bis.C) e che è il più pericoloso dei tre.**

### A. Salvo da solo — nessun intervento Python (13 changeset)

| Changeset | Cosa fa | Presidio | Perché regge |
|---|---|---|---|
| `-02` | via `imposta_riga` / `totale_riga` | schema | La colonna non esiste: nessuno può scriverla |
| `-03` `-04` | **congelamento** oltre EMESSA (D1-bis, **R15**) | trigger *row-level* `BEFORE INSERT/UPDATE/DELETE` | Scatta su ogni scrittore. Verificato: ha anche il bypass GUC per il reset lotto |
| `-05` | **niente numerazione su fattura senza righe** (D3, **R16**) | guard dentro `fn_assign_numero_fattura` | ⭐ **Verificato end-to-end**: `fn_assign_numero_fattura` solleva `E_FATTURA_SENZA_RIGHE`; la chiama `fn_numera_fattura_opz_emessa`; il task `numera_fatture` la invoca via `repository.numera_fattura_opz_emessa`. **Il percorso Python ci passa già oggi** |
| `-06` | totale del payload SDI (D2) | funzione DB | Il task `prepare_sdi_payload_lotto` va via repository, non via servizio Python |
| `-07` | vocabolario unico `UP/DOWN/HALF_UP/HALF_DOWN` | 3 `CHECK` | Il BE non applica mai quei metodi: li legge soltanto nella group key. Nessun impatto |
| `-08` | `script.fn_arrotonda_importo` + **R4** (metodo ignoto → solleva) | chiamata dal trigger di riga | Python non arrotonda: lo fa il trigger |
| `-09` `-10` | **importo di riga** (D1, **R1 R2 R3 R5**) | trigger `a20` *row-level* | ⭐ Legge `articolo_regole_fatturazione` **per articolo** con fallback `2/HALF_UP`, e riscrive `imponibile_riga` a ogni INSERT/UPDATE. **Un valore passato dall'esterno viene sovrascritto** (caso pgTAP 7). È il motivo per cui le fatture sono già corrette oggi pur girando su Python |
| `-11` | FK `attivita_fatturabili.fattura_riga_id` | vincolo | `ON DELETE SET NULL`, indipendente dallo scrittore |
| `-13` | quota proporzionale in dashboard (**D4-dashboard**) | vista | ⚠️ Regge, ma **diventa significativa solo dopo D4 in Python**: con righe 1:1 la quota vale sempre 100% |
| `-14` | 4 colonne kit + **R12** (tutte o nessuna) | `CHECK chk_fatture_righe_kit_coerente` | Verificato presente: blocca una riga kit incompleta da qualunque scrittore |
| `-16` | vista di esposizione (**R13 R14 R18**) | vista | R13 (IVA diverse → due padri) è nel `JOIN`, R14/R18 nella struttura. ⚠️ **ma vedi §3-bis.C** |
| — | `imponibile_riga` **NOT NULL** | schema | Verificato: `is_nullable = NO` |

### B. Vive nel generatore — **Python deve implementarlo** (2 changeset + 2 regole)

| Origine | Cosa | Oggi in Python |
|---|---|---|
| `-12` | **D4** — una riga per gruppo, `qta` = somma esatta | ❌ una riga per attività |
| `-12` | **R8** — `sorgente_*` a NULL sulla riga aggregata | ❌ scrive la sorgente della singola attività. ⚠️ **L'indice `UNIQUE` parziale non lo intercetta**: ogni gruppo prenderebbe la sorgente di un'attività diversa, quindi niente collisione e niente errore |
| `-12` | **R6 R7** — prezzo e `kit_key` nella chiave di gruppo | ❌ `kit_key` non esiste nella chiave Python |
| `-12` | `riga_nr` su ordinamento deterministico | ❌ contatore nell'ordine di arrivo |
| `-12` | `meta` con `n_attivita` e `attivita_ids` | ❌ solo `group_key` |
| `-15` | **D5** — snapshot kit sulle 4 colonne | ❌ non le scrive |
| `-15` | **R11** — fail-loud se manca `componente_di` | ❌ assente |
| (preesistente) | `stato_esecuzione` → RUNNING → COMPLETED | ❌ §3.4 |

### C. ⚠️ Il caso che degrada **in silenzio** — l'aggregazione di stampa

> È l'esempio citato da Tid, ed è il più insidioso dei tre perché **non produce
> nessun errore, nessuna riga mancante e nessun totale sbagliato**.

La vista `vw_fattura_righe_esposte` è una `UNION ALL` di tre rami, e il primo è:

```sql
SELECT ... 'NORMALE' AS tipo_riga, ... FROM vendite.fatture_righe r
 WHERE r.kit_key IS NULL          -- ← qui
UNION ALL  ... FROM kit k                        -- KIT_PADRE
UNION ALL  ... WHERE r.kit_key IS NOT NULL AND r.kit_esposto_in_fattura IS TRUE  -- KIT_COMPONENTE
```

Il ramo `kit` aggrega su `WHERE r.kit_key IS NOT NULL`.

**Poiché il servizio Python non scrive mai `kit_key`, tutte le righe cadono nel
primo ramo.** I rami `KIT_PADRE` e `KIT_COMPONENTE` restituiscono **zero righe**,
sempre. La vista si comporta da passante, la stampa riceve un elenco piatto e
corretto, i totali tornano — e **tutto il lavoro di §4.7-bis sull'esposizione dei
kit semplicemente non avviene**.

Non c'è modo di accorgersene guardando un PDF: sembra una fattura giusta. È lo
**stesso schema del difetto d'origine** — una struttura che esiste, un
consumatore che la legge, e nessuno che la riempie.

⚠️ Aggravante: **oggi nessun kit è mai arrivato in fatturazione** (0 attività
componente su 8). Quindi il no-op è indistinguibile dal comportamento corretto
anche sui dati reali, e lo resterà finché non si costruisce un caso di prova
apposta (§10.2, casi 5-6).

### D. Non presidiato da **nessuna** parte — debito dichiarato

| Regola | Stato | Nota |
|---|---|---|
| **R10** — quantità identica fra padre e figli (`coeff_qta_snapshot = 1`) | ⚠️ **nessun presidio**, né in SQL né altrove | Verificato: la funzione SQL aggiornata **non** ha il guard proposto nel brief DB §4.7-ter. Oggi vero 30/30, ma la colonna esiste apposta per valori diversi: il giorno che qualcuno la usa, `avg(r.qta)` della vista stampa una media senza significato — e il totale resta giusto, quindi nessuno se ne accorge. **Se si porta D4 in Python, è il momento giusto per aggiungere il guard lì** |
| **R17** — PDF, XML SDI e portale leggono la stessa vista | ⚠️ disciplina applicativa | Il DB non può presidiarlo. È esattamente la voce **B3** (§9) |

### E. Changeset non ancora applicati

| Changeset | Effetto su Python |
|---|---|
| `-17` | **Nessuno**: modificava `fn_group_attivita_fatturabili` (SQL), mentre Python usa `_build_group_key`. ✅ Chiarito in B7: era **residuo**, e la funzione è stata **rimossa** il 2026-07-28 (`20260728-21`). Il changeset resta in changelog — è già pushato e non si riscrive la storia |
| `-18` | ⚠️ **Breaking**: `DROP` di `articolo_regole_fatturazione.visibilita_componenti`, letta in 5 punti del BE (§6.4) |

### F. Verifica di contorno

- **`meta.group_key` non ha consumatori** oltre alle due funzioni SQL che lo
  producono: nessuna vista, nessun codice BE/FE lo legge. Cambiarne la forma
  (togliere `visibilita_componenti`, aggiungere `n_attivita`/`attivita_ids`) **non
  rompe nulla a valle**.
- Il **vocabolario di arrotondamento** unificato da `-07` non tocca il BE: i
  metodi vengono letti nella group key ma **mai applicati** lato Python. I
  `COALESCE(..., 'HALF_UP')` di `pipeline_repository.py` sono già dentro il
  vocabolario ammesso.

---

## 4. B0 — sbloccare la stampa (urgente, indipendente da tutto)

**File**: [`vendite_repository.py:1633-1634`](../../../../backend/apps/vendite/db/vendite_repository.py#L1633),
metodo `list_fattura_righe`. Togliere:

```sql
r.imposta_riga,
r.totale_riga
```

⚠️ `r.imponibile_riga` diventa l'ultima voce della `SELECT`: **senza virgola
finale**.

**Non toccare** [`_riepilogo_iva_repo_mixin.py:58`](../../../../backend/apps/vendite/db/_riepilogo_iva_repo_mixin.py#L58),
che seleziona `totale_riga` dalle **viste di riepilogo IVA**, dove è un alias
calcolato. Omonimia, non dipendenza.

⚠️ **Correzione al brief DB §5.0**: le due voci di coda **non** sono in `PENDING`
e **non** ripartono da sole. Rilevato ora:

| Coda | Fattura | Stato | Tentativi | Errore |
|---|---|---|---|---|
| 26 | 329 | **`ERRORE`** | **5** | `ProgrammingError: la colonna r.imposta_riga non esiste` |
| 27 | 362 | **`ERRORE`** | **5** | idem |

Hanno esaurito i tentativi mentre il brief veniva scritto. Dopo la correzione
vanno **rimesse in coda a mano** (voce **B5**).

Distinta la voce **1** (fattura 210), in `ERRORE` per una causa diversa e
precedente: `UndefinedError: 'dict object' has no attribute 'denominazione'` —
difetto di template, non di questa slice.

---

## 5. B1 — nomi di contratto nel context di stampa

**File**: `vendite_repository.py`, `list_fattura_righe`.

È l'unico dei quattro context builder documento che espone i nomi di colonna DB
grezzi invece dei nomi di contratto usati dai template:

| Concetto | ordini | ddt | preventivi | **fattura** |
|---|---|---|---|---|
| quantità | `quantita` | `quantita` | `quantita` | **`qta`** ⚠️ |
| importo | `importo_riga` | `importo_riga` | `importo_riga` | **`imponibile_riga`** ⚠️ |
| sconto | `sconto_percentuale` | `sconto_percentuale` | `sconto_percentuale` | `sconto_percentuale` ✅ |

Aliasare ai nomi di contratto — **solo** quelli, non entrambe le forme: due
chiavi per lo stesso valore sono un invito a divergere.

Aggiornare anche il commento a `vendite_repository.py:1609`, che oggi afferma
che gli importi sono *«già mantenuti dal DB»*: affermazione diventata vera solo
ora, e per un motivo preciso (il trigger di D1) che va citato.

---

## 6. B2 in dettaglio — il porting di D4 e D5 in Python

Il modello di riferimento è la funzione SQL aggiornata oggi: non va promossa a
implementazione, ma **letta come specifica eseguibile**. Traduce così:

### 6.1 D4 — aggregazione

In [`fatture_righe_service.py:174`](../../../../backend/apps/vendite/services/fatture_righe_service.py#L174),
il ciclo `for attivita in attivita_list` che oggi produce un elemento di array
per attività diventa un **raggruppamento**:

1. chiave di gruppo = la `GroupAttivitaKey` già costruita da `_build_group_key`,
   **più** `kit_key` (§6.2) — due istanze di kit diverse non vanno fuse;
2. per ogni gruppo: `qta = sum(quantita)` con `Decimal`, **mai** arrotondata
   (D4-quantità: `arrotondamento_quantita_dec` non si applica all'aggregato);
3. `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` → **`None`**;
4. `meta` = `{"group_key": gk, "n_attivita": n, "attivita_ids": [...]}`;
5. `riga_nr` assegnato su un ordinamento **esplicito** dei gruppi (articolo,
   competenza dal/al, prezzo, uom, kit_key), non sull'ordine di arrivo.

⚠️ **`batch_insert_righe_and_mark` va rifatta**: oggi correla riga e attività
con `(fattura_id, riga_nr)` assumendo **1:1**
([`pipeline_repository.py:2165`](../../../../backend/apps/vendite/db/pipeline_repository.py#L2165)).
Con *n* attività per riga la CTE `correlated` deve mappare *n*→1. È la modifica
più delicata del porting, ed è quella da coprire per prima con i test §9.2.

⚠️ La chiave di gruppo Python usa `_to_float(prezzo_unitario)`
([riga 77](../../../../backend/apps/vendite/services/fatture_righe_service.py#L77)):
raggruppare su un **float** è fragile (`0.1 + 0.2`). Poiché il prezzo è ciò che
rende l'aggregazione un'identità esatta (`Σ(qᵢ×p) = p×Σqᵢ`), va usato `Decimal`
o la sua forma stringa canonica. La versione SQL non ha il problema: raggruppa
sul `jsonb` prodotto dal DB.

### 6.2 D5 — snapshot kit

Alla generazione, per ogni attività, leggere il `meta` (già risolto dal push,
nessuna risoluzione di distinta base):

| Colonna riga | Origine |
|---|---|
| `kit_key` | `segment_key` fino a `#CMP:` — solo se il `segment_key` contiene `#CMP:` |
| `kit_esposto_in_fattura` | `meta->>'esposto_in_fattura'`, default `false` |
| `kit_articolo_padre_id` | `meta->>'componente_di'` |
| `kit_descrizione_padre` | `catalogo.articoli.descrizione` del padre, congelata |

**R11 — fail-loud**: se il `segment_key` dice che è un componente ma manca
`componente_di`, **fermarsi** con `ErrorManager`. Trattarla come riga normale la
farebbe fatturare due volte (nel totale del padre e per conto suo).

Le 4 colonne vanno aggiunte all'`INSERT` di `batch_insert_righe_and_mark`, e il
CHECK `chk_fatture_righe_kit_coerente` le vuole **tutte o nessuna**.

⚠️ **Occasione per chiudere R10** (§3-bis.D). La vista stampa `avg(r.qta)` come
quantità della riga padre: la convenzione della media regge **solo** se tutti i
componenti di un kit portano la stessa quantità. Oggi è vero 30/30, ma
`coeff_qta_snapshot` esiste apposta per valori diversi, e **nessun presidio lo
verifica** — né in SQL né altrove. Il porting è il momento giusto per aggiungere
il guard qui: se i componenti di uno stesso `kit_key` hanno quantità diverse fra
loro, fermarsi. Meglio dichiararlo che stampare una media senza significato con
il totale che torna lo stesso.

### 6.3 B6 — `stato_esecuzione`

Aggiungere le due transizioni mancanti (§3.4): `RUNNING` all'inizio,
`COMPLETED` nell'`UPDATE` finale delle attività. La funzione SQL mostra
entrambe le query.

### 6.4 B4 — `visibilita_componenti`

⚠️ Con la scelta Python **il breaking di `-18` va gestito** (non sparisce come
sarebbe avvenuto instradando sulla funzione SQL). Riferimenti da togliere:

| File | Riga | Cosa |
|---|---|---|
| `pipeline_repository.py` | 1143, 1199 | `COALESCE(r.visibilita_componenti, 'solo_padre')` in due `SELECT` |
| `pipeline_repository.py` | 84, 1171, 1229 | campo di `GroupAttivitaInput` |
| `types.py` | 23 | campo di `GroupAttivitaKey` |
| `fatture_righe_service.py` | 81 | `_build_group_key` lo mette nella chiave |
| `test_fatture_righe_service.py` | 41 | fixture |

⚠️ Toglierlo dalla `GroupAttivitaKey` **cambia la chiave di raggruppamento**:
finché il valore è costante (`solo_padre` per tutti, oggi) l'effetto è nullo, ma
va fatto **insieme** al porting D4 e non prima, perché è la chiave su cui
l'aggregazione raggruppa.

Frontend: **zero riferimenti**, verificato.

---

## 7. B7 — ritirare la funzione SQL gemella

**Brief separato al team DB** ([[feedback_db_actions_passaggio_team]]).

Richiesta: `DROP FUNCTION vendite.fn_generate_fatture_righe`, oppure — se si
preferisce conservarla — un `COMMENT ON FUNCTION` che dichiari senza ambiguità
che **non è in esercizio** e che il percorso vivo è il servizio Python.

**Perché non basta lasciarla lì.** Il manuale backend dice già *«può restare per
compatibilità storica/transitoria»*, ed è proprio quella formula che ha permesso
a un giorno di lavoro (D4 + D5, changeset `-12` e `-15`) di finire su codice non
eseguito. Il residuo non è neutro: è indistinguibile dall'implementazione vera
per chi legge il registry `ALLOWED_TASK_FUNCTIONS`.

Lato BE, contestualmente: `ALLOWED_TASK_FUNCTIONS` va rivista. Oggi mappa nomi
di funzioni SQL che per `generate_fatture_righe` non vengono eseguite — il
commento *«token di compatibilità SQL legacy»* documenta l'ambiguità invece di
risolverla.

⚠️ **Anche `fn_group_attivita_fatturabili` è nella stessa condizione**: esiste in
SQL, ha uno specchio Python, e il changeset `-17` la modifica. Da chiarire nello
stesso brief se sia in esercizio o residuo — il servizio Python usa
`_build_group_key`, non la funzione SQL.

---

## 8. FE — nessuna modifica

Ri-verificato dopo l'allargamento del perimetro DB, non ereditato dal brief
precedente:

- [`DashboardCompetenzaView.vue:186`](../../../../frontend/src/vendite/views/DashboardCompetenzaView.vue#L186)
  e `:1241` leggono `valore_fatturato` / `valore_fatturato_tot`. La vista li
  espone **già valorizzati** dopo il land (attività 192 → 500,00, 190 → 200,00),
  e con la **quota proporzionale** di D4 già applicata: il FE non deve dividere
  nulla, il DB gli consegna la quota;
- [`LottoDrawer.vue:448`](../../../../frontend/src/vendite/components/LottoDrawer.vue#L448)
  legge `totale_doc`: nessun cambio di contratto;
- nessun componente FE renderizza le **righe** di fattura — la fattura si
  consulta come PDF. L'aggregazione D4 e l'esposizione kit D5 non hanno
  superficie FE;
- `visibilita_componenti`: **zero riferimenti** nel frontend.

L'aggregazione D4 rende *n* attività per riga di fattura. Il drill-down della
dashboard va da attività → fattura, mai il contrario: la direzione non
moltiplica nulla. **Nessun impatto.**

---

## 9. B3 — la rappresentazione unica per PDF, XML SDI e portale

Il brief DB pone la regola **R17**: *«PDF, XML SDI e portale leggono la stessa
vista»*, ed è l'unica regola dichiarata **non presidiabile dal database** — resta
disciplina applicativa. Il presidio, quindi, è qui.

**Oggi nessun consumatore la usa**: `vw_fattura_righe_esposte` non compare in
nessun file di `backend/` né di `frontend/` (verificato). `list_fattura_righe`
legge ancora `vendite.fatture_righe` direttamente.

**Modifica**: `list_fattura_righe` legge la **vista**, non la tabella.

Colonne esposte: `fattura_id`, `tipo_riga`, `riga_nr`, `ordinamento`, `livello`,
`fatture_righe_id`, `articolo_id`, `descrizione`, `uom_id`, `qta`,
`prezzo_unitario`, `sconto_percentuale`, `iva_id`, `iva_natura`, `imponibile`,
`dest_billing_account_id`, `kit_key`.

⚠️ **Note di implementazione**:

- la vista espone gli **id** ma non le decodifiche: i `JOIN` per
  `articolo_codice`, `uom_codice`, `iva_codice`, `iva_descrizione`,
  `iva_aliquota` che oggi sono in `list_fattura_righe` **vanno mantenuti**,
  appoggiati alla vista;
- l'ordinamento deve seguire **`ordinamento`**, non `riga_nr`: è la colonna che
  mette padre e componenti nella sequenza giusta;
- l'importo si chiama **`imponibile`**, non `imponibile_riga`: l'alias di B1
  (`AS importo_riga`) si applica su quello.

Il template dovrà distinguere `tipo_riga` e `livello` per rendere il dettaglio
kit — riga padre con il totale, componenti esposti sotto come righe descrittive.
È lavoro di **B8** (Tid, dall'app).

**Da tenere presente**: oggi nessun kit è mai arrivato in fatturazione (0
attività componente su 8, per il brief DB §4.7), quindi la vista si comporta come
un passante e la modifica è a rischio basso. Ma è anche il motivo per cui **non
sarà collaudata dai dati reali**: serve un caso di prova costruito apposta.

---

## 10. Test

### 10.1 Il fatto scomodo: la suite è verde e non ha visto niente

`./manage-test.sh apps.vendite` → **1363 test, OK**, con `list_fattura_righe`
che in produzione solleva `ProgrammingError` su ogni chiamata da stamattina.

Non è un difetto dei test: la regola di progetto impone `unittest.TestCase` con
mock, perché la CI gira **senza DB**. Ma la conseguenza va detta: **nessun test
BE può accorgersi di un disallineamento fra una `SELECT` e lo schema reale.** È
lo stesso punto cieco che ha lasciato passare il difetto d'origine.

### 10.2 Da fare

| # | Livello | Caso | Atteso |
|---|---|---|---|
| 1 | unit | `list_fattura_righe` espone le chiavi di contratto | `quantita`, `importo_riga`, `sconto_percentuale` presenti; `imposta_riga`/`totale_riga` **assenti** |
| 2 | unit | `test_build_context_righe_propagate` | fixture allineata al nuovo contratto (usa `qta`, va cambiata) |
| 3 | unit | il servizio raggruppa 2 attività con stessa chiave | **1** riga, `qta` = somma, `sorgente_*` a `None` |
| 4 | unit | 2 attività a prezzo **diverso** | **2** righe |
| 5 | unit | attività componente senza `componente_di` | solleva (R11) |
| 6 | unit | attività componente completa | 4 colonne kit valorizzate |
| 7 | **integrazione (DB reale)** | lotto con 2 attività stessa chiave | 1 riga in `fatture_righe`, **2** attività con lo stesso `fattura_riga_id` |
| 8 | **integrazione (DB reale)** | `list_fattura_righe` su fattura reale | nessun errore, importi valorizzati |
| 9 | smoke E2E | render PDF | Q.tà, Sconto, Importo **non** `-`; totali ≠ 0 |

I casi 7-8 **non possono** essere unit mockati: verificano proprio ciò che il
mock nasconde. Vanno come smoke bash contro `dbdev`, nella famiglia
`backend/scripts/smoke-test-*.sh`, con cleanup proattivo iniziale
([[feedback_smoke_test_idempotenti]]).

Il caso 9 è quello che avrebbe intercettato **entrambi** i difetti originali: lo
smoke attuale promuove un PDF fatto interamente di trattini.

---

## 11. Ordine di esecuzione

| # | Passo | Chi | Perché in questa posizione |
|---|---|---|---|
| 1 | **B0** — colonne rimosse dalla `SELECT` | BE | Indipendente e urgente: sblocca la stampa. Da fare **subito** |
| 2 | **B5** — rimettere in coda le voci 26 e 27 | Tid | Solo **dopo** B0, altrimenti bruciano altri 5 tentativi |
| 3 | **B1** — nomi di contratto | BE | Stessa `SELECT` di B0 |
| 4 | **B2** — porting D4 + D5 + **B6** (`stato_esecuzione`) in Python | BE | Il cuore. Include il rifacimento della correlazione *n*→1 |
| 5 | **B4** — rimozione `visibilita_componenti` dal BE | BE | **Insieme** al passo 4: cambia la chiave di raggruppamento |
| 6 | **DB** — applicare `-17` e `-18` | team DB | Dopo il passo 5 |
| 7 | Verifica su **lotto nuovo** con 2 attività stessa chiave | BE + Tid | Unico modo di provare che D4 è attivo. ⚠️ Non su lotti esistenti: le loro testate restano a zero per decisione (§7 del brief DB) |
| 8 | **B3** — lettura da `vw_fattura_righe_esposte` | BE | Dopo B1, sulla stessa `SELECT` già toccata |
| 9 | **B7** — brief al team DB per il ritiro della funzione SQL | BE → team DB | Dopo il passo 7: si ritira quando il sostituto è provato |
| 10 | **B8** — template con dettaglio kit + `sconto_percentuale` | Tid, dall'app | Nuove versioni: le `PUBBLICATA` sono protette da trigger |
| 11 | Smoke E2E §10.2 caso 9 | BE | Chiusura |
| 12 | Rientro doc | BE | `api_fatturazione.md` per il contratto del context; manuale `fn_generate_fatture_righe.md` (la nota «compatibilità transitoria» va tolta); brief in `work-done` |

---

## 12. Decisioni aperte

| # | Decisione | Chi | Proposta |
|---|---|---|---|
| **P1** | ~~Quale implementazione sopravvive~~ | — | ✅ **CHIUSA**: resta Python (§3) |
| **P2** | La funzione SQL si **droppa** o resta con commento di non-esercizio? | Tid + team DB | **Droppare**: un residuo che sembra vivo costa più di quanto valga (§7) |
| **P3** | ~~`fn_group_attivita_fatturabili` SQL: in esercizio o residuo come la gemella?~~ | — | ✅ **CHIUSA**: **residuo**, unico chiamante era la gemella. Entrambe **rimosse** dal DB il 2026-07-28 (changeset `20260728-21`, verificato sul vivo) — [brief B7](../work-done/brief-db-ritiro-generatore-righe-fattura-sql.md) |
| **P4** | Chiave di gruppo su `float` o `Decimal`? (§6.1) | BE | **`Decimal`**: il prezzo è ciò che rende l'aggregazione un'identità esatta |
| **P5** | `list_fattura_righe` legge la vista di esposizione **subito** (B3) o dopo? | Tid | **Subito**: rimandare significa che PDF e XML nascono già divergenti (R17) |
| **P6** | Test di integrazione su DB reale: nuova famiglia smoke o estensione? | BE | Estendere gli smoke esistenti — meno superficie nuova |
| **P7** | Il template kit: una versione nuova per volta o una sola con tutte le correzioni? | Tid | **Una sola**, dopo B3: la forma del context cambia una volta |

---

## 13. Registro

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-28 | Verifica dello stato DB dopo il land + analisi impatto BE/FE | Confermato quanto applicato (§1). **Scoperto** che il task pipeline esegue il generatore Python e non la funzione SQL: D4 e D5 inerti (§2). Rilevate 2 voci di coda stampa passate a `ERRORE` con tentativi esauriti, non `PENDING` come annotato nel brief DB. FE riconfermato a zero interventi |
| 2026-07-28 | **B8 — nuove versioni template** | `Fattura` v2 (id 73) e `Ordini vendita` v2 (id 74) create con `clone_versione` → `update_versione` → `pubblica_versione` (service admin, non SQL diretto); le v1 sono passate a `OBSOLETA` con `valido_al` 2026-07-27, auto-chiuse dalla funzione DB. Contenuto: `sconto_perc` → `sconto_percentuale` su entrambi; sulla Fattura anche il rendering del dettaglio kit (`tipo_riga`/`livello`, componenti rientrati e senza importo — il loro valore è nel totale del padre) + CSS `.row-componente`. **Render provato**: fattura 329 stampa `100.000000 · CM · 5.000000 · 0.00% · 22 · 500.000000`, **zero celle a trattino**; gerarchia kit verificata con un context costruito apposta (nessun kit è ancora arrivato in fatturazione) |
| 2026-07-28 | **Sviluppo BE: B0, B1, B2, B3, B4, B6** | 7 file, +770/−243. Suite **3393 verdi**, +11 casi nuovi (aggregazione, kit, R10/R11). Verifiche su DB reale: `list_fattura_righe` OK su 3 fatture; la CTE `n`→1 provata in transazione con rollback — trigger importo (8×10,50 → 84,00), `sorgente_*` NULL, `kit_descrizione_padre` congelata, e la **vista di esposizione che produce `KIT_PADRE` + `KIT_COMPONENTE`** (§3-bis.C risolto). Gunicorn ricaricato. Restano: B5 e B8 (Tid), B7 (brief DB), casi di integrazione §10.2 7-8 |
| 2026-07-28 | **Matrice di conservazione** (§3-bis), su richiesta di Tid | Passati uno per uno i 18 changeset e le 18 regole R1-R18. **13 changeset su 18 sono salvi da soli** perché il presidio è su tabella/trigger/CHECK/vista. ⭐ Verificato end-to-end che il guard «niente numerazione su fattura senza righe» **funziona già oggi sul percorso Python**. Trovato il caso peggiore: senza `kit_key` la vista di esposizione **degrada a passante in silenzio** e tutto il lavoro sull'aggregazione di stampa non avviene, senza alcun segnale (§3-bis.C). Rilevato che **R10 non ha presidio in nessun punto**, nemmeno nella funzione SQL |
| 2026-07-28 | **Verifica su richiesta di Tid**: quale implementazione tenere | ✅ **Python**, come da decisione documentata (commit `ece04a5ff` + manuale backend). Corretta la raccomandazione opposta della prima stesura, che si basava anche su un presupposto falso: il pgTAP **non copre** la funzione SQL generatrice (§3.3). Trovati due elementi nuovi: la funzione SQL **crea le testate in dry-run** (§3.2), il servizio Python **non avanza mai `stato_esecuzione`** — 8 attività su 8 ferme a `PENDING` (§3.4) |
