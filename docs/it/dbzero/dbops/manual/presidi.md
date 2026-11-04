## 📘 Documentazione Concettuale – Tabella `dbops.presidi`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi) — le parole per chi deve agire
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — le cause di un presidio, e a chi tocca ciascuna
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — un registro del debito che una riga nomina
> * [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy) — un altro registro del debito
> * [dbops.rls_perimetro_debito](/dbzero/dbops/tabelle/rls_perimetro_debito) — un altro registro del debito
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio onesto di una vista a catalogo
> * [dbops.fn_conta_presidio_per_variante](/dbzero/dbops/funzioni/fn_conta_presidio_per_variante) — lo stesso conteggio per causa, ed è la sede del filtro
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — il meccanismo condiviso: la misura e il registro

---

### 🎯 Scopo Principale

Il catalogo delle viste di presidio: per ogni vista di controllo dice **che cosa significa una
sua riga**, ogni quanto si guarda, se il conteggio è onesto letto da un programma senza utente e
a chi tocca spegnerla.

Le viste di controllo guardano se qualcosa si è rotto in silenzio: un lavoro notturno fallito,
un operatore configurato a metà, una tabella che dovrebbe filtrare e non filtra. Una vista che
nessuno guarda però non presidia niente: questo catalogo è ciò che permette al digest e al
pannello dei processi automatici di prendere quelle viste e portarne il contenuto davanti a una
persona, senza sommergerla.

---

### ⛔ Non è un elenco in Python

Un elenco scritto nel backend sarebbe una seconda sorgente di verità e diverrebbe stantio alla
prima vista nuova: il presidio nuovo nascerebbe fuori dal digest, in silenzio, cioè lo stesso
guasto che il digest chiude. Il catalogo sta nel database, accanto alle viste che descrive, e un
pgTAP pretende che le due cose coincidano (vedi *Test*).

---

### ⭐ Le nature: nessuna si deduce dal nome della vista

Non tutte le viste dicono la stessa cosa quando non sono vuote. Su una lista di lavori falliti
una riga è un guasto di adesso; su un registro di debito noto l'allarme è la voce che nessuno
aveva registrato; su un inventario dei trigger le righe sono la condizione normale. Un avviso
che non distingue questi casi si apre con l'inventario, e un avviso rumoroso viene ignorato al
secondo invio.

| Natura | Che cosa significa una riga | Nel digest |
| --- | --- | --- |
| `ZERO` | un guasto **adesso**: qualunque riga è un allarme | sì |
| `REGISTRO` | un **debito noto**: l'allarme è la voce non registrata | sì |
| `LAVORAZIONE` | una **coda** che qualcuno consuma, o una **spia** da guardare per tendenza | sì, se la cadenza non è `MAI` |
| `CANCELLO` | è già presidiata in CI o in un pgTAP, che blocca il lavoro | no: ripetere ciò che un cancello ha fermato è rumore |
| `INVENTARIO` | un **panorama**: elenca anche i sani | no, mai |

La natura la sa chi ha scritto la vista, e di solito l'ha già scritta in prosa nel `COMMENT`:
il catalogo la rende leggibile a un programma. ⛔ **Anche un inventario si dichiara**: se una
vista mancasse dal catalogo non si saprebbe se è un inventario o una dimenticanza.

Il database tiene coerente il vocabolario: un `CANCELLO` deve dire **dove** è presidiato
(`presidiato_da`), e un `CANCELLO` o un `INVENTARIO` ha per forza cadenza `MAI`.

---

### ⭐ Il debito si tiene con un registro, non con una soglia

Non c'è una colonna `soglia` («l'allarme scatta oltre N»). Un numero vede solo il totale ed è
cieco sullo **scambio**: un debito saldato e un difetto nuovo comparsi lo stesso giorno lasciano
il conteggio fermo, e il controllo tace.

