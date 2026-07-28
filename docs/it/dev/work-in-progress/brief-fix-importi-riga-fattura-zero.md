# Brief — Importi di riga fattura mai calcolati (fatture a totale zero)

> **Tipo**: brief operativo **misto DB + BE + FE** · **Target DB**: `dev/db-tid` ·
> **Target BE/FE**: `dev/backend-tid` · **Data**: 2026-07-28 · **Owner**: Tid ·
> **Stato**: 🟢 **PERIMETRO DB COMPLETO** (2026-07-28) — 18 changeset, `-07…-16`
> applicati, `-17/-18` scritti e validati. pgTAP verdi, zero regressioni.
> Restano **documentazione** (in corso) e il **perimetro BE** ·
> **Priorità**: 🔴 **ALTA — bug logico del modello**
> ([[feedback_bug_logici_modello]]): fino al 2026-07-28 **ogni fattura emessa dal
> sistema aveva totale 0,00 €**. Non era un caso limite: era il 100% dei casi.
>
> ✅ **Verificato a valle**: il lotto `LTF-0000390` ha prodotto la fattura **362**,
> imponibile **200,00**, numerata **2026/R2/6** — la prima fattura del sistema con
> un totale diverso da zero.
>
> ⚠️ **Il perimetro è cambiato in corsa.** La prima analisi trattava un difetto di
> calcolo: «nessuno valorizza l'importo di riga». La seconda ha stabilito che
> **anche l'oggetto è sbagliato**: una riga di fattura deve essere
> l'**aggregazione di 1..n attività fatturabili**, non la copia di una sola. Da
> qui tre requisiti nuovi (D4 aggregazione, D5 dettaglio componenti) e il
> rifacimento di D1, che era già stato applicato nella forma a colonna generata e
> va **revocato**. Dettaglio in §4.1 e §12.
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
| **D1** — importo di riga | ~~colonna generata~~ → **trigger** che legge le regole di arrotondamento **per articolo** | team DB | ✅ applicato (`-07…-10`), verificato sul lotto `LTF-0000390` |
| **D1-bis** — congelamento | gli **input** della riga non si modificano oltre la soglia di stato | team DB | ✅ applicato (`20260728-03/04`) |
| **D1-ter** — pulizia modello | `imposta_riga` e `totale_riga` **rimosse** ⚠️ *breaking sul BE* | team DB | ✅ applicato (`20260728-02`) |
| **D2** — payload SDI | `fn_prepare_sdi_payload` referenzia una colonna inesistente | team DB | ✅ applicato (`20260728-06`) |
| **D3** — fattura vuota | guard: non si numera una fattura **senza righe** (origine di 207/208) | team DB | ✅ applicato (`20260728-05`) |
| **D4** — ⭐ **aggregazione** | una riga di fattura = aggregazione di **1..n** attività fatturabili (§4.6) | team DB | ✅ applicato (`-11/-12`) + quota dashboard (`-13`) |
| **D5** — esposizione kit | snapshot sulla riga + vista di rappresentazione unica (§4.7-bis) | team DB | ✅ applicato (`-14/-15/-16`) |
| **PULIZIA** — `visibilita_componenti` | rimossa: nessun consumatore vivo, non era la regola (§4.7-bis) | team DB | ✍️ scritti `-17/-18`, da applicare ⚠️ *breaking sul BE* |
| **T** — pgTAP | fixture risanate + file nuovo da 19 casi (§8.1) | team DB | ✅ verdi, zero regressioni |
| **DOC** — documentazione | manuali dbzero, guida fatturazione, regole §4.7-ter | team DB | 🟡 in corso |
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

#### 2.6-bis Evidenza dalla coda di stampa (2026-07-28) — un quarto campo, e più grave

Rilevato ispezionando `vendite.fatture_stampa_coda` durante la verifica del lotto
`LTF-0000390`:

| Coda | Fattura | Stato | Tentativi | Errore |
|---|---|---|---|---|
| 1 | 210 | **ERRORE** *(tentativi esauriti)* | 5 | `E_DOCUMENTI_RENDER_FAILED` → `UndefinedError: 'dict object' has no attribute 'denominazione'` |

Due cose che il censimento della tabella qui sopra non conteneva:

1. **C'è un quarto campo disallineato: `denominazione`.** Non era stato censito
   perché il confronto era stato fatto sulle colonne di *riga*, mentre questo sta
   in un'altra parte del context (probabilmente l'intestazione cliente). Chi
   corregge il template lo chiuda **nella stessa passata** degli altri tre,
   invece di scoprirli uno per volta a ogni stampa.
2. **Qui il template NON usa `.get()`.** L'errore è un `UndefinedError`, cioè
   `StrictUndefined` è scattato: in quel punto c'è un accesso diretto. È
   esattamente il comportamento che §5.4 raccomanda di estendere a tutti i campi
   — con il risultato che questo difetto si è **fermato** invece di stampare un
   trattino, ed è per questo che lo abbiamo trovato.

⚠️ La voce è in stato `ERRORE` con 5 tentativi esauriti: quella fattura **non si
stampa da prima** di questo brief, e nessuno se n'era accorto. Dopo la correzione
del template va rimessa in coda a mano — a differenza delle voci `PENDING`, che
ripartono da sole.

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

### 2.12 ⚠️ Esiste un arrotondamento configurabile **di riga**, per articolo

Rilevato nella 2ª analisi (2026-07-28) e **correzione a §2.10**, che era
incompleta.

`vendite.articolo_regole_fatturazione` definisce, con `UNIQUE (articolo_id)` e
quindi una riga per articolo:

- `arrotondamento_importi_dec` / `metodo_arrotondamento_importi`
- `arrotondamento_quantita_dec` / `metodo_arrotondamento_quantita`
- `visibilita_componenti`, `calcolo_qta_padre`

e il suo manuale dice che le regole vengono lette *«durante la generazione righe
documento (preventivo → ordine → DDT → fattura)»*, al punto *«Calcolo importi e
totali: applica i decimali e i metodi di arrotondamento configurati»*.

**È la configurazione di riga che §2.10 dava per inesistente.** Quella sezione
resta valida per `anagrafiche.emittenti_fiscali_utilities`, che governa davvero
il solo totale a pagare; ma non è l'unica tabella in gioco. Le due convivono su
livelli diversi:

| Livello | Tabella | Governa |
|---|---|---|
| Riga di fattura | `vendite.articolo_regole_fatturazione` | decimali e metodo **dell'importo di riga**, per articolo |
| Totale a pagare | `anagrafiche.emittenti_fiscali_utilities` | decimali e metodo del **dovuto**, con saldo riportato fra documenti |

`fn_group_attivita_fatturabili` legge già oggi le regole dell'articolo e le
porta dentro `meta.group_key` di ogni riga generata — dove restano inutilizzate.

Stato dei dati: tutte e 5 le righe valgono `2 / HALF_UP`, `quantita_dec = 3`,
`visibilita = solo_padre`. Il comportamento configurato coincide oggi con la
formula fissa: è **una configurazione, non una costante**, ed è la ragione per
cui D1 non può essere una colonna generata (§4.1).

### 2.13 La catena è 1:1:1, e non esiste un secondo livello di righe fattura

Verificato su codice e dati nella 2ª analisi, in risposta al dubbio *«sicuro che
non ci sia un altro livello di righe fatture?»*.

**Nessun livello nascosto**:

- l'unica tabella con FK verso `vendite.fatture_righe` è `vendite.note_fatture`;
- delle 25 tabelle `fattur*` di `vendite`, nessuna è un dettaglio di riga;
- la guida stessa (§Tabelle core → *Livello fatturazione*) elenca
  `attivita_fatturabili`, `fatturazione_lotti`, `fatture`, `fatture_righe`,
  `fatture_riepiloghi_iva`, `fatture_scadenze`. Fine.

**La catena, oggi**:

| Passo | Funzione | Rapporto |
|---|---|---|
| `commesse_attivita` → `attivita_fatturabili` | `fn_emit_attivita_fatturabili_da_commessa` | **1:1** — travaso di ~35 colonne, `prezzo_snapshot` → `prezzo_unitario`, `id` → `commessa_attivita_id` |
| `attivita_fatturabili` → `fatture_righe` | `fn_generate_fatture_righe` | **1:1** — ciclo per attività, `qta = quantita`, `prezzo_unitario = prezzo_unitario` |

Confermato anche sui dati: nessuna riga di fattura alimentata da più di
un'attività, nessuna attività alimentata da più di una riga di commessa. La
catena della fattura 329: `commessa_attivita 192 (q=100, p=5)` → `AF 358` →
`riga 89` → imponibile 500.

**Il dettaglio della riga esiste già e sono le attività stesse**: 52 colonne, con
il puntatore `attivita_fatturabili.fattura_riga_id`. Non serve una tabella nuova
per aggregare (§4.6).

