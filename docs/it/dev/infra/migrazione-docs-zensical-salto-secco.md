# Piano Salto Secco Documentazione (MkDocs -> Zensical)

Data piano: 2026-03-04
Obiettivo: migrare alla piattaforma docs piu` recente senza mantenere processi legacy in parallelo oltre il tempo minimo tecnico.

## Premesse operative

- Base attuale: `mkdocs==1.6.1`, `mkdocs-material==9.7.3`.
- Uso intensivo di include: circa 1562 occorrenze `include-markdown`.
- Documentazione ampia: circa 1450 file sotto `docs/`.
- Stato link attuale non pulito: nel build corrente emergono molti warning su link/nav.

## Stima complessiva

- Best case: 5 giorni uomo.
- Caso medio: 8-10 giorni uomo.
- Worst case (plugin incompatibili): 13-20 giorni uomo.

## Task 1 - Baseline e freeze (0.5-1 giorno)

Scopo: bloccare lo stato iniziale e fissare metriche di confronto.

Attivita`:
- congelare versioni docs-tooling nel lock corrente;
- eseguire build baseline;
- salvare report warning/error come artefatto.

Comandi:

```bash
source .venv/bin/activate
mkdocs build > .tmp.docs.baseline.log 2>&1
rg -n "WARNING|ERROR|unrecognized relative link|not found in the documentation files" .tmp.docs.baseline.log
```

Criterio uscita:
- baseline ripetibile con stesso output a parita` di commit.

## Task 2 - PoC su Zensical (1-2 giorni)

Scopo: verificare compatibilita` reale del progetto con il nuovo motore.

Attivita`:
- installazione toolchain Zensical in ambiente isolato;
- migrazione configurazione minima (`mkdocs.yml` -> config equivalente);
- primo build completo.

Criterio uscita:
- build completa terminata;
- elenco gap classificato: blocker / warning / cosmetico.

## Task 3 - Compatibilita` plugin e include (1-3 giorni)

Scopo: chiudere i gap che impattano il rendering o la struttura.

Focus principali:
- `include-markdown` (bloccante se incompatibile);
- i18n;
- rewrite link relativi.

Strategia:
- preferire compat layer nativo;
- se non basta, sostituire plugin con preprocess script deterministici in `scripts/`.

Criterio uscita:
- nessun blocker su include e navigazione multilingua.

## Task 4 - Link hygiene e nav hardening (2-4 giorni)

Scopo: rendere i contenuti pubblicabili senza rotture di navigazione.

Attivita`:
- correzione link relativi non riconosciuti;
- allineamento `nav` con file reali;
- eliminazione warning critici.

Comandi utili:

```bash
source .venv/bin/activate
# Eseguire con il comando build del nuovo motore
<build-command> > .tmp.docs.new.log 2>&1
rg -n "unrecognized relative link|not found in the documentation files|ERROR" .tmp.docs.new.log
```

Criterio uscita:
- zero error;
- warning residui solo non bloccanti e documentati.

## Task 5 - Cutover secco e CI (1-2 giorni)

Scopo: passare definitivamente al nuovo motore senza doppio binario stabile.

Attivita`:
- sostituire comando docs in CI/CD;
- aggiornare runbook team (`docs serve/build`);
- rimuovere dipendenze obsolete;
- definire rollback tecnico a un commit precedente (non doppio processo).

Criterio uscita:
- CI verde su branch di integrazione;
- deploy docs effettuato;
- lock dipendenze finale allineato.

## Go / No-Go

Go:
- include equivalenti funzionanti;
- nav e i18n completi;
- link critici risolti;
- pipeline CI stabile.

No-Go:
- include non migrabili senza riscrivere centinaia di file;
- regressioni strutturali su nav/i18n non chiudibili nei tempi.

## Risposte sintetiche alle domande chiave

- Il Markdown attuale e` in gran parte riusabile: si`.
- I link attuali sono tutti supportati automaticamente: no, gia` oggi ci sono molte anomalie da sanare.
- Salto secco fattibile: si`, con rischio concentrato su plugin/include e quality pass dei link.

## Deliverable attesi

- report baseline e report post-migrazione;
- lista gap chiusi + gap accettati;
- config docs finale;
- checklist operativa di manutenzione minima.

