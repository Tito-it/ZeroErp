# Collaudo in-app · nota di credito sui resi

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md); qui
> c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché un documento a parte.** Il brief è il ragionamento e non si spunta;
> questo si spunta, si annota con quello che si trova, e quando è finito diventa
> il verbale di collaudo.
>
> **Stato**: da eseguire. Ambiente: sviluppo (`dbdev`). Preparato il 2026-08-19.

---

## ⚠️ Le cinque cose da sapere prima di cominciare

1. **C'è un punto di non ritorno, ed è dichiarato**: la **prova 6** numera una
   nota di credito. Oltre la numerazione non si torna indietro — nessun verbo,
   nessun reset. Tutto quello che viene prima è annullabile.
2. **I worker girano ogni minuto** (`zeroerp-coda-lavori`, `zeroerp-coda-stampa`):
   un accredito lasciato in giro **verrà** raccolto da un giro di fatturazione.
   Se interrompi il collaudo a metà, **annulla l'accredito** (prova 4) invece di
   lasciarlo lì.
3. **Il verbo oggi lo esercita solo un SUPER_ADMIN.** Misurato: `tid` può perché
   è super admin, e **nessun profilo** ha l'azione `accredita_riga_reso`. Non è
   un difetto del codice — è configurazione dei permessi che non è stata ancora
   fatta. Vedi la **prova 8**.
4. **Il reset del lotto NON annulla l'accredito**: lo rimette in coda e la nota
   di credito **si rigenera** al giro dopo. Per disfare davvero serve «Annulla
   l'accredito» sulla riga del reso.
5. ⛔ **E nemmeno annullare il RESO è una via d'uscita** (rev 2026-08-19): con un
   accredito registrato il DB lo **rifiuta**, e deve farlo — annullare il reso
   non toglierebbe la rettifica già creata. La sola strada indietro resta
   «Annulla l'accredito». ⚠️ Se in collaudo il reso si annulla lo stesso, la
   guardia non è ancora in esercizio: vedi la prova 4.

---

## La materia: cosa c'è in coda adesso

Misurato il 2026-08-19 (contesto operatore — la vista ha la RLS):

| riga di reso | reso        | DDT        | ordine | dovuto | etichetta   | note                                                                   |
| ------------ | ----------- | ---------- | ------ | ------ | ----------- | ---------------------------------------------------------------------- |
| **24**       | RESO0000017 | DDT0000062 | 240    | 1,00   | DOVUTA      | 🔬 **articolo composito**: produce **3 rettifiche**, una per componente |
| **5797**     | RESO0005122 | DDT0010839 | 19151  | 5,00   | DOVUTA      | articolo semplice, 1 rettifica                                         |
| **5799**     | RESO0005123 | DDT0010839 | 19151  | 3,00   | FACOLTATIVA | stessa partita della 5797                                              |

⚠️ **5797 e 5799 condividono la partita**: accreditare la prima può azzerare il
dovuto della seconda. Non è un difetto, è il conto della merce — se dopo un
accredito la 5799 sparisce dalla coda, è corretto.

📌 **Suggerimento d'ordine**: usa la **24** (il kit) per il giro completo — è il
caso che è già costato una correzione al DB — e tieni la **5797** per l'annullo.

---

## Prove

### 1 · Il pannello collega, e non dice più il falso *(F3)*

**Dove**: `Vendite → Ordini`, apri l'ordine **240** (oppure il DDT **140**), guarda
la riga «situazione merce» sotto i collegamenti, apri il dettaglio.

- [X] la nota *«l'emissione della nota di credito non è ancora disponibile»*
      **non c'è più**;
- [X] al suo posto c'è **«… da accreditare»** con il collegamento;
- [X] cliccando: la dialog **si chiude**, si arriva alla coda accrediti, e in
      cima c'è la riga **«Coda filtrata sul DDT #140»** (o sull'ordine) con il
      link per togliere il filtro;
- [X] l'elenco mostra **solo** le righe di quel documento — non tutta la coda;
- [X] tolto il filtro, la coda torna piena.

⚠️ Se la coda si apre **non filtrata**: è il difetto che F3 doveva chiudere
(«un percorso spezzato uguale, solo con un click in più»). Segnalalo.

### 2 · La coda offre il verbo *(F1)*

**Dove**: `Vendite → Resi → tab «Da accreditare»`.

- [X] c'è la **colonna di selezione** (checkbox) a sinistra;
- [X] selezionando una riga, il pulsante in alto diventa **«Accredita (1)»**;
- [X] il kebab di riga ha **«Accredita questa riga»**;
- [X] **nessuna riga è disabilitata** oggi (nessuna porta un `blocco_codice`) —
      se ne trovi una disabilitata, il tooltip deve **dire perché**.

### 3 · La conferma dice la verità *(F1)*

- [X] cliccando «Accredita», la conferma dice che **la nota di credito NON viene
      emessa adesso** e che nasce al prossimo giro di fatturazione;
- [Nessun problema] ⛔ se il testo promette di «emettere una nota di credito», **fermati**: è
      la cosa che il brief voleva evitare — l'operatore andrebbe a cercare un
      documento che non esiste ancora.

### 4 · Accredita e disfa — il giro reversibile *(F1, F2, B2-bis)*

Usa la riga **5797**.

- [X] accredita: toast verde, e la riga **sparisce subito** dalla coda (l'uscita
      è al verbo, non alla fattura);
- [la riga scompare -corretto ] ri-accredita la stessa riga (se riesci a ritrovarla): risponde
      **«accredito già eseguito»**, non un errore generico;