⚠️ **Ma quel puntatore non ha una foreign key.** È un `bigint` nudo verso
`vendite.fatture_righe`. Oggi regge perché `fn_cleanup_fatture_by_ids` ripulisce
a mano il riferimento quando cancella le fatture — una compensazione applicativa
al posto di un vincolo. Quando il rapporto diventa *n*:1 quel puntatore **è** la
struttura della fattura: senza vincolo, prima o poi ci saranno attività che
puntano a righe inesistenti e nessuno se ne accorgerà.

---

## 3. Diagnosi — sette difetti distinti

| # | Difetto | Effetto oggi | Livello |
|---|---|---|---|
| **A** | Nessuno alimenta gli importi di riga in `vendite.fatture_righe` | **Ogni fattura ha totale 0,00 €.** `valore_fatturato` nullo in dashboard competenza | **DB** |
| **B** | Il template stampa fattura legge 3 chiavi che il context non espone | PDF con Q.tà, Sconto, Importo a `-`, anche una volta risolto **A** | **BE + template** |
| **C** | `fn_prepare_sdi_payload` referenzia `fatture_riepiloghi_iva.totale_riga`, colonna inesistente | Latente: esplode al primo passaggio a INVIATA | **DB** |
| **D** | Nessun presidio impedisce di modificare una riga di fattura **dopo l'emissione** | Uno `UPDATE fatture_righe SET qta=999` su una DEFINITIVA passa. Oggi non si nota perché gli importi sono già vuoti; con **A** risolto, l'importo seguirebbe la nuova quantità | **DB** |
| **E** | Una fattura può ricevere **numerazione fiscale senza avere righe** | Le fatture 207 e 208 sono DEFINITIVE e vuote (§7): documenti fiscali che non sarebbero mai dovuti esistere | **DB** |
| **F** ⭐ | La riga di fattura **non aggrega**: `fn_generate_fatture_righe` ne produce una per ogni attività fatturabile | Fatture con *n* righe dove ne servirebbe una. Non è un difetto di calcolo ma **dell'oggetto**: la riga è la copia di un dettaglio invece della sua sintesi | **DB** |
| **G** | `visibilita_componenti` **non ha dove atterrare** | La regola che decide se sulla stampa vanno mostrati i componenti di un kit viene calcolata, messa in `meta.group_key` e ignorata: la stampa non sa cosa mettere nel dettaglio | **DB** |

