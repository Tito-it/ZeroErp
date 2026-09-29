## 📘 Documentazione Concettuale – Tabella `magazzino.movimenti_attesi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro, di cui questa è la forma «al futuro»
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali) — il verso
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.5) · analisi carico e scarico (§7-bis)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino; si chiamava `reservations`)

**I movimenti che devono ancora accadere e che nessun documento sa dire.** Quanto è impegnato
da un ordine di vendita o in arrivo da un ordine al fornitore lo dicono le righe di quei
documenti: non si ricopia qui. Qui stanno le due cose che un documento non contiene:

* il **blocco manuale** — «tienimene dieci per il cliente Rossi», senza un ordine dietro;
* la **merce prelevata non ancora uscita** — presa dallo scaffale, in attesa della bolla.

La tabella ha la stessa forma del registro: quantità **firmata** (negativa per ciò che
uscirà, positiva per ciò che entrerà), causale che dice il verso, sorgente a catalogo — ma
qui la sorgente è **facoltativa**, perché il blocco manuale non ha documento. Allora per chi
è lo dice il **soggetto** (`soggetto_ruolo_id`) o la **nota**: un'attesa senza sorgente,
senza soggetto e senza nota è una riga muta, e il database la rifiuta (`per_chi`; una nota di
soli spazi non vale).

---

### Il ciclo di vita è una domanda sola

`stato` vale `APERTA` o `CHIUSA`, con `data_chiusura` obbligatoria se e solo se `CHIUSA`.
Il vecchio ciclo a quattro stati (`planned`, `picked`, `fulfilled`, `cancelled`) è uscito:
la *natura* dell'attesa la dicono già la causale (verso) e la sorgente (c'è un documento o
no); allo stato resta «conta ancora?». Liberare un blocco = `CHIUSA`, con la data. Non c'è
`attivo`: sarebbe il secondo modo di dire «non conta».

### Un blocco si apre e si libera con un atto (dal 28-09, Lotto 3)

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

`data_prevista` è ammessa **solo senza documento**: dove c'è un documento, la data è la sua.

---

### Lotto e seriale

`lotto_id` e `asset_id` come sul registro: l'atteso eredita gli obblighi dell'articolo, e con
un asset la quantità è uno.

---

### Chi può vedere e scrivere

`magazzino_id` è obbligatorio: è l'ancora del perimetro. Un operatore **vede** le attese dei
magazzini del **proprio emittente** (policy `rls_movimenti_attesi_ef_whitelist`, via
magazzino). Meccanismo comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

⭐ Dal 28-09 (Lotto 3) l'applicazione le **legge soltanto**: non può inserirle, cambiarle né
cancellarle direttamente. Si scrivono solo con le due operazioni del blocco qui sopra, che
controllano il permesso e il perimetro. È il modello «una scrittura = un'operazione» del
database.

---

### Che cosa è cambiato con la rinomina (2026-09-15)

La tabella `reservations` è stata **rinominata**, non rifatta, con tutto ciò che portava il
suo nome: chiave, sequenza, vincoli, indici, trigger. Via il riferimento libero `doc_*`, lo
stato a quattro valori, `attivo`; dentro la sorgente a catalogo, la causale, il soggetto e la
nota, lotto e asset. Dal 18-09 (Lotto 2) i blocchi aperti **in uscita** (`qta < 0`) entrano nella
disponibilità — [vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) e
[fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita), che esclude
i blocchi della stessa sorgente di chi chiede; un atteso in entrata non è un blocco — e l'app **non
può cancellarli** (`REVOKE DELETE`): un blocco si chiude, non si cancella. L'indice che serve alla
disponibilità è **parziale** sulle
`APERTA`, per articolo e magazzino. Presidio:
`db/pgtap/magazzino/test-movimenti-attesi-forma-v1.sql`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