- [X] apri il **reso RESO0005122** (`Vendite → Resi`, oppure «Apri reso» dal
      kebab): nelle righe c'è la colonna **«Già accreditato»** valorizzata, e il
      kebab della riga offre **«Annulla l'accredito»**;
- [X] l'annullo chiede un **motivo obbligatorio** (senza, il pulsante è spento)
      e avvisa che **questo non è il reset del lotto**;
- [X] dopo l'annullo: toast verde, e la riga **torna** nella coda accrediti col
      suo dovuto.

⭐ Se arrivi in fondo a questa prova, il giro reversibile è chiuso: hai provato
verbo, idempotenza, annullo e ritorno in coda **senza produrre nessun documento**.

### 5 · L'esito parziale si legge *(F2)*

Serve un rifiuto vero. Il modo più semplice: seleziona **due** righe di cui una
già accreditata (accredita la 5797, poi selezionala di nuovo insieme alla 24).

- [X] il toast è **arancione**, non rosso, e dice «X su Y»;
- [X] si apre l'elenco delle righe **non servite**, con **codice** e **motivo**
      per ciascuna;
- [X] le righe passate **sono passate** (non è stato annullato tutto).

### 6 · 🔴 IL GIRO VERO — da qui non si torna indietro

> Questa prova chiude l'unica voce della definizione di «fatto» che il codice non
> può chiudere: `vendite.fatture_rettifiche` **è ancora a zero righe** in
> esercizio.

Usa la riga **24** (il kit).

- [X] accredita la riga 24 → spariscono **3 rettifiche** dietro le quinte (una
      per componente);
- [X] lancia il giro di fatturazione dal cockpit (`Vendite → Fatturazione`),
      oppure aspetta il giro automatico;
- [X] **prima di numerare**, apri il lotto: nel tab **«Documenti»** (non più
      «Fatture») c'è un documento con natura **«Nota di credito»**;
- [X] ⚠️ **il documento della nota di credito è SEPARATO** da quello della
      fattura che rettifica: se le righe di rettifica sono finite dentro una
      fattura ordinaria, **fermati e segnala**;
- [X] «Rendi definitive» → il documento prende un **numero sul sezionale NC**X
      (serie vuota), **non** sul progressivo delle fatture;
- [X ] apri la nota di credito: in testata il Tag **«Nota di credito»**, la riga
      **«Rettifica: …»** con il documento collegato, e sulle righe la colonna
      **«Rettifica riga»** con numero e riga della gemella;
- [X] apri la **fattura rettificata**: in testata dice **«Rettificata da …»** con
      il numero della nota.

### 7 · Dopo il documento: le due strade restano distinte

- [ ] sulla riga del reso ora accreditata **e già emessa**, «Annulla l'accredito»
      risponde che **non è più ammesso**, e il messaggio dice **quale strada
      prendere**;
- [ ] nel drawer del lotto, la conferma di **«Elimina dal lotto»** / «Riporta a
      bozza» / «Annulla lotto» avvisa che **un accredito già registrato NON
      viene annullato** e che la nota **si rigenera** al giro successivo;
- [ ] *(se la riga era anche rinunciata)* riaprire la rinuncia è **rifiutato**,
      con il messaggio sull'accredito già eseguito;
- [ ] e **annullare il reso** è rifiutato a sua volta, con il messaggio
      sull'accredito registrato: qui la strada indietro non c'è più da nessuna
      parte, ed è corretto che i tre verbi lo dicano tutti e tre.

### 8 · Il permesso *(P-1, B2)*

- [X] con un utente **non** super admin (es. `terenzi`): nella coda accrediti il
      pulsante «Accredita» **non compare** e il kebab non offre il verbo;
- [X] 📌 e questo è oggi lo stato **di tutti** i non-admin: l'azione
      `accredita_riga_reso` non è assegnata a nessun profilo. Se il verbo deve
      essere usato da qualcuno che non è super admin, **va concessa** —
      `Amministrazione → profili`.

---

## Cosa NON è coperto da questo collaudo

* **la stampa PDF della nota di credito** e il blocco `DatiFattureCollegate`
  della fattura elettronica: il legame documentale c'è (prova 6), il render
  della TD04 è un altro cantiere;
* **il secondo emittente**: i registri sono intestati (P-6), ma qui si prova con
  l'emittente di default;
* **un terzo emittente**: oggi prenderebbe `E_CONFIG_MANCANTE` alla prima
  fattura — è la decisione aperta del §32.3 del brief.

## Se qualcosa va storto

| Sintomo                                     | Cosa guardare                                                                      |
| ------------------------------------------- | ---------------------------------------------------------------------------------- |
| il verbo risponde 403                       | l'azione non è concessa al profilo (prova 8)                                       |
| la riga resta in coda dopo l'accredito      | il verbo non ha scritto: guarda il toast, poi `vendite.resi_righe_accrediti`       |
| la NC non nasce al giro                     | le rettifiche sono ancora `NON_EMESSA`? il lotto ha incluso quella commessa?       |
| la NC nasce **dentro** la fattura           | 🔴 grave: la chiave documento non sta separando la natura. Fermati                  |
| il numero è sul progressivo fatture         | 🔴 grave: registro sbagliato. Fermati                                               |
| «operazione non consentita» sull'annullo    | è già emessa: è corretto. Il messaggio deve dire il perché                         |
| il **reso** si annulla anche se accreditato | 🔴 grave: la guardia del §38 non è in esercizio. Fermati: la NC uscirebbe lo stesso |

⛔ **Sui due «grave»: non ritentare.** Sono i due casi in cui un secondo giro
produce un secondo documento sbagliato.
