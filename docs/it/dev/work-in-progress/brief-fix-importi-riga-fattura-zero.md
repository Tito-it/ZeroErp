# Brief — Importi di riga fattura mai calcolati (fatture a totale zero)

> **Tipo**: brief operativo **misto DB + BE + FE** · **Target DB**: `dev/db-tid` ·
> **Target BE/FE**: `dev/backend-tid` · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: 🟡 **DECISIONI DB CHIUSE (2026-07-28) — sviluppo da iniziare** ·
> **Priorità**: 🔴 **ALTA — bug logico del modello**
> ([[feedback_bug_logici_modello]]): oggi **ogni fattura emessa dal sistema ha
> totale 0,00 €**. Non è un caso limite: è il 100% dei casi.
>
> **Origine**: segnalazione Tid 2026-07-27 sul lotto `LTF-0000359` («la fattura è
> zero perché tutte le quantità sono azzerate»); analisi su DB vivo `dbdev` la
> stessa sera.
>
> **Come leggere questo brief**: §1-§3 sono il **cosa succede e perché**, con le
> evidenze rilevate sul DB e sul codice vivi (§2.9-§2.11 aggiunte dall'analisi
> critica del 2026-07-28). §4 è il **perimetro DB**: nella prima stesura era a
> specifica funzionale, ora che le decisioni sono chiuse è **prescrittivo**.
> §5 e §6 sono i perimetri **BE** e **FE** (file, funzione, riga, prima/dopo).
> §7 è la questione **dati esistenti**, §8 i **test**, §9 l'**ordine di
> esecuzione**, §10 le **decisioni**, tutte chiuse.
>
> ⚠️ **Chi ha già letto la prima stesura** guardi almeno: §4.2 (la precisione è
> stata **ribaltata**), §4.1-bis (il requisito di immutabilità è stato
> **riformulato**), §4.3 e §5.0 (rimozione di due colonne, **breaking sul BE**),
> §4.5 e §7 (**nuovo requisito**, e nessun intervento sui dati).
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
| **D1** — importo di riga | `imponibile_riga` diventa **colonna generata** `round(..., 2)` `NOT NULL` | team DB | 🔴 da fare |
| **D1-bis** — congelamento | gli **input** della riga non si modificano oltre la soglia di stato | team DB | 🔴 da fare |
| **D1-ter** — pulizia modello | `imposta_riga` e `totale_riga` **rimosse** ⚠️ *breaking sul BE* | team DB | 🔴 da fare |
| **D2** — payload SDI | `fn_prepare_sdi_payload` referenzia una colonna inesistente | team DB | 🔴 da fare |
| **D3** — fattura vuota | guard: non si numera una fattura **senza righe** (origine di 207/208) | team DB | 🔴 da fare |
| **T** — pgTAP | i test attuali **mascherano** il difetto; le fixture si romperanno da sole (§8.1) | team DB | 🔴 da fare |
| **DATI** — fatture a zero | **nessun intervento** — decisione Tid 2026-07-28 (§7) | — | ✅ chiuso |
| **B0** — colonne rimosse | `list_fattura_righe` smette di selezionare le 2 colonne | BE | ⏸️ attende D1-ter |
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

### 2.9 La specifica esisteva già — scritta come voce **opzionale** di roadmap

Aggiunto dall'analisi critica del 2026-07-28. Il manuale
`docs/it/dbzero/vendite/manual/fatture_righe.md` contiene, alle righe 65-67, la
formula per intero:

```
imponibile_riga = round(qta * prezzo_unitario * (1 - sconto_percentuale/100), dec_importi)
imposta_riga    = round(imponibile_riga * (iva_perc/100), dec_importi)
totale_riga     = imponibile_riga + imposta_riga
```

E alla riga 112, sotto «estensioni / roadmap»:

> *«Calcolo automatico importi: **opzionale** trigger BEFORE INSERT/UPDATE per
> calcolare e arrotondare `imponibile_riga`, `imposta_riga`, `totale_riga` se non
> forniti.»*

**È l'origine del difetto.** La regola era progettata e scritta, ma classificata
come facoltativa e mai implementata; nel frattempo il backend l'ha data per
fatta (§2.5). Un requisito marcato «opzionale» in un documento e assunto
«presente» nel codice a valle è esattamente il modo in cui un buco sopravvive
per mesi.

Il manuale è inoltre **stale in due punti**, e va corretto insieme al fix:

- cita `iva_perc` **sulla riga**, colonna che non esiste più — il trigger di
  normalize dichiara esplicitamente *«NON gestisce più aliquota (`iva_perc`) né
  assoggettamento»*;
- prescrive `round(..., dec_importi)` per **tutte e tre** le colonne, cioè
  l'arrotondamento configurabile anche a livello di riga. È sbagliato: quella
  configurazione governa il **totale a pagare**, non la riga (§2.10).

