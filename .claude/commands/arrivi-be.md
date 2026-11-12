---
description: Il team BE/FE ha fatto il push — allinea il branch e dimmi cosa chiede al team DB
argument-hint: "[brief o branch da guardare — vuoto = tutto ciò che è arrivato]"
---

Il team BE/FE ha fatto il push. Allinea il branch di lavoro e dimmi quali
richieste al team DB sono arrivate, quali si sono chiuse e cosa si è sbloccato.

Indicazioni di Tid per questo giro (possono essere vuote): $ARGUMENTS

## 1. Cosa è arrivato

- `git status --short` prima di tutto: segna ciò che è già modificato in locale.
- `git fetch --all --prune`, poi per ogni branch remoto avanti rispetto a HEAD
  (di norma `origin/dev/backend-tid`, `origin/Tito-dev`, `origin/main`) elenca i
  commit che mancano.
- Se non manca niente, dillo e fermati.

## 2. Allineamento

- Verifica se è un fast forward (`git merge-base --is-ancestor HEAD <branch>`).
- **Fast forward e working tree pulito**: eseguilo.
- **Working tree sporco, oppure non è un fast forward**: non toccare niente.
  Mostra a Tid i file locali che l'arrivo modifica anche lui (i brief in
  `work-in-progress/` sono il caso tipico), proponi come procedere (merge o
  rebase) e **aspetta l'ok**. Niente `git stash`: l'albero può essere condiviso
  con un'altra sessione.
- Dopo l'allineamento: nessun marcatore di conflitto rimasto, niente di ciò che
  era in locale è andato perso.
- Se l'arrivo porta file sotto `db/changelog/` (un'altra sessione DB), rilancia
  `scripts/prossimo_changeset.py`: i numeri liberi di prima non valgono più.

## 3. Cosa chiede al team DB

- Dei brief toccati dall'arrivo (`docs/it/dev/work-in-progress/`) leggi il
  **diff** e le sezioni rivolte al team DB, non il brief intero. Guarda anche il
  blocco «⏭️ Chi riparte» e le voci «team DB» di
  `docs/it/dev/work-in-progress/registro-residui-aperti.md`.
- Per ogni richiesta:
  - cerca i **brief vicini** in `work-in-progress/` (un tema, un brief): se uno
    copre già il tema, la richiesta va lì;
  - se chiede un cambio di **modello**, cerca la decisione esistente (`work-done/`,
    guide, `git log -S`) e di' se la richiesta è nuova, ne completa una o ne
    revoca una, con la data;
  - leggi lo stato attuale degli oggetti nominati sulla doc auto-generata
    (`docs/it/dbzero/`), mai dagli YAML;
  - giudicala sul modello (regola zero): «oggi non capita» non la chiude e
    «capita spesso» non la apre.
- Cerca ciò che l'arrivo **chiude**: una richiesta DB consumata dal BE, un
  ripiego ritirato, un'esenzione che non serve più. Un brief che non aspetta più
  nessuno si può archiviare: dillo, non spostarlo.

## 4. Esito, poi aspetta

Riporta a Tid, senza cominciare lo sviluppo:

1. **Richieste nuove al team DB**, con la sigla del brief, cosa chiedono, gli
   oggetti coinvolti e i brief vicini trovati;
2. **Chiuse dall'arrivo**, e quali brief possono essere archiviati;
3. **Domande aperte** per Tid o per il team BE/FE;
4. l'ordine che proponi.

Lo sviluppo parte solo con l'ok di Tid. Nessuna migrazione, nessun commit.
