# Guida — Un database che resta veloce

> **Ultimo aggiornamento**: 18 ottobre 2026
>
> **Destinatari**: sviluppatori database e backend, e chiunque debba capire perché
> una schermata o un test è diventato lento
>
> **Vedi anche** — funzioni e viste DB:
>
> * [maintenance.vw_statistiche_mancanti](/dbzero/maintenance/manual/vw_statistiche_mancanti) — le tabelle senza statistiche
> * [dbops.fk_index_policy](/dbzero/dbops/manual/fk_index_policy) — quali chiavi esterne hanno un indice, e perché
>
> **Vedi anche** — regole e guide correlate:
>
> * [Linee guida SQL §13](/linee-guida-sql#13-prestazioni-la-forma-di-funzioni-e-query) — le regole sulla forma di funzioni e query
> * [Linee guida SQL §8](/linee-guida-sql#8-indici) — gli indici
> * [Le statistiche del planner](/guide/statistiche-del-planner) — la fotografia dei dati e il lavoro notturno
> * [Row Level Security](/postgresql/row-level-security) — le policy, che pesano su ogni lettura
> * [Policy ricerca e paginazione](/dev/Policy-ricerca-e-paginazione(API-DB)) — quanto chiede una lista, e come lo chiede

---

## In una frase

Un database resta veloce se il planner **sa com'è fatto il dato**, se trova
**una strada** per arrivarci, e se la query è scritta in modo da **non rifare lo
stesso lavoro** per ogni riga. Delle tre cose, le prime due il database le cura
quasi da solo; la terza dipende da come scriviamo il codice.

---

## 1. Come decide PostgreSQL

Una query dice **che cosa** si vuole, non **come** ottenerlo. Il come lo sceglie
il **planner**: prova mentalmente più strade (scorrere tutta la tabella, usare un
indice, unire prima questa tabella o quella) e prende quella che **stima** più
economica. Ogni scelta poggia su tre cose:

| | Che cos'è | Chi se ne occupa |
| --- | --- | --- |
| **La fotografia** | quante righe ha una tabella, quali valori sono frequenti: le statistiche | il lavoro notturno e l'autovacuum — [Le statistiche del planner](/guide/statistiche-del-planner) |
| **Le strade** | gli indici, che permettono di arrivare a poche righe senza leggere tutte le altre | le regole di [§8](/linee-guida-sql#8-indici) e la policy automatica degli indici sulle chiavi esterne |
| **La forma** | come è scritta la query o la funzione: che cosa calcola, quante volte, con quali condizioni | chi scrive il codice — [§13](/linee-guida-sql#13-prestazioni-la-forma-di-funzioni-e-query) |

Quando una di queste manca il planner sbaglia la stima, e una stima sbagliata di
cento volte porta a una strada sbagliata di cento volte. Le prime due si possono
rendere automatiche. La terza no: si impara a riconoscerla.

---

## 2. Perché da noi la forma conta di più

Due caratteristiche di ZeroErp rendono la forma più importante che in un
database qualunque.

**La logica sta nel database.** Molte letture non sono una query scritta dal
backend ma una funzione che chiama un'altra funzione, che legge una vista. Il
planner, a volte, vede il tutto come una query unica e lo ottimizza insieme;
altre volte vede solo una scatola chiusa di cui non conosce né il prezzo né
quante righe restituisce. In quel caso stima con valori fissi, e spesso sbaglia.

**Quasi ogni tabella ha una policy di sicurezza.** La Row Level Security
aggiunge a ogni lettura un controllo: «questa riga, questo utente la può
vedere?». Il controllo si paga **per riga**. Su dieci righe non si nota; se il
planner decide di applicarlo a tutta la tabella prima di scartare quelle che non
servono, diventa il grosso del tempo. E per sicurezza il planner non usa gli
indici con le condizioni di cui non si fida: una condizione che da
amministratore va dritta sull'indice, come applicazione legge tutto.

⇒ Per questo la regola più importante del capitolo successivo è la prima.

---

## 3. Come si indaga una lentezza

### Prima: misurare come l'applicazione

L'amministratore del database **non passa dalle policy**, e il planner gli
prepara un altro piano, spesso migliore. Una query provata da amministratore
può sembrare veloce e non esserlo per nessun utente. Si misura sempre con
l'utente dell'applicazione e il contesto di un utente vero, dentro una
transazione che si annulla alla fine.

E si misura **chi chiama davvero**, non solo il pezzo sospettato: la stessa
funzione chiamata con un valore scritto a mano e chiamata da un'altra funzione
può comportarsi in modo molto diverso.

### Poi: leggere il piano

Il comando `EXPLAIN ANALYZE` esegue la query e mostra, passo per passo, che
strada ha scelto il planner, quante righe **pensava** di trovare e quante ne ha
trovate davvero. Le domande da fargli, in quest'ordine:

1. **Stime e realtà sono vicine?** Se pensava 3 righe e ne ha trovate 30.000, il
   problema è la fotografia o una funzione che non dichiara quante righe dà.
2. **Qualcosa si ripete?** Un passaggio con `loops=168` è stato eseguito 168
   volte. Se fa lo stesso lavoro ogni volta, è il difetto più caro di tutti.
3. **Legge tutta una tabella per trovarne poche righe?** Un `Seq Scan` con
   tante righe scartate, sotto una policy, di solito vuol dire che una
   condizione non è potuta entrare nell'indice.
4. **Quanto costa pianificare?** Se il tempo di pianificazione è grande quanto
   quello di esecuzione, o se compare una voce JIT, il costo non è nella query
   ma nel prepararla.

### Infine: curare la forma, non il numero

Una misura **trova** il difetto e **conferma** che la cura funziona. Non decide
che cosa fare, né se farlo. La cura si descrive sul **modello** — «si ricalcola
per ogni riga», «la policy gira su tutta la tabella» — e allora vale con dieci
righe come con dieci milioni. «Oggi la tabella è piccola» non è un motivo per
lasciare un difetto, e «oggi ci mette 40 ms» non è un criterio per dire che va
bene: sono fotografie della macchina di oggi. È la «regola zero» del progetto,
in testa a `.codex/AGENTS.md`.

Per questo nei brief e nei test un tempo si scrive sempre **con la data, la
macchina e il ruolo** con cui è stato preso: è un fatto che invecchia, non una
regola.

---

## 4. I difetti che abbiamo incontrato

Ognuno ha la sua regola nelle linee guida; qui c'è il sintomo, per riconoscerlo.

| Sintomo | Che cosa succede | Regola |
| --- | --- | --- |
| Una lista diventa lenta in proporzione alle sue righe | per ogni riga si ricalcola qualcosa che ha sempre la stessa risposta: la storia di un documento, il perimetro dell'utente | [§13.2](/linee-guida-sql#132-cio-che-non-dipende-dalla-riga-si-calcola-una-volta) |
| Veloce da amministratore, lenta come applicazione | una condizione non è «sicura» per il planner e non entra nell'indice sotto la policy | [§8.5-bis](/linee-guida-sql#85-bis-sotto-una-policy-rls-entra-nellindice-solo-una-clausola-leakproof), [§13.3](/linee-guida-sql#133-un-cast-o-una-funzione-nel-join-verso-una-tabella-sotto-policy) |
| Una funzione costa sempre uguale, anche quando il lavoro è poco | ripianifica a ogni chiamata invece di tenere il piano in memoria | [§13.4](/linee-guida-sql#134-il-piano-generico-plan_cache_mode-sulla-funzione) |
| Secondi su una funzione che dovrebbe metterci millisecondi, anche a database vuoto | il planner stima un lavoro enorme e compila la query (JIT) prima di eseguirla | [§13.5](/linee-guida-sql#135-il-jit-jit-off-dove-il-piano-tiene-i-rami-di-piu-modi) |
| La policy viene applicata a tutta la tabella invece che alle poche righe cercate | il planner crede che la policy costi quasi niente, o che una funzione restituisca mille righe invece di una | [§10.3](/linee-guida-sql#103-logica-di-scope-in-funzioni-scriptfn_scope_), [§13.6](/linee-guida-sql#136-dichiarare-costo-e-cardinalita-cost-e-rows) |
| Dopo una modifica innocua, tutto torna lento | una riscrittura della funzione ha perso un'impostazione che non si vede nel suo testo | [§13.7](/linee-guida-sql#137-le-proprieta-invisibili-nel-corpo-si-ripetono-a-ogni-create-or-replace) |

⚠️ L'ultima riga è la più subdola: i risultati restano identici, nessun test di
comportamento diventa rosso. Per questo ogni impostazione di quel tipo ha un
test che la pretende per nome.

---

## 5. Che cosa fa il database da solo, e che cosa no

### Da solo

| Che cosa | Quando | Dove si legge |
| --- | --- | --- |
| Rifà le statistiche di tutte le tabelle, e fallisce se ne salta una | ogni notte, e in CI prima dei test | [Le statistiche del planner](/guide/statistiche-del-planner) |
| Rianalizza e ripulisce le tabelle che cambiano molto (autovacuum) | di continuo, secondo quanto cambiano | impostazioni di PostgreSQL, non nostre |
| Crea o toglie gli indici sulle chiavi esterne, secondo la policy | a ogni migrazione | [§8.7](/linee-guida-sql#87-automazione-indici-fk) |

### Con un controllo a disposizione

| Che cosa | Dove |
| --- | --- |
| Indici doppi o coperti da un altro più largo | due viste, [§8.6](/linee-guida-sql#86-gestione-indici-ridondanti) |
| Chiavi esterne senza indice | [§8.7](/linee-guida-sql#87-automazione-indici-fk) |
| Tabelle senza statistiche | [vw_statistiche_mancanti](/dbzero/maintenance/manual/vw_statistiche_mancanti) |

### Fuori perimetro, oggi

ZeroErp non è ancora in produzione. Alcuni temi di manutenzione appartengono al
database **in esercizio** e oggi non hanno un caso su cui scrivere regole; si
dichiarano qui perché nessuno li creda coperti:

* **lo spazio sprecato dalle righe aggiornate** (il «bloat») e la manutenzione
  straordinaria che lo recupera;
* **lo storico delle query più costose** (`pg_stat_statements`): l'estensione
  **non è installata**, e installarla è una decisione di progetto;
* **i parametri del server** (memoria per le operazioni, cache, numero di
  connessioni), che dipendono dalla macchina di produzione.

---

## Area tecnica — esempi

Misurare una query come applicazione, senza lasciare traccia:

```sql
BEGIN;
SET LOCAL ROLE zeroerp_app;
-- il contesto GUC di un utente vero (utente, ruolo applicativo, emittente…):
-- l'elenco completo è il contratto in /guide/contratto-guc-app
SELECT set_config('app.current_user_id', '19', true);
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM vendite.ddt WHERE id = 42;
ROLLBACK;
```

Confrontare piano su misura e piano generico su un ciclo di chiamate (§13.4):

```sql
BEGIN;
SET LOCAL ROLE zeroerp_app;
SET LOCAL plan_cache_mode = force_generic_plan;   -- poi rifarlo con 'auto'
DO $$
DECLARE t0 timestamptz := clock_timestamp();
BEGIN
  FOR i IN 1..50 LOOP
    PERFORM schema.fn_da_misurare(i);
  END LOOP;
  RAISE NOTICE 'ms: %', extract(epoch FROM clock_timestamp() - t0) * 1000;
END $$;
ROLLBACK;
```

Le impostazioni «invisibili» di una funzione (§13.7):

```sql
SELECT p.oid::regprocedure, p.procost AS cost, p.prorows AS rows, p.proconfig
  FROM pg_proc p
 WHERE p.pronamespace = 'vendite'::regnamespace
   AND p.proname = 'fn_documento_lineage_archi';
```

Gli indici ridondanti:

```sql
SELECT * FROM dbops.vw_duplicate_indexes;
SELECT * FROM dbops.vw_indici_ridondanti_prefisso;
```