### 2.10 L'arrotondamento configurabile governa il **totale**, non la riga

Rilevato nella stessa analisi, e determinante per la scelta implementativa di §4.1.

`anagrafiche.emittenti_fiscali_utilities` espone `arrotondamento_importi_dec` e
`metodo_arrotondamento_importi` (`CEIL` / `FLOOR` / `HALF_DOWN` / `HALF_UP`).
`fn_ricalcola_totali_fattura` li legge e li applica a:

```
v_raw_totale := v_totale_doc + fondi + arrotondamento_precedente
```

cioè **all'importo dovuto**, non alle righe. Lo conferma il meccanismo del saldo
riportato fra documenti (`fn_set_arrotondamento_scope`): ha senso solo
sull'importo a pagare.

Non sono quindi due applicazioni della stessa regola a due livelli, ma **due
regole distinte**:

| Livello | Regola | Configurabile? |
|---|---|---|
| Riga di fattura | 2 decimali, arrotondamento commerciale | **No** — convenzione fiscale |
| Totale a pagare | decimali + metodo dell'emittente-utility | **Sì**, già implementato |

Stato della configurazione oggi: `2 decimali / HALF_UP` su entrambe le righe di
`emittenti_fiscali_utilities`.

### 2.11 Chi dipende davvero da queste colonne

Verifica fatta prima di decidere la rimozione (§4.3).

| Oggetto | Colonna | Dipendenza reale? |
|---|---|---|
| `vw_dash_competenza_attivita` | `imponibile_riga` | ✅ **sì**, legge `vendite.fatture_righe` |
| `vw_ordini_righe_iva_base`, `vw_ddt_righe_iva_base`, `vw_preventivi_righe_dettaglio` | `imponibile_riga` | ❌ **omonimia**: alias calcolato sulle proprie tabelle |
| `vw_*_riepilogo_iva_dettaglio` (ordini/DDT/preventivi) | `totale_riga` | ❌ **omonimia**: alias `imponibile + imposta` per aggregato IVA |
| `vendite_repository.list_fattura_righe` | `imposta_riga`, `totale_riga` | ✅ **sì**, `SELECT` diretto — **si rompe al DROP** |
| `test-ricalcola-riepiloghi-iva.sql` | tutte e tre | ✅ **sì**, le inserisce in fixture — si romperà (voluto, §8.1) |

⚠️ Il nome `totale_riga` **resta vivo nel modello** con un altro significato: è
la colonna calcolata delle viste di riepilogo IVA degli altri tre documenti.
Rimuovere `fatture_righe.totale_riga` **non** le tocca, e non vanno «bonificate»
per simmetria.

---

## 3. Diagnosi — cinque difetti distinti

| # | Difetto | Effetto oggi | Livello |
|---|---|---|---|
| **A** | Nessuno alimenta gli importi di riga in `vendite.fatture_righe` | **Ogni fattura ha totale 0,00 €.** `valore_fatturato` nullo in dashboard competenza | **DB** |
| **B** | Il template stampa fattura legge 3 chiavi che il context non espone | PDF con Q.tà, Sconto, Importo a `-`, anche una volta risolto **A** | **BE + template** |
| **C** | `fn_prepare_sdi_payload` referenzia `fatture_riepiloghi_iva.totale_riga`, colonna inesistente | Latente: esplode al primo passaggio a INVIATA | **DB** |
| **D** | Nessun presidio impedisce di modificare una riga di fattura **dopo l'emissione** | Uno `UPDATE fatture_righe SET qta=999` su una DEFINITIVA passa. Oggi non si nota perché gli importi sono già vuoti; con **A** risolto, l'importo seguirebbe la nuova quantità | **DB** |
| **E** | Una fattura può ricevere **numerazione fiscale senza avere righe** | Le fatture 207 e 208 sono DEFINITIVE e vuote (§7): documenti fiscali che non sarebbero mai dovuti esistere | **DB** |

