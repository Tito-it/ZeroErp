## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva_movimenti`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo padre ·
> [vendite.fatture](/dbzero/vendite/tabelle/fatture) ·
> [anagrafiche.fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe) — chi scrive le righe di consumo ·
> [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi tiene la somma

---

### 🎯 Scopo Principale

(rev 2026-08-29 — tabella nata il 2026-08-29)

Il **registro del plafond**: quanto tetto di una dichiarazione d'intento è stato
usato, un movimento alla volta.

| Movimento | Segno | Da dove |
| --- | --- | --- |
| `FATTURA` | `±` | una riga di fattura sotto il titolo: positiva consuma capienza, negativa (uno sconto, un componente di kit negativo) la restituisce |
| `NOTA_CREDITO` | `−` | la nota di credito la restituisce |
| `FORZATURA` | `±` | l'operatore, con **motivo obbligatorio** |

⭐ **Dal 2026-10-04 un movimento `FATTURA` può essere negativo** (`20261004-02`,
decisione C di Tid, `brief-db-bom-flag-quantita-e-kit-in-fattura` §13): il plafond si
consuma sul **netto** della fattura, e la riga negativa scrive il suo movimento col
suo segno. Resta di tipo `FATTURA` perché il tipo dice **quale documento** l'ha
prodotto: scriverla `NOTA_CREDITO` farebbe dire al registro che esiste una nota di
credito che non c'è. Lo zero resta vietato: non è un movimento. La fattura non
restituisce mai più di quanto essa stessa consuma, quindi la sua somma resta fra zero
e la capienza.

`anagrafiche.soggetti_titoli_iva.imponibile_utilizzato` è la **somma** di queste
righe, e nessuno la scrive a mano.

---

### ⭐ Perché un registro e non una colonna

Le due richieste sembravano in conflitto: il residuo doveva essere **memorizzato**
(serve a poterlo ridurre a mano quando esistono fatturazioni fuori dal sistema) e la
nota di credito doveva **restituirlo**.

⛔ Ma un numero memorizzato *e* forzabile a mano **diverge in silenzio da ciò che
rappresenta**: due sorgenti della stessa verità, e nessuna delle due sa di essere
sbagliata. Su un plafond il costo non è un numero storto in una lista — è il dato che
l'Agenzia delle Entrate **verifica**.

Con il registro si guadagnano tre cose che la colonna nuda non dà:

* la forzatura ha un **motivo, un autore e una data**;
* il consumo è **algebrico**, senza casi speciali per la nota di credito;
* la riconciliazione col fatturato è una **query**, non un'indagine.

⚠️ Non è un pattern nuovo da inventare: il progetto lo usa già nel ponte
`vendite.resi_righe_riconsegne` e nelle rettifiche di `vw_partite_merce`.

---

### ⚠️ Una forzatura non nomina nessuna fattura, ed è il suo senso

Esiste per registrare ciò che il sistema **non** ha fatturato. Un controllo impone
`fattura_id` vuoto sulla forzatura e valorizzato sugli altri due: senza,
«forzatura» diventerebbe la scorciatoia con cui si scrive un consumo di fattura
**saltando la primitiva che lo calcola** — cioè l'unica che prende il lock e decide
la spezzatura.

E il **motivo** è obbligatorio: è ciò che distingue una correzione tracciata da un
numero sovrascritto. Uno spazio non è una spiegazione, e il controllo lo sa.

---

### ⭐ La rete contro il doppio consumo

Un'unicità parziale su *(titolo, tipo, fattura, riga)* impedisce allo **stesso
documento di consumare due volte lo stesso titolo**.

È la rete sotto al lock: il lock serializza due fatture che diventano definitive
nello stesso istante, questa ferma la ripetizione a distanza di tempo.

⚠️ Sulle **forzature** non si applica, ed è voluto: due correzioni identiche nello
stesso giorno possono essere due fatti distinti.

⭐ In pratica non ci si arriva quasi mai, perché `fn_consuma_plafond_titolo_iva_righe`
è **idempotente**: se quella fattura ha già consumato quel titolo rilegge i movimenti
che ci sono invece di scriverne altri. L'unicità resta come rete — ma parlerebbe
con un errore tecnico muto dentro un cambio di stato, ed è meglio non doverla
incontrare.

---

### ⚠️ La data è obbligatoria e non ha un default

Nessun «adesso»: la data la porta chi scrive — la data documento della fattura, o la
data che l'operatore dichiara sulla forzatura.

⭐ È lo stesso vincolo che vale per il risolutore, e per la stessa ragione: **il giro
di fatturazione può girare il giorno dopo**, e un registro fiscale datato con
l'orologio del batch racconta il giorno sbagliato.

---

### ⛔ Le righe **non** spariscono col titolo

Nessun `ON DELETE CASCADE`, al contrario delle righe di ambito. Un ambito è una
clausola; un movimento di plafond è un **fatto contabile**. Un titolo con movimenti
non si cancella: **si spegne**.

---

## ⛔ Il registro è «solo aggiunte», e dal 2026-08-31 lo impone il database

Una riga scritta **non si modifica e non si cancella**:
[`trgfn_stiva_movimenti_append_only`](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_append_only)
rifiuta `UPDATE` e `DELETE` con `E_TITOLO_IVA_MOVIMENTO_IMMUTABILE`.

⚠️ **Prima era una promessa, non una regola.** Il disegno di `D5` poggiava su
«il registro resta append-only», ma nel database non c'era nulla che lo
imponesse: il backend non cancellava perché era scritto in un brief. Decisione di
Tid del 2026-08-30.

⛔ **Si vietano entrambe le operazioni, e la metà che sembra meno grave è la
peggiore.** Un `UPDATE` riscrive la storia **in silenzio**: l'accumulatore
ricalcola e il totale resta «giusto», quindi nessuno vede che un importo è
cambiato. Un `DELETE` almeno lascia un buco.

⚠️ **Conseguenza da conoscere**: di
[`trgfn_soggetti_titoli_iva_movimenti_accumulatore`](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore)
gira ormai **solo il ramo `INSERT`**; gli altri due, e il trigger di storico, sono
irraggiungibili. Restano dove sono come difesa in profondità, ed è dichiarato nel
loro manuale.

📌 ~~**La pulizia della fattura, un giorno, dovrà passare.**~~ ⭐ **Deciso il 2026-10-04 (strada A di Tid):** una fattura che ha consumato plafond **non si disfa più** — le tre porte di reset e la pulizia la fermano con `E_FATTURE_PLAFOND_CONSUMATO` ([script.fn_check_fatture_con_plafond_consumato](/dbzero/script/funzioni/fn_check_fatture_con_plafond_consumato)), e il lotto va avanti. Uno storno non avrebbe risolto: anche lo storno nomina la fattura. Il testo che segue è la domanda com'era posta prima della decisione. Oggi non tocca questa
tabella — è un'eccezione dichiarata nel presidio di copertura, con l'alibi «zero
righe con una fattura» — ma con `I5` servirà decidere: o un'apertura dichiarata,
o (preferibile) **stornare invece di cancellare**, cioè lo stesso meccanismo
dell'annullo qui sotto. Sta scritto nel corpo del guard.

---

## ⭐ Annullare una forzatura: una riga in più, non un flag

Una forzatura sbagliata **non si cancella e non si spegne**: si annulla scrivendo
una **seconda riga `FORZATURA` di segno opposto**, collegata alla prima da
`annulla_movimento_id`.

| | |
| --- | --- |
| **Chi la scrive** | [`fn_annulla_movimento_titolo_iva(movimento, motivo)`](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — il chiamante passa **quale riga** e **perché**; importo e titolo li **deriva** il database |
| **Chi decide se si può** | [`script.fn_check_annullo_movimento_titolo_iva`](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — la stessa che spegne il pulsante nel read-side |
| **Chi presidia la riga scritta** | [`trgfn_stiva_movimenti_guard_annullo`](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_guard_annullo) |
| **Dove si vede** | [`vw_stiva_movimenti_dettaglio`](/dbzero/anagrafiche/views/vw_stiva_movimenti_dettaglio) |

⭐ **Perché una riga e non un flag `annullato`**, ed è lo stesso ragionamento che
ha prodotto il registro:

1. il registro resta **append-only** — un flag sarebbe di nuovo un valore
   sovrascritto sopra a un altro;
2. ⭐ **l'accumulatore non si tocca**: somma **senza filtri**, quindi un
   contro-movimento riporta `imponibile_utilizzato` al valore giusto da sé. Un
   flag imporrebbe un `WHERE NOT annullato`, cioè mettere le mani nel cuore di
   `I7` per un caso di correzione;
3. la **data dell'annullo** è essa stessa un'informazione — *quando* qualcuno si è
   accorto dell'errore. Un flag la perde, una riga la porta in `data_movimento`;
4. la traccia è più forte: si vedono **entrambe** le righe, l'errore e la
   correzione, ognuna col suo motivo.

### I vincoli, e cosa impedisce ciascuno

| Vincolo | Cosa impedisce |
| --- | --- |
| `fk_soggetti_titoli_iva_movimenti_annulla` | un collegamento a un movimento che non esiste. ⚠️ `ON DELETE NO ACTION`: una `SET NULL` messa «per sicurezza» svuoterebbe il legame in silenzio |
| `chk_stiva_movimenti_auto_annullo` | una riga che annulla **sé stessa**. ⭐ È uno dei pochi casi in cui il `CHECK` è la sede giusta: confronta due colonne della **stessa** riga |
| `uq_stiva_movimenti_annulla` (unique parziale) | il **doppio annullo** della stessa riga |
| il guard | movimento non `FORZATURA`, **titolo diverso**, **importo non opposto**, già annullato, o esso stesso un annullo |

⛔ **Profondo uno: un annullo non si annulla** (decisione di Tid, 2026-08-30). Se
la forzatura serve ancora, se ne scrive una **nuova** col suo motivo — il registro
si legge come un racconto dritto invece che come una catena da risalire.

> ⛔ **Il controllo sul TITOLO è il più importante dei cinque**, e non si vede.
> Un annullo collegato a un movimento di un **altro** titolo decurterebbe il
> plafond sbagliato e lascerebbe gonfiato quello della forzatura — **senza
> sollevare niente**, perché l'accumulatore somma *per titolo* e del collegamento
> non sa nulla. Si vedrebbe solo guardando due plafond insieme. Nel dato reale
> quel «altro titolo» è di **un altro cliente**.
>
> ⛔ **E quello sull'IMPORTO è ciò che rende vera la promessa.** Senza, il
> database ammetterebbe un «annullo» di 100 su una forzatura di 250, e
> `imponibile_utilizzato` **non tornerebbe** al valore precedente — cioè proprio
> la cosa per cui l'annullo esiste.

### ⚠️ Un annullo si può rifiutare, e per un motivo che sorprende

Annullare **riduce** l'usato, quindi di norma passa. Ma se nel frattempo le note
di credito hanno superato le fatture, togliere la forzatura porterebbe la somma
**sotto zero** — e il conto sotto zero non è ammesso.

⭐ Per questo il motivo `PLAFOND_NEGATIVO` è **fra quelli che spengono il
pulsante**, non fra gli errori: l'operatore lo scopre guardando, non premendo.

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`.

---

### Il conto non può andare sotto zero — e il tetto non si controlla qui

L'accumulatore rifiuta una somma negativa: nessuna lettura del dominio la ammette.
Il caso arriva da una nota di credito più grande del consumato, o da una forzatura
negativa sbagliata.

⛔ **Il superamento del tetto invece non si blocca**, ed è una decisione:

* sulle **fatture** il caso non si presenta — la spezzatura fa sì che il consumo
  netto non superi mai la capienza, e a garantirlo è la madre del consumo;
* sulle **forzature** un superamento è un'informazione sul mondo. Se le fatturazioni
  fuori sistema sfondano il plafond, è il **plafond registrato a essere sbagliato** —
  e impedire di scrivere il fatto impedirebbe di **accorgersene**.

📌 Il presidio giusto per quel caso non è un rifiuto: è una **lista di titoli
sfondati che qualcuno guarda**. Non esiste ancora, ed è annotato fra i residui del
cantiere.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D5`.

---

{% include-markdown "signature-core.md" %}
