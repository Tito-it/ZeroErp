## 📘 Documentazione Concettuale – Tabella `magazzino.movimenti_attesi`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, di cui questa è la forma «al futuro»
> * [magazzino.causali](/dbzero/magazzino/tabelle/causali) — il verso
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo delle sorgenti
>
> Approfondimento viste:
>
> * [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — la disponibilità, con i blocchi
>
> Approfondimento funzioni:
>
> * [magazzino.fn_apri_blocco](/dbzero/magazzino/funzioni/fn_apri_blocco) — apre un blocco manuale
> * [magazzino.fn_libera_blocco](/dbzero/magazzino/funzioni/fn_libera_blocco) — lo libera
> * [script.fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita) — il controllo che i blocchi fermano

---

### 🎯 Scopo Principale

**I movimenti che devono ancora accadere e che nessun documento sa dire.** Quanto è impegnato
da un ordine di vendita o in arrivo da un ordine al fornitore lo dicono le righe di quei
documenti: non si ricopia qui. Qui stanno le due cose che un documento non contiene:

* il **blocco manuale** — «tienimene dieci per il cliente Rossi», senza un ordine dietro;
* la **merce prelevata non ancora uscita** — presa dallo scaffale, in attesa della bolla.

La tabella ha la stessa forma del registro: quantità **firmata** (negativa per ciò che
uscirà, positiva per ciò che entrerà), causale che dice il verso, sorgente a catalogo — ma
qui la sorgente è **facoltativa**, perché il blocco manuale non ha documento. Allora per chi
è lo dice il **soggetto** (`soggetto_ruolo_id`) o la **nota**: un'attesa senza sorgente,
senza soggetto e senza nota è una riga muta, e il database la rifiuta
(`chk_mag_movimenti_attesi_per_chi`; una nota di soli spazi non vale).

---

### Il ciclo di vita è una domanda sola

`stato` vale `APERTA` o `CHIUSA`, con `data_chiusura` obbligatoria se e solo se `CHIUSA`.
La *natura* dell'attesa la dicono già la causale (verso) e la sorgente (c'è un documento o
no); allo stato resta «conta ancora?». Liberare un blocco vuol dire portarlo a `CHIUSA`, con
la data. Non c'è `attivo`: sarebbe il secondo modo di dire «non conta».

`data_prevista` è ammessa **solo senza documento**: dove c'è un documento, la data è la sua.

---

### Un blocco si apre e si libera con un atto

Un blocco manuale è una **promessa**, non un fatto sulla merce: ferma gli scarichi degli
altri finché qualcuno non lo libera. Per questo lo apre e lo libera **una persona**, con
due operazioni che chiedono il permesso *Blocca merce* (`blocca_merce`):

* [magazzino.fn_apri_blocco](/dbzero/magazzino/funzioni/fn_apri_blocco) — quanta merce, di
  quale articolo, per chi o perché; la posizione (lotto, seriale, ubicazione) la giudica la
  stessa regola dei movimenti. Chi lo ha aperto resta scritto;
* [magazzino.fn_libera_blocco](/dbzero/magazzino/funzioni/fn_libera_blocco) — porta il
  blocco a `CHIUSA` e scrive chi, quando e perché. Un blocco già liberato non si libera
  due volte, e un blocco non si cancella mai.

Non si riusa il permesso delle registrazioni di magazzino: chi può contare la merce non è
per forza chi può riservarla a un cliente.

---

### I blocchi entrano nella disponibilità

I blocchi aperti **in uscita** contano nella disponibilità —
[vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) li somma tutti,
[fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita)
esclude quelli della stessa sorgente di chi chiede. Un atteso in entrata è merce in arrivo,
non un blocco. L'indice che serve alla disponibilità è **parziale** sulle attese `APERTA`,
per articolo e magazzino.

---

### Lotto e seriale

`lotto_id` e `asset_id` come sul registro: l'atteso eredita gli obblighi dell'articolo, e con
un asset la quantità è uno.

---

### Chi può vedere e scrivere

`magazzino_id` è obbligatorio: è l'ancora del perimetro. Un operatore **vede** le attese dei
magazzini del **proprio emittente** (policy `rls_movimenti_attesi_ef_whitelist`, via
magazzino). Meccanismo comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

⭐ L'applicazione le **legge soltanto**: non può inserirle, cambiarle né cancellarle
direttamente. Si scrivono solo con le due operazioni del blocco, che controllano il permesso
e il perimetro. È il modello «una scrittura = un'operazione» del database: un blocco si
chiude, non si cancella.

---

### Codici errore

* `E_MAG_BLOCCO_NON_TROVATO` — il blocco da liberare non esiste, è fuori perimetro o non è un
  blocco manuale;
* `E_MAG_BLOCCO_GIA_CHIUSO` — il blocco è già stato liberato;
* `E_MAG_MOVIMENTO_VERSO_INCOERENTE` — la quantità non ha il segno della causale.

---

### Test

* `db/pgtap/magazzino/test-movimenti-attesi-forma-v1.sql` — i vincoli e i guard della
  tabella, provati con scritture dirette dal proprietario;
* `db/pgtap/magazzino/test-blocco-manuale-e-porta-lotto3-v1.sql` — apertura e liberazione del
  blocco, e la postura: che cosa l'app può e non può eseguire.

---

### Note di migrazione

* 2026-09-15 — la tabella si chiamava `reservations` ed è stata **rinominata**, non rifatta,
  con tutto ciò che portava il suo nome: chiave, sequenza, vincoli, indici, trigger
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.5; analisi carico e scarico, §7-bis). Escono
  il riferimento libero `doc_*`, il ciclo a quattro stati (`planned`, `picked`, `fulfilled`,
  `cancelled`) e `attivo`; entrano la sorgente a catalogo, la causale, il soggetto e la nota,
  lotto e asset.
* 2026-09-18 — i blocchi in uscita entrano nella disponibilità e l'app perde la
  cancellazione (Lotto 2).
* 2026-09-28 — i due verbi del blocco, e l'app passa a sola lettura
  (`brief-db-magazzino-lotto-3-scarico-da-ddt`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
