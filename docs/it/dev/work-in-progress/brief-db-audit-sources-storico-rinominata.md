# Brief team DB — `dbops.audit_sources` punta a una storico che non nasce più

> Destinatario: team DB (`dev/db-tid`) · Origine: `dev/backend-tid` · 2026-09-02
> Dimensione: **una riga di CSV, e una decisione che ne vale tre.**
> ⛔ Nessuna modifica applicata: qui si segnala, non si tocca.

## 1. Il sintomo

La CI GitHub è rossa con **9 `errors`**, tutti la stessa frase:

```
django.db.utils.ProgrammingError: relation "storico.risorse_umane_auth_user" does not exist
LINE 1: ...ry('risorse_umane_auth_user', s.id) AS audit FROM storico.ri...
```

⭐ **I 9 sono un errore solo, contato nove volte**, ed è utile saperlo perché il
numero fa pensare a nove cose diverse. Vengono tutti da un'unica lista —
`storico.audit_log` — esercitata da
`apps/core/tests/db/test_lista_proiezione_campo_sorgente.py`:

| Da dove | Quanti |
| --- | --- |
| la proiezione della lista (test 1) | 1 |
| le 4 colonne di `AUDIT_ORDER_COLUMNS` × 2 versi (test 4) | 8 |

⇒ **9.** Il difetto è uno.

## 2. Il fatto

`db/changelog/migrations_v2/80_data/sql/dbops/audit_sources.csv`, riga con `id = 5`:

```csv
5,risorse_umane_auth_user,storico.risorse_umane_auth_user,risorse_umane_auth_user_id,amm.audit_tabella_ruolo,AUTH,t,…
```

Quella `storico_table` **in dev esiste** — è documentata in
[docs/it/dbzero/storico/tabelle/risorse_umane_auth_user.md](../../dbzero/storico/tabelle/risorse_umane_auth_user.md)
— e **in CI no**.

⭐ **E la CI ha ragione, il dev è indietro.** `anagrafiche.risorse_umane_auth_user`
oggi è una **vista**: la tabella vera è stata rinominata
`anagrafiche._legacy_risorse_umane_auth_user` (changeSet `20260429-19a`). Su un
database ricostruito da zero l'automazione dello storico gira sullo schema di
**oggi** e produce lo storico della **tabella**, non della vista; il database di
dev si porta dietro la vecchia dalla propria storia — e infatti in
`docs/it/dbzero/storico/tabelle/` **ci sono tutte e due**,
`risorse_umane_auth_user.md` e `_legacy_risorse_umane_auth_user.md`.

⚠️ **Questa è una deduzione, non una misura.** Non ho eseguito niente contro il
database di CI né contro quello di dev: è lettura di changeSet, del CSV e della
documentazione `dbzero`. La verifica che chiude la questione è una sola —
`SELECT to_regclass('storico.risorse_umane_auth_user')` su un database
**ricostruito**, non su dev.

## 3. ⛔ Il difetto sotto, che è indipendente e resterà anche dopo

Il nome della tabella viene dedotto in **due modi diversi**, da due posti che
non si parlano:

| Chi | Come costruisce il nome | Sede |
| --- | --- | --- |
| `script.fn_audit_summary` | legge **`storico_table`** e `storico_pk_col`, poi `EXECUTE format(%I)` | changeSet `20260429-07` |
| il backend | concatena **`code`**: `f"FROM storico.{code}"` | `amm_software_repository.py:1109` |

⭐ **La colonna `storico_table` esiste apposta perché i due possano divergere** —
lo dice il changeSet `20260429-06` in prima persona: *«le colonne tecniche
storico_table / storico_pk_col restano nella tabella sottostante
dbops.audit_sources e sono lette solo dalla fn dispatch script.fn_audit_summary»*.
Il backend però la stessa deduzione la rifà da sé, dal campo sbagliato.

⛔ **E non può farla giusta**, oggi: `script.vw_audit_sources` espone solo
`code`, `label_key`, `area_funzionale`. Il nome fisico dallo strato pubblico
**non è raggiungibile**.

