## 📘 Documentazione Concettuale – Tabella `dbops.processi_bersagli`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo di cui la riga dichiara un bersaglio
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — i modi: la via di un bersaglio è uno di loro
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) — il livello 1: bersaglio mancante, senza percorso o con un percorso rotto
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — il livello 2: percorso dichiarato, ma nessuna policy o guard lo applica
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura che il livello 2 cerca sulla tabella
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta di scrittura dichiarata per `dbops.coda_lavori`
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

La via è un **modo** del registro [`dbops.emittente_modi`](/dbzero/dbops/tabelle/emittente_modi)
(chiave esterna): il modo con cui il guard di scrittura (`script.trgfn_guard_emittente_scope`) trova
l'emittente della riga. La colonna è quella che il modo legge. Sono i due argomenti con cui il guard
è montato sulla tabella, e la dichiarazione dice la stessa cosa del montaggio. Qualche esempio:

| `emittente_via` | Che cosa contiene `emittente_colonna` |
| --- | --- |
| `fiscale` | è **già** l'id dell'emittente fiscale |
| `soggetto_ruolo` | l'id del soggetto-ruolo dell'emittente |
| `fattura` | l'id di una fattura, da cui si risale |
| `listino` | l'id del listino da cui una versione eredita l'emittente |
| `magazzino` | l'id di un magazzino, che appartiene a un emittente |

Una riga figlia dichiara il modo con cui il guard la risolve: una versione di listino dice `listino`
sulla colonna `listino_id`, come il guard montato su `vendite.listini_versioni`. Che cosa vuol dire
ogni modo, e da dove passa, lo dice il registro.

⚠️ **Via e colonna vivono o muoiono insieme** (`chk_processi_bersagli_via_colonna`): o si
dichiarano tutte e due, o nessuna. Una via senza colonna sembrerebbe una dichiarazione fatta e non
direbbe niente, e il presidio non potrebbe verificarla.

⚠️ Che la via dichiarata sia quella del guard montato lo controlla oggi il pgTAP
`dbops/test-emittente-modi-registro-v1` (test 14).

---

### La porta di scrittura: quando la difesa non è il guard

Di norma la scrittura di un bersaglio la difende il guard `script.trgfn_guard_emittente_scope`.
Su qualche tabella il guard non si può montare: respinge le scritture senza utente che passano
da una funzione `SECURITY DEFINER`, e quella tabella la scrivono proprio così (i job che accodano
da proprietario). Lì la riga dichiara in `porta_scrittura` la funzione, scritta come
`schema.nome`, da cui passa **ogni** scrittura del processo sul bersaglio
(`chk_processi_bersagli_porta_qualificata` ne controlla il formato).

La porta conta come difesa di scrittura solo se:

* la funzione esiste ed è `SECURITY DEFINER`;
* la tabella ha la row level security attiva, con policy permissive che coprono `INSERT` e
  `UPDATE`.

⭐ Le due metà si dividono il lavoro: la policy difende le scritture dell'applicazione, la porta
quelle del proprietario. Vuota (`NULL`) vuol dire che la difesa attesa è il guard.

È il caso di `dbops.coda_lavori`, che dichiara la porta `dbops.fn_accoda_lavoro`.

---

### Quando una riga diventa un allarme

| Che cosa succede | Dove si vede |
| --- | --- |
| il processo di dominio non ha nessun bersaglio, la tabella non esiste, la via manca o la colonna non esiste più | [vw_processi_dominio_senza_emittente](/dbzero/dbops/views/vw_processi_dominio_senza_emittente) |
| il percorso c'è, ma sulla tabella manca la policy con la row level security attiva, o manca la difesa di scrittura (il guard, o la porta dichiarata in `porta_scrittura`) | [vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) |

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
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — la porta dichiarata: conta se è `DEFINER` con RLS e
  policy, non conta se è `INVOKER` o con la RLS spenta; `dbops.coda_lavori` esce dal presidio.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-05 — nasce `debito_dichiarato` (`brief-db-processi-automatici-residui-be`, DB-2): prima le
  righe attese erano scritte solo nelle note del seed, mentre le viste dicevano «deve restare
  vuota».
* 2026-11-08 — perde `tx_id`, `data_update`, `user_update` e i due trigger montati a mano che li
  scrivevano: la tabella la scrive solo la migrazione, dal CSV, e le colonne direbbero sempre «il
  migratore» (regola dello scrittore, `automazione-db.md` §1.1; `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — nasce `porta_scrittura`: prima una tabella difesa da una porta `DEFINER` invece
  che dal guard restava nel livello 2 come debito dichiarato (`dbops.coda_lavori`).

---

{% include-markdown "signature-core.md" %}
