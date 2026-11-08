## 📘 Documentazione Concettuale – Funzione `dbops.fn_conta_presidio_per_variante`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo: perimetro, stato atteso e colonna della causa
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — le cause, e a chi tocca ciascuna
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio intero, che è la somma di questo
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — il meccanismo dei presidi

---

### 🎯 Scopo Principale

Conta le righe che chiedono un intervento su una vista di presidio dichiarata in `dbops.presidi`,
raggruppate per causa. È la sede unica del conteggio dei presidi: perimetro, rifiuto e filtro di
stato stanno qui, e `dbops.fn_conta_presidio` ne è la somma.

Alcuni presidi raccolgono guasti diversi nella stessa vista: un timer fermo, un servizio
scollegato, un lavoro del database mai partito. Il catalogo dice da quale colonna della vista si
legge la causa (`colonna_variante`), e questa funzione conta le righe di ciascuna.

---

### Perché un conteggio per causa

Il pannello e il digest mostrano un **campione** delle righe, non tutte. Contare le cause sul
campione darebbe numeri sbagliati appena le righe sono più del campione, e una causa che tocca
allo sviluppo, finita oltre il campione, non arriverebbe mai a chi deve intervenire. Il conteggio
lo fa quindi il database, sulla vista intera.

---

### Che cosa restituisce

* per un presidio con la colonna della causa, una riga per ciascuna causa **presente**: le cause
  senza righe non compaiono, e le righe senza causa formano un gruppo a sé, vuoto, che non sparisce
  e non si confonde con un'altra causa;
* per un presidio **senza** colonna della causa, una riga sola con la causa vuota e il totale,
  **anche a zero**: chi legge ha un modo solo di chiedere, per qualunque presidio.

Le righe che contano sono tutta la vista oppure, se il catalogo dichiara uno stato atteso, quelle
con uno stato **diverso** da quello (un valore assente conta come «non atteso»). La risposta è
ordinata per causa, con il gruppo vuoto in coda.

---

### ⭐ Perimetro e sicurezza

La funzione è `SECURITY DEFINER` del **proprietario** delle tabelle, non di un superuser: alcune
viste di presidio, lette da un programma senza un utente in sessione, risponderebbero zero per
cecità (il difetto è raccontato in
[dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio)).

Due limiti la rendono sicura:

* **torna numeri, mai le righe**. Il valore del gruppo è un codice del catalogo delle cause, non un
  dato di un cliente o di un documento;
* **conta solo ciò che è a catalogo**, attivo e non ritirato. Un nome sconosciuto, spento,
  ritirato o vuoto si rifiuta, non si conta a zero: è ciò che impedisce alla funzione di diventare
  una porta per contare qualunque relazione aggirando la row level security.

I nomi di vista e colonne vengono da una tabella, quindi entrano nella query come identificatori
quotati, mai per concatenazione.

---

### Codici errore

* `E_PRESIDIO_NON_A_CATALOGO` — la vista chiesta non è in `dbops.presidi`, oppure è spenta o
  ritirata, oppure il nome è vuoto.

---

### Test

* `db/pgtap/dbops/test-conta-presidio-per-variante-v1.sql` — rifiuto di una vista non a catalogo e
  del nome vuoto; una riga sola anche a zero per un presidio senza causa; un caso costruito con due
  cause, il filtro di stato che esclude e il gruppo vuoto; nessun gruppo quando non c'è niente da
  guardare; `SECURITY DEFINER`, `search_path` pinnato, `EXECUTE` dell'applicazione; sui presidi
  veri la somma dei gruppi è il conteggio.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — il proprietario delle tabelle protette lette
  dalle viste `DEFINER` è quello di questa funzione.

---

### Note di migrazione

* 2026-10-10 — nasce con `brief-db-presidio-processi-testo-per-causa` §6.2 (R-2) e prende da
  `fn_conta_presidio` il perimetro, il filtro e il `SECURITY DEFINER`.

---

{% include-markdown "signature-core.md" %}