**A**, **C**, **D**, **E**, **F** e **G** sono di competenza del team DB. **B** è
metà backend (shape del context) e metà dato applicativo (HTML del template, che
risiede in tabella e si modifica dall'app, non da migration — verificato: nessun
changelog in `migrations_v2` contiene l'HTML di quei template).

**D** ed **E** sono stati aggiunti dall'analisi critica del 2026-07-28. Non sono
scoperte laterali: sono **la stessa famiglia di difetto** — un invariante che il
modello dà per acquisito e nessuno presidia. Chiuderli qui evita di riaprire il
tema fra sei mesi, quando gli importi saranno valorizzati e quindi *modificabili*.

**F** e **G** vengono dalla seconda analisi (2026-07-28, §12) e sono di natura
diversa: non un presidio mancante ma **un pezzo di modello mai collegato**.
`fn_group_attivita_fatturabili` calcola una chiave di raggruppamento completa e
la salva in `meta.group_key` di ogni riga — senza raggruppare niente;
`attivita_fatturabili.fattura_riga_id` esiste per reggere un rapporto *n*→1 che
oggi è sempre 1→1. Il disegno c'è per intero, l'implementazione no. È la stessa
storia degli importi, un livello più su.

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

> ⚠️ **REVISIONE DEL 2026-07-28 (2ª analisi).** Questo requisito era stato chiuso
> con una **colonna generata** ed è stato applicato sul DB in quella forma
> (`20260728-01`). **Va revocato.** Il motivo non è la formula, che resta valida,
> ma il fatto che una colonna generata può usare solo dati della propria riga e
> **non può leggere le regole di arrotondamento configurate per articolo**
> (§2.12). La prima analisi aveva escluso quella configurazione dopo aver
> guardato solo `anagrafiche.emittenti_fiscali_utilities` — che governa davvero
> il solo totale a pagare — e non `vendite.articolo_regole_fatturazione`, che è
> invece **di riga**. Vedi §12 per il registro della revisione.

**Soluzione: trigger `BEFORE INSERT OR UPDATE` che calcola l'importo.**

```
imponibile_riga = arrotonda(
        qta × prezzo_unitario × (1 − COALESCE(sconto_percentuale,0)/100),
        decimali  ← articolo_regole_fatturazione.arrotondamento_importi_dec   (default 2)
        metodo    ← articolo_regole_fatturazione.metodo_arrotondamento_importi (default HALF_UP)
    )
```

**Perché il trigger e non la colonna generata**: `articolo_id` è una colonna
della riga, quindi un trigger può risalire alle regole dell'articolo; una colonna
generata no. Si perde la garanzia assoluta del motore, ma non molto: un
`BEFORE INSERT OR UPDATE` scatta comunque per **ogni** scrittore, funzione DB o
Python che sia. La differenza è teorica (un trigger si può disabilitare, il
motore no), non pratica.

**Perché i decimali non sono un hardcode**: `arrotondamento_importi_dec` è una
configurazione **per articolo**, documentata come applicata *«durante la
generazione righe documento (preventivo → ordine → DDT → fattura)»* e al
*«calcolo importi e totali»*. Oggi tutte e 5 le righe di
`articolo_regole_fatturazione` valgono `2 / HALF_UP`, quindi il comportamento
coincide con la formula fissa — ma è una configurazione, non una costante.

> **Il valore di riga resta a 2 decimali** (domanda esplicita di Tid). Il tipo
> della colonna resta `numeric(18,6)`: è il **contenitore**, non la regola.
> Stringerlo a `numeric(18,2)` ri-arrotonderebbe **in silenzio** l'importo di un
> articolo configurato a 3 decimali — un secondo arrotondamento invisibile,
> esattamente la classe di difetto che questo brief chiude.

**`NOT NULL` resta**: `qta` e `prezzo_unitario` sono già `NOT NULL`, quindi
l'espressione non può mai produrre vuoto. Dichiararlo è il modo di **scrivere**
l'invariante nello schema invece di limitarsi a garantirlo. Con il trigger va
imposto dopo il primo popolamento.

**Estrazione richiesta — `fn_arrotonda_importo(valore, decimali, metodo)`.** Il
`CASE` con i quattro metodi (`CEIL` / `FLOOR` / `HALF_DOWN` / `HALF_UP`) oggi
vive **inline** dentro `fn_ricalcola_totali_fattura`. Con questo trigger nasce il
secondo consumatore: o si richiama, o si riscrive — e riscrivere significa due
copie della stessa regola fiscale destinate a divergere. È il momento di
estrarla, né prima né dopo ([[feedback_regola_del_2_estrai_bb]]).

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

1. **Non serve alcun rollback, e non si tocca nessuna vista.** Il passaggio da
   colonna generata a colonna normale si fa in posto:

   ```sql
   ALTER TABLE vendite.fatture_righe ALTER COLUMN imponibile_riga DROP EXPRESSION;
   ```

   Verificato in transazione: la colonna smette di essere generata, **`NOT NULL`
   resta**, i **valori sono conservati** (7/7 valorizzate, totale 2.700) e la
   catena delle quattro viste dipendenti **non viene toccata**. Cade quindi tutto
   il rischio del ritorno — niente `DROP`+`ADD`, niente ricreazione con
   `security_invoker` da ri-specificare.

2. ⚛️ **`DROP EXPRESSION` e armamento del trigger vanno nello STESSO changeset.**
   Un trigger **non può assegnare** un valore a una colonna generata (PostgreSQL
   lo rifiuta), quindi non si può armare prima; ma appena tolta la generazione la
   colonna resta `NOT NULL` **senza nessuno che la riempia**, quindi non si può
   aspettare dopo. Fra i due atti esiste una finestra in cui qualunque `INSERT`
   fallirebbe: si chiude mettendoli nella stessa transazione di changeset.

3. **Nessun backfill.** `DROP EXPRESSION` conserva i valori già calcolati: le 7
   righe restano corrette senza un `UPDATE` di innesco, e senza dover
   attraversare il guard D1-bis sulle 5 fatture già numerate.

4. **Le fixture pgTAP si romperanno comunque** (§8.1): con il trigger l'importo
   iniettato a mano verrebbe **sovrascritto**, non rifiutato. È un
   peggioramento rispetto alla colonna generata, che le faceva fallire in modo
   rumoroso: va compensato con un test esplicito (caso 7 di §8.1) che verifichi
   che il valore scritto dall'esterno **non** sopravvive.

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
6. Un valore di `imponibile_riga` passato dall'esterno viene **ignorato**: dopo
   l'`INSERT` la colonna contiene il valore calcolato, non quello fornito.
7. Un articolo con `arrotondamento_importi_dec = 3` produce un imponibile a **3**
   decimali; uno con `metodo = FLOOR` tronca invece di arrotondare. È il test che
   distingue il trigger dalla formula fissa — senza, i due sono indistinguibili
   sui dati attuali.
8. Dopo `fn_ricalcola_riepilogo_iva_fattura` + `fn_ricalcola_totali_fattura`
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

### 4.1-ter Un solo vocabolario per i metodi di arrotondamento

> **Aggiunto il 2026-07-28 su decisione di Tid**: *«unifichiamo anche i metodi…
> confermo quelli di emittenti fiscali utilities»*.

Estraendo `fn_arrotonda_importo` è emerso che il metodo di arrotondamento è
configurabile in **quattro punti** del modello, e ogni punto ammetteva un insieme
**diverso** di valori. In comune ce n'era **uno solo**:

| Dove | Vocabolario |
|---|---|
| `anagrafiche.emittenti_fiscali_utilities.metodo_arrotondamento_importi` | `UP` `DOWN` `HALF_UP` `HALF_DOWN` |
| `config.termini_pagamento.arrotondamento_metodo` | `HALF_UP` `HALF_DOWN` `HALF_EVEN` |
| `vendite.articolo_regole_fatturazione.metodo_arrotondamento_importi` | `HALF_UP` `HALF_EVEN` `FLOOR` `CEIL` |
| `vendite.articolo_regole_fatturazione.metodo_arrotondamento_quantita` | `HALF_UP` `HALF_EVEN` `FLOOR` `CEIL` |

Tre vocabolari per la stessa idea. Una funzione condivisa avrebbe dovuto
gestirne l'unione — sette nomi per quattro comportamenti, alcuni sovrapposti solo
in parte — e chi scrive codice che arrotonda avrebbe dovuto sapere **quale** dei
tre stava leggendo.

**Decisione: vale il vocabolario di `emittenti_fiscali_utilities`**, esteso a
tutti e quattro i punti:

```
UP        allontana da zero      DOWN       avvicina a zero
HALF_UP   sul mezzo allontana    HALF_DOWN  sul mezzo avvicina
```

**Cosa sparisce, e perché si può**:

- **`CEIL` e `FLOOR`**: sui valori **non negativi** — la totalità dei casi di
  fatturazione — coincidono con `UP` e `DOWN`. La differenza esiste solo sui
  negativi (verso ±∞ anziché da/verso zero) e nessuno la sfruttava.
- **`HALF_EVEN`** (arrotondamento bancario): era un valore **ammesso** in due
  tabelle ma **nessuna funzione del database lo implementava** — verificato su
  `pg_proc`. Era una promessa scritta nel CHECK e mai mantenuta: la stessa forma
  di difetto che questo brief chiude sugli importi. Se servisse davvero, si
  riaggiunge **insieme** al codice che lo applica.

**Nessuna migrazione di dati**: tutte e 16 le righe configurate nei quattro punti
valgono `HALF_UP`, che sopravvive. Il changeset ha una `preCondition` che lo
verifica e si ferma se trova un valore fuori vocabolario.

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

### 4.6 ⭐ Requisito D4 — la riga di fattura è un'**aggregazione**

> **Aggiunto il 2026-07-28 (2ª analisi), su decisione di Tid**: *«è fondamentale
> che una riga della fattura sia l'aggregazione di 1 o n righe di attività
> fatturabili secondo le regole già esistenti»*.

**Invariante richiesto**: una riga di `vendite.fatture_righe` rappresenta
l'aggregazione di **1..n** righe di `vendite.attivita_fatturabili` che
condividono la stessa chiave di raggruppamento. Il legame è
`attivita_fatturabili.fattura_riga_id`, che diventa l'**unico** riferimento fra
riga e dettaglio.

**Lo stato di fatto** (§2.13): oggi `fn_generate_fatture_righe` cicla sulle
attività e ne inserisce **una riga per ciascuna**. Il rapporto è 1:1 nel codice e
nei dati (verificato: nessuna riga alimentata da più di un'attività). Ma il
disegno dell'aggregazione **esiste già per intero** e non serve alcuna tabella
nuova:

- la **chiave** la produce `fn_group_attivita_fatturabili`: articolo · billing
  account destinatario · unità di misura · **prezzo unitario** · IVA · competenza
  dal/al;
- il **puntatore *n*→1** è `attivita_fatturabili.fattura_riga_id`, che ha senso
  solo in un rapporto molti-a-uno: se fosse per sempre 1:1 quella colonna sarebbe
  inutile. La sua esistenza *è* la prova che l'aggregazione era prevista;
- il **dettaglio** sono le attività stesse (52 colonne: quantità, prezzo,
  competenza, sorgente, snapshot di pricing).

**L'algoritmo**:

```
per ogni fattura del lotto:
    raggruppa le attività per la chiave di fn_group_attivita_fatturabili
    per ogni gruppo:
        qta    = SUM(quantita)          ← somma ESATTA, mai arrotondata
        prezzo = prezzo del gruppo      ← unico per costruzione: è nella chiave
        → INSERT di UNA riga
        → UPDATE delle n attività: fattura_riga_id = riga appena creata
    l'importo lo calcola il trigger di D1 (§4.1)
```

**Perché questo È la sommatoria, e non un'approssimazione.** Il prezzo unitario
fa parte della chiave, quindi è costante dentro il gruppo:

```
Σ(qᵢ × p)  =  p × Σqᵢ  =  qta × prezzo_unitario
```

è un'**identità**, non un'approssimazione. E la somma delle quantità è esatta:
ogni `quantita` è `numeric(18,6)`, la somma di addendi a 6 decimali ha esattamente
6 decimali, e `qta` è `numeric(18,6)`. Nessun troncamento in nessun punto.
L'unico arrotondamento è quello finale, sull'importo.

> ⚠️ **`arrotondamento_quantita_dec` non si applica MAI all'aggregato.**
> È una regola della **singola attività**, a monte. Arrotondare la quantità
> sommata prima di scriverla in `qta` perderebbe precisione lì — a monte
> dell'importo, dove nessuno la cerca. È la garanzia esplicitamente richiesta da
> Tid e va scritta nel modello, non lasciata all'implementazione.

**Cosa va modificato** — otto punti, tutti conseguenza diretta:

| # | Oggetto | Cosa |
|---|---|---|
| 1 | `fn_generate_fatture_righe` | da ciclo per attività a raggruppamento: una riga per gruppo, `qta` = somma esatta, poi `UPDATE` delle *n* attività |
| 2 | `fatture_righe.sorgente_*` | **NULL** sulle righe aggregate (vedi sotto) |
| 3 | `attivita_fatturabili.fattura_riga_id` | **aggiungere la FK**, oggi assente |
| 4 | importo di riga | trigger di D1 (§4.1) |
| 5 | `fn_arrotonda_importo` | estrazione dal `CASE` inline (§4.1) |
| 6 | `vw_dash_competenza_attivita` | **quota proporzionale** per attività (vedi sotto) |
| 7 | ~~`vw_documento_lineage_archi`~~ | ✅ **niente da fare** — verificato 2026-07-28, vedi sotto |
| 8 | `riga_nr` | ordinamento **deterministico** dei gruppi |

> ✅ **Punto 7 — falso allarme, e vale la pena scriverlo.** §2.11 segnalava
> `vw_documento_lineage_archi` fra i lettori delle colonne sorgente, e §12.5 lo
> metteva fra il debito da progettare. **Non lo è**: la vista costruisce l'arco
> commessa→fattura già oggi con
> `attivita_fatturabili af JOIN fatture_righe fr ON fr.id = af.fattura_riga_id`,
> cioè **proprio il puntatore** che D4 rafforza. Zero riferimenti a
> `fr.sorgente_*`.
>
> Il segnale era un falso positivo del censimento: la vista è una `UNION` di
> archi, e nomina sia `fatture_righe` sia `sorgente_uid` — ma su rami diversi.
> Gli alias che usano `sorgente_uid` sono `cs` (`commesse_sorgenti`), `d`
> (documenti) e `r`, che è **`vendite.resi`**, non le righe di fattura.
> Portare `fr.sorgente_*` a NULL non tocca il lineage.

**⚠️ Punto 2 — le colonne sorgente perdono senso.** Oggi ogni riga porta
`sorgente_tipo_id / sorgente_uid / sorgente_riga` della **singola** attività, e i
dati lo confermano (7 righe, 7 uid distinti, `sorgente_riga` = id della riga di
commessa). Con l'aggregazione *n* attività di sorgenti diverse finiscono nella
stessa riga: **non esiste più una sorgente singola**. Sceglierne una sarebbe una
bugia, e comunque esiste

```sql
CREATE UNIQUE INDEX uq_fatture_righe_v_sorgente_fk
    ON vendite.fatture_righe (sorgente_tipo_id, sorgente_uid)
    WHERE sorgente_tipo_id IS NOT NULL
```

che lo impedirebbe. Le colonne vanno quindi a **NULL** sulle righe aggregate —
l'indice è parziale e le tollera — e la tracciabilità passa interamente dal
puntatore delle attività. Coerente con la decisione: `fattura_riga_id` è *il*
riferimento.

**⚠️ Punto 6 — la dashboard raddoppierebbe i totali.**
`vw_dash_competenza_attivita` espone una riga **per attività** e prende
`fr.imponibile_riga AS valore_fatturato`. Con *n* attività sulla stessa riga,
ciascuna mostrerebbe l'importo **intero**, e `vw_dash_competenza_mensile` fa
`sum(valore_fatturato)`: il totale fatturato risulterebbe moltiplicato per il
livello di aggregazione. Va attribuita a ogni attività la sua **quota**:

```
valore_fatturato = imponibile_riga × qᵢ / qta
```

che con prezzo unico è esattamente `qᵢ × p`. È la forma più onesta: ogni attività
porta il proprio valore, e la somma torna.

**⚠️ Punto 8 — `riga_nr`.** Oggi è `max(riga_nr)+1` calcolato dentro il ciclo, e
l'ordine segue l'`ORDER BY a.id` delle attività. Con i gruppi serve un
ordinamento **esplicito e deterministico** (es. articolo, competenza), altrimenti
l'ordine delle righe della fattura cambia a ogni rigenerazione.

**Criteri di accettazione D4**:

1. Due attività con **stessa** chiave (stesso articolo, prezzo, uom, IVA, BA,
   competenza) → **una sola** riga, con `qta` = somma delle due.
2. Entrambe le attività hanno `fattura_riga_id` = quella riga.
3. Due attività con prezzo **diverso** → **due** righe distinte (il prezzo è
   nella chiave).
4. `qta` della riga aggregata **non è arrotondata**: con quantità `0.333333` e
   `0.333333` risulta `0.666666`, non `0.667`.
5. L'importo della riga aggregata coincide con `round(Σ(qᵢ × p), dec)` — cioè la
   sommatoria, non la somma di importi già arrotondati.
6. Sulla riga aggregata le colonne `sorgente_*` sono **NULL**.
7. `vw_dash_competenza_mensile.valore_fatturato_tot` su una fattura con righe
   aggregate coincide con `SUM(imponibile_riga)` delle righe — **non** con un suo
   multiplo.
8. Rigenerando lo stesso lotto, l'ordine dei `riga_nr` è identico.

### 4.7 Requisito D5 — il dettaglio componenti sulla stampa

> **Aggiunto il 2026-07-28 su richiesta di Tid**: *«dobbiamo fare in modo che la
> stampa sappia cosa mettere nel dettaglio»*.

**Il fatto.** `fn_group_attivita_fatturabili` restituisce anche
`visibilita_componenti`, che vale `solo_padre` · `padre_componenti` ·
`solo_componenti` (CHECK su `vendite.articolo_regole_fatturazione`). Il valore
viene calcolato, salvato in `meta.group_key` di ogni riga di fattura… **e
ignorato**: sulla fattura non esiste alcuna struttura che distingua un padre da
un componente, quindi la stampa non ha modo di sapere cosa mostrare nel
dettaglio. Oggi tutti e 5 gli articoli configurati sono `solo_padre`, ed è il
motivo per cui non se n'è ancora accorto nessuno.

**È l'unico documento monco.** Cinque famiglie su sei hanno il secondo livello:
`contratti_righe_componenti`, `ddt_righe_componenti`, `listini_righe_componenti`,
`ordini_righe_componenti`, `preventivi_righe_componenti`. `fatture_righe` no.

**Come viaggiano i componenti a monte** (verificato): a livello commessa **non**
sono figli, sono **righe sorelle**, e la parentela è codificata dentro la stringa
`segment_key`:

```
padre:      ORD:<uid>:R:<riga>
componente: ORD:<uid>:R:<riga>#CMP:<articolo_componente_uid>
```

12 righe su 83 di `commesse_attivita` sono componenti. Su
`attivita_fatturabili` **non esiste alcuna colonna** padre/figlio: la parentela
sopravvive solo dentro quella stringa.

**Conseguenza con l'aggregazione**: padre e componente hanno articoli diversi,
quindi chiavi di gruppo diverse, quindi **righe di fattura separate** — senza
nulla che dica quale discende da quale. Il problema non nasce con D4, ma D4 lo
rende visibile.

**Le tre strade**:

| | Come | Valutazione |
|---|---|---|
| **(a)** `vendite.fatture_righe_componenti` | tabella figlia come negli altri documenti | Simmetrica col resto del modello, ma **non** riflette come i componenti viaggiano a monte, dove sono righe sorelle: duplicherebbe le stesse quantità in due forme |
| **(b)** `fatture_righe.riga_padre_id` *(raccomandata)* | self-FK: il componente resta una riga, con un puntatore al padre | Minima, strutturale, coerente con l'upstream. `visibilita_componenti` decide cosa la stampa mostra; il dato resta uno solo |
| **(c)** derivare la parentela dal `segment_key` in una vista di stampa | nessuna struttura nuova | La stampa dipenderebbe dal **parsing di una stringa**: la stessa fragilità che il progetto rifiuta altrove |

**Raccomandazione iniziale: (b)**, con `visibilita_componenti` **congelata sulla
riga** (snapshot alla generazione) e non riletta a valle: è un documento fiscale,
la regola dell'articolo può cambiare dopo l'emissione.

> ⛔ **SOSPESO il 2026-07-28 — la raccomandazione (b) poggia su un presupposto che
> i dati smentiscono.** L'opzione (b) collega il componente a una **riga padre**.
> Quella riga padre **non esiste**, e non può esistere.

**Le evidenze, raccolte prima di scrivere il changeset:**

| Verifica | Esito |
|---|---|
| Colonna di parentela su `commesse_attivita` / `attivita_fatturabili` | **nessuna**: la relazione vive solo dentro la stringa `segment_key` |
| Per ogni segmento con componenti, esiste la riga padre? | **No, in tutti e 4 i casi**: `n_componenti = 3`, `n_padre = 0` |
| Gli articoli di quei componenti hanno una regola? | **No** → fallback `solo_padre` |
| Gli articoli che *hanno* una regola sono arrivati in commessa? | 1 su 5, e comunque `solo_padre` |
| Attività fatturabili che sono componenti | **0 su 8**: nessun componente è mai arrivato alla fatturazione |

**Cosa dicono messe insieme.** I componenti arrivano in commessa come attività
autonome perché il **push del documento sorgente** porta le righe componente già
separate — non perché `visibilita_componenti` sia stata applicata. La prova è che
quegli articoli ricadono nel fallback `solo_padre`, e con `solo_padre` il padre
dovrebbe esserci e i componenti no: nei dati è l'esatto contrario.

**`visibilita_componenti` non viene consultata su questo percorso.** Non è che il
suo valore non abbia dove atterrare: non viene proprio applicato.

**Perché il changeset non è stato scritto.** Aggiungere `riga_padre_id` ora
significherebbe creare una colonna che non può essere valorizzata — il padre non
esiste come attività, quindi non può esistere come riga di fattura. Sarebbe
esattamente il difetto che questo brief chiude: una colonna persistita e mai
scritta.

**Le domande da chiudere, prima di qualunque riga di SQL:**

1. Quando un kit entra in commessa devono entrare **solo i componenti** (come
   accade oggi), **solo il padre**, o **entrambi**? Oggi il comportamento non
   segue la regola configurata sull'articolo.
2. Se la fattura deve poter mostrare padre **e** componenti, il padre va
   **generato a monte**: non è un problema di rappresentazione sulla fattura, ma
   di cosa entra in commessa. In quel caso D5 non è un changeset sulle righe
   fattura ma un intervento sulla catena di push.
3. Se invece la fattura deve mostrare i componenti come righe autonome —
   comportamento odierno, e coerente col fatto che ognuno ha articolo, quantità e
   prezzo propri — allora non serve `riga_padre_id`, e va semmai tolta
   `visibilita_componenti` dal `group_key`, dove oggi viaggia senza avere titolo.

Finché non è chiusa la 1, qualunque struttura sulle righe di fattura è una
scommessa.

---

### 4.7-bis D5 — la strada scelta: **esposizione separata dal dato** ✅

> **Sbloccata il 2026-07-28.** La domanda 1 è stata risolta ribaltando
> l'impostazione: non «quale forma entra in commessa», ma «il dato resta il
> dettaglio, l'esposizione è un livello a parte».

**Il principio.** `vendite.fatture_righe` conserva **sempre tutte le righe
componente**, con articolo, quantità e prezzo propri. Il raggruppamento per la
presentazione è una **rappresentazione**, non un dato diverso.

⚠️ **Vale per OGNI uscita, non solo per la stampa** (confermato da Tid): PDF, XML
SDI, portale. Se il PDF mostrasse il kit raggruppato e l'XML trasmettesse i
componenti, avremmo due uscite dello stesso documento che raccontano dettagli
diversi — totali uguali, quindi nulla di irregolare, ma una divergenza che
nessuno ha deciso. Per questo **non** si chiama «tabella di stampa»: è la
rappresentazione del documento.

**Perché una VISTA e non una tabella materializzata.** Una tabella sarebbe un
secondo artefatto da tenere allineato, e porterebbe tre domande: quando la
generi, cosa succede se la stampa viene rilanciata, cosa se qualcuno tocca le
righe dopo. Con una vista spariscono tutte: fonte unica, nessun momento di
generazione, nessuna idempotenza da garantire. Se un domani costasse troppo,
materializzarla è banale — la definizione è già scritta.

**✅ Il congelamento non richiede alcun meccanismo nuovo.** La modalità di
esposizione si congela sulla riga, e le righe oltre EMESSA sono **già
intoccabili** grazie al guard D1-bis (§4.1-bis): niente `INSERT`, `UPDATE` o
`DELETE`. Quindi:

- cambiare la regola di un articolo **non tocca** le fatture emesse — non perché
  ce ne ricordiamo, ma perché il database lo impedisce;
- **rigenerare** una fattura passa dal reset lotto, che cancella le righe con la
  GUC di manutenzione e le riscrive leggendo la regola corrente: l'esposizione
  cambia, ed è corretto che cambi;
- **quando la fattura non è più modificabile, la stampa è immutabile.**

Le tre condizioni poste da Tid sono soddisfatte da ciò che è già in piedi.

### ⚠️ Correzione sostanziale (2026-07-28, seconda parte della sessione)

Tre scoperte hanno cambiato la forma di D5. Sono elencate qui perché quanto
scritto sopra su `visibilita_componenti` e sulla risoluzione del padre **è
superato**.

**1. D5 non è un disegno nuovo: è la metà mancante di uno già deciso.** Il
docstring di `backend/apps/vendite/services/commesse_source_handlers.py`
(«Modello unificato componenti BoM 2026-05-13») lo dice per esteso:

> *«il padre composito viene **sempre espanso in N righe**… `esposto_in_fattura`
> ora è un flag di **presentazione fattura**, non gate di expansion: tutti i figli
> attivi passano in commessa, la separazione fra "padre con totale" e "figli
> esposti come righe descrittive" avviene **a valle (generazione
> fatture_righe)**.»*

La prima metà è stata costruita — per questo in commessa si trovano **solo
componenti e mai il padre**, ed è voluto, non un difetto come ipotizzato sopra.
La seconda metà, quella «a valle», non è mai stata scritta. Esattamente come per
gli importi: regola decisa, documentata, mai collegata.

**2. La regola è `esposto_in_fattura`, non `visibilita_componenti`.**
`catalogo.articoli_componenti.esposto_in_fattura` è un flag **per singolo
componente**, valorizzato per davvero (14 `TRUE`, 11 `FALSE`) e usato da
catalogo, ordini, preventivi, contratti, DDT e dagli handler di push.
`vendite.articolo_regole_fatturazione.visibilita_componenti` invece **non ha
alcun consumatore vivo**: solo `fn_group_attivita_fatturabili`, che la infila in
`meta.group_key` e la abbandona lì, più il suo specchio Python. Frontend: zero
riferimenti.

**3. Il padre e il flag viaggiano già con l'attività** — niente risoluzione
polimorfa, niente distinta base. Il push scrive nel `meta` di
`commesse_attivita`, e la catena lo propaga:

```json
"componente_di":      "019e2234-…",   ← l'articolo padre, già risolto
"esposto_in_fattura": false,          ← il flag, già congelato
"coeff_qta":          "1.000000"
```

⚠️ La distinta base **non sarebbe servita comunque**: lo stesso componente può
appartenere a più kit. Verificato — i tre componenti del caso reale risultano in
**quattro prodotti diversi**, nessuno dei quali è il padre effettivo. Solo il
documento sorgente sa quale kit è stato venduto, e il push ha già fatto quel
lavoro.

**Le colonne su `vendite.fatture_righe`** (snapshot alla generazione):

| Colonna | Da dove viene |
|---|---|
| `kit_key` | prefisso del `segment_key` (`ORD:<uid>:R:<riga>`). Identifica l'**istanza**, non l'articolo: lo stesso kit può comparire due volte sulla stessa fattura da righe sorgente diverse |
| `kit_esposto_in_fattura` | `meta->>'esposto_in_fattura'` — **booleano per riga**, non un modo a tre valori |
| `kit_articolo_padre_id` | `meta->>'componente_di'` — sempre valorizzato (*«per sicurezza mettere sempre id del padre»*), serve al codice articolo sull'XML |
| `kit_descrizione_padre` | da `catalogo.articoli`, congelata per stamparla senza risalire a monte |

**La vista di esposizione**, secondo il disegno del 2026-05-13:

| Caso | Cosa produce |
|---|---|
| `kit_key IS NULL` | la riga passa così com'è |
| riga di kit | **una riga padre con il totale** del kit, e sotto i soli componenti con `kit_esposto_in_fattura = true`, come righe **descrittive** |

I componenti con il flag a `false` non compaiono: il loro valore è già dentro il
totale del padre.

**Le tre convenzioni decise da Tid:**

1. **Quantità della riga aggregata = la MEDIA delle quantità dei componenti.**
   In un kit da 2 pezzi tutti i componenti portano quantità 2 e il padre porta 2:
   la media restituisce 2. ⚠️ *Verificato che regge oggi*: tutte e 30 le righe di
   `ordini_righe_componenti` hanno `coeff_qta_snapshot = 1`, quindi i componenti
   portano sempre la quantità del padre. **Il giorno in cui comparisse un
   coefficiente ≠ 1** (la colonna esiste apposta) la media diventerebbe un numero
   che non corrisponde a nulla: kit da 2 con un componente a coefficiente 3
   darebbe media di `{2, 6, 6}`. Il rimedio, se servirà, è a costo zero —
   congelare anche `kit_qta_padre`, dato che alla generazione si legge già la
   riga d'ordine del padre per descrizione e articolo.
2. **`riga_nr` della riga aggregata = quello della prima componente.**
3. **Importo della riga aggregata = somma dei componenti.** Verificato sui dati
   che coincide col prezzo del padre: 2 + 6 + 9 = 17,00, e la riga d'ordine 589
   ha prezzo 17,00. Il totale della fattura non cambia al variare
   dell'esposizione — l'invariante richiesto dal criterio 5.

**Prerequisito ancora aperto (domanda 2 di §4.7)**: oggi `visibilita_componenti`
**non viene consultata** su questo percorso. Va deciso dove leggerla — al push in
commessa o alla generazione della fattura. Con la strada scelta la risposta
naturale è **alla generazione**: la commessa resta il registro fedele del
dettaglio, la fattura decide come esporlo.

**Criteri di accettazione D5**:

1. Un articolo con `visibilita_componenti = 'padre_componenti'` produce righe di
   componente **collegate** alla riga padre.
2. Con `solo_padre` i componenti non generano righe proprie.
3. Con `solo_componenti` non viene generata la riga padre.
4. La stampa distingue padre e componenti **senza** interpretare `segment_key`.
5. Il totale della fattura non cambia al variare della visibilità: cambia **cosa
   si mostra**, non quanto si fattura. *(Da verificare: oggi `solo_componenti` e
   `padre_componenti` avrebbero effetti diversi sull'imponibile se sia il padre
   sia i componenti portassero un prezzo — punto da chiudere in implementazione.)*

### 4.7-ter Le regole che tengono in piedi calcolo e stampa

> Richiesta di Tid: *«evidenziare tutte le regole per il corretto funzionamento…
> per fare in modo che non ci siano comportamenti anomali sul calcolo e stampa
> fattura»*.
>
> La colonna che conta è la terza: **cosa impedisce che la regola salti**. Una
> regola solo documentata è una regola che prima o poi qualcuno viola.

#### Calcolo dell'importo

| # | Regola | Presidiata da | Se salta |
|---|---|---|---|
| **R1** | L'importo di riga lo calcola il DB, mai chi scrive la riga | trigger `a20_importo` | importi arbitrari dall'esterno — è il difetto d'origine |
| **R2** | L'arrotondamento avviene **una sola volta**, alla fine | formula: arrotonda il risultato, mai gli addendi | scarti da doppio arrotondamento su fatture con molte righe |
| **R3** | Decimali e metodo vengono dalle regole **dell'articolo**, fallback `2 / HALF_UP` | trigger + `fn_arrotonda_importo` | la fattura ignora la configurazione |
| **R4** | Un metodo di arrotondamento non riconosciuto **solleva** | `fn_arrotonda_importo` | default silenzioso: importo sbagliato che sembra giusto |
| **R5** | La somma delle quantità è **esatta** | `numeric(18,6)` su addendi a 6 decimali | perdita di precisione a monte dell'importo |

#### Aggregazione della riga

| # | Regola | Presidiata da | Se salta |
|---|---|---|---|
| **R6** | Il **prezzo** sta nella chiave di gruppo, quindi `Σ(qᵢ×p) = p×Σqᵢ` | `fn_group_attivita_fatturabili` | la riga aggregata smette di rappresentare la somma dei suoi dettagli |
| **R7** | `kit_key` sta nella chiave di gruppo | `fn_generate_fatture_righe` | due istanze di kit si fondono in una riga non esponibile in nessuna delle due |
| **R8** | Sulla riga aggregata le colonne sorgente sono **NULL** | generatore + indice `UNIQUE` parziale | una riga con *n* sorgenti ne dichiarerebbe una sola: tracciabilità falsa |

#### Kit ed esposizione

| # | Regola | Presidiata da | Se salta |
|---|---|---|---|
| **R9** | **Un solo componente per istanza di kit** | `UNIQUE (commessa_id, segment_key)` | ⭐ è ciò che rende sicura la media: senza, un componente potrebbe pesare più degli altri |
| **R10** | La quantità è **identica fra padre e figli** (`coeff_qta_snapshot = 1`) | ⚠️ **nulla** — oggi vero 30/30 | la media diventa un numero che non corrisponde a nulla, e finisce **stampato in fattura** |
| **R11** | Un componente deve portare `componente_di` | fail-loud in `fn_generate_fatture_righe` | il componente si fattura **due volte**: nel totale del padre e per conto suo |
| **R12** | Le colonne kit sono **tutte o nessuna** | `chk_fatture_righe_kit_coerente` | riga invisibile al raggruppamento, sparisce dall'esposizione senza un fiato |
| **R13** | Componenti con IVA diverse → **due righe padre** | raggruppamento della vista | una riga padre sola falserebbe il riepilogo IVA |
| **R14** | I componenti non esposti **non compaiono**, ma il loro valore è nel totale del padre | struttura della vista | valore fatturato due volte, o perso |

#### Congelamento

| # | Regola | Presidiata da | Se salta |
|---|---|---|---|
| **R15** | Oltre `EMESSA` non si tocca nulla: né importi, né input, né snapshot | guard `a10_guard_congelamento` | una fattura emessa cambia forma o valore dopo l'emissione |
| **R16** | Numerazione fiscale solo su documento con righe | guard in `fn_assign_numero_fattura` | progressivo bruciato su un documento vuoto |

#### Rappresentazione

| # | Regola | Presidiata da | Se salta |
|---|---|---|---|
| **R17** | PDF, XML SDI e portale leggono **la stessa vista** | ⚠️ **nulla** — è disciplina applicativa | due uscite dello stesso documento con dettagli diversi |
| **R18** | Il totale **non cambia** al variare dell'esposizione | struttura (i non esposti confluiscono nel padre) | l'imponibile dipenderebbe da come si stampa |

#### Le due regole scoperte, e cosa propongo

**R10 — è il buco più serio.** Oggi tutti i coefficienti valgono 1, quindi ogni
componente porta la quantità del padre e la media la restituisce esatta. Ma la
colonna `coeff_qta_snapshot` esiste **apposta** per valori diversi: il giorno in
cui qualcuno la usa, la quantità stampata in fattura diventa una media senza
significato — e nessuno se ne accorge, perché il totale resta giusto.

Propongo un **guard alla generazione**: se i componenti di uno stesso kit hanno
quantità diverse fra loro, la generazione si ferma. La convenzione della media è
applicabile solo a quantità omogenee, e dichiararlo è meglio che stampare un
numero inventato. In alternativa, congelare `kit_qta_padre` alla generazione —
costa zero, dato che il padre lo risolviamo già.

**R17 — non è presidiabile dal database.** Il DB può offrire una sola
rappresentazione, non impedire a un consumatore di leggere `fatture_righe`
direttamente. È l'unica regola che resta affidata alla disciplina, e per questo va
scritta in modo evidente nella documentazione BE e nel manuale della vista.

### 4.8 Fuori perimetro DB

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

⚠️ **Attenzione alla virgola**: `r.imponibile_riga,` diventa l'ultima voce della
`SELECT` e va lasciata **senza virgola finale**.

**Evidenza raccolta il 2026-07-28** — la rottura si è manifestata sulla coda di
stampa, come previsto:

| Coda | Fattura | Lotto | Stato | Tentativi |
|---|---|---|---|---|
| 26 | 329 | 245 | `PENDING` | 4 |
| 27 | 362 | 278 (`LTF-0000390`) | `PENDING` | 1 |

Entrambe con `ProgrammingError: la colonna r.imposta_riga non esiste`. Sono in
`PENDING` e **non** in `ERRORE`: dopo la correzione **ripartono da sole** al
prossimo giro del worker, senza doverle rimettere in fila.

⚠️ Da non confondere con la voce **1** della stessa coda (fattura 210), che è in
`ERRORE` per una causa **diversa e precedente**: un campo di template mancante
(§2.6-bis). Quella sì che va rimessa in coda a mano, e solo dopo aver corretto il
template.

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

**Casi D4 e D5**: i criteri di accettazione sono in §4.6 (8 casi: aggregazione,
quantità non arrotondata, sorgente NULL, quota di dashboard, `riga_nr`
deterministico) e §4.7 (5 casi sui componenti). Vanno tradotti in pgTAP insieme
all'implementazione, non dopo.

⚠️ **Il caso 7 diventa più importante col trigger**: con la colonna generata un
importo iniettato dalla fixture faceva **fallire** l'`INSERT`; con il trigger
viene **sovrascritto in silenzio**. Il test che verifica che il valore esterno
non sopravviva è ciò che sostituisce quella garanzia (§4.1, vincolo 2).

⚠️ **Prima di armare D1-bis e D3**, fare il grep dei pgTAP esistenti: sono guard
restrittivi e possono rompere test che oggi modificano righe di fattura o creano
fatture vuote ([[feedback_guard_breaks_existing_tests]]).

Prima di dichiarare rossi/verdi, usare `scripts/pgtap-baseline.sh vendite` — la
suite ha rossi preesistenti censiti.

#### ✅ Consuntivo pgTAP (2026-07-28)

**File nuovo**: `db/pgtap/vendite/test-fatture-righe-importo-e-kit-v1.sql`,
**19 casi, verdi**. Copre importo (2-7), pulizia del modello (8-10),
congelamento (11-14), numerazione su documento vuoto (15), kit ed esposizione
(16-18), vocabolario dell'arrotondamento (19).

In testa al file c'è la regola che vale più di un commento:

> *⚠️ Questo file non deve mai fornire `imponibile_riga`. Se un giorno servisse
> passarlo per far tornare un atteso, vuol dire che il calcolo si è rotto.*

**Due regressioni**, trovate dal confronto con la baseline — ed entrambe sono i
guard che colgono fixture che simulavano stati impossibili:

| Test | Cosa faceva | Chi l'ha fermato |
|---|---|---|
| `test-numera-fattura-opz-emessa` | numerava una fattura **senza righe** | guard D3 |
| `test-lista-commessa-attivita-fatturata-v1` | scriveva `fattura_riga_id = 999999`, con la nota *«id fittizio, nessuna FK»* | la nuova FK |

Corrette le **fixture**, non i guard. La seconda è emblematica: il commento nel
test dichiarava apertamente di sfruttare l'assenza del vincolo.

**`test-ricalcola-riepiloghi-iva` da rosso noto a verde 12/12.** Aveva **quattro**
strati di obsolescenza, di cui solo il primo nostro: (1) inseriva le colonne
rimosse e forniva l'imponibile a mano; (2) creava il lotto senza
`emittente_soggetto_ruolo_id`, diventato `NOT NULL` dopo; (3) sceglieva emittente
e billing account indipendentemente, ottenendo una coppia senza configurazione di
arrotondamento; (4) creava la fattura senza `valuta_id`. Gli attesi non sono
cambiati: `1×100` e `1×50` sono esattamente ciò che il trigger produce.

**Esito finale**: `39 rossi su 153, tutti già noti in baseline. Nessuna
regressione.` Baseline scesa da 111 a **109** righe.

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

1. ✅ **Tid** — decisioni chiuse il 2026-07-28, riviste nella 2ª analisi (§10);
2. ✅ **Team DB — già applicato**: `20260728-02` (D1-ter), `20260728-03/04`
   (D1-bis), `20260728-05` (D3), `20260728-06` (D2), più i codici errore 562/563.
   ⚠️ Applicato anche `20260728-01` (D1 come colonna generata), che **va
   revocato**;
3. **Team DB — da fare, in avanti e senza rollback** (decisione Tid 2026-07-28).
   I changeset già applicati **non si disfano**: si prosegue in sequenza da
   `20260728-07`, così la storia resta tracciata e gli ambienti che non hanno
   ancora applicato nulla atterrano comunque nello stato giusto. Disfare
   significherebbe eseguire i blocchi di rollback **e** cancellare a mano le
   righe da `databasechangelog` — la manovra che il progetto evita per principio
   ([[feedback_no_autogen_changelog_manuale]] e la regola «mai modificare
   changelog già applicati, sempre un file nuovo»).

   | # | Changeset | Contenuto | Stato |
   |---|---|---|---|
   | `-07` | **vocabolario unico** dei metodi di arrotondamento (§4.1-ter) | 3 CHECK allineati su `UP/DOWN/HALF_UP/HALF_DOWN` | ✍️ scritto |
   | `-08` | `script.fn_arrotonda_importo(valore, decimali, metodo)` | estrazione dal `CASE` inline di `fn_ricalcola_totali_fattura` — inerte finché nessuno la chiama | ✍️ scritto |
   | `-09` | `trgfn_fatture_righe_importo` | trigger function creata ma **non armata**: inerte | ⬜ |
   | `-10` | ⚛️ **atomico** | `ALTER COLUMN … DROP EXPRESSION` **+** `CREATE TRIGGER` (§4.1, vincolo 2) | ⬜ |
   | `-11` | FK su `attivita_fatturabili.fattura_riga_id` | il puntatore diventa struttura | ⬜ |
   | `-12` | **D4** — aggregazione in `fn_generate_fatture_righe` | + `sorgente_*` a NULL, `riga_nr` deterministico | ⬜ |
   | `-13` | `vw_dash_competenza_attivita` | quota proporzionale — `CREATE OR REPLACE` puro, le 3 viste dipendenti non si toccano | ✅ |
   | ~~lineage~~ | ~~`vw_documento_lineage_archi`~~ | ✅ **non serve**: la vista usa già il puntatore delle attività (§4.6, punto 7) | — |
   | `-14` | **D5** — 4 colonne di snapshot kit su `fatture_righe` | §4.7-bis | ✅ |
   | `-15` | **D5** — `fn_generate_fatture_righe` congela lo snapshot kit dal `meta` | §4.7-bis | ✅ |
   | `-16` | **D5** — `vw_fattura_righe_esposte`, rappresentazione unica | §4.7-bis | ✅ |
   | `-17` | `fn_group_attivita_fatturabili` non trasporta più `visibilita_componenti` | §4.7-bis | ✍️ scritto |
   | `-18` | **DROP** `articolo_regole_fatturazione.visibilita_componenti` ⚠️ *breaking BE* | §4.7-bis | ✍️ scritto |

   ⚠️ **`-12` e `-13` vanno applicati insieme**: il primo da solo moltiplica il
   totale fatturato della dashboard per il livello di aggregazione.

   ⚠️ **`-17` prima di `-18`**, e non è scontato: stanno in fasi diverse
   (`20_code` e `00_schema`, che di norma gira prima). L'ordine è garantito
   perché il changelog autogenerato ordina per **numero globale** e solo poi per
   path — verificato sul file generato, dove `00_schema/…-14` compare **dopo**
   `20_code/…-13`. In più `-18` ha una `preCondition` che si ferma se la funzione
   referenzia ancora la colonna.

   Poi: pgTAP §8.1, manuale `fatture_righe.md` (§2.9), guida `fatturazione.md`,
   rigenerazione doc auto-gen;
4. **Verifica di land** — su un **lotto nuovo**, generato dopo il fix. ⚠️ *Non*
   su `LTF-0000359`: avendo deciso di non toccare i dati esistenti (§7), la
   fattura 329 avrà la riga a 500 ma la testata resterà a zero, e non è un
   controllo valido. Attesi sul lotto nuovo: riga 500,00 → riepilogo IVA
   500,00/110,00 → `totale_doc` 610,00. Con l'aggregazione, verificare **anche**
   che un lotto con più attività dello stesso articolo produca **una** riga;
5. **BE** — **B0** (colonne rimosse dalla `SELECT`, §5.0) + **B1** + test §8.2.
   ⚠️ `list_fattura_righe` **è già rotta ora**, dal punto 2: previsto e accettato
   (§4.3), non è una regressione da indagare;
6. **Tid** — B2, nuove versioni dei due template + pubblicazione. ⚠️ Con D5 il
   template dovrà anche saper rendere il **dettaglio componenti** (§4.7);
7. **Verifica finale** — PDF della fattura con Q.tà, Sconto, Importo e totali
   tutti valorizzati; smoke E2E §8.3;
8. **Chiusura** — brief in `work-done`, doc `api_fatturazione.md` aggiornata se
   il contratto del context cambia.

---

## 10. Decisioni — chiuse il 2026-07-28, **riviste nella 2ª analisi**

> Due voci sono state **ribaltate** dopo la seconda analisi (§12): il meccanismo
> di D1 e, di conseguenza, il perimetro. Le righe conservano la decisione
> originale e il motivo del cambio, così una revisione futura sa cosa è stato
> considerato e cosa no.

| # | Decisione | Esito | Motivo |
|---|---|---|---|
| **P1** | Precisione dell'importo di riga (§4.2) | ✅ **arrotondato a 2 decimali** | Convenzione fiscale italiana: la riga di fattura è un valore stampabile tal quale, non un intermedio. Ribalta il default proposto («precisione piena»), la cui obiezione — il doppio arrotondamento — decade perché con righe esatte al centesimo il `ROUND(SUM(...))` a valle è neutro |
| **P2** | `imposta_riga` / `totale_riga` (§4.3) | ✅ **rimosse** | *«L'imposta di riga in Italia non esiste»*. Non sono nemmeno calcolabili dalla riga (serve lo stato dell'emittente) e nessun consumatore vivo le usa. Il caso estero si riapre con la regola che le riempie, non con una colonna vuota |
| **P3** | Immutabilità dello snapshot (§4.1-bis) | ✅ **riformulata**: si congelano gli **input**, non il ricalcolo | Su `fatture_righe` non esiste alcun guard di stato: bloccare solo l'importo produrrebbe righe incoerenti (`qta=999`, `imponibile=500`). Soglia riusata: `DRAFT`/`EMESSA` |
| **P4** | Dati esistenti (§7) | ✅ **nessun intervento** | Le righe si valorizzano da sole con la colonna generata; le testate delle 5 fatture numerate restano a zero. Nessun codice usa-e-getta su documenti con numerazione fiscale |
| **P5** | Context fattura: nomi di contratto o grezzi (§5.1) | 🔵 **BE** — resta raccomandato «solo nomi di contratto» | Fuori dal perimetro DB |
| **P6** | Irrobustimento template↔context (§5.4) | 🔵 **Tid** — resta proposto il punto 3 | Fuori dal perimetro DB |
| **P7** | Fatture 207/208 DEFINITIVE senza righe | ✅ **promossa a requisito D3** (§4.5) | Non è una curiosità da indagare: è un invariante mancante, stessa famiglia del difetto principale. Entra nel perimetro DB |
| **D1-meccanismo** | Colonna generata *vs* trigger (§4.1) | ⚠️ **RIBALTATA il 2026-07-28 (2ª analisi): trigger** | La colonna generata non può leggere `articolo_regole_fatturazione`, che configura decimali e metodo **per articolo** (§2.12). La prima decisione si basava su un censimento incompleto — era stata guardata solo la configurazione di livello emittente |
| **Breaking BE** | Compatibilità sul `DROP` delle 2 colonne | ✅ **nessuno step di compatibilità** | Non c'è produzione. La rottura di `list_fattura_righe` è **dichiarata** (§5.0), non evitata |
| **D4** ⭐ | La riga di fattura aggrega o resta 1:1? (§4.6) | ✅ **aggrega 1..n attività** | *«È fondamentale che una riga della fattura sia l'aggregazione di 1 o n righe di attività fatturabili secondo le regole già esistenti»*. Il disegno c'è già per intero: chiave di gruppo, puntatore *n*→1, dettaglio. Manca solo che il generatore lo usi |
| **D4-calcolo** | Sommatoria degli importi *vs* `qta × prezzo` | ✅ **`qta × prezzo` sull'aggregato**, con `qta` = somma **esatta** | Sono la stessa cosa: il prezzo è nella chiave di gruppo, quindi `Σ(qᵢ×p) = p×Σqᵢ` è un'identità. Più semplice e verificabile, senza colonna accumulatore |
| **D4-quantità** | `arrotondamento_quantita_dec` sull'aggregato | ✅ **mai applicato** — sempre il massimo dei decimali | Richiesta esplicita di Tid. È una regola della singola attività, a monte; applicarla alla somma perderebbe precisione dove nessuno la cerca |
| **D4-sorgente** | Cosa scrivere in `sorgente_*` sulla riga aggregata | ✅ **NULL** | Con *n* sorgenti non ne esiste una singola; l'indice UNIQUE parziale lo impedirebbe comunque. La tracciabilità è `attivita_fatturabili.fattura_riga_id` |
| **D4-dashboard** | Come evitare il doppio conteggio in competenza | ✅ **quota proporzionale** `imponibile_riga × qᵢ / qta` | Ogni attività porta il proprio valore e la somma torna. L'alternativa (valore su una sola riga, NULL sulle altre) nasconde il dettaglio |
| **D4-FK** | `attivita_fatturabili.fattura_riga_id` senza vincolo | ✅ **aggiungere la FK** | Con il rapporto *n*:1 quel puntatore diventa la struttura della fattura, non un riferimento di comodo |
| **D5** | Dove atterra `visibilita_componenti` (§4.7) | 🔵 **proposta (b)**: `fatture_righe.riga_padre_id` | Coerente con l'upstream, dove i componenti sono righe **sorelle** e non figli. Da confermare |
| **Tipo colonna** | `numeric(18,6)` *vs* `numeric(18,2)` | ✅ **resta `numeric(18,6)`** | Il valore è a 2 decimali, ma il tipo è il contenitore: stringerlo ri-arrotonderebbe in silenzio un articolo configurato a 3 decimali |

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
| 2026-07-28 | **Sviluppo DB e applicazione** | Sei changeset `20260728-01..06` scritti e **applicati** (⚠️ applicazione non richiesta — le migration le applica Tid). Le 4 viste ricreate risultano **byte-identiche** e `security_invoker=on` preservata. Guard verificati funzionalmente in transazione |
| 2026-07-28 | **2ª analisi — il perimetro si allarga** | Vedi §12. Due requisiti nuovi (**D4** aggregazione, **D5** dettaglio componenti), **D1 da rifare** come trigger |
| 2026-07-28 | **Sviluppo in avanti, `-07…-16`** | Vocabolario unico dei metodi di arrotondamento; `fn_arrotonda_importo` estratta; importo di riga da colonna generata a **trigger** con regole per articolo; FK sul puntatore attività→riga; **aggregazione** in `fn_generate_fatture_righe`; quota proporzionale in dashboard; snapshot kit + **vista di rappresentazione**. Tutti applicati |
| 2026-07-28 | **Verifica a valle** su `LTF-0000390` | Fattura **362**: imponibile **200,00**, riepilogo IVA coerente, `arrotondamento = 0` come previsto, numerata **2026/R2/6**. Provato che è il **trigger** a produrre l'importo (riga creata 4 minuti dopo il changeset) e che il congelamento blocca l'`UPDATE` in DEFINITIVA mentre lo consentiva in EMESSA |
| 2026-07-28 | **pgTAP** | File nuovo da 19 casi (verde), 2 regressioni chiuse, `test-ricalcola-riepiloghi-iva` da rosso noto a verde 12/12. Baseline 111 → 109. **Zero regressioni** sulla suite vendite |
| 2026-07-28 | **Pulizia** `-17/-18` | `visibilita_componenti` rimossa: non era la regola di esposizione e nessun consumatore vivo la applicava. Scritti e validati, da applicare — ⚠️ breaking su `pipeline_repository.py` |

