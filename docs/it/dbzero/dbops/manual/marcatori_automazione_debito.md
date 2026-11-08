## 📘 Documentazione Concettuale – Tabella `dbops.marcatori_automazione_debito`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove questo registro è dichiarato
>
> Approfondimento viste:
>
> * [dbops.vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore) — il presidio che questo registro fa tacere, riga per riga
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — la forma comune di misura e registro

---

### 🎯 Scopo Principale

L'elenco delle tabelle che hanno una colonna che **promette un'automazione** (`tx_id`, `storicizza`,
`cleanup_at`) senza che nessuno la esegua, ognuna con scritto accanto **perché**. È il registro del
presidio `dbops.vw_marcatori_automazione_senza_esecutore`: una riga lo fa tacere su quella tabella e
per quel marcatore soltanto.

Non è una lista di eccezioni concesse: è un elenco di lavori con un nome. Una riga dice «sappiamo che
questa colonna non la scrive nessuno, sappiamo come si chiude». Non dice «va bene così».

---

### ⚠️ È un debito, quindi deve calare

Ogni riga ha una data (`data_registrazione`), e una riga ferma da mesi è un'informazione.

⛔ Quando un lavoro è finito, **la riga va tolta**, dal CSV e con un changeSet di cancellazione: il
caricamento del seed aggiunge e aggiorna, non cancella. Una riga rimasta continuerebbe a far tacere il
presidio; lui se ne accorge da solo, e la riga diventa `DEBITO_ESTINTO`.

Un debito si chiude in tre modi, e la scelta è per tabella:

* la tabella **entra nell'ambito** delle automazioni, con una riga in `dbops.automation_scope`;
* il trigger si **monta a mano**, come su `dbops.processi` e `dbops.coda_lavori` (non vale per
  `cleanup_at`: il purge è solo del runner);
* la colonna **si toglie**, come su `dbops.audit_sources`.

---

### I tre marcatori

| `marcatore` | Che cosa resta senza esecutore |
| --- | --- |
| `TX_ID` | la colonna `tx_id`, senza il trigger di `dbops.trgfn_tx_id_managed` |
| `STORICIZZA` | la colonna `storicizza`, senza il trigger dello storico |
| `CLEANUP_AT` | la colonna `cleanup_at`, su una tabella che il purge non vede |

Il vocabolario è chiuso da un vincolo, ed è da quel vincolo che il test legge i marcatori ammessi: un
marcatore nuovo senza il suo ramo nella vista fa rosso. Il marcatore entra nella chiave: una tabella
può avere due marcatori scoperti, e allora sono due righe e due lavori.

---

### ⛔ La ragione si legge, non si timbra

`ragione` dice perché la colonna resta senza esecutore e che cosa servirebbe per chiudere il debito.
Il vincolo ne misura solo la **lunghezza** minima, quaranta caratteri: ferma «da fare», non una frase
vuota abbastanza lunga. La qualità la giudica una persona.

---

### Si alimenta dal seed

Le righe stanno nel CSV `80_data/sql/dbops/marcatori_automazione_debito.csv`, con gli id scritti a
mano e la data nel CSV: è un seed di catalogo, che nomina tabelle del software e vale identico su ogni
installazione. Nessuno lo scrive a runtime.

Per questo il registro non porta `tx_id`, `data_update` e `user_update`: lo scrive solo la
migrazione, e quelle colonne direbbero sempre «il migratore» (regola in `automazione-db.md` §1.1).
Un registro che presidia le promesse senza esecutore non promette niente lui stesso.

Oggi è **vuoto**: è la sede in cui una tabella nuova con un marcatore senza esecutore entra, con la
sua ragione, finché non si decide come chiuderla.

---

### Test

* `db/pgtap/dbops/test-marcatori-automazione-senza-esecutore-v1.sql` — il registro rende una riga
  dichiarata o estinta, rifiuta una ragione corta e un marcatore fuori vocabolario, e il suo
  vocabolario è quello che la vista riconosce.

---

### Note di migrazione

* 2026-11-07 — nasce con il presidio. Il contenuto iniziale sono dieci cataloghi e registri di `dbops`
  con `tx_id` e senza il trigger: `dbops` espone alle automazioni solo i suoi registri, e su queste
  tabelle nessuno aveva montato i trigger a mano.
* 2026-11-08 — le dieci righe escono: le tabelle hanno perso `tx_id`, perché le scrive solo la
  migrazione (la colonna tolta, non i trigger montati). Il registro stesso perde `tx_id`,
  `data_update`, `user_update` e i due trigger. Il CSV resta col solo header.

---

{% include-markdown "signature-core.md" %}
