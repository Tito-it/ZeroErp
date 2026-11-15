---
description: Verifica critica del lavoro DB non committato — changeSet, pgTAP, CSV e doc; cerca e corregge difetti, censimenti saltati, regole di §11
argument-hint: "[perimetro: un path, un commit o un intervallo — vuoto = lavoro non committato]"
---

Fai una verifica critica del lavoro DB: changeSet, pgTAP, CSV di seed e
documentazione. Cerca e correggi difetti, censimenti saltati, violazioni delle
linee guida.

Indicazioni di Tid per questo giro (possono essere vuote): $ARGUMENTS

## Perimetro

- Senza indicazioni il perimetro è il **lavoro non committato** sotto `db/` e
  `docs/` (`git status --short`, `git diff HEAD`, più i file non tracciati). Se
  Tid ha indicato un path, un commit o un intervallo, il perimetro è quello.
- Se il working tree è pulito e Tid non ha indicato niente, dillo e fermati.
- Il diff è il punto di partenza, non il confine: di ogni oggetto toccato leggi
  chi lo chiama e chi fa la stessa cosa accanto.
- Questa è una sessione di revisione: non conosci le ragioni di chi ha scritto,
  ed è il suo valore. Il contesto lo dà il brief in
  `docs/it/dev/work-in-progress/` che il diff aggiorna.
- Lo stato attuale di un oggetto si legge dalla doc auto-generata
  (`docs/it/dbzero/`), mai da uno YAML precedente. Se un changeSet del perimetro
  è già applicato lo dice il `databasechangelog` del database, non la memoria.

## Un'altra sessione sullo stesso working tree

Prendi `git status --short` all'inizio e riprendilo prima di ogni correzione e
alla fine. Se cambiano file che non hai toccato tu, un'altra sessione sta ancora
scrivendo: fermati, di' a Tid quali file si sono mossi e aspetta.

## Cosa cercare

### 1. La meccanica del changeSet

- `scripts/prossimo_changeset.py --doppi`: nessun numero usato due volte. Nome
  del file, `id` e `logicalFilePath` allineati; un changeSet per file.
- Nessun changelog **già pushato** modificato (`git diff --name-status
  origin/dev/db-tid -- db/changelog` non deve mostrare `M`): si rompe il
  checksum. Un changeSet applicato ma non pushato si segnala a Tid.
- Le `preConditions` guardano solo oggetti nati da changeSet **precedenti**
  nell'ordine del migrate, e reggono su un database ricostruito da zero.
- I divieti di `linee-guida-sql.md` §11: leggi i titoli e apri quelli che il
  perimetro sfiora.
- Il corpo di una funzione riscritta parte dalla doc auto-generata: confrontalo
  con quella, perché ripartire da uno YAML vecchio fa regredire le revisioni
  intermedie. Le proprietà fuori dal corpo (`SET`, `COST`, `ROWS`, volatilità,
  `SECURITY`) sono ripetute (§13.7).
- Il `COMMENT` descrive l'oggetto al presente, non la sua storia (§5d).

### 2. I censimenti

Ognuno si fa cercando, non ricordando. Per ogni modifica del perimetro chiediti
quale riga la riguarda:

