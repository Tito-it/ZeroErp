## 📘 Documentazione Concettuale – Tabella `config.nature_vendita`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
>
Approfondimento funzioni:
> • [vendite.trgfn_preventivi_righe_set_natura_vendita](/dbzero/vendite/funzioni/trgfn_preventivi_righe_set_natura_vendita)

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

La natura vive su `catalogo.articoli.natura_vendita_id` ed è **ereditata e congelata** sulla
riga di preventivo da `trgfn_preventivi_righe_set_natura_vendita`. L'operatore non la sceglie:
la sceglie chi classifica l'articolo.

La ragione è che lo smistamento post-accettazione dev'essere **deterministico**. Se la natura
fosse decidibile riga per riga, lo stesso articolo potrebbe finire in un ordine o in un
contratto a seconda di chi compila il preventivo.

Dal 2026-08-21 il congelamento è presidiato anche da un lock di colonna
(`E_PREV_RIGA_NATURA_IMMUTABILE`): prima la dichiarazione «no override operatore» viveva solo
nel commento della funzione.

---

### ⚠️ `destinazione_tipo` è la colonna portante — e il guard la legge

`trgfn_preventivi_righe_set_natura_vendita` blocca le righe la cui natura ha
`destinazione_tipo = 'CONTRATTO'`: la ricorrenza non può stare su un preventivo, va
sull'**offerta commerciale**.

⭐ Il controllo è **data-driven**: guarda `destinazione_tipo`, non il codice della natura.
Aggiungere una natura nuova mappata a `CONTRATTO` la fa bloccare da sé, senza toccare il
trigger.

⚠️ Il rovescio: **cambiare il `destinazione_tipo` di una natura esistente cambia il
comportamento del guard per tutte le righe future**, e non c'è nulla che lo segnali. È una
colonna di configurazione con effetti di codice.

---

### Struttura

`codice_interno` / `codice` (doppia chiave), `descrizione`, `destinazione_tipo` (`NOT NULL`),
`attivo`, `ordine`, `meta`.

`destinazione_tipo` è una stringa vincolata da CHECK, non una FK a un vocabolario di
destinazioni: le tre destinazioni sono strutturali del ciclo di vendita, non configurabili.

---

{% include-markdown "signature-core.md" %}
