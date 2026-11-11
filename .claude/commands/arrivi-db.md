---
description: Il team DB ha fatto il push — allinea il branch e dimmi quali attività BE/FE si sono sbloccate
argument-hint: "[brief o branch da guardare — vuoto = tutto ciò che è arrivato]"
---

Il team DB ha fatto il push. Allinea il branch di lavoro e dimmi quali attività
BE/FE sono arrivate o si sono sbloccate.

Indicazioni di Tid per questo giro (possono essere vuote): $ARGUMENTS

## 1. Cosa è arrivato

- `git status --short` prima di tutto: segna ciò che è già modificato in locale.
- `git fetch --all --prune`, poi per ogni branch remoto avanti rispetto a HEAD
  (di norma `origin/dev/db-tid`, `origin/Tito-dev`, `origin/main`) elenca i
  commit che mancano.
- Se non manca niente, dillo e fermati.

## 2. Allineamento

- Verifica se è un fast forward (`git merge-base --is-ancestor HEAD <branch>`).
- **Fast forward e working tree pulito**: eseguilo.
- **Working tree sporco, oppure non è un fast forward**: non toccare niente.
  Mostra a Tid i file locali che l'arrivo modifica anche lui (i brief in
  `work-in-progress/` sono il caso tipico), proponi come procedere (stash dei
  soli file in conflitto, merge, rebase) e **aspetta l'ok**.
- Dopo l'allineamento: nessun marcatore di conflitto rimasto, e niente di ciò
  che era in locale è andato perso. Uno stash fatto da te lo riapplichi e lo
  chiudi tu.

## 3. Cosa chiede al BE/FE

- Dei brief toccati dall'arrivo (`docs/it/dev/work-in-progress/brief-*`) leggi
  il **diff** e le sezioni rivolte al BE/FE, non il brief intero.
- Per ogni attività verifica che il prerequisito DB sia davvero applicato,
  sulla doc auto-generata in `docs/it/dbzero/` (mai dagli YAML di migration).
  Un'attività col prerequisito non pronto si elenca come **in attesa**, non si
  comincia.
- Cerca i percorsi che l'arrivo ha **rotto**: funzioni rinominate, parametri o
  chiavi cambiati, colonne tolte, codici errore nuovi. Si verificano sul codice
  che li chiama, con una chiamata reale o un `EXPLAIN` sul DB vero: i test con
  i mock non vedono un binding per nome.
- Un codice errore nuovo vuole la policy generata **e** il messaggio di
  ripiego. `error_policies_generated.py` non si rigenera se il DB è avanti
  rispetto a git.

## 4. Esito, poi aspetta

Riporta a Tid, senza cominciare lo sviluppo:

1. **Rotto adesso** su dbdev, da fare per primo;
2. **Attività sbloccate**, con la sigla del brief (BE…, FE…), cosa chiedono e i
   file coinvolti;
3. **In attesa** di un prerequisito DB, e quale;
4. **Domande aperte** per Tid o per il team DB;
5. l'ordine che proponi.

Lo sviluppo parte solo con l'ok di Tid. Nessuna azione sul DB, nessun commit.