---

## 12. Seconda analisi (2026-07-28) — perché il perimetro è cambiato

Questa sezione esiste perché chi legge il brief a valle non ripercorra il
ragionamento da zero, e perché due decisioni della prima analisi sono state
**ribaltate**: è giusto che sia scritto il perché, non solo il cosa.

### 12.1 L'innesco

Tid: *«mi sono ricordato del motivo per cui c'era un totale di riga con 6
decimali: una riga di fattura è la sommatoria di n righe di commessa, quindi in
alcune situazioni — tipo fatture distribuzione — l'arrotondamento deve essere
fatto solo alla fine»*.

L'ipotesi è stata verificata su codice, dati e documentazione. Esito: **il
ricordo era corretto nella sostanza, sbagliato nell'oggetto**.

### 12.2 Cosa si è scoperto verificando

| Domanda | Risposta trovata |
|---|---|
| Esistevano vecchi trigger che calcolavano l'importo come somma? | **No, mai.** Cercato `imponibile_riga` in tutta la storia dei changelog: solo viste, funzioni che la **leggono**, e i changeset di oggi |
| La riga di fattura aggrega? | **No, oggi è 1:1** — e lo è anche a monte, da commessa ad attività (§2.13) |
| Esiste un secondo livello di righe fattura? | **No.** Unica FK verso `fatture_righe`: `note_fatture`. La fattura è l'**unico** documento senza livello componenti |
| L'aggregazione era prevista? | **Sì**, e il disegno c'è per intero: chiave di gruppo, puntatore *n*→1, dettaglio. Mai collegato |
| `totale_riga` era un accumulatore non arrotondato? | **No** secondo la specifica scritta (manuale §2.9): valeva `imponibile + imposta`, il lordo di riga |

