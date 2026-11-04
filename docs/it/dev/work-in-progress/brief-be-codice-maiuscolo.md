# Brief BE — Il codice si salva in maiuscolo: che cosa cambia per il backend

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari:** backend (`dev/backend-tid`). Il lato DB è chiuso e applicato: commit `b26b103bae`
> su `dev/db-tid`, changeSet `20261104-01` … `-08`, applicato su dbdev il 2026-11-04 con i pgTAP verdi.
> Nessuna richiesta al team DB.
>
> **Stato:** aperto, non iniziato. **Da leggere per primo: §2, che cosa cambia.**
>
> **Il disegno** sta nella guida [Framework di automazione DB §4.8](../../guide/automazione-db.md), §4.8 e il suo «Per il backend»:
> questo brief dice solo che cosa deve fare il BE.

---

## 1. Da dove viene

Il 2026-11-04 Tid ha deciso che il codice che l'operatore digita **non distingue le maiuscole**:
`VITE-M8` e `vite-m8` sono lo stesso articolo, non due. Il DB ora salva ogni colonna `codice` in
`upper(btrim(codice))`, con un trigger che l'automazione CODICE_MAIUSCOLO monta da sola su ogni
tabella dell'ambito: oggi 116 tabelle negli schemi `anagrafiche`, `catalogo`, `config`, `documenti`,
`magazzino`, `pagamenti`, `pratiche`, `vendite`. Una tabella nuova con la colonna `codice` nasce
già col trigger.

Le righe già scritte sono state normalizzate una volta (`sql-una-tantum-codice-maiuscolo.sql`).

**Restano come sono** (eccezioni, `dbops.automazione_codice_eccezioni`): `ui.lista_colonna`,
`ui.lista_definizione`, `ui.lista_preset`, `ui.widget`, `ui.dashboard_definizione`,
`ui.dashboard_preset`, `dbops.processi`, `config.aree_funzionali`, `config.assets_ownership`,
`config.note_stili`. Sono chiavi tecniche lette per nome. `codice_interno` non è toccato su nessuna
tabella, e gli schemi fuori dall'ambito (per esempio `dbops`, `ui`) nemmeno.

---

## 2. Che cosa cambia per il BE

| # | Che cosa | Effetto se non si fa |
| --- | --- | --- |
| K-1 | **Il valore salvato può essere diverso da quello inviato.** Dopo un INSERT o un UPDATE il codice va riletto dal DB (`RETURNING codice`, o la rilettura del dettaglio), non rimandato al client com'era nel payload | Il client mostra `vite-m8` mentre il DB ha `VITE-M8` |
| K-2 | **Una ricerca esatta per codice** su un input dell'utente (`WHERE codice = %s`, un filtro `?codice=`, una risoluzione «trova per codice») confronta con `upper(btrim(input))`. Le ricerche `ILIKE` non cambiano | `?codice=vite-m8` non trova niente |
| K-3 | **Il duplicato ora è senza maiuscole.** Creare `vite-m8` quando c'è `VITE-M8` dà la stessa violazione di unicità (23505 sul vincolo del codice) che prima dava solo il codice identico. La traduzione dell'errore che il BE già fa per il codice duplicato resta quella: va solo verificato che il messaggio non suggerisca «c'è già `vite-m8`» | Nessuno: è il comportamento voluto |
| K-4 | **`E_CODICE_MAIUSCOLO`**, codice nuovo, classe `TECNICO`. Nasce solo dal motore dell'automazione (migrate, job notturno), mai da una richiesta dell'utente: basta che `genera_error_policies` lo porti nel modulo generato | Il cancello «ogni codice che il DB può nominare ha una policy» resta rosso |
| K-5 | **I test Django** che creano un codice con lettere minuscole (un suffisso `uuid4().hex`, `token_hex`, `md5` senza `.upper()`) e poi lo cercano o lo confrontano per valore. La correzione è mettere `.upper()` sul **generatore** del suffisso, non sulle ricerche: è quello che si è fatto sui cinque pgTAP | Il test non trova la riga che ha appena creato |

⚠️ K-1 e K-2 valgono solo per le tabelle del perimetro. Un repository che legge una tabella in
eccezione o fuori ambito (`ui.*`, `dbops.*`) non cambia.

---

## 3. Il punto di partenza del censimento (dal lato DB, non esaustivo)

Un grep fatto dalla sessione DB il 2026-11-04, per dare un inizio, non un elenco chiuso: il
censimento vero lo fa il BE.

| Dove | Che cosa | Nota |
| --- | --- | --- |
| `anagrafiche/db/soggetti_repository.py` `resolve_tipo_ruolo` | `config.tipi_ruoli WHERE codice = %s OR codice_interno = %s ORDER BY (codice = %s)` | K-2: il payload può arrivare minuscolo |
| `core/db/email_repository.py` (lista `email_template`) | filtro `et.codice = %s` | K-2 |
| `vendite/tests/db/test_listini_create_db.py`, `pagamenti/tests/db/test_enti_incasso_create_db.py` | suffisso già `uuid4().hex[:8].upper()` | ✅ già a posto: sono la forma da copiare |
| 23 file in `backend/apps/*/tests` usano `uuid4().hex`, `token_hex` o `md5` | da guardare uno per uno | K-5 |
| `dbops_repository.py`, `pipeline_repository.py`, `processi_repository.py`, `ui_repository.py`, `dashboard_repository.py`, `lista_catalogo_repository.py` | ricerche esatte su `dbops.*` e `ui.*` | fuori perimetro: non cambiano |

Il censimento si chiude con la lista dei repository che fanno una ricerca esatta sul `codice` di una
tabella del perimetro. Per sapere se una tabella è nel perimetro:

```sql
SELECT schema_name, table_name
  FROM dbops.fn_codice_maiuscolo_perimetro(NULL)
 WHERE nel_perimetro AND NOT in_eccezione;
```

---

## 4. Il FE

Facoltativo, non una richiesta: un campo codice può mostrare il testo in maiuscolo mentre si digita,
così l'operatore vede subito come verrà salvato. Il DB normalizza comunque: il FE non deve ripetere
la regola.

---

## 5. Chiusura

Il brief si archivia in `work-done/` quando K-1 … K-5 sono fatti e i test Django sono verdi.
