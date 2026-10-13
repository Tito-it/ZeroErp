## 📘 Documentazione Concettuale – Tabella `config.nature_vendita`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
>
Approfondimento funzioni:
> • [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — le regole sulle righe, che leggono la destinazione

---
### 🎯 Scopo Principale

(rev 2026-08-21)

La **natura commerciale** di una riga, e con essa la sua destinazione operativa dopo
l'accettazione del preventivo. Tre voci, e ciascuna manda la riga da un'altra parte:

| Natura | `destinazione_tipo` | Dove finisce la riga |
|---|---|---|
| `MERCE` | `ORDINE` | ciclo ordini → DDT |
| `SERVIZIO_UNA_TANTUM` | `COMMESSA` | commessa diretta |
| `SERVIZIO_RICORRENTE` | `CONTRATTO` | contratto a canone |

---

### ⭐ È una proprietà dell'**articolo**, non della riga

La natura vive su `catalogo.articoli.natura_vendita_id` ed è **ereditata e congelata** sulle
righe di preventivo, ordine e bolla da [`script.trgfn_righe_natura_vendita`](/dbzero/script/manual/trgfn_righe_natura_vendita) (dal 2026-10-13; prima, sul solo preventivo,
da `trgfn_preventivi_righe_set_natura_vendita`, ritirato lo stesso giorno). La riga porta la natura **con cui è stata
venduta**: l'ordine quella del preventivo, la bolla quella dell'ordine, la riconsegna quella
della bolla resa. Un cambio di natura dell'articolo in anagrafica non tocca le righe già
scritte. L'operatore non la sceglie: la sceglie chi classifica l'articolo.

La ragione è che lo smistamento post-accettazione dev'essere **deterministico**. Se la natura
fosse decidibile riga per riga, lo stesso articolo potrebbe finire in un ordine o in un
contratto a seconda di chi compila il preventivo.

Dal 2026-08-21 il congelamento è presidiato anche da un lock di colonna: prima la
dichiarazione «no override operatore» viveva solo nel commento della funzione. Dal 2026-10-13
il codice è `E_RIGA_NATURA_VENDITA_IMMUTABILE`, lo stesso sulle tre tabelle (fino a quel giorno
`E_PREV_RIGA_NATURA_IMMUTABILE`, ora ritirato).

---

### ⚠️ `destinazione_tipo` è la colonna portante — e il guard la legge

[`script.fn_check_articolo_riga`](/dbzero/script/manual/fn_check_articolo_riga) legge la
destinazione della natura della riga: sul preventivo blocca `destinazione_tipo = 'CONTRATTO'`
(la ricorrenza va sull'**offerta commerciale**), su ordine e bolla ammette solo `ORDINE` (la
merce). Fino al 2026-10-13 il blocco del preventivo stava in
`trgfn_preventivi_righe_set_natura_vendita`, ritirato nella check.

⭐ Il controllo è **data-driven**: guarda `destinazione_tipo`, non il codice della natura.
Aggiungere una natura nuova mappata a `CONTRATTO` la fa bloccare da sé, senza toccare il
trigger.

⚠️ Il rovescio: **cambiare il `destinazione_tipo` di una natura esistente cambia il
comportamento del guard per tutte le righe future**, e non c'è nulla che lo segnali. È una
colonna di configurazione con effetti di codice.

---

### ⭐ `e_cessione_beni` — beni o servizi, e **non** si deduce da `destinazione_tipo`

Dal 2026-08-29 la tabella porta **`e_cessione_beni`**: `true` = cessione di beni,
`false` = prestazione di servizi.

Serve perché in ambito **intracomunitario** è questa distinzione a determinare il
**luogo di imposizione** — beni e servizi non seguono la stessa regola — ed è un
pezzo della firma del risolutore IVA.

> ⛔ **Non poteva stare su `config.iva` o `config.iva_natura`, e non per mancanza
> di spazio: sarebbe circolare.** Beni-vs-servizi serve a *scegliere* il codice
> natura (`N3.1` esportazioni è merce, `N7` è prestazione di servizi): ricavarlo
> da lì significherebbe ricavare l'**input** del risolutore dal suo **output**.

> ⚠️ **E NON si deduce da `destinazione_tipo`**, che pure sembra dire la stessa
> cosa (`MERCE → ORDINE`, i due servizi → `COMMESSA`/`CONTRATTO`). Quella colonna
> risponde a **un'altra domanda**: dove finisce la riga dopo l'accettazione del
> preventivo. Appoggiarci sopra il luogo di imposizione è la forma esatta del
> **flag composto** — un campo che risponde a due domande in AND — e il giorno che
> le due risposte divergono non c'è modo di separarle.

⚠️ È `NOT NULL` **senza default**: chi conia una natura nuova deve **dire** quale
delle due è, perché nessuna delle due risposte è quella conservativa.

---

### Struttura

`codice_interno` / `codice` (doppia chiave), `descrizione`, `destinazione_tipo` (`NOT NULL`),
`e_cessione_beni` (`NOT NULL`), `attivo`, `ordine`, `meta`.

`destinazione_tipo` è una stringa vincolata da CHECK, non una FK a un vocabolario di
destinazioni: le tre destinazioni sono strutturali del ciclo di vendita, non configurabili.

---

{% include-markdown "signature-core.md" %}
