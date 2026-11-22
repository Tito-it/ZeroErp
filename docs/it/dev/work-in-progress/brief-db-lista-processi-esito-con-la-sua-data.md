# Brief DB — Lista processi: la colonna «Esito» con la sua data

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Riparte: team DB** (`dev/db-tid`). Il lato BE/FE è già fatto (§2); manca il catalogo della lista (§3).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Le corse della lista nella forma unica, `ultimo_ok` tenuto come ponte | §2 | — |
| 2 | **team DB** ⏭️ | La colonna 722 portata su `ultima_conclusa` | §3 | 1 |
| 3 | sessione BE/FE | Ritirare `ultimo_ok` dalla proiezione e dallo slot FE, decidere l'export | §5 | 2 |

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-22. **A chi:** team DB.
> **Origine:** allineamento della lista `amm.processi` alla forma unica delle corse, chiesto da Tid
> (2026-11-22); scelta «in due tempi» di Tid, perché il BE non rinomina prima del DB.
> **Brief vicini verificati:** [brief-db-giornale-corse-indici](brief-db-giornale-corse-indici.md), stesso
> giornale ma altro tema (gli indici). Nessun altro brief aperto tocca la lista 66.

## 1. Il caso

La lista `amm.processi` (`ui.lista_definizione` 66) ha due colonne affiancate:

| id | codice / `campo_sorgente` | etichetta |
| --- | --- | --- |
| 721 | `ultimo_run` | Ultima corsa |
| 722 | `ultimo_ok` | Esito |

Fino al 2026-11-22 `ultimo_run` era la riga più recente del giornale (anche una corsa **saltata**) e
`ultimo_ok` l'esito dell'ultima corsa **vera**: due corse diverse che a video si leggevano come una. È la
cucitura che `MaintenanceRepository` aveva già tolto il 2026-09-14 con `ultima_conclusa`.

## 2. Che cosa ha fatto il BE/FE

* `ProcessiRepository.list_processi` legge le corse con le CTE comuni `cte_corse(chiave="processo_codice")`
  e consegna `ultimo_run` + `in_corso` (la riga più recente) e
  `ultima_conclusa = {started_at, ended_at, ok}` (l'ultima corsa vera chiusa).
* `ultimo_ok` resta nella proiezione **solo come ponte**, perché la colonna 722 ha quel
  `campo_sorgente` e il presidio `test_lista_proiezione_campo_sorgente` lo pretende. È
  `ultima_conclusa.ok`, preso dalla stessa riga.
* A video lo slot della colonna 722 legge già `ultima_conclusa` e mostra la data della sua corsa.

⚠️ Resta cucito l'**export**: esporta `ultimo_ok` (un booleano) senza la sua data.

## 3. La richiesta

1. Portare la colonna 722 da `ultimo_ok` a `ultima_conclusa` (`codice` e `campo_sorgente`; sono campi del
   software sotto `trgfn_seed_primo_impianto`, quindi passano dal seed).
2. `tipo_dato` e `formato` di una colonna il cui valore è un oggetto `{started_at, ended_at, ok}`: li
   decide il team DB secondo il vocabolario di `ui.tipo_dato`. Se il vocabolario non ha una forma per un
   oggetto, dirlo nel ritorno: è un'informazione che serve al BE per l'export (§5).
3. Le preferenze utente e i preset che nominano la colonna per `codice` (`ultimo_ok`) vanno riportati sul
   codice nuovo nello stesso changeSet, altrimenti chi l'aveva spenta o spostata la ritrova di default.
4. L'etichetta estesa «Esito dell ultima corsa» diventa «Esito dell'ultima corsa conclusa» (o la forma che il
   team DB preferisce): è la corsa che la colonna mostra davvero.

## 4. Doc

* `docs/it/dbzero/ui/` si rigenera; il seed `lista_colonna.csv` porta la riga 722 nuova.

## 5. Ricadute BE/FE, al ritorno (`/arrivi-db`)

La sessione BE, nello stesso giro:

* toglie `ultimo_ok` da `list_processi`, insieme al commento del ponte;
* rinomina lo slot FE `#cell-ultimo_ok` in `#cell-ultima_conclusa` (`ProcessiAutomaticiTab.vue`);
* decide come `ListaExportService` scrive un oggetto `ultima_conclusa` (esito + data in una cella), sulla
  base del §3.2;
* corregge [api_amm_software.md](../../backend/amm-software/manual/api_amm_software.md) §6.6, riga
  `ultimo_ok`.
