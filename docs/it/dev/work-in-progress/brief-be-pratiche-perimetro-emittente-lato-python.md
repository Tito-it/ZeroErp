# Brief BE — Pratiche: il perimetro emittente letto anche lato Python

> **Destinatari:** backend (`dev/backend-tid`). Nessuna richiesta al team DB:
> le policy RLS su `pratiche.*` ci sono già e reggono da sole (§2).
>
> **Tipo:** brief di cantiere, **differito per decisione di Tid del
> 2026-09-21** (*«per le pratiche al momento sono ferme, lo farei dopo»*).
> Nasce dal censimento dello stesso giorno sul filtro di scope applicativo
> (§1), che ha già allineato `vendite` — satelliti a 404 e lista offerte —
> e ha lasciato `pratiche` come unico dominio con un'anomalia di **forma**
> ancora aperta.
>
> **Stato:** ⏸️ in attesa — si apre quando si riapre il cantiere pratiche.
> Nessuna riga scritta, per scelta.
>
> **Da leggere per primo: §2 — che cosa regge oggi, e perché non è urgente.**

---

## 1. Da dove viene

Il 2026-09-21 Tid ha chiesto di verificare se *ogni* endpoint DRF filtri per
utente/azienda anche lato Django, non solo via RLS. Il censimento (per metodo
Python che legge una delle 119 tabelle con RLS, `storico` escluso) ha dato:

| App | Metodi che leggono tabelle RLS | Con scope Python | Solo RLS |
| --- | --- | --- | --- |
| vendite | 154 | 16 | 138 |
| anagrafiche | 29 | 6 | 23 |
| **pratiche** | **20** | **0** | **20** |
| magazzino | 10 | 1 | 9 |
| pagamenti | 8 | 0 | 8 |

⚠️ Il numero **non è il problema**, ed è la cosa da non fraintendere: la regola
del progetto è *«RLS come cancello uniforme, filtro Python sulle liste di
testata e ordine di lettura sui satelliti»* ([api.md §«Scope
emittente»](../api.md)). Il doppio filtro su ogni endpoint è esattamente il
pattern che l'analisi RLS ha dichiarato fragile
([analisi-attivazione-rls-operatori.md §2.3](../work-done/analisi-attivazione-rls-operatori.md)).
Quello che il censimento ha trovato in `pratiche` sono **tre anomalie di
forma**, non venti buchi.

## 2. Che cosa regge oggi

Verificato sul DB vivo il 21-09 (struttura, non popolazione):

- `pratiche.pratiche` → `rls_pratiche_ef_whitelist`, **`FOR ALL`** (anche
  scrittura), su `fn_scope_ef_whitelist(current_user_id, emittente_fiscale_id)`;
- `pratiche.flussi` → `rls_flussi_ef_whitelist`, `FOR ALL`, via
  `fn_scope_ef_whitelist_via_pratica`;
- i satelliti (`sospensioni`, `note_pratiche`, `allegati_pratiche`,
  `calcoli_tempo`, `giornale`, `pratiche_sorgenti`, `allegati_flussi`,
  `note_flussi`) hanno ciascuno la propria policy — 10 tabelle su 23 dello
  schema, le altre 13 sono catalogo (definizioni, template, stati);
- l'app connette come `zeroerp_app` (né owner né `BYPASSRLS`), il middleware
  azzera i GUC per richiesta e rifiuta un ruolo con bypass
  (`E_DB_ROLE_UNSAFE`).

⇒ Un operatore fuori perimetro **non legge e non scrive** una pratica altrui,
oggi, per qualunque via. Il brief non chiude una falla: chiude un'asimmetria
con `vendite` che, finché resta, si paga in due modi — un pannello **vuoto**
dove ci vorrebbe un 404, e un parametro del client che *sembra* un cancello e
non lo è.

## 3. Le tre anomalie, sul modello

### 3.1 `list_pratiche` riceve l'emittente dal client e non lo verifica

[views.py:71](../../../../backend/apps/pratiche/api/views.py) — la lista
pretende `emittente_fiscale_id` in query string, obbligatorio e `> 0`, e lo
passa al repository come **filtro**. Nessun punto Python lo confronta con la
whitelist dell'operatore (`get_emittenti_pk_ids`).

Regge perché la RLS interseca: un emittente fuori whitelist dà **zero righe**.
Ma la forma è sbagliata sul modello, e in due modi:

