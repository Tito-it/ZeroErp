# Standard delle guide — checklist di revisione

> **Ultimo aggiornamento**: 12 novembre 2026
>
> **Destinatari**: chiunque scriva o riveda una guida in `docs/it/guide/` o una pagina
> `docs/it/dbzero/<schema>/manual/` (persone o agenti).
>
> **Vedi anche** — regole:
>
> * `.codex/AGENTS.md`, sezione «Documentazione» — la regola in forma breve; il dettaglio è qui
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — esempio di guida che possiede il dettaglio di una materia

---

## La regola in una riga

Una guida descrive **lo stato attuale** del sistema: il cambiamento si integra nella sezione
che parla di quella cosa, oppure diventa una sezione nuova. Non si racconta, si descrive.

## Header da copiare

```markdown
# Guida — <Titolo>

> **Ultimo aggiornamento**: <giorno> <mese> <anno>   (es. 19 settembre 2026)
>
> **Destinatari**: <chi legge>
>
> **Vedi anche** — schemi DB:
>
> * [schema.tabella](/dbzero/schema/tabelle/tabella) — <cosa rappresenta, in mezza riga>
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [schema.fn_nome](/dbzero/schema/funzioni/fn_nome) — <cosa fa, in mezza riga>
>
> **Vedi anche** — API e service backend:
>
> * [API Nome](/backend/schema/manual/api_nome) — <cosa espone>
>
> **Vedi anche** — guide correlate:
>
> * [Altra guida](/guide/altra-guida)

---
```

Note:

