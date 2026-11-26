# Brief DB — Lista processi: la colonna «Esito» con la sua data

## ✅ Chiuso — 2026-11-22

**Nessuno riparte.** Il lato DB è applicato (il seed della riga 722, Tid, 2026-11-22), le ricadute
BE/FE del §6.5 sono fatte lo stesso giorno (§7). Archiviato in `work-done/`.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Le corse della lista nella forma unica, `ultimo_ok` tenuto come ponte | §2 | — |
| 2 | ✅ team DB | Verifica critica: il codice della colonna non si cambia; il vocabolario non ha un tipo oggetto | §6 | 1 |
| 3 | ✅ Tid | D-2: che cosa è il valore della colonna «Esito» | §6.3 | 2 |
| 4 | ✅ team DB | La riga 722 nel seed: l'etichetta estesa | §6.4 | 3 |
| 5 | ✅ Tid | Applicare il seed (`lista_colonna.csv`, mirror `20260806-15`); rigenerare la doc `ui` | §6.4 | 4 |
| 6 | ✅ sessione BE/FE | Le ricadute del §6.5 | §6.5, §7 | 5 |

**Decisioni di Tid:** ✅ D-1 (2026-11-22): strada (b), il codice resta `ultimo_ok` (§6.2). ✅ D-2 (2026-11-22):
strada (ii), un solo valore booleano (§6.3). Nessuna decisione aperta.
**Committato** (2026-11-22, `dev/db-tid`): la riga 722 di `lista_colonna.csv` e questo brief.

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

⚠️ Corretta dal §6: il punto 1 non si può fare per il `codice` (§6.2), il punto 3 non serve più, il
punto 2 aspetta D-2 (§6.3).

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

⚠️ Corrette dal §6.5: con la strada (b) lo slot FE non si rinomina.

La sessione BE, nello stesso giro:

* toglie `ultimo_ok` da `list_processi`, insieme al commento del ponte;
* rinomina lo slot FE `#cell-ultimo_ok` in `#cell-ultima_conclusa` (`ProcessiAutomaticiTab.vue`);
* decide come `ListaExportService` scrive un oggetto `ultima_conclusa` (esito + data in una cella), sulla
  base del §3.2;
* corregge [api_amm_software.md](../../../backend/amm-software/manual/api_amm_software.md) §6.6, riga
  `ultimo_ok`.

## 6. Verifica DB — 2026-11-22

Fatta sul catalogo dello scratch `zeroerp_ruoli`.

### 6.1 Che cosa si è trovato

* **Il `codice` della colonna non si riscrive.** `ui.lista_colonna.codice` ha il lucchetto
  `trg_lista_colonna_a10_lock_columns_upd` (`E_UI_COLONNA_CODICE_IMMUTABILE`, U23 di
  [brief-db-revisione-ui](brief-db-revisione-ui.md)): il codice è la chiave con cui preferenze e preset
  citano la colonna. Il punto 1 del §3, così come è scritto, si ferma su quel lucchetto.
* **Il §3.3 aveva una premessa sbagliata.** `ui.lista_preset_colonna` cita la colonna per **id**
  (`66,722` in `lista_preset_colonna.csv`), non per codice. Per codice la citano solo le preferenze utente
  (`lista_preferenza_utente.configurazione`) e l'`ordinamento_default` dei preset.
* **Il vocabolario non ha un tipo oggetto.** `ui.tipo_dato` vale `string`, `numeric`, `date`, `datetime`,
  `boolean`, `enum`.
* La lista 66 non ha `vista_sql`: il validatore del `campo_sorgente` non lo confronta con una vista, e
  `ultima_conclusa` passa.

### 6.2 D-1 ✅ (Tid, 2026-11-22): strada (b), il codice resta `ultimo_ok`

La colonna «Esito» resta la stessa colonna: cambia da dove legge, non che cosa è. Quindi il codice resta
`ultimo_ok`, cambiano `campo_sorgente` (un campo del software, che passa dal seed) e l'etichetta estesa.
Preferenze e preset non si toccano: il §3.3 non serve più.

Scartata: la strada (a), che spegneva la 722 e creava una colonna nuova `ultima_conclusa`, portandoci
sopra preset e preferenze.

### 6.3 D-2 ✅ (Tid, 2026-11-22): strada (ii), un solo valore