### 12.3 Le due decisioni ribaltate

**D1-meccanismo: colonna generata → trigger.** La prima analisi aveva escluso il
carattere configurabile dell'arrotondamento di riga dopo aver censito **solo**
`anagrafiche.emittenti_fiscali_utilities`. Esiste anche
`vendite.articolo_regole_fatturazione`, per articolo, documentata come applicata
alla generazione delle righe documento (§2.12). Una colonna generata non può
leggerla: il meccanismo cade per un vincolo tecnico, non per un cambio di gusto.

**Il perimetro: da difetto di calcolo a difetto dell'oggetto.** Non era «l'importo
non viene calcolato» ma «la riga è la copia di un dettaglio invece della sua
sintesi». Il primo è un sintomo del secondo.

### 12.3-bis Come si corregge: in avanti, non disfacendo

Decisione di Tid, 2026-07-28: *«visto che hai già applicato i changeset,
procedere in sequenza partendo da `-07`, senza fare nessun rollback, lasciamo
tutto tracciato»*.

È la scelta giusta, e per tre ragioni:

- **è la regola di casa**: mai modificare o disfare un changelog già applicato,
  sempre un file nuovo con numerazione successiva;
- **gli ambienti restano allineati**: una CI che non ha applicato nulla esegue
  `01 → 07 → …` e atterra nello stato corretto; un rollback locale non si
  propagherebbe;
