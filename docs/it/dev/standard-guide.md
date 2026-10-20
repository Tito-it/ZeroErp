# Standard delle guide — checklist di revisione

> **Ultimo aggiornamento**: 19 settembre 2026
>
> **Destinatari**: chiunque scriva o riveda una guida in `docs/it/guide/` (persone o agenti).
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
* Il footer `{% include-markdown "signature-core.md" %}` lo appende `scripts/apply_signatures.py`:
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
  standard dei manuali (Scopo, Contesto, … Note di migrazione): lì la provenance di un oggetto è
  contenuto legittimo, non changelog.

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

## Le altre pagine: `manual/` e doc auto-generata

* Le pagine sotto `/dbzero/<schema>/tabelle`, `/views`, `/funzioni` sono **auto-generate**
  (`scripts/gen_db_docs.py`): si leggono, non si modificano. Si scrive solo in
  `<schema>/manual`.
* Le pagine `manual/` del **backend** (Django) seguono una struttura fissa: Scopo, Contesto,
  Input, Output, Regole, Dipendenze DB, Note di migrazione (se applicabile). Template:
  `docs/it/backend/_templates/manual-standard.md`.

## Build e anteprima

* Stack: `zensical` (con `deepmerge`), versioni in `requirements.txt`. `mkdocs build` non è
  più il comando di progetto.
* Build: `python scripts/build_docs_zensical.py` — preprocessa `docs/` in `.tmp/zensical_docs`,
  espande gli `include-markdown`, riscrive i link `](/dbzero/...)` in `](/it/dbzero/...)`,
  genera `mkdocs.zensical.yml` e produce `site-zensical/`.
* Anteprima: `bash scripts/serve_docs.sh` — build più server statico su `127.0.0.1:8010`,
  scrive solo in `/tmp/zeroerp-docs-preview`.
* Se un markdown documenta la sintassi di include come esempio, il segnaposto va in un blocco
  di codice, o il preprocess emette un warning.

## Verifica finale

1. Nel **corpo** della guida, `grep -n '^```'` → solo blocchi `text` e `mermaid`. Gli esempi
   eseguibili stanno in coda, nell'area tecnica.
2. `grep -n '<nome_ritirato>' <guida>` → zero occorrenze, tranne la nota storica.
3. La guida non contiene più `latest review`: l'header è nel formato nuovo.
4. Ogni link nuovo: il file di destinazione esiste sotto `docs/`.
5. Build locale a cura del manutentore della doc.