| Se il perimetro… | si censisce |
| --- | --- |
| aggiunge una colonna a una tabella di righe | le funzioni che ricopiano la riga con elenco esplicito (push, revisione, clone): una copia dimenticata nasce a `NULL` |
| aggiunge una colonna validata da un guard esistente | l'elenco `UPDATE OF` del trigger: fuori dall'elenco, l'`UPDATE` della sola colonna nuova salta il guard |
| aggiunge un `CHECK` o un `NOT NULL` | le fixture pgTAP e i seed che scrivono quel valore, compreso il `NULL` scritto e non solo la colonna omessa |
| aggiunge un guard restrittivo | i pgTAP che fanno `UPDATE`/`DELETE` su quella tabella, e le funzioni madri di sistema che attraversano la stessa porta |
| cancella o ritira una fonte (tabella, colonna, funzione) | i suoi lettori: corpi delle funzioni, viste, pgTAP, e il BE come richiesta nel brief |
| ritira un valore di un vocabolario | chi filtrava su un valore vicino senza nominare quello ritirato |
| normalizza un valore in scrittura | chi lo ricompone e lo ricerca per valore (fixture, «trova per codice») |
| introduce una regola che confronta una data con oggi | i pgTAP con date fisse che attraversano quel passaggio |
| cambia un messaggio o un codice di errore | i consumatori, cercati dal nome di chi lo solleva e non dal testo |
| cambia il significato di un oggetto | `COMMENT`, pagine `manual/`, guide e note dei presidi, nello stesso giro |
| tocca trigger scritti a mano | i `CREATE TRIGGER` nei changelog, non `pg_trigger` del database di sviluppo |

Le funzioni `BEGIN ATOMIC` non hanno il corpo in `prosrc`: per loro si cerca con
`dbops.fn_find_function_usage` o nel viewdef (§5c).

### 3. Il modello

- Regola zero: un ramo che il modello ammette va gestito anche se oggi non ha
  righe; un guard non si restringe su un conteggio.
- Regola del 2: una logica già presente in `script` o `dbops` si riusa; una
  seconda copia si estrae, e le copie si ritirano nello stesso giro.
- Capability e guard leggono la **stessa** check (§12): un predicato riscritto
  due volte è un difetto anche se oggi coincide.
- Perimetro: una tabella nuova con dati di un emittente ha la sua policy e i
  suoi pgTAP di scope (§10); una vista sopra tabelle protette è
  `security_invoker`.

### 4. I test

- Ogni comportamento nuovo ha un pgTAP che **costruisce** il caso, non uno che
  itera sui dati presenti: su un database da zero passerebbe a vuoto.
- Un test verde perché i dati non sanno produrre il caso è un presidio, e va
  dichiarato tale.

## La prova

Per i changeSet del perimetro **non ancora applicati**:

```bash
scripts/prova_changeset.py <a.yaml> <b.yaml> … --pgtap <test toccato o vicino>
```

nell'ordine di esecuzione, sullo scratch. L'esito si riporta com'è, limiti
compresi: gira da owner, non copre i change non SQL, le `preConditions` valgono
per quel database. Poi `pre-commit run --files <file del perimetro>`.

Nessuna migrazione. Le corse pgTAP complete e le baseline le lancia Tid.

## Cosa correggi senza chiedere, e cosa no

**Correggi subito** nei file **non applicati** del perimetro: difetti del corpo,
censimenti saltati, `COMMENT` e documentazione rimasti indietro, pgTAP mancanti
o che passano a vuoto, brief non allineato a ciò che il codice fa.

**Dichiara a Tid e aspetta l'ok**:

- qualunque correzione a un changeSet **già applicato** (vuole un changeSet
  nuovo, col suo numero);
- un building block nuovo, un cambio di firma, un oggetto da ritirare;
- un cambio di modello o di perimetro rispetto al brief.

**Non fare, scrivi nel brief**: tutto ciò che ricade su `backend/` o
`frontend/`. Va come richiesta al team, col percorso intero e l'elenco chiuso
di ciò che cambia.

## Chiusura

- **Niente commit**: lo chiede Tid.
- Riepilogo in quattro parti:
  1. **corretto** (file, difetto, prova);
  2. **da decidere** (ciò che aspetta Tid o il team BE/FE);
  3. **non verificato** (ciò che la prova non copre, e perché);
  4. **da lanciare**: i comandi esatti per Tid, nell'ordine (migrazione, pgTAP,
     baseline), con l'esito atteso di ciascuno, così da riportare solo i rossi.
- Se non hai trovato niente, dillo in una riga e di' cosa hai guardato.
- La sessione finisce con la revisione: lavoro nuovo vuole una sessione nuova.