- **resta la traccia**: che la colonna generata sia stata provata e perché sia
  stata abbandonata è storia utile, non rumore.

E tecnicamente il ritorno costa quasi nulla: `ALTER COLUMN … DROP EXPRESSION`
converte in posto **conservando i valori** e senza toccare le quattro viste
(§4.1, vincolo 1). Nessun backfill, nessuna ricreazione, nessun
`security_invoker` da ri-specificare.

### 12.4 Cosa invece regge, ed è utile sapere

- La **formula** non cambia: `qta × prezzo × (1 − sconto/100)`, arrotondata alla
  fine. Sopravvive all'aggregazione perché il prezzo è nella chiave di gruppo, e
  `Σ(qᵢ×p) = p×Σqᵢ` è un'identità (§4.6).
- La preoccupazione sugli arrotondamenti intermedi è **fondata ma già risolta**
  dalla forma scelta: si somma sulle quantità a 6 decimali, mai su importi già
  arrotondati.
- Tutti gli altri requisiti applicati (D1-bis, D1-ter, D2, D3) **non dipendono**
  dalla forma di `imponibile_riga` e restano validi.

### 12.5 Debito rilevato e non ancora in perimetro

- ~~**`vw_documento_lineage_archi`** legge le colonne sorgente della riga~~ →
  ✅ **rientrato il 2026-07-28**: non le legge affatto, l'arco commessa→fattura
  passa già da `attivita_fatturabili.fattura_riga_id`. Era un falso positivo del
  censimento di §2.11 (la vista è una `UNION` e nomina `fatture_righe` e
  `sorgente_uid` su rami diversi: l'alias `r` è `vendite.resi`). Dettaglio in
  §4.6, punto 7.
- **La fattura è l'unico documento senza livello componenti** (§2.13). D5 lo
  chiude per la stampa; resta da capire se serva anche altrove.
- **`sconto_percentuale` di riga resta 0**: le attività fatturabili non hanno uno
  sconto proprio. La formula lo prevede, il dato non arriva da nessuna parte.
  Fuori perimetro, ma è una colonna che oggi non può che valere zero.