⚠️ **Perché la confusione è comoda e quindi dura.** `code` non è solo un'etichetta:
è anche una **colonna di ordinamento** (`AUDIT_ORDER_COLUMNS["tabella"] = "code"`)
e il filtro `?tabella=` dell'API. Cioè fa già da identità logica — e finché
identità logica e nome fisico coincidono, usarla per il `FROM` sembra funzionare.
Il giorno in cui una storico viene rinominata i due si separano, e la separazione
non produce un avviso: produce **questo** errore, a valle, su un database che
qualcun altro ha ricostruito.

## 4. Le tre strade, con il loro prezzo

⚠️ Non ne scelgo una: la riga è vostra e la decisione tocca la storia già scritta.

| # | Cosa | Cosa chiude | Cosa costa |
| --- | --- | --- | --- |
| **A** | riga 5 → `storico_table = storico._legacy_risorse_umane_auth_user`, `code` invariato | il rosso di CI, e **conserva** gli snapshot già scritti | ⛔ **da sola non basta**: il BE continua a costruire il nome da `code`, quindi l'errore resta **identico**. Va con la C |
| **B** | riga 5 → `attivo = f` | il rosso di CI, in una riga | ⚠️ l'audit AUTH dopo il cutover è `identita_digitali` (riga 8, già attiva), quindi il presente è coperto — ma gli snapshot **pre-cutover** restano nella tabella **senza nessuna strada per leggerli** dal drawer |
| **C** | `vw_audit_sources` espone anche `storico_table`, e il BE legge quella invece di `code` | il difetto **latente**: da lì in poi una storico si può rinominare senza rompere l'audit | è DDL sulla vista (vostro) **più** una modifica BE (mia, e la faccio appena la colonna c'è) |

⛔ **E QUI C'È LA COSA DA NON SBAGLIARE: `C` DA SOLA NON FA TORNARE VERDE LA
CI.** Sembra la strada «giusta» perché corregge il difetto vero, e infatti lo
corregge — ma il valore scritto oggi nella riga 5 è
`storico.risorse_umane_auth_user`: un backend che leggesse `storico_table`
invece di `code` costruirebbe **esattamente lo stesso nome** e fallirebbe
identico. `C` sistema il *come* si deduce il nome, non il *nome*.

⇒ **Le uniche due combinazioni che spengono i 9 errori sono `B` da sola, oppure
`A` + `C`.** Ogni altra le lascia lì.

⭐ **A + C insieme** è l'unica che toglie anche la trappola, non solo il rosso.
**B** è la più corta e non è sbagliata — ma va scelta sapendo che butta via
l'unica strada verso la storia vecchia, non che la rimanda.

## 5. Cosa serve a me, e quando

⚠️ **Non sblocco la CI da solo**: qualunque strada passa dal database. Fino ad
allora quei 9 `errors` restano, e sono *questi* — cioè non nascondono nient'altro.

* se scegliete **C**, la modifica BE (`storico_table` al posto di `code` nella
  costruzione dell'`UNION ALL`) la faccio io **dopo** che la colonna è nella
  vista: prima non compilerebbe niente di sensato;
* se scegliete **B** da sola, dal BE non serve nulla e la riga di
  `test_lista_proiezione_campo_sorgente` torna verde da sé.

## 6. Cosa NON ho verificato

* nessuna query eseguita, né su dev né su CI: tutto quanto sopra è lettura di
  `db/changelog/`, del CSV e di `docs/it/dbzero/`;
* non ho controllato **se e quando** `storico._legacy_risorse_umane_auth_user`
  venga creata su un database ricostruito — la sua pagina in `dbzero` dice che
  in **dev** c'è, e questo non dice niente su una ricostruzione;
* non ho guardato se altre righe di `audit_sources.csv` abbiano lo stesso
  problema latente. ⚠️ Vale la pena farlo nello stesso giro: il controllo è
  `SELECT code, storico_table, to_regclass(storico_table) FROM dbops.audit_sources
  WHERE attivo` su un database ricostruito, e una riga con `to_regclass` a NULL
  è lo stesso difetto che aspetta il suo turno.
