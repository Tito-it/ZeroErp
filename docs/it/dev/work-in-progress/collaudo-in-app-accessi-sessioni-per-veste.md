# Collaudo in-app · Accessi: la veste spenta chiude solo le sue sessioni

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief: il *perché* di ogni scelta sta in
> [brief-be-accessi-credenziale-e-vesti.md](../work-done/2026/brief-be-accessi-credenziale-e-vesti.md)
> (§2 il collaudo di D-5, §1 la revoca D-4 e A-6), nel
> [piano accessi](../work-done/2026/piano-be-fe-accessi-credenziale-e-vesti.md) §4.3-bis e, per la regola
> della revoca a DB, nel [brief DB accessi](brief-db-accessi-area-clienti.md) §2 e §5.3. Qui c'è solo **cosa
> fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** Il codice è chiuso su tutti i lati: le sessioni per veste dal 2026-10-02, la revoca
> dell'amministratore dal 2026-11-26, il verbo che segna l'invito spedito dal 2026-11-27. I test sul DB vero
> provano i verbi uno per uno, ma **nessun test tiene aperte due porte insieme**: che «Disabilita» butti fuori
> dall'amministrazione **e non** dallo shop si vede solo con due browser accesi sulla stessa persona. È la
> differenza fra «la sessione della veste» e «la sessione della credenziale», e un errore lì non dà nessun
> errore: chiude troppo o troppo poco.
>
> **Stato**: ✏️ scritto il 2026-11-27, **da eseguire**.
> **Ambiente**: sviluppo (`dbdev`). **Utenti**: un **amministratore** che può disabilitare operatori e
> invitare (il SUPER_ADMIN va bene: qui non si prova il perimetro di chi agisce, ma l'effetto su chi subisce),
> e le **persone di prova** del §0, costruite da schermata.
> **Dove**: Amministrazione → *Operatori* (drawer dell'operatore), area *Accessi* (scheda «Altri accessi»),
> la porta dello **shop**, il **giornale email**.

---

## ⛔ Tre cose da sapere PRIMA di cominciare

|              | Cosa | Perché conta |
| ------------ | ---- | ------------ |
| **Tempo**    | Il token d'accesso dura **10 minuti** (`ACCESS_TOKEN_LIFETIME` in `zeroerp_backend/settings.py`). La sessione spenta si accorge al **primo rinnovo** | Subito dopo «Disabilita» la scheda aperta funziona ancora: **non è un difetto**. Si aspetta fino a 10 minuti, poi si fa un'azione qualunque (apri una lista) |
| **Browser**  | Una porta per browser: due browser diversi, o uno normale e uno in incognito | Due porte nello stesso browser condividono lo storage, e il caso a non si vede |
| **Mail**     | In sviluppo la mail non parte: è stampata, e il giornale email la segna `SIMULATA`. Il **link** dell'invito si copia da lì | Per il caso b serve il link di un invito **non usato** |

⚠️ **Dal 2026-11-26 spegnere è revocare.** «Disabilita» e l'interruttore «Accesso attivo» lasciano sulla
veste il segno della revoca: la veste **non si riaccende** da nessuna strada, se non dal **nuovo invito**
dell'amministratore. Il caso c del brief («riaccendere la veste») si fa quindi con **«Reinvia invito»**.

---

## 0. Le persone di prova

|         | Cosa fare | Cosa deve succedere | Se non succede |
| ------- | --------- | ------------------- | -------------- |
| **0.1** | Scegli (o crea) un **operatore attivo** con un'email sua, e accertati di conoscerne la password | Entra nell'amministrazione | — |
| **0.2** | Invita allo **shop**, con **la stessa email**, un cliente qualunque (pannello accesso del cliente) | ⭐ L'invito parte col testo «entra con le credenziali che usi già»: la credenziale ha già una password, l'attivazione è **un clic** | Se chiede di scegliere una password, l'invito ha creato una credenziale nuova: le due vesti non sono della stessa persona e il caso a non prova niente. Si ferma e si segnala |
| **0.3** | Apri il link dal giornale email e attiva | La veste shop è accesa. In *Accessi → Altri accessi* la credenziale mostra la veste shop **Attivo** | — |
| **0.4** | Prepara una **seconda** persona costruita allo stesso modo (serve al caso a-bis) | Come 0.1 – 0.3 | — |
| **0.5** | Invita un **operatore nuovo** e **non** attivarlo; copia il link dal giornale | In lista l'operatore è «Invito inviato» | ⚠️ Se resta «Invito non spedito» con la mail partita, il verbo `fn_segna_invito_inviato` non ha scritto la data (§3.2) |

---

## 1. Caso a — «Disabilita» chiude l'amministrazione, non lo shop

|           | Cosa fare | Cosa deve succedere | Se non succede |
| --------- | --------- | ------------------- | -------------- |
| **1.1**   | Browser 1: entra nell'**amministrazione** con la persona del §0.1. Browser 2: entra nello **shop** con la stessa persona | Due sessioni aperte, una per porta | — |
| **1.2**   | Da un terzo accesso come amministratore: *Operatori* → drawer della persona → **«Disabilita operatore»** → conferma | Il messaggio dice che l'accesso è revocato subito, le sessioni si chiudono e il rapporto si chiude con la data di oggi | — |
| **1.3**   | Aspetta il rinnovo (fino a 10 minuti), poi fai un'azione nel **browser 1** | ⭐ Esce dall'amministrazione: il rinnovo risponde 401 e si torna al login | Se resta dentro dopo il rinnovo, la sessione della veste non è chiusa: difetto di **modello**, si ferma e si segnala |
| **1.4**   | Fai un'azione nel **browser 2** (anche dopo i 10 minuti) | ⛔ **Resta nello shop** e lavora | Se esce anche da qui, lo spegnimento ha chiuso le sessioni della **credenziale** invece di quelle della veste: difetto di **modello** |
| **1.5**   | *Accessi → Altri accessi*, la credenziale | La veste operatore non compare qui (è nella lista operatori); la veste shop è ancora **Attivo** | — |
| **1.a-bis** | Rifai 1.1 – 1.4 con la persona del §0.4, ma invece di «Disabilita» **spegni l'interruttore «Accesso attivo»** nel drawer e salva | Lo stesso esito: fuori dall'amministrazione, dentro lo shop | Interruttore e «Disabilita» passano dalla stessa revoca: se divergono, una delle due strade non è sul verbo |

---

## 2. Caso b — «Disabilita» fa scadere l'invito pendente

|         | Cosa fare | Cosa deve succedere | Se non succede |
| ------- | --------- | ------------------- | -------------- |
| **2.1** | Sull'operatore del §0.5 (invito pendente, mai attivato): **«Disabilita operatore»** | Confermato | — |
| **2.2** | Apri il link copiato al §0.5 | ⭐ «Token non valido»: l'invito della veste è chiuso insieme alla veste | Se il link attiva la veste, la revoca non ha chiuso gli inviti pendenti: difetto di **modello**. ⚠️ Se l'attivazione si ferma con «veste revocata» invece che sul token, il guard del DB tiene ma l'invito è rimasto vivo: difetto di **resa** del BE, si segnala |

---

## 3. Caso c — dopo la riaccensione si rientra col login

|         | Cosa fare | Cosa deve succedere | Se non succede |
| ------- | --------- | ------------------- | -------------- |
| **3.1** | Riprendi la persona del caso a; **lascia aperta** nel browser 1 la scheda di prima | — | — |
| **3.2** | Dal drawer: **«Reinvia invito»** | ⭐ Partito l'invito, lo stato della veste è **«Invito inviato»**, non «Invito non spedito»: la data l'ha scritta il verbo `fn_segna_invito_inviato` (dal 2026-11-27) | Se l'invito parte ma la chiamata finisce in errore, il verbo ha rifiutato dopo la mail: si annota il messaggio e si segnala (il rifiuto **non** si ingoia per scelta, brief DB §5.3.10) |
| **3.3** | Apri il link dal giornale email e attiva | Un clic (la credenziale ha già la password): la veste è accesa e il segno della revoca è tolto | Se l'attivazione si ferma con «veste revocata», il nuovo invito non ha tolto il segno |
| **3.4** | Torna sulla **vecchia scheda** del browser 1 | ⛔ **Non torna dentro da sola**: chiede il login | Se la vecchia sessione si riapre, riaccendere la veste ha riaperto i token chiusi: difetto di **modello** |
| **3.5** | Fai il login | Si entra nell'amministrazione | — |

---

## 4. Il filtro «Revocato» (giro 3c, 2026-11-27)

|         | Cosa fare | Cosa deve succedere | Se non succede |
| ------- | --------- | ------------------- | -------------- |
| **4.1** | *Accessi → Altri accessi* → filtro **Stato** | Fra le voci c'è **Revocato**, dopo «Disattivato» e prima di «Non invitato» | Se manca, il FE è indietro rispetto a `STATI_ACCESSO` del BE |
| **4.2** | Dal pannello accesso di un cliente shop: **«Disattiva accesso shop»**. Poi filtra per **Revocato** | La credenziale compare, **se è l'unica veste** che aveva | — |
| **4.3** | Una credenziale con una veste revocata **e** una spenta senza revoca (per esempio spenta da un invito mai attivato) | ⭐ Risulta **Disattivato**, non Revocato: è revocata solo quando lo sono **tutte** le vesti (D-3c-2) | Se risulta Revocato, l'aggregato della vista non segue la regola: si segnala al DB |

---

## 5. Registro

| Data | Cosa |
| ---- | ---- |
| **2026-11-27** | Stesura, all'archiviazione del [brief BE accessi](../work-done/2026/brief-be-accessi-credenziale-e-vesti.md): il collaudo a video di D-5 (§2 del brief) è l'unica cosa che ne resta, e vive qui. Il caso c è riscritto sulla revoca (dal 2026-11-26 si riaccende solo col nuovo invito). §4 nuovo, dal giro 3c. Da eseguire (Tid) |
