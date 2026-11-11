---
description: Verifica critica del codice modificato — cerca e corregge bug, codice fragile, duplicato, hardcoded
argument-hint: "[perimetro: un path, un commit o un intervallo — vuoto = codice non committato]"
---

Fai una verifica critica del codice modificato: cerca e correggi bug, codice
fragile, codice duplicato, valori hardcoded.

Indicazioni di Tid per questo giro (possono essere vuote): $ARGUMENTS

## Perimetro

- Senza indicazioni il perimetro è il **codice non committato**: file modificati
  e file nuovi (`git status --short`, `git diff HEAD`, più il contenuto dei file
  non tracciati). Se Tid ha indicato un path, un commit o un intervallo, il
  perimetro è quello.
- Se il working tree è pulito e Tid non ha indicato niente, dillo e fermati: non
  scegliere tu un perimetro.
- Il diff è il punto di partenza, non il confine della lettura: di ogni funzione
  toccata leggi i chiamanti e i punti vicini che fanno la stessa cosa. I difetti
  stanno spesso nel codice **attorno** al diff, rimasto alla regola di prima.
- Questa è una sessione di revisione: non conosci le ragioni di chi ha scritto
  il codice, ed è il suo valore. Se serve il contesto, lo dà il brief in
  `docs/it/dev/work-in-progress/` che il diff aggiorna.

## Un'altra sessione sullo stesso working tree

Prendi `git status --short` all'inizio e riprendilo prima di ogni correzione e
alla fine. Se cambiano file che non hai toccato tu, un'altra sessione sta ancora
scrivendo: fermati, di' a Tid quali file si sono mossi e aspetta. Non si rivede
un bersaglio che si muove, e non si toccano i file dell'altra sessione.

## Cosa cercare

1. **Bug**: logica sbagliata, rami non gestiti che il modello ammette (una
   colonna nullable è un caso anche se oggi non ha righe), errori del DB non
   tradotti che escono come 500, nomi di parametri o chiavi non allineati al
   contratto del DB, contratti dichiarati (OpenAPI, docstring, whitelist) che
   non corrispondono a ciò che il codice fa.
2. **Codice fragile**: `assert` al posto di un controllo, eccezioni inghiottite,
   dipendenza dall'ordine o dai dati di oggi, test verdi perché i dati non
   sanno produrre il caso.
3. **Duplicato**: prima leggi i due indici dei building block (CLAUDE.md). Una
   logica che esiste già come BB va sostituita con il BB. Una seconda copia
   senza BB è un caso di regola del 2.
4. **Hardcoded**: ID numerici, codici, testi per l'utente fuori da i18n, valori
   che hanno già una sede (config, costanti, lookup per codice).

Valgono le regole di `.codex/AGENTS.md`, a partire dalla regola zero: un
difetto si giudica sul modello, non su quante righe oggi lo attraversano.

## Cosa correggi senza chiedere, e cosa no

**Correggi subito**, con il suo test quando il difetto è di comportamento:
- bug e fragilità dentro il perimetro;
- sostituzione di una copia con un building block che esiste già;
- valori hardcoded che hanno già una sede;
- documentazione, catalogo BB (e indice rigenerato) e brief rimasti indietro
  rispetto al codice del perimetro.

**Dichiara a Tid e aspetta l'ok**:
- estrazione di un building block nuovo (regola del 2);
- cambio di una firma pubblica o di un contratto con chiamanti fuori dal
  perimetro;
- cancellazioni e dipendenze nuove.

**Non fare, scrivi nel brief**: tutto ciò che richiede una modifica al DB. Va
come richiesta al team DB; nessun ripiego lato BE/FE nell'attesa.

## Verifica

- Rilancia i test dei moduli toccati (quelli sul DB vero compresi) e ruff sui
  file Python toccati; per il frontend gli spec dei componenti toccati e i
  controlli i18n e classi morte.
- Un bug corretto ha un test che diventa rosso se rimetti il codice di prima:
  provalo, non darlo per fatto.
- Riporta l'esito com'è: ciò che è rosso, ciò che non hai potuto lanciare e
  perché.

## Chiusura

- **Niente commit**: lo chiede Tid.
- Riepilogo in tre parti: **corretto** (file, difetto, test), **da decidere**
  (ciò che aspetta l'ok di Tid o del team DB), **non verificato** (ciò che non
  hai potuto provare). Se non hai trovato niente, dillo in una riga e di' cosa
  hai guardato.
- La sessione finisce con la revisione. Se Tid chiede lavoro nuovo (un altro
  push del DB, un altro brief), ricordagli che conviene una sessione nuova: la
  prossima revisione deve arrivare a mente fredda.
