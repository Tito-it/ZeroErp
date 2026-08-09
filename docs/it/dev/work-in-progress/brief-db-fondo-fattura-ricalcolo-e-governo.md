# Fondo fattura — un numero ricalcolato che muove denaro

> **Cos'è.** Il brief di un problema **strutturale** del meccanismo dei fondi
> fattura, emerso il **2026-08-09** analizzando gli incassi e messo da parte
> perché è un cantiere suo, in `vendite`, non in `pagamenti`.
>
> **Perché esiste questo file.** L'analisi è già stata fatta, in profondità, e
> sarebbe andata persa dentro il brief di un altro cantiere. Qui non c'è un
> piano: c'è la **diagnosi** e ciò che è già stato deciso a tampone altrove.
>
> **Non è urgente oggi. Lo diventa il giorno in cui esiste il primo incasso** —
> vedi §3, ed è la ragione per cui vale la pena averlo scritto adesso.
>
> **Origine**: [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis D1-bis.

---

## 1. La tesi, in una frase

> **Il fondo fattura è un numero che viene ricalcolato, e che muove denaro.**

Le due cose insieme non stanno in piedi. Un numero **derivato** può essere
ricalcolato quante volte si vuole: se sbaglia, al giro dopo si corregge, e nel
frattempo non è successo niente. Un numero che **muove denaro** — che viene
assegnato a una fattura figlia e ne cambia l'importo — è un **atto**, e un atto
non si ricalcola: si compie, e semmai si annulla con un altro atto.

Oggi il fondo è tutte e due le cose insieme. È da lì che discende il resto.

---

## 2. Come funziona oggi — misurato il 2026-08-09

### Il calcolo

`vendite.fn_genera_fondi_fattura_source(...)` calcola, per le fatture con
`minimo IS TRUE` di un dato billing account / tipo doc / emittente / valuta:

```text
importo_target = pagamenti.fn_get_saldo_fattura(f.id).saldo
               − pagamenti.fn_get_saldo_fattura_contabili(f.id).saldo_contabile
```

e poi:

| Ramo | Condizione | Effetto |
| --- | --- | --- |
| `UPDATE` | il fondo esiste già e il valore è cambiato | `importo = target`; `stato = ANNULLATO` **se e solo se** `target = 0`, altrimenti `DISPONIBILE` |
| `INSERT` | il fondo non esiste e `target <> 0` | crea il fondo `DISPONIBILE` |

⚠️ **`<> 0` è l'unica condizione sull'importo.** Non c'è limite inferiore.

### Il resto della catena

| Pezzo | Cosa fa |
| --- | --- |
| `vendite.fatture_fondi_fattura_source` | stati `DISPONIBILE` → `ASSEGNATO` → `ANNULLATO`. ⚠️ **Nessun CHECK sull'importo**: un fondo negativo è strutturalmente ammesso |
| task `genera_fondi_source_lotto` | `attivo = true` nel registry — **codice vivo** |
| task `applica_fondi_lotto` | `attivo = true` — assegna i fondi `DISPONIBILE` a una fattura figlia |
| `fn_sync_contabili_fondo_fattura(fattura_figlia)` | crea **righe contabili** per il fondo applicato; chiamata da `fn_ricalcola_totali_fattura` |
| `fn_reset_fondi_fattura(fattura)` | riporta `ASSEGNATO` → `DISPONIBILE` |
| centro `FONDI_FATTURA` (id 37, `is_fondo_fattura`) | la corsia contabile dedicata |

### ⚠️ Una funzione il cui nome mente — e nessuno la chiama

`vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id)` restituisce
`TABLE(inserted_movimenti, updated_movimenti, annullati_source)`.

Il nome e le colonne dicono **movimenti**. Il corpo, letto per intero, è un
guscio: delega **tutto** a `fn_sync_contabili_fondo_fattura` e si limita a
rinominare `inserted_righe` → `inserted_movimenti`. **Non crea nessun
movimento**, e ✅ **nessuna funzione del database la chiama**.

🔴 Va segnalata per due ragioni:

1. chi legge la firma crede che il **posting esista** — ed è probabilmente una
   delle ragioni per cui la guida lo descrive come se ci fosse (non c'è: vedi il
   brief incassi §1-bis);
2. è **codice morto con un nome che promette**, cioè il tipo di residuo che al
   prossimo giro qualcuno chiama pensando di aver trovato il pezzo mancante.

Da decidere: rinominarla onestamente o ritirarla.

---

## 3. 🔴 Il fatto che rende la cosa non rimandabile all'infinito

> **Il meccanismo dei fondi non ha mai visto un pagamento.**

Il fondo si calcola da `fn_get_saldo_fattura`, che è il residuo *dopo i
movimenti*. Ma **nessuna funzione, in tutto il database, scrive
`pagamenti.vendite_movimenti`**: il posting non è implementato.

Ne segue che finora `fn_get_saldo_fattura` ha sempre restituito, per costruzione,
**l'intero `totale_a_pagare`**. Il fondo è stato progettato, scritto e messo in
pipeline in un mondo in cui **quel termine non si muoveva mai**.

**La slice 1 del cantiere incassi cambia questo per sempre**, e da quel momento
il fondo comincia a oscillare a ogni incasso. Non è un difetto che si manifesta:
è un comportamento che **non è mai stato esercitato**.

### Le due serrature, e chi apre quale

| Serratura | Stato al 2026-08-09 | Chi la apre |
| --- | --- | --- |
| `f.minimo IS TRUE` | **0 fatture a minimo** su 12; **0 fondi** generati | una configurazione, in qualunque momento |
| saldo negativo (sovra-incasso) | impossibile: nessun movimento esiste | 🔴 **la slice 1 del cantiere incassi** |

Con entrambe aperte, un sovra-incasso genera un fondo di importo **negativo** in
stato **`DISPONIBILE`**, che `applica_fondi_lotto` assegna a una fattura figlia.
Nessun `CHECK` lo ferma.

---

## 4. Il difetto strutturale, oltre il caso del segno

Il fondo negativo è il sintomo che si vede per primo. Il problema è più a monte, e
si chiude solo separando due cose che oggi sono una sola:

| | Natura | Regola |
| --- | --- | --- |
| **I fatti** | denaro entrato o uscito, con o senza destinazione | si **aggiungono**, non si aggiornano mai |
| **I saldi** | residuo per fattura, per rata, credito del cliente | si **leggono**, non si conservano — quindi non possono divergere |
| **Le decisioni** | rimborsare, portare avanti, compensare | le prende una **persona**, e ognuna diventa un fatto |

Il fondo oggi sta **in mezzo**: è calcolato come un saldo, ma si comporta come una
decisione. Andrebbe portato **fra le decisioni** — un atto deliberato, non un
numero che un batch riscrive ogni notte.

### ⭐ Perché questo elimina il rischio di rincorsa

Il timore — legittimo — è di *«rincorrere gli incassi»*: un automatismo che
aggiorna un numero, un altro che lo rilegge e ne aggiorna un terzo, all'infinito.

Un ciclo del genere richiede che **un automatismo riscriva un numero che un altro
rilegge**. Se l'unica scrittura è l'aggiunta di un fatto e tutto il resto è
derivato, **non c'è niente che possa rincorrersi**: un saldo non insegue sé
stesso. Non «improbabile» — **impossibile per costruzione**.

---

## 5. Cosa è già stato deciso (a tampone) nel cantiere incassi

Non aspetta questo brief: sta in
[brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis
ed è **dentro la slice 1**, perché è la slice che apre la seconda serratura.

1. **Limite inferiore alla generazione**: si crea un fondo solo per
   `importo_target > 0`. Il verso opposto **non è un fondo**: è denaro in
   eccesso, un fatto di natura diversa.
2. **Nessun automatismo tocca il fondo in base agli incassi.** Un fondo già
   esistente il cui target diventa negativo **resta com'è**; la fattura compare
   in un **elenco da guardare**, insieme alle rate sovra-incassate.

⭐ La seconda regola chiude anche la domanda *«il fondo va portato ad `ANNULLATO`
quando il target diventa negativo?»* — non scegliendo fra le due strade, ma
osservando che chiuderlo in automatico **sarebbe un automatismo che scrive**, e
sono stati esclusi tutti. Se non ci si fida di un automatismo a **creare** un
fondo, tanto meno a **cancellarlo**.

⚠️ **Sono tamponi, non la soluzione.** Impediscono al meccanismo di peggiorare
quando gli incassi arriveranno; non risolvono il fatto che un numero ricalcolato
muova denaro.

---

## 6. Le domande aperte

| | Domanda |
| --- | --- |
| **F-1** | Il fondo diventa un **atto** (creato da una decisione, con la sua causale) o resta un numero derivato che qualcuno approva prima che muova denaro? |
| **F-2** | Che cosa succede a un fondo `ASSEGNATO` se la fattura sorgente riceve poi un incasso che ne cambia la base? Oggi `fn_reset_fondi_fattura` sa riportarlo a `DISPONIBILE`, ma **chi decide** che vada fatto? |
| **F-3** | L'eccedenza di un sovra-incasso: rimborso, compensazione (`pagamenti.compensazioni` esiste ed è il candidato naturale) o applicazione a una fattura futura? Sono tre atti diversi con tre tracce diverse |
| **F-4** | `fn_sync_pagamento_fondo_fattura` — rinominare o ritirare? |
| **F-5** | Serve un `CHECK` sull'importo di `fatture_fondi_fattura_source`, o basta il limite inferiore nella funzione? (Un CHECK è una garanzia strutturale; un `WHERE` è una garanzia da ricordare) |

---

## 7. Dove guardare

| Cosa | Dove |
| --- | --- |
| Il calcolo | `vendite.fn_genera_fondi_fattura_source` |
| La tabella e i suoi stati | [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) + il suo `manual` |
| L'applicazione alla figlia | task `applica_fondi_lotto` → `fn_sync_contabili_fondo_fattura` |
| Il reset | `vendite.fn_reset_fondi_fattura` |
| Il guscio vuoto | `vendite.fn_sync_pagamento_fondo_fattura` |
| I due saldi che lo alimentano | `pagamenti.fn_get_saldo_fattura`, `fn_get_saldo_fattura_contabili` |
| Il modello contabile intorno | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Il cantiere che apre la serratura | [brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis |

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-09 | Stesura, estraendo l'analisi dal cantiere incassi su indicazione di Tid — «meglio un brief apposito per non dimenticare, dato che l'analisi è già approfondita». Misurati: l'unico filtro `<> 0`, l'assenza di CHECK sull'importo, i due task `attivo = true`, le due serrature (0 fatture a minimo / nessun movimento), e il guscio vuoto `fn_sync_pagamento_fondo_fattura` che nessuno chiama |