La colonna `registro` porta invece il **nome della tabella** che tiene le voci note, una per
caso, con il motivo scritto e la data. Dove il registro non esiste ancora la colonna è vuota e
la `nota` dice che quello è il lavoro: un vuoto dichiarato, non una dimenticanza. Il nome deve
essere qualificato, e il pgTAP verifica che la tabella esista.

---

### ⭐ Si dichiara lo stato atteso, non quelli di allarme

Su alcune viste la domanda non è «è vuota?»: la vista ha una colonna di stato, e una riga con lo
stato «debito dichiarato» è **attesa**. Per queste il catalogo dichiara la coppia
`colonna_stato` + `stato_atteso`, e si conta tutto ciò che è **diverso** dallo stato atteso.

Elencare gli stati di allarme sembrerebbe più naturale ed è la scelta permissiva: uno stato
nuovo, aggiunto domani alla vista, non sarebbe nell'elenco e cadrebbe nel silenzio. Dichiarando
l'unico stato accettato, uno stato nuovo cade nell'allarme e chi lo aggiunge deve venire qui a
decidere. E il caso a più valori viene da sé: «diverso dall'atteso» prende un allarme e una riga
di registro da togliere senza doverli nominare.

⛔ La coppia è indivisibile: o ci sono tutte e due, o nessuna, e uno stato atteso vuoto è
rifiutato (sarebbe un filtro che accende su tutto). ⚠️ Non ogni colonna chiamata `stato` va
qui: se lo stato è quello del lavoro e ogni riga va comunque guardata, filtrarla spegnerebbe il
presidio.

---

### ⚠️ Cadenza e perimetro: due colonne che sembrano dettagli

**`cadenza`** (`GIORNALIERA`, `SETTIMANALE`, `MAI`) non è solo una scelta di rumore ma anche di
**costo**: la lista di lavoro dei riferimenti morti ricompila ogni funzione del database a ogni
lettura, e non è una vista da interrogare tutte le notti. Il costo è un attributo della singola
riga, non del digest.

**`perimetro`** risponde a una domanda che sfugge: *il conteggio è onesto letto da un programma
senza utente?* `LIBERO` vuol dire sì. `DEFINER` vuol dire che la vista attraversa una tabella in
row level security o una funzione che vede solo ciò che possiede chi la chiama: da un comando
lanciato da un timer tornerebbe zero, e su una vista che deve restare vuota «zero righe» e «non
ho potuto vedere» si scrivono uguale. Il conteggio passa sempre da
[dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio), che lo fa onesto per tutte;
`perimetro` dice se chi legge può anche **elencare** le righe, e per le `DEFINER` il digest
riporta il numero e non le righe.

---

### Chi lo spegne, e con quali parole

`chi_agisce` dice a chi tocca spegnere il presidio:

| Valore | Chi è | Per chi legge il pannello |
| --- | --- | --- |
| `AMMINISTRATORE` | chi usa l'applicazione | «puoi sistemarlo tu» |
| `SISTEMISTA` | chi gestisce server, servizi, timer e ruoli del database | «da segnalare a chi gestisce il server» |
| `SVILUPPO` | serve una modifica al codice o al database | «da segnalare allo sviluppo» |

È un **dato** e non una frase perché il pannello deve distinguere «tocca a te» da «inoltra», e il
digest deve poterli raggruppare. Il database la pretende su ogni natura tranne `INVENTARIO`, che
non si accende.

Le **parole** per chi agisce stanno in [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi).
La `nota` di questa tabella e il `COMMENT` della vista restano scritti per chi **mantiene** il
presidio.

**`colonna_variante`** serve ai presidi le cui righe sono guasti **diversi**: dice da quale
colonna della vista si legge la causa di ogni riga, e da lì si scelgono il testo e «a chi tocca»
riga per riga ([dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause)); `chi_agisce` qui resta
il valore del presidio nel suo insieme. Vuota vuol dire un testo solo per tutto il presidio. Anche
il conteggio si legge per causa, da
[dbops.fn_conta_presidio_per_variante](/dbzero/dbops/funzioni/fn_conta_presidio_per_variante),
perché pannello e digest mostrano solo un campione delle righe e da un campione non si contano i
gruppi.

