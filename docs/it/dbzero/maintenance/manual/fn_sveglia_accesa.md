## 📘 Documentazione Concettuale – Funzione `maintenance.fn_sveglia_accesa()`

> 👀 **Vedi anche**
>
> [dbops.processi](/dbzero/dbops/manual/processi) ·
> [dbops.processi_accensione](/dbzero/dbops/manual/processi_accensione) ·
> [dbops.installazione](/dbzero/dbops/manual/installazione)

### 🎯 Scopo
(16-10-2026 — brief `brief-db-processi-accensione-per-ambiente`)

**La sveglia di questo processo deve far partire il lavoro?** `true` o
`false`, mai `NULL`: ciò che non si sa decidere è un errore.

### Chi la chiede

* Il **passo di ogni job pgAgent** di un processo. Il passo è avvolto così
  (`85_pgagent/20261016-30`):

  ```sql
  DO $sveglia$
  BEGIN
      IF maintenance.fn_sveglia_accesa('<codice>') THEN
          CALL maintenance.proc_<…>_job();
      END IF;
  END
  $sveglia$;
  ```

  Da spento il lavoro non parte e il giornale non scrive niente: il panorama
  dice `SPENTO` dal catalogo.
* Le **sveglie systemd** dei comandi del backend, e «Esegui ora», che su un
  processo spento non parte.

⛔ **Non la chiede la convergenza del rilascio** (`90_end/ci_apply/20260926-10`):
quella chiama le procedure strutturali sempre. Spegnere ferma la sveglia
notturna, non l'aggiornamento: un rilascio lascia il database completo.

### Errori

| Caso | Codice |
| --- | --- |
| codice inesistente | `E_PROCESSO_NON_TROVATO` |
| processo senza sveglia (`CODA`, ritirato) | `E_PROCESSO_SENZA_SVEGLIA` |
| ambiente non dichiarato (e nessuna scelta a mano) | `E_CONFIG_MANCANTE` |
| catalogo senza il default di accensione | `E_CONFIG_MANCANTE` |

Un **non spegnibile** risponde `true` senza leggere l'ambiente: un'installazione
non ancora dichiarata non ferma i processi che non devono fermarsi mai.

### Forma

`SECURITY DEFINER`: pgAgent gira come `zeroerp_job`, che chiama solo le
procedure dei job e non legge `dbops`. La porta è stretta: un codice in, un
booleano fuori. La regola sta in `dbops.fn_processo_acceso_su_valori`, la
lettura in `dbops.fn_processo_acceso_dichiarato`.

### Test

`db/pgtap/dbops/test-processi-accensione-v1.sql` (2, 3, 18–22),
`db/pgtap/dbops/test-installazione-ambiente-v1.sql` (15–17, 20–22).

---

{% include-markdown "signature-core.md" %}
