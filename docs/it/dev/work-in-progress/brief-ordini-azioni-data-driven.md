# Brief DB — Modello azioni/transizioni data-driven per gli ordini di vendita

> **Origine**: richiesta Tid 2026-06-05, emersa mentre si pianificava la stampa
> documentale ordini (`brief-ordini-stampa.md` §6). Leggendo il piano si è notato
> che gli ordini, a differenza degli altri documenti vendite, **non hanno un
> modello azioni data-driven**.
>
> **Natura del brief**: descrive **cosa serve e perché** (la logica e la
> motivazione), **non il come**. La strada implementativa (oggetti DB, struttura,
> seed, test) la sceglie il team DB nel rispetto dei pattern già rodati sugli altri
> documenti (`feedback_db_actions_passaggio_team`). BE/FE partono a consegna
> avvenuta (`feedback_be_fe_attende_prerequisiti_db`).
>
> **Sequenza ratificata (Tid)**: **prima** questo modello, **poi** la stampa §6 —
> così l'azione di emissione/conferma nasce già come azione data-driven invece di
> essere cablata a mano e poi rifatta.

---

## 1. Cosa è stato riscontrato

Tutti i documenti commerciali vendite **tranne l'ordine** espongono le azioni di
stato in modo **data-driven**: una funzione di dominio, dato l'id del documento,
ritorna le azioni disponibili nel suo stato corrente (con i metadati per la UI:
etichetta, severità, icona, se richiede conferma) più le capacità di editing.

- **Preventivi**: `script.fn_available_actions_preventivo` + matrice transizioni
  `config.transizioni_stati_preventivi`.
- **Offerte**: `script.fn_available_actions_offerta` + `config.stati_doc_offerte_transizioni`.
- **Contratti**: `script.fn_available_actions_contratto` (variante con metadati di
  stato).

Gli **ordini** invece:

- hanno **solo** la lista degli stati (`config.stati_doc_ordini`), **senza alcuna
  matrice di transizioni** né funzione di azioni disponibili;
- le azioni e le capacità (può confermare, può fare push, può modificare testata/
  righe) sono **calcolate a mano nel backend Python**, con stati cablati nel codice;
- di conseguenza il frontend **ricostruisce i pulsanti a mano**, mentre per gli
  altri documenti li deriva automaticamente dai metadati dell'API.

In sintesi: l'ordine è l'**unico outlier** della famiglia. Funziona, ma con una
logica parallela e duplicata rispetto agli altri tre.

## 2. Perché conviene chiuderlo (motivazione)

- **Simmetria di modello**: alla quarta occorrenza dello stesso schema, mantenere
  l'ordine fuori dal modello è un debito che costa duplicazione e divergenze
  (`feedback_simmetria_modello_no_meta_scope`). I tre domini gemelli sono la prova
  che il pattern è quello giusto e stabile.
- **Single source of truth**: le transizioni ammesse e i metadati delle azioni
  vivono in un solo posto (configurazione), non sparsi tra codice BE e FE. Le
  azioni diventano configurabili senza toccare il software.
- **Coerenza dell'esperienza**: stesse etichette, severità, icone, conferme e
  stessa logica di abilitazione/disabilitazione (con motivo) di tutti gli altri
  documenti vendite.
- **Abilita la stampa §6 in modo pulito**: l'emissione/conferma dell'ordine (che
  genera il documento) diventa **una delle azioni data-driven**, esattamente come
  l'`emetti` di preventivi/offerte — invece di un caso speciale cablato a mano.
- **Riuso lato applicativo**: i building block frontend per consumare le azioni
  data-driven **esistono già** (sono usati dagli altri domini); allineare l'ordine
  **rimuove** codice manuale invece di aggiungerne.

## 3. Cosa deve fornire il modello (logica, non implementazione)

Il modello ordini deve offrire, in modo data-driven e coerente con gli altri
documenti, la possibilità — dato un ordine — di sapere:

1. **quali azioni di stato sono disponibili** nel suo stato corrente, ciascuna con
   i metadati necessari alla UI (etichetta, severità, icona, eventuale conferma,
   stato di destinazione);
2. **quali transizioni di stato sono ammesse** e quali sono **manuali** (azione da
   interfaccia) rispetto a quelle **automatiche/di processo** (guidate da eventi a
   valle, non da un pulsante);
3. **quali capacità di editing** valgono nello stato (modifica testata/righe) e
   quali campi sono eventualmente bloccati;
4. dove un'azione non è disponibile, **il motivo** (per il tooltip), come già fanno
   gli altri documenti.

Come questo venga realizzato (matrice transizioni, funzione di dominio, metadati,
seed, test) è **scelta del team DB**, allineata al pattern di
preventivi/offerte/contratti.

## 4. Punto di dominio da chiudere — quali transizioni sono *manuali*

Questo è l'unico nodo che **non** è una scelta implementativa ma di **dominio**, e
va deciso prima del seed. La proposta (da ratificare):

- **`DRAFT → CONFERMATO`**: azione manuale di conferma/emissione (con la §6,
  genera anche il documento). **Sì, manuale.**
- **`DRAFT → ANNULLATO`**: annullo di una bozza. **Sì, manuale.**
- **`CONFERMATO → ANNULLATO`**: **da decidere** — un ordine confermato è
  annullabile da interfaccia? Presumibilmente solo se non già evaso/fatturato a
  valle. Serve la regola di dominio.
- **`CONFERMATO → ALLOCATO → SPEDITO → CONSEGNATO → FATTURATO`**: questi stati
  rappresentano l'avanzamento **a valle** (magazzino/DDT/fatturazione). **Non sono
  azioni manuali** dell'interfaccia ordine: sono guidati dai processi a valle. Non
  entrano nel grafo delle azioni manuali (al più come transizioni automatiche).

Inoltre: il **push a commessa** non è una transizione di stato ma un'azione
applicativa a sé (come il `push_commessa` dei preventivi); resta gestita come tale,
non come passaggio di stato.

> Esito atteso del confronto: un piccolo grafo di transizioni **manuali**
> (essenzialmente conferma/emissione e annullo) + la chiarezza su cosa è invece
> automatico/di processo.

## 5. Confini

- **Indipendente** dalle altre estensioni ordini già in corso (riepilogo IVA,
  stampa): è il **prerequisito** della stampa §6 ma non la include.
- **Fuori da questo brief**: il "come" DB (oggetti, struttura, seed, pgTAP) e
  l'adeguamento BE/FE (lettura del modello data-driven al posto del calcolo
  hardcoded, riuso dei building block frontend esistenti). Quest'ultimo parte a
  consegna DB avvenuta.
- **Riferimenti** (evidenza del pattern da replicare, non prescrizione): le
  funzioni `fn_available_actions_*` e le matrici `transizioni_stati_*` /
  `stati_doc_offerte_transizioni` dei tre domini gemelli.

## 6. Seguito

A modello consegnato: ordine BE legge le azioni/capacità dal modello (eliminando il
calcolo hardcoded), FE consuma le azioni con i building block già esistenti, e si
procede con la stampa §6 (`brief-ordini-stampa.md`) appoggiando l'emissione sul
nuovo modello.