---

### ⛔ Che cosa non sta qui

* **Il destinatario.** A chi arriva la posta è un fatto di questa installazione, non del
  software: un indirizzo in un catalogo o viaggia su ogni installazione o rende la riga non
  seminabile. Vive dove vive il deploy, nel backend.
* **La soglia.** Vedi sopra.
* **Il ritiro per cancellazione.** `attivo = false` spegne una riga, ma la `nota` resta
  obbligatoria e non vuota anche lì; per ritirare una vista dal catalogo si usa `obsoleto_dal`.
  Una riga spenta o ritirata non si conta: il contatore la rifiuta come una vista sconosciuta.
  ⚠️ L'eccezione è la vista che sparisce dal database: ogni riga, anche ritirata, deve puntare a
  una vista viva, quindi quando la vista si toglie la sua riga si cancella, prima i testi e poi
  il presidio, nello stesso giro.

---

### Come si aggiunge una riga

1. Si scrive la vista, con il suo `COMMENT`, nello schema `dbops` o in un altro schema già
   presente nel catalogo.
2. Si aggiunge la riga a `80_data/sql/dbops/presidi.csv`, con `nota` e `chi_agisce` (vuota solo
   su un `INVENTARIO`). La chiave del seed è la colonna `vista`, il nome qualificato.
3. Se il presidio può accendersi, si aggiunge la riga `it` a `80_data/sql/dbops/presidi_testi.csv`;
   se dichiara `colonna_variante`, anche le cause e i loro testi.

Non c'è un passo 4: se si dimentica il passo 2 un pgTAP diventa rosso, e la vista non nasce fuori
dal digest; se si dimentica il 3 è rosso il pgTAP dei testi; senza `chi_agisce` la riga la rifiuta
il database.

⚠️ Il seed è un upsert `runOnChange` sulla chiave `vista`: a ogni modifica del file rilegge
**tutte** le righe e le ripropone ai vincoli, quindi appendere una riga mette alla prova anche le
altre. Una riga tolta dal file non sparisce dal database: serve una modifica a parte.

---

### Test

* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — i due versi: ogni vista degli schemi presenti
  nel catalogo ha la sua riga, e ogni riga punta a una vista viva; la colonna di stato e il
  registro dichiarati esistono; la `nota` e il `presidiato_da` di un `CANCELLO` sono pretesi dal
  database; il contatore rifiuta una vista non a catalogo, conta la vista intera senza colonna di
  stato e «diverso dall'atteso» con la colonna; il proprietario delle tabelle protette lette dalle
  viste `DEFINER` è ancora quello della funzione che conta.
* `db/pgtap/dbops/test-presidi-testi-v1.sql` — `chi_agisce` obbligatoria tranne che su un
  `INVENTARIO`, il suo dominio, e la `colonna_variante` che esiste nella vista.

---

### Note di migrazione

* 2026-09-10 — nasce con `brief-db-un-destinatario-per-i-presidi` §4.1, il giorno dopo un lavoro
  notturno fallito quattro notti di fila mentre la vista che lo diceva restava lì senza un
  destinatario. Il perimetro del pgTAP si legge dagli schemi presenti nel catalogo e non da un
  prefisso: la trentaduesima vista era nata il giorno stesso in cui se ne contavano trentuno.
* 2026-10-06 — nasce `chi_agisce` (`brief-db-presidi-cosa-significa-cosa-fare`).
* 2026-10-09 — nasce `colonna_variante` (`brief-db-presidio-processi-testo-per-causa`); il
  conteggio per causa arriva il 2026-10-10.
* 2026-11-04 — esce dal catalogo `dbops.vw_run_senza_attore`, tolta dal database: la riga è
  cancellata, non ritirata con `obsoleto_dal`, perché la vista non c'è più
  (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