* L'header **contiene la lista delle tabelle**: non esiste più una sezione `## Tabelle coinvolte`.
* Il `---` separa l'header dal primo `##`.
* I blocchi vuoti si omettono: si tengono solo quelli che hanno contenuto.
* Il footer (l'include di `signature-core.md`) lo appende `scripts/apply_signatures.py`:
  non serve scriverlo a mano, ma non va rimosso.

## Checklist di revisione

Da fare **in quest'ordine**, su una guida esistente.

1. **Inventario dei residui.** Cerca in testa e nel corpo: blocchi `> **…**` di stato/storicizzazione,
   `latest review` con descrizione, catene di «revisione precedente», id di migrazione
   (`90_end/2026…`), parole come «decisione di», «dal `<data>`», «non esiste più».
2. **Dove sta la verità.** Verifica ogni affermazione tecnica sul **modello**, non sulla memoria:
   `db/changelog/migrations_v2/` per gli oggetti, `docs/it/dbzero/…` (auto-generata) per firme e
   colonne, `db/pgtap/…` per il comportamento presidiato. Un nome di funzione o di trigger si
   controlla sempre: sono la cosa che invecchia più in fretta.
3. **Dissolvi il changelog.** Per ogni riga trovata al punto 1: entra nella sezione del tema,
   diventa sezione nuova, o si cancella. Scendi a **una sola nota breve** se serve a capire il
   resto, senza date e senza attribuzioni.
4. **Allinea il corpo.** Nomi di tabelle, funzioni, trigger, campi, catene di join, diagrammi ER,
   tabelle di trigger, best practice. Questo è il grosso del lavoro e non si salta: un blocco in
   testa aggiornato su un corpo vecchio fa una guida che si contraddice.
5. **Sposta gli esempi.** Ogni esempio va nell'`## Area tecnica — esempi` in coda oppure diventa un
   link — vedi il criterio qui sotto.
6. **Snellisci le sezioni «di sistema».** Impianto, connessioni, infrastruttura: si tiene il
   contratto e i punti di attenzione, il dettaglio resta nella guida che lo possiede.
7. **Header.** Applica il formato qui sopra; la data è quella della revisione, non quella della
   fondazione della guida.
8. **Verifica.** Vedi in fondo.

## I tre residui tipici, e cosa farne

| Residuo                                                                          | Cosa farne                                                                                                                              |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Blocco changelog / storicizzazione in testa**                                  | Dissolto: il contenuto vivo entra nelle sezioni, il resto si cancella. La tabella «legacy → nuovo» è changelog: non diventa una sezione |
| **Esempio nel corpo** (SQL, JSON, bash, .ini, python)                            | Spostato nell'`## Area tecnica — esempi`, oppure (se descrive un oggetto) sostituito da un link alla scheda `/dbzero/...`               |
| **Contratto ricopiato** (firma di funzione, elenco colonne, corpo di un trigger) | Cancellato e sostituito dal link. La doc auto-generata è la fonte, e si aggiorna da sola                                                |

## `## Area tecnica — esempi`

Sta in coda, subito prima dell'include finale. Ogni esempio ha **una riga di scopo** sopra, che
dice a cosa serve — non cosa fa il comando.

Criterio con una domanda sola:

| L'esempio risponde a…                                 | Dove                           |
| ----------------------------------------------------- | ------------------------------ |
| «che cos'è / qual è la firma / cosa fa quell'oggetto» | link alla scheda `/dbzero/...` |
| «come faccio X» (comando, diagnosi, configurazione)   | `## Area tecnica — esempi`     |

⛔ Dentro l'area tecnica **non** entrano:

* copie di contratti già auto-generati (firme, colonne, corpi di funzione);
* DDL di oggetti che esistono già — al massimo la ricetta per crearne uno nuovo, con il link
  alla scheda della funzione-guard;
* codice di cose non ancora implementate: se non esiste, non si documenta un'astrazione per
  uno scenario ipotetico.

✅ Restano nel corpo narrativo: i flussi in blocchi `text` e i diagrammi `mermaid`. Spiegano,
non si eseguono.

## Cosa NON si converte

* **Pseudo-SQL normativo.** In `pgtap-come-si-scrive-un-test.md` i blocchi non sono esempi
  eseguibili: definiscono una sintassi leggibile da un cancello automatico. Restano dove sono.
* **Documenti di registrazione storica.** Tutto ciò che sta in `docs/it/dev/work-done/` e
  `docs/it/dev/work-in-progress/` **non si tocca**: è il verbale di quello che è stato deciso e
  fatto, ed è giusto che porti date e id di migrazione.
* **Note di migrazione nei `manual/`.** Le pagine `docs/it/dbzero/<schema>/manual/` seguono lo
  [standard delle pagine `manual/` del database](#le-pagine-manual-del-database): lì la
  provenienza di un oggetto è contenuto legittimo, ma ha **una** sezione sua in coda, non è
  sparsa nel corpo.

## Trappole note

* **Anchor linkati da fuori.** Prima di rinominare o rimuovere una sezione, cerca il suo anchor:
  `automazione-db.md` è linkato per anchor da `docs/it/tutorial/framework-automazione-db.md`.
* **Indici generati.** `index.md` e `index.ci.md` sotto `docs/it/dbzero/` sono prodotti da
  `scripts/gen_db_docs.py`: se si cancella o si sposta una pagina `manual/`, l'elenco si allinea
  alla **prossima rigenerazione**. Non si edita a mano.
* **Un link morto è peggio di nessun link.** Un rimando a una pagina cancellata — tipicamente la
  scheda di un oggetto ritirato — va tolto o ripuntato all'oggetto che ha preso il posto. Per
  trovarli: `grep -rn "views/<nome_ritirato>" docs/`.
* **La pagina del successore.** Quando un oggetto viene ritirato, la spiegazione del ritiro va nel
  `manual/` dell'oggetto che lo ha sostituito, non in un blocco in testa alla guida.
* ⛔ **La pagina `manual/` di un oggetto ritirato si cancella**, nello stesso lavoro che lo ritira:
  non si lascia una pagina che spiega dov'è finito. L'indice dello schema si genera scansionando
  `manual/`, e una pagina rimasta continua a pubblicizzare un oggetto che non esiste. «Si marca, non
  si cancella» vale per i documenti di registrazione storica, non per `manual/`.
* **Un debito documentale è saldato solo se il file lo dice.** Prima di dichiararlo fatto si cerca
  nel documento la frase che doveva entrare e si guarda la data di revisione. Una guida lunga si
  aggiorna in **ogni** punto che parla della cosa (tabelle d'esempio, riepiloghi, checklist). Chi
  chiude un lavoro che ha ereditato debito documentale da un altro lo evade o lo restituisce.

## Le altre pagine: `manual/` e doc auto-generata

* Le pagine sotto `/dbzero/<schema>/tabelle`, `/views`, `/funzioni` sono **auto-generate**
  (`scripts/gen_db_docs.py`): si leggono, non si modificano. Si scrive solo in
  `<schema>/manual`.
* Le pagine `manual/` del **database** seguono lo standard della sezione qui sotto.
* Le pagine `manual/` del **backend** (Django) seguono una struttura fissa: Scopo, Contesto,
  Input, Output, Regole, Dipendenze DB, Note di migrazione (se applicabile). Template:
  `docs/it/backend/_templates/manual-standard.md`.

## Le pagine `manual/` del database

Una pagina `docs/it/dbzero/<schema>/manual/<nome>.md` racconta **il significato** di un
oggetto: perché esiste, che regola regge, che cosa non fa. Il **contratto** (colonne, firma,
vincoli, corpo, trigger agganciati) lo scrive la doc auto-generata, che include questa pagina
in testa alla propria: la pagina `manual/` non lo ricopia.

⛔ **In una pagina `manual/` non compare codice**: né SQL, né JSON, né frammenti di script,
né esempi di chiamata, nemmeno in un'area esempi in coda. La pagina contiene solo concetti e
spiegazioni. Chi deve leggere il codice ha tutto il sorgente nella doc auto-generata, nella
stessa scheda. Restano ammessi i **nomi** degli oggetti, delle colonne e dei codici errore,
scritti come codice inline, e i diagrammi che spiegano un flusso (`text`, `mermaid`).

La pagina ha una **cornice fissa** e un **corpo libero**. La cornice è la stessa per tabelle,
viste, funzioni, trigger e procedure; il corpo si organizza per temi, e i titoli delle sezioni
dicono la cosa, non la categoria.

### La cornice da copiare

```markdown
## 📘 Documentazione Concettuale – <Tipo> `<schema>.<nome>`

> **Ultimo aggiornamento**: <giorno> <mese> <anno>
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [schema.tabella](/dbzero/schema/tabelle/tabella) — <che ruolo ha qui, in mezza riga>
>
> Approfondimento viste:
>
> * [schema.vw_nome](/dbzero/schema/views/vw_nome) — <…>
>
> Approfondimento funzioni:
>
> * [schema.fn_nome](/dbzero/schema/funzioni/fn_nome) — <…>
>
> Guide:
>
> * [Titolo della guida](/guide/nome-guida) — <…>

---

### 🎯 Scopo Principale

<Un paragrafo: che cos'è l'oggetto o che cosa fa, nello stato di oggi.>

<Altri paragrafi, se servono.>

---

### <Primo tema>

…

---

### Codici errore

---

### Test

---

### Note di migrazione

---

<firma: l'include di signature-core.md, su una riga sua>
```

### Le regole della cornice

| Elemento | Regola | Perché |
| --- | --- | --- |
| **Titolo** | Un solo `##` per pagina. `<Tipo>` è uno fra `Tabella`, `Vista`, `Funzione`, `Trigger function`, `Procedura`. Il nome è qualificato con lo schema, senza `()` | Le sezioni sono tutte `###`: un secondo `##` spezza la pagina in due nella navigazione |
| **Ultimo aggiornamento** | Prima riga del blocco in testa, aggiornata a ogni modifica, anche piccola | È l'unica data della pagina: dice da quanto non viene rivista |
| **Vedi anche** | Un blocco citazione unico: **ogni** riga comincia con `>` seguito da uno spazio, comprese le etichette e le righe vuote. Le etichette sono le quattro della cornice, in quell'ordine, e un'etichetta senza link si omette. I link sono elenchi `*`, uno per riga | Una riga senza `>` chiude la citazione: il blocco esce in pezzi staccati |
| **Destinazione dei link** | La scheda dell'oggetto (`/dbzero/<schema>/tabelle\|views\|funzioni/<nome>`), non la sua pagina `manual/`. Le guide con `/guide/…`, le linee guida con la loro pagina e l'anchor | La scheda contiene già la pagina `manual/` più il contratto: chi la apre ha tutto |
| **Scopo Principale** | Si chiama esattamente `### 🎯 Scopo Principale` e c'è in **ogni** pagina. Il **primo paragrafo** è la descrizione dell'oggetto in una o due frasi, senza marcatori di revisione | `scripts/gen_db_docs.py` cerca questo titolo e copia il primo paragrafo nell'indice dello schema: un `(rev …)` lì diventa la descrizione dell'oggetto nell'indice |
| **Separatori** | `---` fra il blocco in testa e lo Scopo, fra una sezione e l'altra, e prima della firma | — |
| **Firma** | L'include di `signature-core.md` in fondo, su una riga sua, scritto a mano: la riga si copia dal fondo di una pagina `manual/` esistente | `scripts/apply_signatures.py` salta le cartelle `manual/`: lì la firma non la aggiunge nessuno |

### Il corpo

* **Sezioni per tema.** Il titolo di una sezione dice la regola o il fatto («La chiave è
  (articolo, codice)», «Un ledger non si spegne: si storna»), non una categoria generica.
  I segni `⭐` (perché è fatto così), `⚠️` (punto d'attenzione) e `⛔` (che cosa non si fa) si
  usano in testa al titolo quando aiutano chi legge.
* **Sezioni ricorrenti in coda**, nell'ordine della cornice, quando hanno contenuto:
  * `### Codici errore`: i codici che l'oggetto solleva e quando li solleva. Il testo del
    messaggio sta in `config.messaggi_errore`, e qui non si ricopia;
  * `### Test`: i file pgTAP che presidiano l'oggetto e che cosa provano;
  * `### Note di migrazione`: vedi sotto.
* **Che cosa non entra nel corpo** (le stesse regole delle guide, applicate alla scheda):

| Residuo | Cosa farne |
| --- | --- |
| Firma, elenco di parametri e tipi, valore di ritorno, elenco delle colonne, DDL, corpo di una funzione, elenco dei trigger agganciati | Si cancella: lo scrive la doc auto-generata nella stessa pagina. Resta il **significato** di un parametro o di una colonna, quando non si capisce dal nome |
| Marcatori di revisione nel testo: `(rev …)`, `(latest review …)`, titoli come «🔄 rev 19-10-2026 — …», «Dal 18-09 (Lotto 2)», frasi come «Dal 15 settembre 2026 la tabella…» | Il contenuto vivo entra nella sezione del tema, scritto al presente. La data va in «Ultimo aggiornamento». La provenienza, se serve, va in «Note di migrazione» |
| Nomi di brief, di lotti, di analisi (`brief-db-…`, «Lotto 2», «M-1 → M-8») nel corpo o nel «Vedi anche» | Si tolgono: il lettore della scheda vuole la regola, non il cantiere che l'ha prodotta. Restano, se servono, in «Note di migrazione» |
| Codice di qualsiasi tipo: esempi di chiamata, query, payload JSON, frammenti del corpo, pseudo-SQL | Si cancella. Se l'esempio spiegava una regola, la regola si scrive a parole nella sezione del tema. A differenza delle guide, qui non c'è un'area esempi: il sorgente è nella stessa scheda |
| «Vantaggi operativi», «Best practice» generiche | Si tolgono, oppure diventano un tema con un titolo che dice la cosa |

### Note di migrazione

È l'**unico** posto della pagina in cui stanno date, nomi di brief e provenienza. È facoltativa,
e serve solo a chi deve capire perché l'oggetto ha la forma che ha: che cosa ha sostituito, un
nome che aveva prima, una regola che è cambiata e perché.

* Un punto per fatto, con la data in testa: «2026-09-18 — prende il posto di `reservations`, …».
* Niente id di changeSet: il file si trova da `git log -S`, e un id ricopiato non dice niente
  a chi legge.
* Un fatto che serve a capire il presente («il nome vecchio compare ancora nei log») si scrive
  nel corpo, al presente; qui resta solo la provenienza.

### Blocchi comuni di uno schema

Un testo che vale per tutte le pagine di uno schema (lo stato del dominio, la spiegazione di
una famiglia di partizioni) sta in **un** file `docs/it/dbzero/<schema>/_<nome>.md`, e ogni
pagina lo include con un `include-markdown` su una riga sua, col percorso `it/dbzero/<schema>/_<nome>.md`,
prima della firma.

⚠️ **In un documento che spiega gli include non si scrive mai il tag letterale**, nemmeno nel
codice inline o in un blocco di codice: `scripts/build_docs_zensical.py` espande ogni tag che
trova, senza riconoscere il codice. Un tag con un percorso segnaposto non si risolve, resta nel
testo, e zensical ferma la build («include-markdown tags must be on their own lines»).

* Il blocco descrive lo stato attuale come una guida: ha la sua riga «Ultimo aggiornamento» e
  si rivede quando cambia lo schema, non quando cambia una pagina.
* Una pagina che è **solo** un include (le partizioni delle note) ha comunque cornice e Scopo:
  una riga che dice che cos'è, così l'indice dello schema ha una descrizione.

### Verifica di una pagina `manual/`

1. `grep -nE '^(Approfondimento|Guide)' <pagina>` → zero righe: tutte le etichette cominciano con `>`.
2. `grep -n '^### 🎯 Scopo Principale' <pagina>` → una riga, e la riga di testo che la segue
   non comincia con `(`.
3. `grep -nE '\(rev |latest review|brief-' <pagina>` → solo dentro «Note di migrazione».
4. `grep -c '^## ' <pagina>` → `1`.
5. In fondo c'è `signature-core.md`, e ogni link `/dbzero/…` punta a un file che esiste.
6. `grep -n '^```' <pagina>` → solo blocchi `text` e `mermaid`.

## Build e anteprima

* Stack: `zensical` (con `deepmerge`), versioni in `requirements.txt`. `mkdocs build` non è
  più il comando di progetto.
* Build: `python scripts/build_docs_zensical.py` — preprocessa `docs/` in `.tmp/zensical_docs`,
  espande gli `include-markdown`, riscrive i link `](/dbzero/...)` in `](/it/dbzero/...)`,
  genera `mkdocs.zensical.yml` e produce `site-zensical/`.
* Anteprima: `bash scripts/serve_docs.sh` — build più server statico su `127.0.0.1:8010`,
  scrive solo in `/tmp/zeroerp-docs-preview`.
* Un markdown che documenta la sintassi di include **non scrive il tag letterale**, nemmeno in
  un blocco di codice: il preprocess lo espande comunque, e un tag che non si risolve ferma la
  build. Si descrive a parole («l'include di `signature-core.md`»), come nella
  [cornice delle pagine `manual/`](#blocchi-comuni-di-uno-schema).

## Verifica finale

1. Nel **corpo** della guida, `grep -n '^```'` → solo blocchi `text` e `mermaid`. Gli esempi
   eseguibili stanno in coda, nell'area tecnica.
2. `grep -n '<nome_ritirato>' <guida>` → zero occorrenze, tranne la nota storica.
3. La guida non contiene più `latest review`: l'header è nel formato nuovo.
4. Ogni link nuovo: il file di destinazione esiste sotto `docs/`.
5. Build locale a cura del manutentore della doc.
