# Brief — Importi di riga fattura mai calcolati (fatture a totale zero)

> **Tipo**: brief operativo **misto DB + BE + FE** · **Target DB**: `dev/db-tid` ·
> **Target BE/FE**: `dev/backend-tid` · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: 🔴 **APERTO — nessuna riga sviluppata** · **Priorità**: 🔴 **ALTA —
> bug logico del modello** ([[feedback_bug_logici_modello]]): oggi **ogni fattura
> emessa dal sistema ha totale 0,00 €**. Non è un caso limite: è il 100% dei casi.
>
> **Origine**: segnalazione Tid 2026-07-27 sul lotto `LTF-0000359` («la fattura è
> zero perché tutte le quantità sono azzerate»); analisi su DB vivo `dbdev` la
> stessa sera.
>
> **Come leggere questo brief**: §1-§3 sono il **cosa succede e perché**, con le
> evidenze rilevate sul DB e sul codice vivi. §4 è il **perimetro DB**, scritto
> **a specifica funzionale**: dice *cosa* deve valere, **non** come implementarlo —
> l'implementazione (trigger vs colonna generata vs funzione, naming, migration)
> è scelta del team DB. §5 e §6 sono i perimetri **BE** e **FE**, scritti in modo
> **dettagliato e prescrittivo** (file, funzione, riga, prima/dopo). §7 è la
> questione **dati esistenti**, §8 i **test**, §9 l'**ordine di esecuzione**,
> §10 le **decisioni aperte**.
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → breaking change secchi ammessi, nessuna fase di compatibilità.
>
> **Sequenziamento deciso da Tid (2026-07-28)**: prima il **DB**, il BE/FE parte
> **dopo il land** ([[feedback_be_fe_attende_prerequisiti_db]]). Il perimetro
> BE/FE è comunque specificato qui sotto perché è già completamente noto e non
> dipende da scelte implementative del DB.

---

## ⚡ Stato in testa (aggiornare a ogni avanzamento)

| Fase | Contenuto | Owner | Stato |
|---|---|---|---|
| **D1** — importo di riga | `vendite.fatture_righe`: importi di riga alimentati da chi scrive la riga | team DB | 🔴 da fare |
| **D2** — payload SDI | `fn_prepare_sdi_payload` referenzia una colonna inesistente | team DB | 🔴 da fare |
| **D3** — dati esistenti | 3 fatture con righe + 2 fatture vuote, tutte a totale 0 | Tid (decisione) | 🔴 da decidere (§7) |
| **T** — pgTAP | i test attuali **mascherano** il difetto (§8.1) | team DB | 🔴 da fare |
| **B1** — context builder fattura | allineamento nomi campo riga al contratto documenti | BE | ⏸️ attende D1 |
| **B2** — template stampa | `sconto_perc` non esiste in nessun context (§5.2) | Tid via app | ⏸️ attende B1 |
| **F** — frontend | **nessuna modifica prevista** (§6) | — | ✅ n/a |

---

## 1. Sintomo osservato

Lotto `LTF-0000359` (id 245, MASSIVO, competenza 2026-07, stato `COMPLETATO`/`CHIUSO`)
→ una fattura, id **329**, `2026/R2/5`, stato **DEFINITIVA**.

Nel PDF della fattura la colonna **Q.tà** è vuota, la colonna **Sconto** è vuota,
la colonna **Importo** è vuota, e i totali di testata sono **0,00 €**.

L'ipotesi iniziale — un problema di **unità di misura / fattore di conversione** —
è stata **verificata e scartata**: vedi §2.1.

## 2. Fatti verificati (DB e codice vivi, 2026-07-27)

### 2.1 La catena delle quantità è INTATTA — nessun problema di UoM

Percorso completo dell'unica attività del lotto:

| Stadio | Chiave | Quantità | UoM | Fattore | Prezzo |
|---|---|---|---|---|---|
| `vendite.commesse_attivita` | id 192, commessa 150 | `quantita=100`, `qta_operativa=100` | `uom_id=8`, `uom_operativa_id=8` | `factor_to_base=1.0` | `prezzo_snapshot=5.0` |
| `vendite.attivita_fatturabili` | id 358 | `quantita=100`, `qta_operativa=100` | `uom_id=8`, `uom_operativa_id=8` | `factor_to_base=1.0` | `prezzo_unitario=5.0` |
| `vendite.fatture_righe` | id 89, fattura 329 | `qta=100` | `uom_id=8` | — | `prezzo_unitario=5.0` |

