## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva_movimenti`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo padre ·
> [vendite.fatture](/dbzero/vendite/tabelle/fatture) ·
> [anagrafiche.fn_consuma_plafond_titolo_iva](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva) — chi scrive le righe di consumo ·
> [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi tiene la somma

---

### 🎯 Scopo Principale

(rev 2026-08-29 — tabella nata il 2026-08-29)

Il **registro del plafond**: quanto tetto di una dichiarazione d'intento è stato
usato, un movimento alla volta.

| Movimento | Segno | Da dove |
| --- | --- | --- |
| `FATTURA` | `+` | una fattura emessa sotto il titolo consuma capienza |
| `NOTA_CREDITO` | `−` | la nota di credito la restituisce |
| `FORZATURA` | `±` | l'operatore, con **motivo obbligatorio** |

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

⭐ In pratica non ci si arriva quasi mai, perché `fn_consuma_plafond_titolo_iva` è
**idempotente**: se quella fattura ha già consumato quel titolo rilegge il movimento
che c'è invece di scriverne un secondo. L'unicità resta come rete — ma parlerebbe
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

### Il conto non può andare sotto zero — e il tetto non si controlla qui

L'accumulatore rifiuta una somma negativa: nessuna lettura del dominio la ammette.
Il caso arriva da una nota di credito più grande del consumato, o da una forzatura
negativa sbagliata.

⛔ **Il superamento del tetto invece non si blocca**, ed è una decisione:

* sulle **fatture** il caso non si presenta — la spezzatura fa sì che il consumo non
  superi mai la capienza, e a garantirlo è la primitiva;
* sulle **forzature** un superamento è un'informazione sul mondo. Se le fatturazioni
  fuori sistema sfondano il plafond, è il **plafond registrato a essere sbagliato** —
  e impedire di scrivere il fatto impedirebbe di **accorgersene**.

📌 Il presidio giusto per quel caso non è un rifiuto: è una **lista di titoli
sfondati che qualcuno guarda**. Non esiste ancora, ed è annotato fra i residui del
cantiere.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D5`.

---

{% include-markdown "signature-core.md" %}
