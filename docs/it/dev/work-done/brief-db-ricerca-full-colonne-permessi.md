# Brief DB — In quali colonne può cercare chi guarda la lista

> **Da leggere per primo: §2 (cosa è stato verificato prima di scrivere) e §6
> (la risposta al BE).**
> Origine: richiesta del team BE, 2026-09-23 — la ricerca libera delle liste
> passa alla lettura del catalogo a runtime, perché oggi `ricercabile_full` si
> cambia dal pannello di amministrazione e la ricerca non se ne accorge. Il BE
> cita un suo brief (`brief-be-ricerca-full-liste-residue.md` §2) che al
> 2026-09-23 **non è nel repository**: la richiesta vale per come è stata
> incollata, ed è riassunta in §1.
>
> ✅ **Stato 2026-09-23: CHIUSO — applicato, mergiato e consumato dal BE.**
> - **DB**: cinque changeSet (`20260923-11…-15`), due righe di CSV (note del
>   codice d'errore), un pgTAP nuovo, cinque pagine `manual/`. Applicati e
>   provati da Tid (commit `55341db80`, PR #1656). Nella stessa giornata, su
>   richiesta del BE, `ricercabile_full = t` su `ddt_origine_numero` di
>   `vendite.resi` (seed `lista_colonna.csv` id 156, PR #1658).
> - **Verificato dal BE sul DB di sviluppo**: `ui.fn_lista_colonne_ricerca_full`
>   restituisce le colonne attese (preventivi, resi, clienti), una lista
>   inesistente solleva `E_UI_LISTA_NON_TROVATA`.
> - **Consumatore**: il BB `add_ricerca_full_condition` + `RicercaFull`
>   (`backend/apps/core/db/_helpers.py`), che legge questa funzione a ogni
>   ricerca e cerca sull'intersezione con le colonne dichiarate dal repository.
>   Le dieci liste di vendite ci passano; presidi `test_ricerca_full_seed` e
>   `tests/db/test_ricerca_full_db`. Le altre 32 liste:
>   [brief-be-ricerca-full-liste-residue](../work-in-progress/brief-be-ricerca-full-liste-residue.md).
> - §6, ultimo punto: il commento di `ui_repository.list_colonne_by_codice` ora
>   dice che quella non è la sede delle colonne di ricerca.
>
> ⚠️ Nota storica: quando questo brief è stato scritto, il brief BE citato qui
> sotto non era ancora nel repository; oggi c'è, al link sopra.

---

## 1. La richiesta

Una lettura che, per una lista e per l'utente corrente, restituisca `codice` e
`campo_sorgente` delle colonne che sono **insieme**: attive, `ricercabile_full`,
con `campo_sorgente` valorizzato, con livello effettivo diverso da `BLOCCATO`.
Contesto dalle GUC di sessione (firma: il solo codice lista), `STABLE`, grant a
`zeroerp_app`. Il calcolo del livello non va ricopiato: o si estrae in un pezzo
condiviso, o si aggiungono i due campi agli elementi di `colonne` di
`fn_resolve_lista_config` — «scegliete voi».

pgTAP col caso costruito: sensibile senza grant esclusa; con grant TUTTO o
LETTURA inclusa; grant BLOCCATO esclusa; non ricercabile, disattiva o senza
sorgente esclusa; lista inesistente → errore catalogato.

---

## 2. Cosa è stato verificato prima di scrivere — sul corpo vivo

Letto da `pg_get_functiondef` (coincide con la doc auto-gen) il 2026-09-23.

1. **L'emittente non entra nel livello di colonna.** La richiesta parla di
   «grant di ruolo ed emittente». Nel risolutore `p_emittente_fiscale_id`
   sceglie solo il **preset** (passo 2c); il livello (passo 4) si calcola dai
   soli profili d'accesso, e `ui.lista_colonna_permesso` non ha colonne di
   emittente. ⇒ La lettura nuova **non legge** `app.current_emittente_id`: una
   GUC che non decide niente non si legge.
2. **Il livello vive nei passi 4 e 5** del risolutore: il passo 4 sceglie il
   grant (profilo più specifico, a parità il più restrittivo), il passo 5
   applica il ripiego «sensibile senza grant → BLOCCATO». Sono **una** regola
   spezzata in due punti.
3. **La veste ha già due copie.** Il cast blindato «GUC → `config.ruolo_applicativo`,
   fuori dominio → `NULL`» è identico in testa a `fn_resolve_lista_config` e a
   `fn_resolve_dashboard_config`. La lettura nuova sarebbe stata la terza.
4. **Il modello dei binding** (`config.profili_accesso_bindings`): un solo
   binding per identità, uno per veste, uno per unità organizzativa (indici
   unici parziali). Conta per il pgTAP (§4).
5. **GRANT**: `EXECUTE` a `PUBLIC` sui due risolutori, più `zeroerp_app` dai
   default privileges del loop di `ci_apply`. Nessuna `GRANT` nei changeSet.
6. **Nessun presidio legge il testo** dei due risolutori (`prosrc` /
   `pg_get_functiondef` nei pgTAP): riscriverli non sposta conteggi.

---

## 3. La forma — due building block e la lettura sopra

**Scelta: estrarre, non allargare il JSONB del risolutore.** Tre ragioni sul
modello: (a) il JSONB di `fn_resolve_lista_config` va al **frontend**, e
`campo_sorgente` è il nome di una colonna della vista — struttura interna che
al browser non serve; (b) il risolutore fa la cascata dei preset e il merge
delle preferenze, lavoro che la ricerca non usa; (c) la regola del 2 lo chiede
comunque: il BE è il secondo consumatore del livello.

### 3.1 `ui.fn_veste_corrente()` — `20260923-11`

La veste dalla GUC `app.ruolo_applicativo`. `NULL` = tutte le vesti, sia per
GUC assente o vuota sia per valore fuori dominio; mai eccezione. Semantica
**di presentazione**: sta in `ui` apposta, perché le funzioni di permesso di
`script` (`fn_resolve_livello_area`, `fn_is_super_admin`) sono fail-**closed**
sulla veste, e un cancello d'accesso costruito su questa aprirebbe dove
quelle chiudono. Scritto nel COMMENT e nella pagina `manual/`.

### 3.2 `ui.fn_lista_colonne_livello(lista, utente, veste)` — `20260923-12`

Una riga per **ogni** colonna attiva: `colonna_id`, `codice`,
`livello_accesso`. Regola trascritta dai passi 4-5, senza ritocchi. Non
filtra: il risolutore toglie le `BLOCCATO` e spegne l'export sulle
`LETTURA`, la ricerca toglie le `BLOCCATO` — ognuno filtra a modo suo.
Chiama il risolutore dei profili una volta (CTE `MATERIALIZED`).

### 3.3 `fn_resolve_lista_config` passa dai due BB — `20260923-13`

Corpo dall'oggetto vivo, sostituzioni puntuali verificate a occorrenza unica:
via il cast della veste, via il passo 4 e la variabile `v_permessi`, il passo
5 legge il livello dal BB con un `JOIN`. **Contratto invariato.** Il risolutore
chiama il risolutore dei profili una volta in meno.

### 3.4 `fn_resolve_dashboard_config` passa dal BB della veste — `20260923-14`

Solo il cast della veste. Seconda delle due copie ritirate.

### 3.5 `ui.fn_lista_colonne_ricerca_full(lista_codice)` — `20260923-15`

`RETURNS TABLE(codice, campo_sorgente)`, `STABLE`. Utente da
`app.current_user_id`, veste dal BB. «Sorgente valorizzato» scritto come lo
scrive il guard a10 (`COALESCE(btrim(...), '') <> ''`), perché il loader del
catalogo scrive la stringa vuota e non il `NULL`. Lista assente o spenta:
`E_UI_LISTA_NON_TROVATA`, già registrato (NON_TROVATO) — le note del codice nei
due CSV nominano ora anche questa funzione.

⚠️ **Senza utente in sessione** (command, job): nessun grant, le **sensibili
escono**, le altre restano. È fail-closed dove conta; è anche la ragione per
cui un command che un giorno usasse la ricerca libera deve dire chi è.

---

## 4. Il presidio — `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql`

`plan(20)`. Il caso si **costruisce**: due profili nuovi (AD_HOC sull'identità
OPERATORE dell'utente di contesto, priorità 1; PORTALE sulla veste OPERATORE,
priorità 2) e otto colonne su una lista a catalogo.

- test 3-12: le condizioni della richiesta, una per asserzione, più il ripiego
  e i due grant;
- ⭐ test 10: **TUTTO dall'AD_HOC contro BLOCCATO dal PORTALE → inclusa**. È il
  test che discrimina la regola (vince il più specifico, non il più
  restrittivo). Il caso «pari priorità» della richiesta non si costruisce sotto
  una sola veste se non con PORTALE + REPARTO (§2.4): si è scelto il caso che
  distingue le due letture possibili della regola;
- ⭐ test 13: sulla stessa fixture la ricerca usa **esattamente** le colonne
  che `fn_resolve_lista_config` mostra — la coerenza fra i due consumatori;
- test 15-18: il BB della veste (valida, fuori dominio, vuota) e il fatto che
  la veste si legge davvero dalla GUC;
- test 19-20: senza utente.

⚠️ Stesso patto del test del contatore colonne nuove: se un giorno l'identità
dell'operatore di contesto o la veste OPERATORE avessero un binding a
catalogo, l'`INSERT` della fixture è un `23505` esplicito, non un verde a vuoto.

---

## 5. Le prove — 2026-09-23, scratch `zeroerp_ci`, come `zeroerp`

SQL **estratto** dai cinque YAML (`yaml.safe_load`), un solo `BEGIN … ROLLBACK`
scritto in testa, `ON_ERROR_STOP=1`.

| Prova | Esito |
| --- | --- |
| SQL estratto + pgTAP nuovo | **20/20 ok** |
| mutazione: tolto `pa.priorita ASC` dall'ordinamento del BB | **rosso il solo test 10** — il presidio discrimina |
| pgTAP esistenti che chiamano i due risolutori (7 file), senza e con l'SQL nuovo | conteggi **identici** (dashboard 12/12, contatore 5/5, preset-aggiornato 6/6, resolve 13/13, contratti-seed 14/14, multi-emittente 3/9, perimetro-emittente 7/8). I rossi degli ultimi due sono le **stesse** asserzioni prima e dopo, dichiarate «rosse da owner» nei file stessi |
| `plpgsql_check` sulle cinque funzioni | zero errori; un avviso «STABLE con `PERFORM` volatile» su ricerca e sui due risolutori, lo stesso che i risolutori hanno già (`fn_log_and_raise_error`) |
| dopo il `ROLLBACK` | nessuna delle tre funzioni nuove esiste; corpo del risolutore invariato (md5) |

⚠️ La prova gira **da owner**: la RLS non c'è. Le tabelle `ui` coinvolte non
hanno RLS; `identita_digitali` sì, e il suo comportamento come `zeroerp_app`
lo dice solo la corsa di Tid dopo l'apply.

Presidi trasversali da guardare nella corsa: `dbops/test-riferimenti-morti-v1`
(tre plpgsql nuove, già a zero errori col `plpgsql_check` sopra);
`script/test-rubinetto-primo-motivo-v1` non si muove (nessuna funzione nuova
chiama `fn_raise_primo_motivo_se_presente`).

---

## 6. Risposta al BE

**Chiamata:**

```sql
SELECT codice, campo_sorgente
  FROM ui.fn_lista_colonne_ricerca_full(%s);   -- il codice della lista
```

- ⚠️ `SELECT … FROM`, non `SELECT ui.fn_…(...)`: la seconda forma restituisce
  ogni riga come un'unica tupla in un campo solo.
- Utente e veste: dalle GUC che l'autenticazione JWT già imposta. Nessun
  emittente (§2.1).
- `LETTURA` **entra** (si vede, quindi si cerca); `BLOCCATO` no.
- Lista assente o spenta: `E_UI_LISTA_NON_TROVATA` (404), lo stesso codice del
  risolutore.
- Zero righe = nessuna colonna in cui cercare: la ricerca libera va
  **spenta**, non allargata a un elenco di ripiego.
- `campo_sorgente` è un nome di colonna della vista della lista: resta un
  identificatore da quotare lato BE (`sql.Identifier`), non un pezzo di SQL.
- ⚠️ Per il BE: il commento di `ui_repository.list_colonne_by_codice` dice che
  il filtro `BLOCCATO` è «delegato a `fn_resolve_lista_config`». Per la ricerca
  la sede è ora questa funzione — la whitelist `search_cols` dei repository
  (`resi`, `offerte`, `preventivi`, `famiglie` …) è la copia da ritirare nel
  giro BE.

---

## 7. Debiti trovati per strada — dichiarati, non aperti

- **`NULLIF(current_setting('app.current_user_id', true), '')::integer` è
  scritto inline in dodici funzioni** (la tredicesima è questa). È un idioma di
  una riga, non una regola con un significato che possa divergere come il
  cast della veste; con un valore non intero solleva `22P02` ovunque allo
  stesso modo. Non estratto in questo giro, per non allargare il perimetro a
  quattro schemi: se lo si vuole come BB, è un cantiere `script` suo.
- **La veste ha due semantiche nel database**: fail-open in `ui`
  (presentazione), fail-closed in `script` (permesso). È giusto che siano due,
  ma oggi solo i nomi e i commenti le distinguono. Scritto nei COMMENT e nelle
  pagine `manual/`.

---

## 8. Cosa è stato scritto

| Pezzo | File |
| --- | --- |
| BB veste | `20_code/ui/20260923-11-create-fn-veste-corrente-mctit.yaml` |
| BB livello | `20_code/ui/20260923-12-create-fn-lista-colonne-livello-mctit.yaml` |
| risolutore liste sui BB | `20_code/ui/20260923-13-update-fn-resolve-lista-config-livello-dal-bb-mctit.yaml` |
| risolutore dashboard sul BB | `20_code/ui/20260923-14-update-fn-resolve-dashboard-config-veste-dal-bb-mctit.yaml` |
| la lettura della ricerca | `20_code/ui/20260923-15-create-fn-lista-colonne-ricerca-full-mctit.yaml` |
| note di `E_UI_LISTA_NON_TROVATA` | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` |
| pgTAP | `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` |
| doc | `dbzero/ui/manual/`: tre pagine nuove (`fn_veste_corrente`, `fn_lista_colonne_livello`, `fn_lista_colonne_ricerca_full`), aggiornate `fn_resolve_lista_config`, `fn_resolve_dashboard_config`, `lista_colonna_permesso` |

Ordine: `-11` e `-12` prima di `-13…-15` (i numeri lo garantiscono).
