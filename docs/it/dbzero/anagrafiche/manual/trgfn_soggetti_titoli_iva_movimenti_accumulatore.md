## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti)
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
>
Approfondimento funzioni:
> • [anagrafiche.fn_consuma_plafond_titolo_iva](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva) — chi scrive le righe di consumo

---

### 🎯 Scopo Principale

(rev 2026-08-29 — funzione nata il 2026-08-29)

Riporta `anagrafiche.soggetti_titoli_iva.imponibile_utilizzato` alla **somma** del
registro dei movimenti, dopo ogni scrittura sul registro.

⭐ È ciò che rende vera la promessa del disegno: il valore è **memorizzato** — perché
serve poterlo correggere a mano quando esistono fatturazioni fuori dal sistema — ma
**non può mentire**, perché nessuno lo scrive direttamente. Una forzatura è una
**riga** con motivo, autore e data, invece di un numero sovrascritto sopra a un
altro.

---

### Contesto di Esecuzione

* **Tipo**: trigger `AFTER INSERT OR UPDATE OR DELETE`, per riga
* **Fascia**: `z90`

---

### ⚠️ Ricalcola dalla somma, non somma un delta

Un accumulatore incrementale (*«aggiungi l'importo a quello che c'è»*) va fuori
sincrono al primo caso che nessuno ha previsto: un importo modificato, una riga
cancellata, un movimento spostato da un titolo a un altro.

Il ricalcolo **non ha casi**: qualunque cosa succeda al registro, la colonna torna a
dire quello che il registro dice. Costa una scansione dei movimenti di **un** titolo,
che è esattamente ciò che il suo indice serve.

---

### 🔴 Il caso che si sbaglia se non ci si pensa

Un aggiornamento che **sposta un movimento da un titolo a un altro** deve
ricalcolarli **entrambi**. Guardando distrattamente solo il valore nuovo se ne
ricalcola uno, e il titolo abbandonato resta con la somma di prima — cioè **un
plafond che risulta consumato da un movimento che non è più suo**.

Qui i due identificativi si raccolgono e si ricalcolano tutti e due.

---

### ⛔ Il conto sotto zero si rifiuta qui, non con un vincolo di colonna

`imponibile_utilizzato` **non ha** un controllo «maggiore o uguale a zero», e non è
una dimenticanza: quella colonna la scrive **questo trigger**, che gira dentro una
scrittura su un'**altra** tabella. Un errore di vincolo lì sarebbe **muto** —
sollevato dentro un trigger, su una tabella diversa da quella che l'operatore stava
toccando.

Qui invece il codice è registrato e la frase nomina il titolo e l'importo.

---

### ⛔ E il **tetto** non si controlla qui, ed è una decisione

Verrebbe naturale rifiutare anche «somma maggiore del plafond». Non si fa:

* sulle **fatture** il caso non si presenta — la spezzatura fa sì che il consumo non
  superi mai la capienza, e a garantirlo è la primitiva, che è anche l'unica a
  prendere il lock;
* sulle **forzature** il superamento è un'informazione sul mondo: una forzatura
  esiste per registrare ciò che il sistema non ha fatturato, e se quelle fatture
  sfondano il plafond è **il plafond registrato a essere sbagliato**. Impedire di
  scrivere il fatto impedirebbe di **accorgersene**.

📌 Il presidio giusto per quel caso non è un rifiuto: è una **lista di titoli sfondati
che qualcuno guarda**. Non esiste ancora, ed è annotato fra i residui del cantiere.

---

### ⚠️ Un limite dichiarato

La colonna resta **scrivibile** a livello di privilegi: in questo progetto un
permesso per singola colonna non tiene, perché il ciclo delle automazioni lo
ri-concede. Il presidio è che ogni corsa del trigger la **riscrive** dalla somma —
un valore messo a mano sopravvive fino al primo movimento e poi sparisce.

È meno di un divieto, ed è quanto si può ottenere qui: la sede del divieto vero è il
backend, che quella colonna non deve mettere in nessuna lista di campi aggiornabili.

---

### Codici errore

| Codice | Motivo |
| --- | --- |
| `E_TITOLO_IVA_UTILIZZATO_NEGATIVO` | la somma del registro scenderebbe sotto zero (`DATO_ERRATO`, 400) |

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D5`.

---

{% include-markdown "signature-core.md" %}
