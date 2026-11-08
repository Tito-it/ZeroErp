## 📘 Documentazione Concettuale – Tabella `dbops.storico_scope_policy`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — il valore a cui ogni strada arriva
>
> Approfondimento viste:
>
> * [dbops.vw_storico_scope_da_dichiarare](/dbzero/dbops/views/vw_storico_scope_da_dichiarare) — il debito della mappa, nel digest settimanale
>
> Approfondimento funzioni:
>
> * [dbops.fn_storico_risolvi_scope](/dbzero/dbops/funzioni/fn_storico_risolvi_scope) — chi segue la strada scritta qui
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — chi legge il modo per decidere se armare la shadow
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — il trigger che congela il valore nella shadow
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

La mappa che dice, per ogni tabella storicizzata, da dove si prende l'emittente fiscale di una
sua riga. Il trigger di storico, quando fotografa una versione, segue questa strada e congela
l'emittente nella shadow: è ciò che permette di mostrare la storia di un documento solo agli
operatori che possono vedere il documento.

Il trigger è uno per tutte le tabelle e non sa niente della tabella che sta fotografando: la
conoscenza «per le righe di fattura si risale alla fattura» sta qui, scritta come dato, non
nel codice. Una riga per madre, con chiave schema e tabella.

---

### ⭐ Sei strade verso lo stesso fatto

| `modo` | Che cosa dice | Che cosa c'è in `colonna` |
| --- | --- | --- |
| `EF` | la riga ha già l'emittente fiscale: si copia | la colonna dell'emittente |
| `SR` | la riga ha il soggetto-ruolo dell'emittente: si converte nel suo emittente fiscale (è uno a uno) | la colonna del soggetto-ruolo |
| `BA` | la riga porta un billing account, che ha **esattamente un** emittente | la colonna del billing account |
| `COPPIA` | la riga porta la coppia (istanza, utility) di un billing account: si prende l'emittente del billing account di quella coppia | i due nomi, «istanza,utility», separati da una virgola |
| `PADRE` | la riga è un satellite: si risale al padre e si continua sulla **riga di mappa del padre**, anche per più salti | la FK verso il padre; padre in `padre_schema` e `padre_tabella` |
| `NESSUNO` | la madre non è protetta: la shadow non si arma, e `ragione` dice perché | vuota |

⭐ Il valore che si congela è sempre uno solo, un `emittenti_fiscali.id`: i sei modi sono sei
modi di arrivarci, non sei cose diverse. Ogni modo ha una sua forma, e un vincolo la impone:
le colonne che un modo non usa devono restare vuote.

---

### ⭐ È anche un elenco di lavori

Ogni madre con il trigger di storico deve avere la sua riga. Quindi:

* una madre storicizzata **senza riga** è una tabella che nessuno ha ancora guardato;
* una madre **protetta** dalla row level security ma dichiarata `NESSUNO` è un debito: la storia
  di quelle righe è ancora aperta;
* una riga **senza più madre** (tabella cancellata, storicizzazione tolta) è un resto da togliere.

I tre casi li asserisce il pgTAP in CI e li mostra
[dbops.vw_storico_scope_da_dichiarare](/dbzero/dbops/views/vw_storico_scope_da_dichiarare) nel
digest settimanale, che deve restare vuota. Il pgTAP verifica anche che la mappa **non menta**:
la colonna dichiarata esiste, la FK verso il padre punta davvero a quel padre, ogni catena arriva
a un emittente e non gira in cerchio.

⛔ Una riga `NESSUNO` deve dire **perché**, in almeno quaranta caratteri: «la tabella non ha la row
level security», non «TODO». La data di registrazione è l'orologio del debito.

---

### ⚠️ Due cose da sapere

**La chiave porta lo schema.** `acquisti.ddt` e `vendite.ddt` sono due righe distinte: scrivono
nella stessa shadow `storico.ddt`, ma la loro strada verso l'emittente non è la stessa.

**Un padre dichiarato deve esistere nella mappa.** Lo impone una FK della tabella su se stessa,
**differita** al commit: il CSV di seed carica una riga alla volta e un satellite può venire
prima del suo padre. Un CSV con un padre senza riga fa fallire il migrate.

---

### Come si aggiorna

La sede è il CSV di seed `80_data/sql/dbops/storico_scope_policy.csv`, caricato come mirror
(`loadUpdateData`, rieseguito quando il file cambia): si edita quello, mai con un `UPDATE` a
parte. Il mirror aggiunge e aggiorna, non cancella: una riga tolta dal CSV va cancellata anche
con un changeSet. Quando una madre entra in RLS, la sua riga passa da `NESSUNO` al modo giusto;
la shadow la arma la convergenza al migrate successivo (`fn_storico_arma_scope_tutte`).

⚠️ Lo scope si congela alla scrittura: le versioni scritte mentre la madre era `NESSUNO` hanno
lo scope vuoto e nessuno lo ricalcola (il backfill tocca solo le versioni senza origine). Con
la shadow armata quelle versioni non le vede nessun operatore.

---

### Test

* `db/pgtap/dbops/test-storico-scope-policy-v1.sql` — completezza (ogni madre ha la riga, nessuna
  madre in RLS è `NESSUNO`, nessuna riga orfana), coerenza col catalogo (colonne, FK verso il padre,
  FK composta della coppia, catene che terminano, ogni modo del vincolo ha il suo ramo nel
  resolver) e la vista di presidio su casi costruiti.
* `db/pgtap/storico/test-storico-scope-congelato-v1.sql` — la mappa al lavoro: shadow armate solo
  per le madri protette, scope congelato per madre, shadow condivisa fra una madre protetta e una
  `NESSUNO`.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b): il CSV
  iniziale è stato generato dal catalogo di quel giorno, il modo dalla policy della madre e il
  padre dalla FK reale.
* 2026-10-09 — arriva il modo `COPPIA` (`brief-db-istanza-nasce-col-ba`), con la sua forma nel
  vincolo: primo adottante `anagrafiche.istanze_dati_precontrattuali`.
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
