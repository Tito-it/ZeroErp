# Radici dei namespace i18n — come si individuano e come se ne crea una

> **Tipo**: riferimento di dettaglio · **Stato**: ✅ VIGENTE · **Data**: 2026-07-19
> · **Ambito**: frontend, backend e database — ogni livello che *emette* o
> *consuma* una chiave i18n.
> **La regola vive in** [frontend-standards.md §Multilingua](frontend-standards.md#struttura-chiavi-radici-dei-namespace)
> (lettura obbligatoria di progetto): quella è la fonte canonica. Questo
> documento è il suo **approfondimento** — procedura di classificazione,
> soglia del 70%, inventario — e le è subordinato.

Questo documento spiega **come si decide dove va una radice** esistente o nuova
(la procedura, i casi limite, l'inventario della migrazione 2026-07). La regola
in sé — indirizzo per area, pericolo del testo silenzioso, obbligo lato DB — è
enunciata in `frontend-standards.md §Multilingua`. Non esistono convenzioni
alternative valide altrove.

## 0. Cosa questo documento sostituisce

Fino al 2026-07-19 la convenzione era descritta in due tabelle «Struttura
chiavi» / «Convenzioni chiavi» — in [frontend-standards.md](frontend-standards.md)
§Multilingua e in `work-in-progress/frontend/guida-sviluppo-frontend.md` §10 —
che elencavano `soggetti.*`, `indirizzi.*`, `geo.*`, `amm.*` come «etichette
dominio-specifiche», **sancendo cioè lo stile piatto**, e non nominavano affatto
`vendite.*`, che pure è la radice più popolosa dell'archivio.

Quelle due tabelle sono **superate da questo documento**: descrivevano una
minoranza dell'archivio e omettevano lo stile effettivamente prevalente. Vanno
sostituite da un rimando qui, non lasciate a fianco — finché restano, continuano
a produrre chiavi piatte in buona fede.

**Questo difetto si è già ripetuto almeno tre volte**, sempre nella stessa forma
(DB che emette la chiave senza il prefisso d'area, frontend che non trova nulla e
resta muto): sulle **offerte**, corretto con
`work-done/addendum-db-stati-doc-offerte-transizioni-label-key.md`; sugli
**ordini**, aperto; e in forma latente su ogni modulo elencato nel brief di
migrazione. Le prime due volte è stato riparato il singolo caso senza toccare la
convenzione documentata: è per questo che è tornato.

## 1. Perché la radice conta

Le frasi che l'utente legge non stanno nel codice: stanno in
`frontend/src/locales/{it,en}.json`, e il codice ne conosce solo **l'indirizzo**
(`vendite.ordini.push_commessa_reason.gia_inviato`).

L'indirizzo **non è una faccenda interna al frontend**: è un contratto fra tre
livelli. Il database lo emette (`label_key`, `reason_key` nelle capability e nel
`meta` delle transizioni di stato), il backend lo trasporta senza interpretarlo,
il frontend lo risolve. Le coordinate di un contratto devono voler dire qualcosa
per tutti e tre i firmatari: `vendite.ordini` è uno schema del DB, una cartella
del codice e una voce di menu; `ordini` da solo non distingue le vendite dagli
acquisti.

Se l'indirizzo non esiste, il frontend non mostra un errore: **non mostra
nulla**. Le chiavi sbagliate sono quindi invisibili finché qualcuno non nota il
messaggio mancante — motivo per cui questa regola è accompagnata da un controllo
automatico (§6) e non affidata alla sola disciplina.

## 2. La regola

> **Se una stringa appartiene a un modulo che vive dentro una cartella d'area del
> frontend, il suo indirizzo parte da quell'area. Se è vocabolario trasversale,
> riusato da più aree, resta in cima.**

Le **aree** sono le cartelle di dominio di `frontend/src/`: `vendite`,
`anagrafiche`, `catalogo`, `acquisti`, `magazzino`, `contabilita`, `pagamenti`,
`pratiche`, `documenti`, `config`, `amministrazione`, `portale`, `shop`, `ui`.
Coincidono quasi sempre con gli schemi del database, ma **l'ancora è la
cartella del codice**, non lo schema: `listini` sta in `vendite/` anche se il
catalogo sarebbe plausibile, e `clienti` sta in `anagrafiche/` pur essendo una
lente sui soggetti. Ancorare al codice evita di arbitrare questi casi a tavolino:
la risposta l'ha già data chi ha messo il file dove sta.

**Non** sono aree: `core`, `stores`, `router`, `assets`, `locales`. Chi vive lì
non ha un'area proprietaria per costruzione.

## 3. Procedura di decisione

Per stabilire dove va una radice — nuova o esistente — si contano i file che la
consumano, **escludendo** `core/`, `stores/`, `router/`:

1. **Nessun file di dominio la consuma** (solo `core/` o nessuno)
   → **trasversale**: resta in cima.
2. **Un'area detiene ≥ 70% dei file di dominio**
   → quell'area la **possiede**: l'indirizzo diventa `<area>.<modulo>`.
   Gli usi sparsi nelle altre aree sono *prestiti* e non spostano la proprietà.
3. **Nessuna area raggiunge il 70%**
   → **trasversale**: resta in cima, e va nominata con vocabolario di interfaccia
   (`common`, `errors`, `search`), non con un nome di dominio.
4. **Nessun consumatore, in nessuna area** → radice **morta**: si rimuove, non si
   sposta.

La soglia serve a distinguere il possesso dal prestito, ed è il punto in cui la
regola grezza «conta quante aree la citano» sbaglia. Esempio reale: `contratti` è
citata da tre aree, il che la farebbe sembrare condivisa, ma **8 file su 10**
stanno in `vendite/` — è di vendite, con due prestiti. All'opposto `indirizzi` ha
la maggioranza dei consumatori in `core/` e nessuna area sopra il 70%: è
condivisa davvero.

### Il caso «due indirizzi con lo stesso nome» non è sempre un errore

Coesistono `indirizzi.*` (vocabolario condiviso dell'indirizzo) e
`vendite.indirizzi.*` (indirizzi di un documento di vendita). Applicata la
procedura, **entrambe sono corrette**: la prima è trasversale, la seconda
appartiene a vendite. Prima di «unificare» due nomi uguali, applicare la
procedura a tutte e due.

## 4. Regole di nome

- **La foglia non ripete l'area.** Spostando si toglie il prefisso ridondante:
  `amm_emittenti_fiscali` → `amministrazione.emittenti_fiscali`, non
  `amministrazione.amm_emittenti_fiscali`. Stessa cosa per `ui_admin` → `ui.admin`
  e `config_documenti` → `config.documenti`.
- **Un'area, una radice.** Se esistono più radici per la stessa area
  (`amm`, `amministrazione`, `amm_emittenti_fiscali`), confluiscono in quella
  unica dell'area.
- **Niente abbreviazioni** nella radice: `amministrazione`, non `amm`.
- **Nomi trasversali dal vocabolario di interfaccia**, mai dal dominio: una
  radice in cima che si chiama come un'entità di business è quasi sempre una
  radice di dominio finita nel posto sbagliato.

## 5. Obblighi lato database

Le chiavi emesse dal DB seguono **la stessa regola**, senza deroghe. Riguarda:

- le capability `script.fn_available_actions_*` (`label_key`, `reason_key`);
- il `meta` jsonb delle `config.transizioni_stati_*`, che vive nei seed CSV di
  `80_data` — quindi **una rinomina i18n è anche lavoro DB**, non solo frontend;
- qualunque funzione che restituisca una chiave destinata all'interfaccia.

Due avvertenze operative:

- I codici tecnici che accompagnano una chiave (`reason`, `action_key`,
  `codice_interno`) **non sono chiavi i18n** e non seguono questa regola: non
  vanno rinominati insieme, perché sono contratto verso superfici diverse.
- Per modificare una funzione esistente partire **sempre** dal corpo della doc
  auto-generata in `docs/it/dbzero/<schema>/funzioni/<nome>.md`, mai da uno YAML
  di migration: le revisioni successive lo rendono stale, e una chiave sbagliata
  si propaga per ereditarietà a ogni `CREATE OR REPLACE` successivo. È
  esattamente così che è nato il difetto storico delle reason ordini.

## 6. Controllo automatico

La disciplina non basta, perché una chiave sbagliata è **silenziosa**. Il
controllo minimo che rende l'errore rumoroso:

- **Frontend**: uno script che estrae tutte le chiavi citate nel codice e tutte
  quelle presenti nei locales, e fallisce se una citata non esiste (chiave morta
  in emissione) o se una radice di dominio compare in cima violando §3.
- **Database**: un pgTAP che asserisca il prefisso delle chiavi emesse dalle
  capability — es. che `can_push_commessa_reason_key` di un ordine inizi per
  `vendite.ordini.`. Costa poco e blocca la propagazione per ereditarietà al
  primo copia-incolla sbagliato.

## 7. In pratica: dove metto una stringa nuova?

- Il componente sta in `frontend/src/<area>/...` e la stringa parla di quel
  dominio → `<area>.<modulo>.<foglia>`.
- Il componente sta in `core/` o la stringa serve a più aree → radice
  trasversale esistente (`common`, `errors`, `validation`, `actions`,
  `confirm`, `nav`, `pagination`, `search`, `tabs`, `placeholder`).
- **Non creare** una radice nuova in cima senza aver applicato §3: nella
  stragrande maggioranza dei casi la risposta giusta è una sottochiave di
  un'area già esistente.

## 8. Riferimenti

- Standard frontend: [frontend-standards.md](frontend-standards.md)
- Migrazione in corso verso questo standard:
  [brief-i18n-radici-uniformi.md](../work-done/brief-i18n-radici-uniformi.md)
- Locales: `frontend/src/locales/{it,en}.json`