La colonna resta un booleano: `campo_sorgente` `ultimo_ok`, `tipo_dato` `boolean`. Non è più un ponte
ma il campo della colonna. La data la mostra lo slot, che legge `ultima_conclusa`; l'export scrive
l'esito senza la data. Scartate: la (i), che toglieva la colonna dall'export, e la (iii), un cambio
di modello di `ui` per una sola cella. Se più colonne avranno lo stesso bisogno, la (iii) si
riprende allora.

Le strade come erano state poste:

La cella mostra due cose insieme, l'esito e la sua data. Il vocabolario dei tipi non ha una forma per
«due cose insieme». Il tipo serve all'export, che lo usa per scrivere la cella nel file. Le strade:

| | Che cosa | A video | Export |
| --- | --- | --- | --- |
| (i) | Colonna **composta**, come i precedenti 394 `esito` (`vendite.fatture_stampa_coda`) e 690 `validita` (`anagrafiche.soggetto_titoli_iva`): `campo_sorgente` NULL, `tipo_dato` `string` | lo slot compone esito e data | ⛔ no: `chk_ui_lista_colonna_senza_campo_non_esportabile` la rende non esportabile |
| (ii) | **Un solo valore**: `campo_sorgente` resta `ultimo_ok` (`boolean`), che non è più un ponte ma il campo della colonna; la data la aggiunge lo slot | esito e data | esito senza la data |
| (iii) | **Un tipo nuovo** in `ui.tipo_dato` per un valore con più parti | esito e data | esito e data, se l'export impara il tipo nuovo |

La (iii) è un cambio di modello di `ui`: tocca tutti i lettori del tipo, BE e FE, e il brief
`revisione-ui` ancora aperto. Con la (ii) il §6.4 si riduce all'etichetta estesa.

### 6.4 Il giro DB ✅ (2026-11-22)

Con D-1 e D-2 della riga 722 cambia solo `etichetta_estesa`: «Esito dell ultima corsa» diventa
«Esito dell'ultima corsa conclusa», in `80_data/sql/ui/lista_colonna.csv`. Codice, `campo_sorgente`,
`tipo_dato` e `formato` restano. Nessun changeSet nuovo: il CSV lo rilegge il suo mirror
`runOnChange` (`20260806-15-riancora-mirror-ui-lista-colonna`), come vuole §11.2.

⚠️ `etichetta_estesa` è un campo dell'installazione per `script.trgfn_seed_primo_impianto`: il seed la
riscrive solo dove la riga è ancora intatta. Su un'installazione che l'ha personalizzata resta la
sua, ed è voluto.

✅ Tid, 2026-11-22: seed applicato sullo scratch (la riga 722 porta l'etichetta nuova). La doc
auto-generata di `ui` non riporta `etichetta_estesa`: nessuna pagina cambia.

### 6.5 Le ricadute BE/FE del §5, corrette da D-1 e D-2

* lo slot FE resta `#cell-ultimo_ok`, perché il codice non cambia (D-1), e continua a leggere
  `ultima_conclusa` per la data;
* `ultimo_ok` **resta** in `list_processi`: è il campo della colonna (D-2), quindi il commento «ponte»
  diventa la descrizione del campo. È `ultima_conclusa.ok`, dalla stessa riga, quindi non c'è cucitura;
* l'export scrive l'esito senza la data, per scelta (D-2), e `ListaExportService` non cambia;
* `api_amm_software.md` §6.6, riga `ultimo_ok`: l'esito dell'ultima corsa **conclusa**, lo stesso di
  `ultima_conclusa.ok`.

## 7. Chiusura BE/FE — 2026-11-22

Le ricadute del §6.5, tutte di commento e di documentazione: nessuna riga di codice cambia.

| File | Che cosa |
| --- | --- |
| `backend/apps/core/db/processi_repository.py` | il commento di `list_processi`: `ultimo_ok` non è più un ponte da ritirare ma il campo della colonna «Esito», `ultima_conclusa.ok` dalla stessa riga |
| `frontend/src/amministrazione/components/ProcessiAutomaticiTab.vue` | il commento dello slot `#cell-ultimo_ok`: il codice della colonna, il campo che scrive l'export, la data letta da `ultima_conclusa` |
| `docs/it/backend/amm-software/manual/api_amm_software.md` §6.6 | la riga `ultimo_ok`: l'esito dell'ultima corsa conclusa, il campo della colonna 722; senza «transitorio» |
| `backend/apps/core/tests/db/test_corsa_riuscita_dal_db.py` | il commento del test 6 |

`ListaExportService` non cambia (D-2). Verifica: `test_corsa_riuscita_dal_db` sul DB vero
(`ZEROERP_TEST_DB_E2E=1`), 6 su 6.