**A**, **C**, **D** ed **E** sono di competenza del team DB. **B** è metà backend
(shape del context) e metà dato applicativo (HTML del template, che risiede in
tabella e si modifica dall'app, non da migration — verificato: nessun changelog
in `migrations_v2` contiene l'HTML di quei template).

**D** ed **E** sono stati aggiunti dall'analisi critica del 2026-07-28. Non sono
scoperte laterali: sono **la stessa famiglia di difetto** — un invariante che il
modello dà per acquisito e nessuno presidia. Chiuderli qui evita di riaprire il
tema fra sei mesi, quando gli importi saranno valorizzati e quindi *modificabili*.

---

## 4. Perimetro DB — cosa deve valere e **come si realizza**

> **Aggiornata 2026-07-28.** Nella prima stesura questa sezione era
> deliberatamente funzionale, e lasciava la scelta implementativa al team DB.
> Le decisioni sono ora **chiuse** (§10) e la sezione è prescrittiva. Il
> ragionamento che ha portato a ciascuna scelta è nei §2.9-§2.11.

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

**Soluzione decisa: colonna generata.** `imponibile_riga` diventa

```sql
imponibile_riga numeric(18,6)
  GENERATED ALWAYS AS (
      round(qta * prezzo_unitario * (1 - COALESCE(sconto_percentuale, 0) / 100), 2)
  ) STORED
  NOT NULL
```

**Perché la colonna generata e non un trigger.** È il presidio più forte
disponibile: il valore lo calcola il motore, e **nessun `INSERT` o `UPDATE`, in
nessun linguaggio, oggi o fra due anni, può scriverlo diverso** — un trigger si
può disabilitare, una colonna generata no. L'invariante smette di essere una
promessa del comportamento e diventa una proprietà della tabella. Il requisito
«un punto solo, valido per qualunque scrittore» è soddisfatto per costruzione.

**Perché `NOT NULL`**: `qta` e `prezzo_unitario` sono già `NOT NULL`, quindi
l'espressione non può mai produrre vuoto. Dichiararlo è il modo di **scrivere**
l'invariante nello schema invece di limitarsi a garantirlo.

**Perché il `2` non è un hardcode.** L'arrotondamento configurabile
(`arrotondamento_importi_dec` / `metodo_arrotondamento_importi`) governa il
**totale a pagare**, non la riga — verificato in `fn_ricalcola_totali_fattura`,
che lo applica a `totale_doc + fondi + arrotondamento_precedente` (§2.10). La
riga di fattura si arrotonda a 2 decimali per convenzione fiscale italiana: è
una regola diversa, non lo stesso parametro applicato due volte. Nota tecnica:
`round(numeric, int)` di PostgreSQL arrotonda per eccesso sul mezzo, che
coincide con `HALF_UP` senza doverlo dichiarare.

**Formula**:

```
imponibile di riga = round(qta × prezzo_unitario × (1 − COALESCE(sconto_percentuale, 0) / 100), 2)
```

Il nucleo è lo stesso già in uso, verbatim, per ordini, preventivi e DDT (§2.5):
la simmetria fra documenti va mantenuta, non reinventata per la fattura
([[feedback_simmetria_modello_no_meta_scope]]). La differenza è che qui il
risultato viene **persistito e arrotondato**, perché è uno snapshot fiscale e non
un calcolo di presentazione.

**Vincoli tecnici da mettere a verbale, non da scoprire in corsa**:

1. **Serve `DROP` + `ADD`**: PostgreSQL non consente di trasformare in generata
   una colonna già esistente. Con 7 righe tutte a NULL non si perde nulla, ma il
   changeset deve dirlo.
2. **La colonna diventa non scrivibile**: qualunque codice provi ad assegnarle un
   valore riceve un errore. Nessuno scrittore vivo lo fa (§2.3) — ma **le fixture
   pgTAP sì**, e si romperanno (§8.1). È l'esito voluto: la pulizia delle fixture
   non è più una raccomandazione da ricordare, è obbligatoria per far girare i
   test. Il difetto non può ripresentarsi.
3. **Le 7 righe esistenti si valorizzano da sole** all'`ADD COLUMN`, senza una
   riga di backfill (§7).

**Criteri di accettazione D1**:

1. Inserendo una riga con `qta=100`, `prezzo_unitario=5`, `sconto_percentuale`
   NULL, l'imponibile di riga risulta `500.00`.
2. Idem con `sconto_percentuale=10` → `450.00`.
3. Idem con `qta=0` → `0` (zero **esplicito**, non NULL).
4. Il risultato è identico **sia** che la riga arrivi da `fn_generate_fatture_righe`,
   **sia** che arrivi da un `INSERT` diretto del backend.
5. In DRAFT, aggiornando `qta`, `prezzo_unitario` o `sconto_percentuale` di una
   riga esistente, l'imponibile si riallinea da sé. Oltre la soglia di stato
   l'`UPDATE` è respinto a monte (D1-bis), quindi il caso non si pone.
6. Un tentativo di scrivere direttamente `imponibile_riga` **fallisce**.
7. Dopo `fn_ricalcola_riepilogo_iva_fattura` + `fn_ricalcola_totali_fattura`
   sulla fattura 329 rigenerata, `totale_doc` vale 610,00 (500 + 22% IVA —
   aliquota della riga verificata sul DB).

**Conseguenza attesa, non un difetto**: con le righe già arrotondate al
centesimo, `fatture_riepiloghi_iva.arrotondamento` — che vale
`SUM(righe) − ROUND(SUM(righe), 2)` — risulterà **sempre zero**. Corretto: se le
righe sono esatte al centesimo non esiste scarto da conservare. La colonna resta
disponibile per un'eventuale rettifica esplicita.

### 4.1-bis Requisito D1-bis — congelare gli **input**, non il ricalcolo

> **Riformulato il 2026-07-28.** La prima stesura chiedeva di valutare se
> *inibire il ricalcolo* dell'importo oltre una soglia di stato. È il presidio
> sbagliato, per un fatto verificato: su `vendite.fatture_righe` **non esiste
> alcun guard di stato**. I trigger sono quattro `require_attivo`, audit, tx_id,
> normalize e storico — nessuno impedisce un
> `UPDATE fatture_righe SET qta = 999` su una fattura DEFINITIVA.
>
> Congelare solo l'importo lasciando liberi gli input produrrebbe il peggiore dei
> risultati: una riga con `qta=999` e `imponibile=500`, **incoerente e
> indistinguibile da un dato buono**. Con la colonna generata, poi, inibire il
> ricalcolo non è nemmeno possibile: il valore segue sempre le colonne sorgente.

**Invariante richiesto**: oltre la soglia di stato del documento, le colonne che
determinano l'importo — `qta`, `prezzo_unitario`, `sconto_percentuale`, `iva_id`
— **non sono modificabili**. Congelati gli input, l'importo non può derivare,
qualunque sia il meccanismo che lo calcola.

**Soglia**: la stessa già in uso in `fn_ricalcola_riepilogo_iva_fattura`, che
ammette la scrittura solo per `DRAFT` e `EMESSA` e solleva
`E_PARAMETRO_INVALIDO` altrove. Riusarla, non inventarne una nuova.

⚠️ **Guard restrittivo — verificare prima l'impatto**: va fatto il grep dei
pgTAP esistenti **prima** di armarlo ([[feedback_guard_breaks_existing_tests]]).
Un guard su `fatture_righe` può rompere test che oggi modificano le righe
liberamente.

**Criteri di accettazione D1-bis**:

1. `UPDATE` di `qta` su riga di fattura in `DRAFT` → riesce.
2. Stesso `UPDATE` su fattura `DEFINITIVA` → respinto con codice errore
   registrato.
3. `UPDATE` di una colonna **non** di importo (es. `descrizione`) oltre la
   soglia → da decidere in implementazione, ma la scelta va scritta.
4. `DELETE` di una riga oltre la soglia → coerente col punto 2.

### 4.2 Precisione dell'importo di riga — **DECISA: arrotondato a 2 decimali**

> **Chiusa da Tid il 2026-07-28.** La prima stesura raccomandava la precisione
> piena, con l'arrotondamento una sola volta in aggregazione. La decisione è
> l'opposto, e la motivazione è di dominio, non tecnica: **in Italia le righe di
> fattura si arrotondano al centesimo**. L'importo di riga è un valore fiscale
> che deve poter essere stampato tal quale, non un intermedio di calcolo.

L'obiezione che la prima stesura muoveva all'arrotondamento per riga — «diventa
un secondo arrotondamento su valori già arrotondati» — **decade**: se le righe
sono esatte al centesimo, `ROUND(SUM(...), 2)` a valle è un'operazione neutra,
non un secondo arrotondamento. Lo scarto non esiste, e infatti
`fatture_riepiloghi_iva.arrotondamento` risulterà sempre zero (§4.1).

⚠️ **Non è l'arrotondamento configurabile.** I 2 decimali della riga sono una
convenzione fiscale fissa. `arrotondamento_importi_dec` /
`metodo_arrotondamento_importi` restano quel che sono oggi: la regola del
**totale a pagare**, applicata da `fn_ricalcola_totali_fattura` (§2.10). Sono due
regole distinte e non vanno unificate.

La colonna resta `numeric(18,6)`: i valori avranno semplicemente due decimali
significativi. Nessuna modifica di tipo.

**Conseguenza su §5.3 (BE)**: cade. Con l'importo già arrotondato al centesimo,
il PDF non deve arrotondare nulla in presentazione — stampa il valore così
com'è, come già fa per ordini e preventivi.

### 4.3 Requisito D1-ter — `imposta_riga` e `totale_riga`: **RIMOSSE**

> **Decisa da Tid il 2026-07-28**: *«l'imposta di riga in Italia non esiste»*.

`vendite.fatture_righe.imposta_riga` e `vendite.fatture_righe.totale_riga`
vengono **eliminate dal modello**.

**Cosa dovevano essere**, per il verbale — la specifica è nel manuale (§2.9):
`imposta_riga = round(imponibile_riga * iva_perc/100, ...)` e
`totale_riga = imponibile_riga + imposta_riga`, cioè il lordo di riga.

**Perché si rimuovono e non si alimentano**:

1. **Dominio**: in Italia l'IVA si liquida per aliquota nei riepiloghi, non per
   riga. È così che il modello è nato (`fatture_riepiloghi_iva`).
2. **Non sono calcolabili dalla riga.** Servirebbe l'aliquota, che dipende dallo
   stato dell'emittente e si risolve con
   `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)` — informazione che
   sulla riga non c'è. Sono quindi incompatibili con la colonna generata di §4.1
   e richiederebbero un meccanismo proprio, per un dato che nessuno usa.
3. **Nessun consumatore vivo**: l'unico riferimento era quello **rotto** di
   `fn_prepare_sdi_payload` (§2.7) — che peraltro le cercava sulla **tabella
   sbagliata**, i riepiloghi anziché le righe. Chi ha scritto quella query
   ragionava per aggregato: nessuno le ha mai volute davvero.
4. **Una colonna persistita e mai scritta è il difetto che ha prodotto questo
   brief.** Tenerne due «per eventuali regimi esteri» significa riprodurlo
   volontariamente.

**Sul caso estero**, per non lasciare la domanda aperta: il modello **sa già**
gestire l'IVA multi-stato, a livello di aggregato — `fn_get_aliquota_iva` prende
già lo stato dell'emittente. Se un regime richiedesse l'imposta per riga,
l'informazione è disponibile e la colonna si riaggiunge **insieme alla regola che
la riempie**. Riaggiungere una colonna costa poco; una colonna che mente costa
quanto stiamo pagando ora.

**⚠️ Breaking change dichiarato — il BE si rompe, ed è accettato.**
[`vendite_repository.py:1633-1634`](../../../../backend/apps/vendite/db/vendite_repository.py#L1633)
(`list_fattura_righe`) seleziona `r.imposta_riga, r.totale_riga` direttamente
dalla tabella: al `DROP` la query fallisce. Decisione Tid 2026-07-28: **non si
introduce alcuno step di compatibilità**, non essendoci produzione
([[project_no_produzione_solo_sviluppo]]). Il DB atterra, il BE si adegua
(step B0, §5.0). L'importante è che la modifica sia **segnalata**, non
ammorbidita.

**Non toccare gli omonimi** (§2.11): `totale_riga` esiste anche come colonna
**calcolata** nelle viste di riepilogo IVA di ordini, DDT e preventivi, dove vale
`imponibile + imposta` per aggregato. Non c'entra nulla e non va bonificata per
simmetria.

**Aggiornare il manuale** `docs/it/dbzero/vendite/manual/fatture_righe.md`, che
oggi specifica tutte e tre le colonne e cita `iva_perc` sulla riga (§2.9). È il
documento che ha prodotto l'equivoco: lasciarlo com'è significa lasciare in giro
la specifica sbagliata.

### 4.4 Requisito D2 — payload SDI

`vendite.fn_prepare_sdi_payload` deve calcolare il totale documento da colonne
**esistenti**. La funzione oggi somma `ri.totale_riga` su
`vendite.fatture_riepiloghi_iva`, che espone invece `imponibile`,
`imposta`, `arrotondamento` (§2.7).

**Criterio di accettazione**: la funzione eseguita su una fattura reale
completa senza errore, e il totale prodotto coincide con
`fatture.totale_a_pagare` (o con `totale_doc`, secondo quale sia il valore
fiscalmente corretto per il tracciato — decisione del team DB).

⚠️ **Serve un test che la ESEGUA, non che la ispezioni.** Il difetto è
sopravvissuto perché plpgsql pianifica alla prima esecuzione: la funzione è
sintatticamente valida e nessuno se n'è accorto. Un test che ne verifichi il
testo lascerebbe il prossimo riferimento sbagliato ad aspettare di nuovo il primo
`INVIATA`. È il caso 9 di §8.1.

**Nota post-D1-ter**: dopo la rimozione di §4.3, `totale_riga` non esiste più
**neppure** su `fatture_righe`. La correzione deve quindi ricavare il totale
dalle colonne dei riepiloghi (`imponibile`, `imposta`, `arrotondamento`) o dalla
testata, non cercarlo altrove.

### 4.5 Requisito D3 — nessuna numerazione fiscale su fattura vuota

> **Aggiunto al perimetro DB il 2026-07-28.** Nella prima stesura era la voce
> P7, «da indagare», in fondo alle decisioni aperte.

Le fatture **207** e **208** sono `DEFINITIVA` e **non hanno alcuna riga** (§7).
Esiste quindi un percorso che assegna numerazione fiscale a un documento vuoto.
Non è una curiosità sui dati di test: è la stessa famiglia di difetto del resto
del brief — un invariante che tutti danno per acquisito e nessuno presidia.

**Invariante richiesto**: una fattura non può superare la soglia di stato che le
assegna numerazione fiscale se non ha almeno una riga.

**Criteri di accettazione D3**:

1. Transizione verso lo stato che numera, con zero righe → **respinta** con
   codice errore registrato.
2. Stessa transizione con almeno una riga → riesce.
3. Le fatture 207 e 208 restano com'è (§7): il guard vale da qui in avanti, non
   è retroattivo.

**Da chiarire in implementazione**: quale sia esattamente la soglia — la
numerazione avviene al passaggio a `DEFINITIVA`, ma va verificato dove il modello
la assegna davvero prima di scegliere il punto in cui armare il guard.

### 4.6 Fuori perimetro DB

- **Non** toccare la formula del riepilogo IVA né dei totali: sono corretti,
  ricevevano solo input vuoti.
- **Non** toccare le viste di dashboard: `vw_dash_competenza_attivita` mostrerà
  `valore_fatturato` corretto da sola, non appena la colonna sorgente sarà
  valorizzata. ✅ *Verificato 2026-07-28*: è l'**unica** delle sei viste che
  nominano `imponibile_riga` a dipendere davvero da `vendite.fatture_righe`; le
  altre cinque usano lo stesso nome per un alias calcolato sulle proprie tabelle
  (§2.11).
- **Non** toccare la pipeline di fatturazione (`vendite.fatturazione_pipeline`):
  non serve uno step nuovo — se l'invariante D1 è garantito alla scrittura, gli
  step esistenti funzionano così come sono.
- **Non** unificare l'arrotondamento di riga con quello del totale a pagare: sono
  due regole distinte (§2.10, §4.2).

---

## 5. Perimetro BE — **come**, in dettaglio

> Parte **dopo il land del DB** ([[feedback_be_fe_attende_prerequisiti_db]]).
> Le modifiche qui sotto sono già completamente determinate e non dipendono da
> quale implementazione il team DB sceglierà per D1.

### 5.0 B0 — ⚠️ breaking: le due colonne rimosse vanno tolte dalla `SELECT`

**Aggiunto il 2026-07-28**, conseguenza diretta di §4.3.

**File**: [`vendite_repository.py:1633-1634`](../../../../backend/apps/vendite/db/vendite_repository.py#L1633),
metodo `list_fattura_righe`. Rimuovere le due righe:

```sql
r.imposta_riga,
r.totale_riga
```

**Fra il land del DB e questa modifica la query fallisce**: le colonne non
esistono più. È stato deciso di **non** introdurre uno step di compatibilità
(non c'è produzione, [[project_no_produzione_solo_sviluppo]]): la rottura è
dichiarata, non evitata. Questa voce esiste perché sia **segnalata** e non
scoperta a runtime.

Verificare anche i test BE che si appoggiano a quelle chiavi.

**Non toccare** [`_riepilogo_iva_repo_mixin.py:58`](../../../../backend/apps/vendite/db/_riepilogo_iva_repo_mixin.py#L58),
che pure seleziona `totale_riga`: legge le **viste di riepilogo IVA**, dove è un
alias calcolato `imponibile + imposta`. Omonimia, non dipendenza (§2.11).

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
due chiavi per lo stesso valore sono un invito a divergere. Quanto a
`imposta_riga`/`totale_riga`, non è più una verifica ma un fatto: sono **rimosse**
(§4.3), e vanno tolte dalla `SELECT` — è lo step B0.

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

### 5.3 B3 — formattazione importi in stampa — ⛔ **DECADUTO**

Serviva solo nell'ipotesi (a) di §4.2, l'importo di riga a precisione piena, che
avrebbe fatto stampare `500.000000`. Con la decisione del 2026-07-28 l'importo
arriva già arrotondato al centesimo dal DB: il template lo stampa tal quale,
esattamente come fa oggi per ordini e preventivi. Nessun lavoro.

Resta valido il principio generale, se dovesse servire altrove: la formattazione
di presentazione usa gli helper centralizzati, **mai inline**
([[feedback_locale_formatters_centralizzato]]).

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

## 7. Dati esistenti — **DECISO: nessun intervento**

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
Le fatture 207 e 208 sono per giunta **prive di righe** — l'anomalia che ha
prodotto il requisito D3 (§4.5).

### Cosa si ripara da sé, e cosa no

Rilevato nell'analisi del 2026-07-28 e **diverso da quanto ipotizzava la prima
stesura**, che dava per necessario un backfill:

| | Effetto della correzione |
|---|---|
| **Le 7 righe** | ✅ si valorizzano **da sole**: creando la colonna generata, PostgreSQL la calcola anche per le righe già esistenti. Zero codice di recupero |
| **Le testate** (riepiloghi IVA e `totale_doc`) | ❌ **restano a zero**: sono tabelle separate, ricalcolate solo da due funzioni che **rifiutano** i documenti fuori da `DRAFT`/`EMESSA`. Le cinque sono `DEFINITIVA` |

La domanda si riduce quindi alle **testate di cinque fatture già numerate**.

### Decisione di Tid, 2026-07-28: **non si fa nulla**

Le cinque fatture restano a totale zero in testata. Nessuna cancellazione,
nessun backfill, nessun percorso dedicato che scavalchi il blocco di stato — cioè
nessuno strato di codice usa-e-getta su documenti con numerazione fiscale
assegnata.

Conseguenza da conoscere: le prime cinque fatture del sistema valgono zero e
resteranno tali; è dato di sviluppo, non di produzione
([[project_no_produzione_solo_sviluppo]]). Chi legge dashboard o test su quei
documenti deve sapere che sono reperti, non casi validi.

Le fatture 207 e 208, vuote, non sarebbero comunque state riparabili da alcun
ricalcolo: non hanno righe da sommare. Il presidio che impedisce di ripeterle è
D3 (§4.5), e non è retroattivo.

---

## 8. Test da coprire

### 8.1 pgTAP (team DB) — la fixture non si «ricorda» di pulirla: si rompe da sola

**Prerequisito**: `test-ricalcola-riepiloghi-iva.sql` (righe 174-176, 191-193,
225-227) e `test-vw-dash-competenza-v1.sql` (riga 246) inseriscono
`imponibile_riga` — e le prime anche `imposta_riga`/`totale_riga` —
**esplicitamente** in fixture (§2.8). Fornivano alla catena esattamente il dato
che il percorso di produzione non genera mai: è il motivo per cui il buco è
sopravvissuto a una suite verde.

✅ **Con la colonna generata la pulizia non è più affidata alla memoria di
nessuno**: quegli `INSERT` diventeranno **errori** (non si scrive una colonna
generata, e le altre due non esistono più). I test *devono* essere corretti per
girare. La prima stesura scriveva «vanno rivisti, altrimenti i nuovi test verdi
non dimostrano nulla»: ora la revisione è obbligata dal motore, non
raccomandata dal brief.

Correzione da fare: togliere le tre colonne dalle `INSERT` di fixture e lasciare
che sia il DB a produrre l'imponibile. Dove il test asserisce un imponibile
atteso, l'atteso non cambia — cambia solo chi lo scrive.

**Nuovi casi**:

| # | Caso | Atteso |
|---|---|---|
| 1 | INSERT riga senza sconto (`qta=100`, `prezzo=5`) | importo = `500.00` |
| 2 | INSERT riga con `sconto_percentuale=10` | importo = `450.00` |
| 3 | INSERT riga con `sconto_percentuale` NULL **esplicito** | trattato come 0 → `500.00` ⚠️ va forzato: la colonna ha `DEFAULT 0` e sulle 7 righe reali non è mai NULL, quindi è un caso di difesa, non uno scenario che il percorso normale produca |
| 4 | INSERT riga con `qta=0` | importo = `0`, **non NULL** |
| 5 | Arrotondamento: `qta=3`, `prezzo=0.333` | `1.00` — verifica che l'importo sia al centesimo e non a precisione piena (§4.2) |
| 6 | Riga creata da `fn_generate_fatture_righe` | importo valorizzato |
| 7 | Tentativo di scrivere direttamente `imponibile_riga` | **errore** (colonna generata) |
| 8 | `imposta_riga` / `totale_riga` | **non esistono più** su `vendite.fatture_righe` (`hasnt_column`) |
| 9 | UPDATE di `qta` su riga in DRAFT | importo riallineato da sé |
| 10 | UPDATE di `qta` oltre la soglia di stato | **respinto** (D1-bis, §4.1-bis) |
| 11 | Transizione a stato numerante con **zero righe** | **respinta** (D3, §4.5) |
| 12 | Stessa transizione con almeno una riga | riesce |
| 13 | Catena completa riga → riepilogo IVA → totali | `totale_doc` = 610,00 con IVA 22% |
| 14 | `fn_prepare_sdi_payload` **eseguita** su fattura reale | nessun errore, totale coerente (§4.4 — deve **eseguirla**, non ispezionarla) |

⚠️ **Prima di armare D1-bis e D3**, fare il grep dei pgTAP esistenti: sono guard
restrittivi e possono rompere test che oggi modificano righe di fattura o creano
fatture vuote ([[feedback_guard_breaks_existing_tests]]).

Prima di dichiarare rossi/verdi, usare `scripts/pgtap-baseline.sh vendite` — la
suite ha rossi preesistenti censiti (110 righe di baseline al 2026-07-28).

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

1. ✅ **Tid** — decisioni chiuse il 2026-07-28 (§10). Nessuna scelta pendente;
2. **Team DB** — nell'ordine: **D1** (colonna generata) → **D1-ter** (rimozione
   delle due colonne) → **D1-bis** (congelamento input) → **D3** (guard fattura
   vuota) → **D2** (payload SDI). Più: risanamento delle fixture §8.1, nuovi
   pgTAP, correzione del manuale `fatture_righe.md` (§2.9), rigenerazione doc
   auto-gen;
3. **Verifica di land** — su un **lotto nuovo**, generato dopo il fix. ⚠️ *Non*
   su `LTF-0000359`: avendo deciso di non toccare i dati esistenti (§7), la
   fattura 329 avrà la riga a 500 ma la testata resterà a zero, e non è un
   controllo valido. Attesi sul lotto nuovo: riga 500,00 → riepilogo IVA
   500,00/110,00 → `totale_doc` 610,00;
4. **BE** — **B0** (colonne rimosse dalla `SELECT`, §5.0) + **B1** + test §8.2.
   ⚠️ Fra il punto 2 e B0 `list_fattura_righe` **è rotta**: previsto e accettato
   (§4.3), non è una regressione da indagare;
5. **Tid** — B2, nuove versioni dei due template + pubblicazione;
6. **Verifica finale** — PDF della fattura con Q.tà, Sconto, Importo e totali
   tutti valorizzati; smoke E2E §8.3;
7. **Chiusura** — brief in `work-done`, doc `api_fatturazione.md` aggiornata se
   il contratto del context cambia.

---

## 10. Decisioni — **chiuse il 2026-07-28**

| # | Decisione | Esito | Motivo |
|---|---|---|---|
| **P1** | Precisione dell'importo di riga (§4.2) | ✅ **arrotondato a 2 decimali** | Convenzione fiscale italiana: la riga di fattura è un valore stampabile tal quale, non un intermedio. Ribalta il default proposto («precisione piena»), la cui obiezione — il doppio arrotondamento — decade perché con righe esatte al centesimo il `ROUND(SUM(...))` a valle è neutro |
| **P2** | `imposta_riga` / `totale_riga` (§4.3) | ✅ **rimosse** | *«L'imposta di riga in Italia non esiste»*. Non sono nemmeno calcolabili dalla riga (serve lo stato dell'emittente) e nessun consumatore vivo le usa. Il caso estero si riapre con la regola che le riempie, non con una colonna vuota |
| **P3** | Immutabilità dello snapshot (§4.1-bis) | ✅ **riformulata**: si congelano gli **input**, non il ricalcolo | Su `fatture_righe` non esiste alcun guard di stato: bloccare solo l'importo produrrebbe righe incoerenti (`qta=999`, `imponibile=500`). Soglia riusata: `DRAFT`/`EMESSA` |
| **P4** | Dati esistenti (§7) | ✅ **nessun intervento** | Le righe si valorizzano da sole con la colonna generata; le testate delle 5 fatture numerate restano a zero. Nessun codice usa-e-getta su documenti con numerazione fiscale |
| **P5** | Context fattura: nomi di contratto o grezzi (§5.1) | 🔵 **BE** — resta raccomandato «solo nomi di contratto» | Fuori dal perimetro DB |
| **P6** | Irrobustimento template↔context (§5.4) | 🔵 **Tid** — resta proposto il punto 3 | Fuori dal perimetro DB |
| **P7** | Fatture 207/208 DEFINITIVE senza righe | ✅ **promossa a requisito D3** (§4.5) | Non è una curiosità da indagare: è un invariante mancante, stessa famiglia del difetto principale. Entra nel perimetro DB |
| **D1-meccanismo** | Colonna generata *vs* trigger (§4.1) | ✅ **colonna generata** | Presidio più forte: lo calcola il motore, nessuno può scriverla diversa. Possibile perché il `2` è una costante fiscale e non il parametro configurabile, che governa il **totale a pagare** (§2.10) |
| **Breaking BE** | Compatibilità sul `DROP` delle 2 colonne | ✅ **nessuno step di compatibilità** | Non c'è produzione. La rottura di `list_fattura_righe` è **dichiarata** (§5.0), non evitata |

---

## 11. Registro avanzamento

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-27 | Segnalazione Tid su `LTF-0000359` | fattura a zero |
| 2026-07-27 | Analisi su DB vivo `dbdev` + codice | 3 difetti identificati, ipotesi UoM **scartata con evidenza** (§2.1) |
| 2026-07-28 | Stesura di questo brief | 🔴 in attesa delle decisioni §10 e del passaggio al team DB |
| 2026-07-28 | **Analisi critica del perimetro DB** su DB vivo `dbdev` | Tutte le rilevazioni di §2 **confermate**. Aggiunti §2.9 (la specifica esisteva già, marcata «opzionale» e mai implementata), §2.10 (l'arrotondamento configurabile governa il **totale a pagare**, non la riga), §2.11 (chi dipende davvero dalle colonne, e quali omonimie non vanno toccate). Due difetti nuovi in §3: **D** (nessun presidio sulla riga dopo l'emissione) ed **E** (fattura numerabile senza righe) |
| 2026-07-28 | Chiusura decisioni con Tid | P1 ribaltata (arrotondamento a 2 decimali), P2 rimozione, P3 riformulata sugli input, P4 nessun intervento, P7 promossa a requisito. Meccanismo: **colonna generata**. Breaking sul BE accettato e dichiarato |
| 2026-07-28 | Correzione del brief | §4 riscritta da funzionale a prescrittiva; §4.1-bis, §4.5 (D3) e §5.0 (B0) nuove; §4.2/§4.3/§7/§8.1/§9/§10 riscritte; §5.3 decaduta. 🟡 pronto per lo sviluppo DB |