1. un parametro obbligatorio scelto dal client **non è uno scope**: è un
   filtro. Lo scope lo risolve il server dall'utente
   (`get_scope_user_id` → `add_emittente_scope_condition`), come in tutte le
   liste di `vendite`. Se la RLS su `pratiche` venisse spenta col kill-switch
   (`DISABLE ROW LEVEL SECURITY`, previsto dall'analisi §7), quel parametro
   diventerebbe un selettore libero **senza che nessun test lo dica**;
2. la view dichiara già `lista_codice = "pratiche.pratiche"`, quindi il
   cancello di perimetro di `DomainAPIView.initial()` gira — ma senza
   `lista_emittente_param` non sa che l'emittente è **già fissato** dalla
   query, e su un operatore multi-emittente chiede di sceglierne uno (422)
   mentre il client lo ha già detto. È lo stesso caso risolto sui tab-lista
   dei drawer emittente (`base_views.py`, attributo `lista_emittente_param`).

### 3.2 Cinque satelliti rispondono `200 []` a una pratica fuori perimetro

Stessa classe dei dieci satelliti di `vendite` chiusi il 21-09: passano dritti
al repository senza leggere la testata.

| Service (`pratiche_service.py`) | Riga | Cosa manca |
| --- | --- | --- |
| `get_giornale` | 1004 | `_get_testata_or_raise` prima del repository |
| `get_note_pratica` | 1015 | idem |
| `get_allegati_pratica` | 1068 | idem |
| `get_sospensioni` | 1379 | idem |
| `get_calcoli_tempo` | 1388 | idem |

Più `ApiPraticaFlussiList.get` ([views.py:348](../../../../backend/apps/pratiche/api/views.py)),
che chiama `repo.list_flussi(pratica_id)` **dalla view**, senza service e
senza testata — due deviazioni in una riga (tre layer, e ordine di lettura).

Il BB c'è già: `testata_o_not_found` in
`apps/core/services/testata_guard.py`, con il wrapper di dominio
`_get_testata_or_raise(repo, id, *, op)` — stesso nome in ordini, DDT,
preventivi, resi. In `pratiche` il codice è `E_PRATICA_NOT_FOUND` (già a
catalogo, classe `NON_TROVATO`), e la view di dettaglio
([views.py:172](../../../../backend/apps/pratiche/api/views.py)) contiene già
il blocco inline da cui il wrapper nasce.

### 3.3 Il dettaglio della pratica è scritto nella view

`ApiPraticaDetail.get` fa `repo.get_pratica` + `ErrorManager.require` **nella
view** — il service non ha un `get_pratica`. È il punto in cui il wrapper del
§3.2 va a vivere: una volta che esiste nel service, la view torna a una riga.

## 4. Il lavoro, quando si apre

Tutto BE, nessun changeSet, nessun impatto FE dichiarato (il 404 sui
satelliti è già gestito da `useDrawerDetailLoad`; sul §3.1 il FE continua a
mandare `emittente_fiscale_id`, cambia solo cosa il server ne fa).

1. **`_get_testata_or_raise` in `pratiche_service`** su `testata_o_not_found`
   (`E_PRATICA_NOT_FOUND`, «Pratica non trovata.», `pratica_id`); `get_pratica`
   nel service; `ApiPraticaDetail.get` a una riga.
2. **I cinque satelliti** del §3.2 lo chiamano prima del repository;
   `ApiPraticaFlussiList` passa da un `list_flussi(pratica_id)` di service che
   fa lo stesso. Test: per ciascuno, testata `None` → `ServiceError`
   `E_PRATICA_NOT_FOUND` e repository non chiamato (calco:
   `OrdiniSatellitiTestataTests` in `test_ordini_service.py`).
3. **`list_pratiche`**: `emittente_fiscale_id` resta un filtro **facoltativo**
   del client; lo scope lo mette il server con
   `add_emittente_scope_condition(..., auth_user_id=get_scope_user_id(request),
   column="p.emittente_fiscale_id", convention="pk")` nel repository, su righe
   **e** conteggio; la view dichiara `lista_emittente_param =
   "emittente_fiscale_id"` così il cancello di perimetro sa che è già fissato.
   Test nei due versi (clausola presente con whitelist, assente con `None`,
   fail-closed con `[]`), calco: `test_offerte_scope_emittente.py`.
   ⚠️ **Decisione da prendere allora, non qui**: se il parametro resti
   obbligatorio per il FE (oggi la dashboard pratiche lo manda sempre) o
   diventi facoltativo come nelle liste di `vendite`. Sul modello è un filtro,
   quindi facoltativo; ma il FE va guardato prima di togliere il `require`.
4. Aggiornare `docs/it/backend/pratiche/manual/` (scheda della lista) e la
   riga di `pratiche` in [api.md §«Scope emittente»](../api.md).

Stima: **mezza giornata**, BE-only.

## 5. Cosa NON entra

- Nessun doppio filtro sui getter by-id (`get_pratica`, `get_flusso`): sono
  già 404 via RLS (`None` dal repository), come in `vendite`.
- Nessuna modifica alle policy: sono `FOR ALL` e coprono i satelliti.
- `pagamenti` e `magazzino` hanno lo stesso profilo «solo RLS» nel
  censimento, ma la loro **forma** (chi legge la testata, da dove arriva
  l'emittente) **non è stata esaminata** in questo giro: il 21-09 si è
  guardato `vendite` per intero e `pratiche` perché era l'unico dominio con un
  parametro di emittente scelto dal client. Se si vorrà, è un censimento a
  parte, con lo stesso metodo (§3.2: satellite → legge la testata?).
