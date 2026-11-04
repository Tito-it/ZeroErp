## 📘 Documentazione Concettuale – Tabella `dbops.processi_bersagli`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo di cui la riga dichiara un bersaglio
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) — il livello 1: bersaglio mancante, senza percorso o con un percorso rotto
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — il livello 2: percorso dichiarato, ma nessuna policy o guard lo applica
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura che il livello 2 cerca sulla tabella
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — il registro dei processi e i suoi presidi

---

### 🎯 Scopo Principale

Le tabelle che ogni processo di **dominio** scrive, e per ciascuna **come si arriva dalla riga al
suo emittente**. È la risposta scritta alla domanda «questa riga di chi è?», che altrimenti vive
solo nella testa di chi ha scritto il codice.

Senza quella risposta un processo automatico può lavorare righe di un'azienda credendo di lavorare
le proprie, e nessuno se ne accorge finché non esce la fattura sbagliata. ⭐ Il presidio che la
legge prende l'omissione **prima** che il processo giri: a runtime non è recuperabile, perché la
row level security non può filtrare su una colonna che non c'è.

---

### ⚠️ È un elenco dichiarato

La tabella prova che qualcuno ha detto **dove** il processo scrive, non che scriva **solo** lì.
Una tabella scritta dal processo e mai dichiarata qui non la vede nessun presidio.

La matrice copre di proposito i soli processi di **dominio**, quelli in cui sbagliare costa: un
censimento anche di manutenzione e amministrazione sarebbe un elenco lungo, sempre indietro
rispetto al codice, che nessuno leggerebbe.

Una tabella compare una volta sola per processo (chiave unica su processo, schema e tabella).

---

### ⭐ Il percorso è una via più una colonna

| `emittente_via` | Che cosa contiene `emittente_colonna` |
| --- | --- |
| `fiscale` | è **già** l'id dell'emittente fiscale |
| `soggetto_ruolo` | l'id del soggetto-ruolo dell'emittente |
| `fattura` | l'id di una fattura, da cui si risale |
| `contabile` | l'id di una distinta, da cui si risale al conto di incasso |
| `padre` | la chiave verso la testata da cui la riga eredita l'emittente (per esempio il listino sopra la versione) |

⚠️ **Via e colonna vivono o muoiono insieme** (`chk_processi_bersagli_via_colonna`): o si
dichiarano tutte e due, o nessuna. Una via senza colonna sembrerebbe una dichiarazione fatta e non
direbbe niente, e il presidio non potrebbe verificarla.

⚠️ Il vocabolario delle vie è chiuso dal CHECK `chk_processi_bersagli_via`, e **non coincide** con
quello del guard di scrittura `script.trgfn_guard_emittente_scope`: il guard conosce anche
`listino` e `magazzino`, che qui non si possono dichiarare, mentre `padre` esiste solo qui.

---

### Quando una riga diventa un allarme

| Che cosa succede | Dove si vede |
| --- | --- |
| il processo di dominio non ha nessun bersaglio, la tabella non esiste, la via manca o la colonna non esiste più | [vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) |
| il percorso c'è, ma sulla tabella manca la policy con la row level security attiva, o manca il guard di scrittura | [vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) |

⭐ Un percorso verso una colonna cancellata è peggio di un percorso assente, perché sembra a posto:
per questo il livello 1 verifica che la colonna esista davvero.

`debito_dichiarato` dice che una riga in quelle viste è **attesa**: la vista la presenta come
debito con un nome invece che come allarme. Dichiarare un debito non lo assolve: l'invariante di
tutte e due le viste è «nessuna riga non dichiarata». `note` spiega il perché del percorso, o del
debito, quando non è ovvio.

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql` — la chiave esterna verso il processo, i due CHECK
  sul percorso, ogni bersaglio del seed su un processo di dominio, i due livelli su casi costruiti.
* `db/pgtap/dbops/test-presidi-debito-dichiarato.sql` — un bersaglio scoperto ma dichiarato si
  presenta come debito, uno nuovo e rotto come allarme.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-05 — nasce `debito_dichiarato` (`brief-db-processi-automatici-residui-be`, DB-2): prima le
  righe attese erano scritte solo nelle note del seed, mentre le viste dicevano «deve restare
  vuota».

---

{% include-markdown "signature-core.md" %}