UoM identica in ogni stadio, fattore 1, nessuna moltiplicazione o divisione
persa. **La quantità arriva corretta fino alla riga di fattura.**

Controprova dalla vista di dashboard, `vendite.vw_dash_competenza_attivita`
per `commessa_attivita_id=192`:

- `quantita = 100.000000` ✅
- `valore = 500.0000000000000000` ✅ (calcolata al volo: `prezzo_snapshot * quantita`)
- `valore_fatturato = NULL` ❌ (letta da `fatture_righe.imponibile_riga`)

È esattamente il «buco» descritto nella segnalazione: **il valore c'è finché
viene calcolato al volo, sparisce quando viene letto da una colonna persistita.**

### 2.2 Gli importi di riga sono NULL — su tutte le righe del DB, non solo qui

```
SELECT count(*), count(imponibile_riga), count(imposta_riga), count(totale_riga)
  FROM vendite.fatture_righe;
→ 7 righe totali, 0 con imponibile_riga, 0 con imposta_riga, 0 con totale_riga
```

**7 su 7.** Non è un caso isolato né una regressione recente: non è **mai**
successo che una riga di fattura avesse il proprio importo valorizzato.

### 2.3 Nessuno scrive quelle colonne — verificato su tutti e tre i possibili autori

1. **Funzione DB** `vendite.fn_generate_fatture_righe` — è il task
   `generate_fatture_righe` della pipeline DRAFT. La sua `INSERT INTO
   vendite.fatture_righe (...)` elenca `fattura_id, riga_nr, articolo_id,
   descrizione, uom_id, qta, prezzo_unitario, iva_id, dest_billing_account_id,
   sorgente_tipo_id, sorgente_uid, sorgente_riga, meta`. **Gli importi non
   compaiono.**
