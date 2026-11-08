## 📘 Documentazione Concettuale – Funzione `script.fn_get_sorgente_emittente_sr_id`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento, che dice in quale tabella cercare
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che risolve il documento dalla sua chiave
> * [vendite.fn_check_commessa_sorgente_emittente_omogeneo](/dbzero/vendite/funzioni/fn_check_commessa_sorgente_emittente_omogeneo) — la regola «una commessa, un emittente», che la usa
> * [vendite.fn_guard_commessa_sorgente_emittente](/dbzero/vendite/funzioni/fn_guard_commessa_sorgente_emittente) — il guard che compone l'errore di quella regola
> * [vendite.trgfn_commesse_sorgenti_guard_emittente](/dbzero/vendite/funzioni/trgfn_commesse_sorgenti_guard_emittente) — il trigger che la fa valere sui documenti di una commessa
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Dato un documento indicato con le colonne della provenienza (il tipo e la chiave del documento,
`sorgente_id` oppure `sorgente_uid`), risponde alla domanda **«chi lo emette?»**, nella convenzione
del soggetto-ruolo dell'emittente.

---

### Il pezzo che serve per confrontare due documenti

Il modello della provenienza sa rispondere a più domande, ognuna col suo pezzo: **esiste?** (il
guard unico), **che documento è?** (il BB che risolve), **in che stato è?** (la vista dello stato
della sorgente). Questa funzione risponde a **chi lo emette**, che serve per dire se due documenti
appartengono allo stesso emittente: una sola definizione, invece della stessa lettura ricopiata in
ogni punto che ne ha bisogno.

Il documento lo risolve `script.fn_sorgente_documento`, con la chiave che riceve: qui si legge solo
l'emittente.

---

### Le tre strade, in ordine di direttezza

1. **La colonna dell'emittente come soggetto-ruolo**: commesse, fatture, lotti. È già la risposta,
   si copia.
2. **L'emittente fiscale del documento**, tradotto in soggetto-ruolo: i documenti di vendita. È la
   strada normale, e quella colonna non è mai vuota.
3. **Il billing account**, da cui si ricava l'emittente: le tabelle di attività, che un emittente
   proprio non ce l'hanno.

La strada la sceglie la tabella del tipo, prima ancora di leggere il documento: una tabella senza
nessuna delle tre colonne è un difetto di catalogo, non di un documento.

---

### ⛔ Il billing account non viene prima dell'emittente

Chiedere l'emittente al cliente del documento sembra la strada generica, e non lo è: su ordini,
preventivi, DDT e resi il billing account **può mancare**, ed è uno stato legittimo, mentre
l'emittente c'è sempre. Un risolutore che passasse dal cliente si fermerebbe su documenti
perfettamente validi.

La regola vale oltre questa funzione: **un controllo che rifiuta una situazione che il modello
ammette non è severo, è rotto.**

---

### Perché è privilegiata

I documenti sono protetti da regole di visibilità per emittente. Se la funzione girasse con i
permessi di chi la chiama, il documento di un altro emittente sarebbe invisibile, e chi la interroga
concluderebbe «non esiste» invece di «è di un altro». Sono due risposte diverse: la prima è un
errore da segnalare, la seconda è esattamente il caso che i controlli a valle devono bloccare.

La funzione vede tutto **per rispondere correttamente**, non per aggirare il perimetro di chi la
chiama: il filtro di visibilità resta di chi la usa.

---

### ⛔ Non risponde mai «non lo so»

Ogni strada che non porta a un risultato certo si ferma con un errore parlante. Un risolutore che
rispondesse vuoto lascerebbe passare il confronto a valle, e trasformerebbe il controllo che lo usa
in un controllo che non controlla niente, in silenzio. Un documento che non esiste e un documento
senza un emittente risolvibile, per chi chiama, sono la stessa cosa: tutti e due sono un errore.

---

### Codici errore

* `E_SORG_CONF` — il tipo manca, è spento o non ha una tabella, oppure la tabella non ha nessuna
  delle tre colonne da cui si ricava l'emittente.
* `E_SORG_KEY_MISSING` — non arriva nessuna delle due chiavi.
* `E_SORG_EMITTENTE_NON_RISOLTO` — il documento non esiste, o non ha un emittente risolvibile.

---

### Test

* `db/pgtap/vendite/test-commessa-sorgente-emittente-omogeneo-v1.sql` — la regola «una commessa, un
  emittente», che si appoggia a questa funzione.
* `db/pgtap/vendite/test-sorgente-commesse-sorgenti-v1.sql` — i documenti di una commessa con le
  colonne del modello.

---

### Note di migrazione

* 2026-10-05 — la chiave, allora in testo, deve essere nella forma canonica: una chiave con
  maiuscole, zeri davanti o spazi riceve `E_SORG_FORMATO`.
* 2026-11-08 — con il cantiere della provenienza documento e riga (`brief-db-sorgente-documento-e-riga`)
  la funzione lavora sulle colonne del modello: tipo, `sorgente_id` e `sorgente_uid`, tipizzate, al
  posto di un'unica chiave in testo che il chiamante doveva scrivere nella forma canonica del tipo.
  Il documento lo risolve il BB che risolve, e la chiave in testo, dove esiste per costruzione, ha
  il suo ponte (`script.fn_sorgente_documento_da_chiave`).

---

{% include-markdown "signature-core.md" %}