2. **Repository Python** — [`pipeline_repository.py:2048`](../../../../backend/apps/vendite/db/pipeline_repository.py#L2048)
   (`insert_fattura_riga`) e [`pipeline_repository.py:2151`](../../../../backend/apps/vendite/db/pipeline_repository.py#L2151)
   (`batch_insert_righe_and_mark`): stessa lista di colonne, **stessa
   omissione**.
3. **Trigger** su `vendite.fatture_righe` — l'unico `BEFORE INSERT OR UPDATE`
   applicativo è `trgfn_fatture_righe_guard_normalize`, che normalizza solo il
   `dest_billing_account_id` ereditato dalla testata e lo snapshot
   `iva_natura`. **Non tocca gli importi.**

Interrogazione di controllo su `pg_proc` dell'intero DB: le uniche funzioni che
nominano `imponibile_riga` sono `vendite.fn_ricalcola_riepilogo_iva_fattura` e
`vendite.fn_ricalcola_riepilogo_iva_preventivo`, ed entrambe la **leggono**.
Nessun oggetto in tutto il database la scrive.

### 2.4 Come il NULL diventa uno zero in testata

```
fatture_righe.imponibile_riga = NULL
  └─> fn_ricalcola_riepilogo_iva_fattura
        ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2)   ──> 0.00
        (il COALESCE trasforma silenziosamente l'assenza di dato in uno zero legittimo)
      └─> fatture_riepiloghi_iva.imponibile = 0.000000, imposta = 0.000000
          └─> fn_ricalcola_totali_fattura
                SUM(r.imponibile), SUM(r.imposta) sui riepiloghi ──> 0
              └─> fatture.imponibile_tot = 0, imposta_tot = 0,
                  totale_doc = 0, totale_a_pagare = 0
```

Nessun passo della catena solleva un errore: ogni anello fa il suo lavoro
correttamente su un input vuoto. **Il difetto è a monte di tutti.**

### 2.5 È un'asimmetria del modello rispetto agli altri documenti

| Documento | Dove sta l'importo di riga | Chi lo produce |
|---|---|---|
| Ordine | `vw_ordini_righe_iva_base.imponibile_riga_full` (**calcolata**) | la vista, al volo |
| Preventivo | `vw_preventivi_righe_dettaglio` (**calcolata**) | la vista, al volo |
| DDT | `vw_ddt_righe_iva_base.imponibile_riga_full` (**calcolata**) | la vista, al volo |
| **Fattura** | `fatture_righe.imponibile_riga` (**colonna persistita**) | **nessuno** ❌ |

Gli altri tre documenti calcolano al volo `quantita * prezzo_unitario *
(1 - COALESCE(sconto_percentuale,0)/100)` e hanno anche un trigger
statement-level di ricalcolo totali (`trgfn_ordini_righe_ricalcola_totali` e
gemelli). La fattura, giustamente, **persiste** l'importo — è uno snapshot
fiscale, deve restare immutabile e non ricalcolabile a posteriori. Ma la
persistenza non è mai stata implementata: c'è il contenitore, manca chi lo
riempie.

Il backend dà per scontato che il DB lo faccia. Commento testuale a
[`vendite_repository.py:1609`](../../../../backend/apps/vendite/db/vendite_repository.py#L1609):

> *«Espone gli importi di riga **già mantenuti dal DB** (imponibile/imposta/totale)»*

Assunzione mai verificata, mai implementata.

### 2.6 Il template di stampa legge chiavi che il context non produce (difetto indipendente)

Difetto **separato** dal precedente e con causa diversa. Il template `Fattura`
v1 (stato `PUBBLICATA`, riga di `documenti.template_documenti_versioni`) itera
`{% for r in righe %}` e legge:

| Colonna PDF | Chiave usata dal template | Chiave realmente prodotta da `list_fattura_righe` | Esito |
|---|---|---|---|
| # | `r.get("riga_nr")` | `riga_nr` | ✅ |
| Descrizione | `r.get("descrizione")` | `descrizione` | ✅ |
| **Q.tà** | `r.get("quantita")` | **`qta`** | ❌ stampa `-` |
| UoM | `r.get("uom_codice")` | `uom_codice` | ✅ |
| Prezzo | `r.get("prezzo_unitario")` | `prezzo_unitario` | ✅ |
| **Sconto** | `r.get("sconto_perc")` | **`sconto_percentuale`** | ❌ stampa `-` |
| IVA | `r.get("iva_codice")` | `iva_codice` | ✅ |
| **Importo** | `r.get("importo_riga")` | **`imponibile_riga`** | ❌ stampa `-` |

Il context builder passa le righe **grezze**, senza reshaping —
[`fattura_document_context_builder.py:100`](../../../../backend/apps/vendite/services/fattura_document_context_builder.py#L100):
`"righe": righe`. E poiché il template usa `.get()` invece dell'accesso diretto,
**StrictUndefined non scatta**: nessun errore, il valore risulta `None`, e
`{{ ... or "-" }}` stampa un trattino.

Origine: il template Fattura è un copia-incolla del template **Ordini vendita**,
dove `quantita` e `importo_riga` **esistono davvero** (sono i nomi esposti da
`ordini_repository.list_ordine_righe`, con `importo_riga` calcolato in `SELECT`).

**Conseguenza operativa importante**: anche risolvendo §2.2-§2.4, la colonna
**Importo** e la colonna **Q.tà** del PDF continuerebbero a stampare `-`.
I due difetti vanno chiusi **entrambi** perché la fattura stampata sia corretta.

**Ricaduta laterale**: `sconto_perc` è sbagliato **anche** nel template Ordini
vendita (`ordini_repository` espone `sconto_percentuale`). La colonna Sconto è
muta su entrambe le stampe. Il template Preventivo è invece robusto: usa catene
di fallback (`r.get("qta") or r.get("quantita")`, ecc.).

### 2.7 Difetto latente sul payload SDI

`vendite.fn_prepare_sdi_payload` contiene:

```
COALESCE((SELECT SUM(ri.totale_riga)
            FROM vendite.fatture_riepiloghi_iva ri
           WHERE ri.fattura_id = ...), 0)
```

`vendite.fatture_riepiloghi_iva` **non ha** una colonna `totale_riga`. Le sue
colonne di importo sono `imponibile`, `imposta`, `arrotondamento`. Trattandosi
di plpgsql (pianificazione differita), l'errore non si manifesta finché la
funzione non viene eseguita: **il primo lotto che raggiunge lo stato INVIATA
fallisce**. Oggi non è ancora successo perché nessun lotto è arrivato a quel
punto.

### 2.8 Perché i test non hanno intercettato nulla

I pgTAP che coprono il riepilogo IVA — `test-ricalcola-riepiloghi-iva.sql`
(righe 174, 191, 225) e `test-vw-dash-competenza-v1.sql` (riga 246) — inseriscono
`imponibile_riga` **esplicitamente nella fixture**.

I test verificano quindi che, *dato* un imponibile di riga, il riepilogo e i
totali siano corretti — e infatti lo sono. **Nessun test verifica che l'atto di
creare una riga di fattura produca il suo importo.** La fixture fornisce alla
catena esattamente il dato che il percorso di produzione non genera mai. È il
motivo per cui il buco è sopravvissuto a una suite verde.

---

## 3. Diagnosi — tre difetti distinti

| # | Difetto | Effetto oggi | Livello |
|---|---|---|---|
| **A** | Nessuno alimenta gli importi di riga in `vendite.fatture_righe` | **Ogni fattura ha totale 0,00 €.** `valore_fatturato` nullo in dashboard competenza | **DB** |
| **B** | Il template stampa fattura legge 3 chiavi che il context non espone | PDF con Q.tà, Sconto, Importo a `-`, anche una volta risolto **A** | **BE + template** |
| **C** | `fn_prepare_sdi_payload` referenzia `fatture_riepiloghi_iva.totale_riga`, colonna inesistente | Latente: esplode al primo passaggio a INVIATA | **DB** |

**A** e **C** sono di competenza del team DB. **B** è metà backend (shape del
context) e metà dato applicativo (HTML del template, che risiede in tabella e
si modifica dall'app, non da migration — verificato: nessun changelog in
`migrations_v2` contiene l'HTML di quei template).

---

## 4. Perimetro DB — **cosa** deve valere

> Questa sezione è deliberatamente **funzionale**. Definisce l'invariante e i
> criteri di accettazione; **non** prescrive trigger, colonne generate, funzioni,
> naming o numerazione delle migration. La scelta implementativa è del team DB.

### 4.1 Requisito D1 — l'importo di riga esiste sempre

**Invariante richiesto**: dal momento in cui una riga di `vendite.fatture_righe`
esiste, il suo importo imponibile è **valorizzato e coerente** con quantità,
prezzo e sconto della riga stessa. Non deve esistere alcun percorso — presente
o futuro — che produca una riga di fattura priva del proprio importo.

**Perché l'invariante e non «aggiungi il calcolo al task X»**: gli scrittori di
`fatture_righe` sono oggi **due e indipendenti** — la funzione DB
`fn_generate_fatture_righe` e il repository Python (§2.3). Correggerne uno solo
lascia il buco aperto sull'altro; correggerli entrambi crea due copie della
stessa regola in due linguaggi, che divergeranno. Il presidio deve stare **dove
la riga viene scritta**, in un punto solo, valido per qualunque scrittore
attuale o futuro ([[feedback_normalize_guard_simmetrico]]).

**Formula funzionale**:

```
imponibile di riga = qta × prezzo_unitario × (1 − COALESCE(sconto_percentuale, 0) / 100)
```

È la stessa già in uso, verbatim, per ordini, preventivi e DDT (§2.5): la
simmetria fra documenti va mantenuta, non reinventata per la fattura
([[feedback_simmetria_modello_no_meta_scope]]).

**Criteri di accettazione D1**:

1. Inserendo una riga con `qta=100`, `prezzo_unitario=5`, `sconto_percentuale`
   NULL, l'imponibile di riga risulta `500`.
2. Idem con `sconto_percentuale=10` → `450`.
3. Idem con `qta=0` → `0` (zero **esplicito**, non NULL).
4. Il risultato è identico **sia** che la riga arrivi da `fn_generate_fatture_righe`,
   **sia** che arrivi da un `INSERT` diretto del backend.
5. Aggiornando `qta`, `prezzo_unitario` o `sconto_percentuale` di una riga
   esistente, l'imponibile si riallinea (vedi però D1-bis).
6. Dopo `fn_ricalcola_riepilogo_iva_fattura` + `fn_ricalcola_totali_fattura`
   sulla fattura 329 rigenerata, `totale_doc` vale 610,00 (500 + 22% IVA).

**D1-bis — immutabilità dello snapshot fiscale**: da valutare esplicitamente. La
fattura è un documento fiscale: una volta **EMESSA**, gli importi non dovrebbero
poter cambiare. Se il presidio ricalcola su ogni UPDATE, un `UPDATE` accidentale
su una fattura DEFINITIVA ne muterebbe gli importi. Il team DB valuti se il
ricalcolo vada **inibito** (o trasformato in guard fail-fast) oltre un certo
stato del documento, coerentemente con quanto già fatto in
`fn_ricalcola_riepilogo_iva_fattura`, che ammette il ricalcolo **solo** per
`DRAFT` e `EMESSA` e solleva `E_PARAMETRO_INVALIDO` altrove. Suggerisco di
riusare la stessa soglia, non di inventarne una nuova.

### 4.2 Decisione richiesta — precisione dell'importo di riga

**Serve una scelta esplicita**, perché cambia i numeri stampati:

| Opzione | Comportamento | Conseguenza |
|---|---|---|
| **(a) Precisione piena** *(raccomandata)* | l'importo di riga non viene arrotondato; l'arrotondamento avviene **una sola volta**, in aggregazione | Coerente con `fn_ricalcola_riepilogo_iva_fattura`, che **già** fa `ROUND(SUM(...), 2)`. Coerente con `imponibile_riga_full` di ordini/DDT/preventivi, esplicitamente documentato come *«per aggregazioni precise»*. Nessun doppio arrotondamento |
| **(b) Arrotondato per riga** | l'importo di riga è arrotondato secondo `arrotondamento_importi_dec` / `metodo_arrotondamento_importi` dell'emittente-utility | Il `ROUND(SUM(...))` a valle diventa un **secondo** arrotondamento su valori già arrotondati → scarti da somma su fatture con molte righe. Ma è il valore che vorresti stampare tal quale per riga |

**Raccomandazione: (a)**. Vincolo tecnico da tenere presente: la colonna è
`numeric(18,6)`, quindi «precisione piena» significa comunque troncata a 6
decimali in scrittura — sufficiente per gli importi reali, ma è un fatto da
mettere a verbale, non da scoprire dopo.

Se si sceglie **(a)**, la stampa per riga va arrotondata **lato presentazione**,
non lato dato (§5.3).

### 4.3 Requisito D1-ter — `imposta_riga` e `totale_riga`

Le altre due colonne di importo sono anch'esse sempre NULL. Prima di alimentarle
per simmetria, va deciso **se servono**. Rilevazione: nessun consumatore vivo
oggi le usa in modo funzionante — il solo riferimento è quello **rotto** di
`fn_prepare_sdi_payload` (§2.7), che peraltro le cerca sulla tabella sbagliata.
L'IVA di fattura è governata per **aggregato** in `fatture_riepiloghi_iva`
(così è nato il modello), non per riga.

Le due strade:

- **Non alimentarle** e rimuoverle dal modello, se davvero il fisco non richiede
  l'imposta per riga → il modello resta onesto, nessuna colonna vuota che
  qualcuno un giorno leggerà credendola valida;
- **Alimentarle** per completezza dello snapshot, con l'aliquota effettiva già
  risolta da `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)` come fa il
  riepilogo.

**Non lasciarle NULL senza decidere.** Una colonna persistita e mai scritta è
esattamente il difetto che ha prodotto questo brief.

### 4.4 Requisito D2 — payload SDI

`vendite.fn_prepare_sdi_payload` deve calcolare il totale documento da colonne
**esistenti**. La funzione oggi somma `ri.totale_riga` su
`vendite.fatture_riepiloghi_iva`, che espone invece `imponibile`,
`imposta`, `arrotondamento` (§2.7).

**Criterio di accettazione**: la funzione eseguita su una fattura reale
completa senza errore, e il totale prodotto coincide con
`fatture.totale_a_pagare` (o con `totale_doc`, secondo quale sia il valore
fiscalmente corretto per il tracciato — decisione del team DB).

### 4.5 Fuori perimetro DB

- **Non** toccare la formula del riepilogo IVA né dei totali: sono corretti,
  ricevevano solo input vuoti.
- **Non** toccare le viste di dashboard: `vw_dash_competenza_attivita` mostrerà
  `valore_fatturato` corretto da sola, non appena la colonna sorgente sarà
  valorizzata.
- **Non** toccare la pipeline di fatturazione (`vendite.fatturazione_pipeline`):
  non serve uno step nuovo — se l'invariante D1 è garantito alla scrittura, gli
  step esistenti funzionano così come sono.

---

## 5. Perimetro BE — **come**, in dettaglio

> Parte **dopo il land del DB** ([[feedback_be_fe_attende_prerequisiti_db]]).
> Le modifiche qui sotto sono già completamente determinate e non dipendono da
> quale implementazione il team DB sceglierà per D1.

### 5.1 B1 — allineare il context della stampa fattura al contratto documenti

**File**: [`backend/apps/vendite/db/vendite_repository.py`](../../../../backend/apps/vendite/db/vendite_repository.py),
metodo `list_fattura_righe` (riga 1612).

**Problema**: è l'**unico** dei quattro context builder documento che espone i
nomi di colonna DB grezzi invece dei nomi di contratto usati dai template.
Confronto rilevato:

| Concetto | `ordini_repository` | `ddt_repository` | `preventivi_repository` | `vendite_repository` (fattura) |
|---|---|---|---|---|
| quantità | `quantita` | `quantita` | `quantita` | **`qta`** ⚠️ |
| importo | `importo_riga` | `importo_riga` | `importo_riga` | **`imponibile_riga`** ⚠️ |
| sconto | `sconto_percentuale` | `sconto_percentuale` | `sconto_percentuale` | `sconto_percentuale` ✅ |

**Modifica**: nella `SELECT` di `list_fattura_righe`, aliasare i due campi
divergenti al nome di contratto:

```sql
r.qta              AS quantita,
...
r.imponibile_riga  AS importo_riga,
```

**Direzione della correzione — perché il BE e non il template**: tre template su
quattro concordano già su `quantita`/`importo_riga`; l'anomalo è il context
fattura. Allineare il context rende i template **uniformi fra tipi documento**,
che è la proprietà che si vuole tenere. Aliasare al contrario (aggiungere
`qta`/`imponibile_riga` ai template) propagherebbe l'eccezione.
Non è un tampone: è la rimozione dell'asimmetria ([[feedback_no_quick_fix_soluzione_assoluta]]).

**Decisione da prendere all'implementazione**: se esporre **solo** i nomi di
contratto o **anche** quelli grezzi. Raccomando **solo i nomi di contratto**:
due chiavi per lo stesso valore sono un invito a divergere. Verificare
`imposta_riga`/`totale_riga`: se il team DB decide di rimuoverle (§4.3), vanno
tolte anche dalla `SELECT`.

**Test da aggiornare**:
[`test_fattura_document_context_builder.py:140`](../../../../backend/apps/vendite/tests/services/test_fattura_document_context_builder.py#L140) —
la fixture usa `{"id": 1, "articolo_descrizione": "Art A", "qta": "2"}`; va
allineata al nuovo contratto.

**Test da aggiungere**: un test che asserisca la presenza delle chiavi di
contratto (`quantita`, `importo_riga`, `sconto_percentuale`) nel context
prodotto. È il test che oggi manca e che avrebbe intercettato §2.6.

**Aggiornare il commento** a `vendite_repository.py:1609`: oggi afferma che gli
importi sono *«già mantenuti dal DB»* — affermazione falsa fino al land di D1, e
vera solo dopo. Va riscritto citando l'invariante D1 come sua fonte.

### 5.2 B2 — template di stampa: `sconto_perc` non esiste in nessun context

**Chi lo fa**: Tid, dall'app. L'HTML dei template **non** è in
`migrations_v2` (verificato) — è dato applicativo in
`documenti.template_documenti_versioni`. Le versioni `PUBBLICATA` sono protette
da `trgfn_template_documenti_versioni_protect_pubblicata`: serve una **nuova
versione** e una pubblicazione via `fn_pubblica_template_documento_versione`,
non un UPDATE in place.

**Due template da correggere**:

| Template | Versione | Correzione |
|---|---|---|
| `Fattura` | v1 PUBBLICATA | `r.get("sconto_perc")` → `r.get("sconto_percentuale")` |
| `Ordini vendita` | v1 PUBBLICATA | `r.get("sconto_perc")` → `r.get("sconto_percentuale")` |

Dopo B1, il template Fattura **non** richiede altre modifiche: `quantita` e
`importo_riga` cominceranno a risolversi da sole.

**Nota**: la colonna Sconto è muta anche sulle stampe ordine da sempre, per la
stessa ragione. Nessuno se n'è accorto perché finora nessun documento stampato
aveva uno sconto valorizzato.

### 5.3 B3 — formattazione importi in stampa (solo se §4.2 chiude su (a))

Se l'importo di riga resta a precisione piena, il PDF stamperebbe
`500.000000`. La formattazione per la presentazione va fatta con gli helper
centralizzati già esistenti, **mai inline** ([[feedback_locale_formatters_centralizzato]]).
Verificare come i template Ordini/Preventivo formattano oggi `importo_riga`
(che arriva già `ROUND(...,2)` dal `SELECT`) e allinearsi, in modo che le tre
stampe restino identiche nell'aspetto.

### 5.4 B4 — irrobustire il contratto template↔context (opzionale, raccomandato)

Il difetto §2.6 è sopravvissuto perché `.get()` **disinnesca** StrictUndefined:
una chiave sbagliata non è un errore, è un trattino. È lo stesso meccanismo che
aveva già prodotto la stampa fattura rotta trovata in C-9
([[handoff_20260721_cockpit_fase_c_completa]]) — **secondo incidente della
stessa famiglia**, quindi vale la pena presidiarlo e non solo ripararlo.

Opzioni da valutare, in ordine di costo crescente:

1. usare accesso diretto (`r.riga_nr`) invece di `.get()` nei template dove il
   campo è **sempre** atteso, così una chiave sbagliata diventa un errore di
   render invece di un trattino silenzioso;
2. valorizzare `context_schema` su `template_documenti_versioni` (la colonna
   esiste già, oggi non usata a questo scopo) e validare il context prodotto
   contro lo schema prima del render;
3. estendere lo smoke di render E2E già esistente da C-9 con un'asserzione sul
   **contenuto** del PDF, non solo sulla sua generazione senza errori — un PDF
   pieno di trattini oggi passa lo smoke.

Il punto 3 è quello che avrebbe intercettato **entrambi** i difetti A e B.

---

## 6. Perimetro FE — nessuna modifica prevista

Verificato: **il frontend non richiede alcun intervento.** I consumatori degli
importi di fattura leggono campi già corretti nel contratto API, e mostrano zero
solo perché il dato a monte è zero:

- [`DashboardCompetenzaView.vue:186`](../../../../frontend/src/vendite/views/DashboardCompetenzaView.vue#L186)
  e `:1241` leggono `valore_fatturato` / `valore_fatturato_tot`: torneranno
  valorizzati da soli dopo D1;
- [`LottoDrawer.vue:448`](../../../../frontend/src/vendite/components/LottoDrawer.vue#L448)
  legge `totale_doc` della fattura: idem;
- non esiste alcun componente FE che renderizzi le **righe** di fattura — la
  fattura si consulta come PDF. Il difetto B è quindi interamente lato
  BE + template.

Questa voce è qui per **chiudere** la domanda, non per aprirla: se durante lo
sviluppo emergesse una schermata FE che mostra importi di riga fattura, va
riportata qui.

---

## 7. Dati esistenti — decisione richiesta a Tid

Situazione rilevata su `dbdev`:

| Fattura | Numero | Stato | Righe | Imponibile atteso | Imponibile attuale |
|---|---|---|---|---|---|
| 205 | — | DRAFT | 0 | — | 0,00 |
| 207 | 2026/R2/3 | **DEFINITIVA** | 0 | — | 0,00 |
| 208 | 2026/R2/4 | **DEFINITIVA** | 0 | — | 0,00 |
| 210 | 2026/R2/1 | **DEFINITIVA** | 1 | **200,00** | 0,00 |
| 244 | 2026/R2/2 | **DEFINITIVA** | 5 | **2.000,00** | 0,00 |
| 329 | 2026/R2/5 | **DEFINITIVA** | 1 | **500,00** | 0,00 |

Cinque documenti hanno già **numerazione fiscale assegnata** con totale zero.
Le fatture 207 e 208 sono per giunta **prive di righe** — anomalia a sé, da
guardare a parte: una DEFINITIVA senza righe non dovrebbe essere producibile.

Tre strade, la scelta è di Tid:

1. **Cancellare i dati di test** e rifare i lotti dopo il fix. È la via che
   AGENTS.md raccomanda esplicitamente per i bug di dati in sviluppo — evita di
   scrivere codice di backfill che poi va rimosso. Da preferire, **se** i lotti
   sono rigenerabili;
2. **Backfill una tantum** degli importi + rilancio di `fn_ricalcola_riepilogo_iva_fattura`
   e `fn_ricalcola_totali_fattura`. Attenzione: entrambe rifiutano documenti
   fuori da DRAFT/EMESSA, e queste sono DEFINITIVE — servirebbe un percorso
   dedicato, cioè esattamente lo strato di codice usa-e-getta da evitare;
3. **Lasciarli** come reperti storici, accettando che le prime cinque fatture
   del sistema valgano zero.

**Raccomandazione: (1).** Con la nota che serve capire a parte come siano nate
207 e 208 senza righe.

---

## 8. Test da coprire

### 8.1 pgTAP (team DB) — sanare prima la fixture che maschera il difetto

**Prerequisito**: `test-ricalcola-riepiloghi-iva.sql` (righe 174, 191, 225) e
`test-vw-dash-competenza-v1.sql` (riga 246) inseriscono `imponibile_riga`
**esplicitamente** (§2.8). Vanno rivisti: se l'importo è prodotto
dall'invariante D1, la fixture **non deve più fornirlo**, altrimenti continua a
testare uno scenario che in produzione non esiste. È il punto più importante di
questa sezione — senza questo, i nuovi test verdi non dimostrano nulla.

**Nuovi casi**:

| # | Caso | Atteso |
|---|---|---|
| 1 | INSERT riga senza sconto (`qta=100`, `prezzo=5`) | importo = 500 |
| 2 | INSERT riga con `sconto_percentuale=10` | importo = 450 |
| 3 | INSERT riga con `sconto_percentuale` NULL | trattato come 0, importo = 500 |
| 4 | INSERT riga con `qta=0` | importo = 0, **non NULL** |
| 5 | Riga creata da `fn_generate_fatture_righe` | importo valorizzato |
| 6 | UPDATE di `qta` su riga in DRAFT | importo riallineato |
| 7 | UPDATE di `qta` su fattura DEFINITIVA | secondo la decisione D1-bis (§4.1) |
| 8 | Catena completa riga → riepilogo IVA → totali | `totale_doc` = 610,00 con IVA 22% |
| 9 | `fn_prepare_sdi_payload` su fattura reale | nessun errore, totale coerente |

Prima di dichiarare rossi/verdi, usare `scripts/pgtap-baseline.sh vendite` — la
suite ha rossi preesistenti censiti.

### 8.2 Django (BE)

| # | Caso | Atteso |
|---|---|---|
| 1 | `list_fattura_righe` restituisce le chiavi di contratto | presenti `quantita`, `importo_riga`, `sconto_percentuale` |
| 2 | Context builder propaga le chiavi di contratto | il test esistente `test_build_context_righe_propagate` aggiornato |
| 3 | Render del template Fattura su context reale | nessun `-` nelle colonne Q.tà / Importo |

### 8.3 Smoke E2E

Rieseguire lo smoke di render documenti introdotto in C-9, **con l'asserzione
aggiuntiva** che il PDF prodotto contenga quantità e importi non vuoti (§5.4
punto 3). Lo smoke attuale supera un PDF interamente fatto di trattini.

---

## 9. Ordine di esecuzione

1. **Tid** — decide §4.2 (precisione), §4.3 (imposta/totale di riga) e §7 (dati
   esistenti). Sono le tre scelte che condizionano tutto il resto;
2. **Team DB** — D1 + D1-bis + D2, pgTAP §8.1 (**incluso** il risanamento delle
   fixture), doc `dbzero` manual, rigenerazione doc auto-gen;
3. **Verifica di land** — su `LTF-0000359` rigenerato: riga con importo 500,
   riepilogo IVA 500/110, `totale_doc` 610;
4. **BE** — B1 + test §8.2 (parte solo dopo il punto 3);
5. **Tid** — B2, nuove versioni dei due template + pubblicazione;
6. **Verifica finale** — PDF della fattura con Q.tà, Sconto, Importo e totali
   tutti valorizzati; smoke E2E §8.3;
7. **Chiusura** — brief in `work-done`, doc `api_fatturazione.md` aggiornata se
   il contratto del context cambia.

---

## 10. Decisioni aperte

| # | Decisione | Chi | Default proposto |
|---|---|---|---|
| **P1** | Precisione dell'importo di riga: piena o arrotondata (§4.2) | Tid + team DB | **(a) piena** |
| **P2** | `imposta_riga` / `totale_riga`: alimentare o rimuovere (§4.3) | Tid + team DB | **rimuovere**, se il fisco non le richiede per riga |
| **P3** | Ricalcolo inibito oltre EMESSA? (§4.1, D1-bis) | team DB | **sì**, stessa soglia di `fn_ricalcola_riepilogo_iva_fattura` |
| **P4** | Dati esistenti: cancellare, backfillare o lasciare (§7) | Tid | **cancellare e rifare** |
| **P5** | Context fattura: solo nomi di contratto o anche grezzi (§5.1) | BE | **solo nomi di contratto** |
| **P6** | Irrobustimento template↔context: quale opzione (§5.4) | Tid | **punto 3** (asserzione sul contenuto nello smoke) |
| **P7** | Fatture 207/208 DEFINITIVE **senza righe**: com'è potuto succedere? | da indagare | — |

---

## 11. Registro avanzamento

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-27 | Segnalazione Tid su `LTF-0000359` | fattura a zero |
| 2026-07-27 | Analisi su DB vivo `dbdev` + codice | 3 difetti identificati, ipotesi UoM **scartata con evidenza** (§2.1) |
| 2026-07-28 | Stesura di questo brief | 🔴 in attesa delle decisioni §10 e del passaggio al team DB |
