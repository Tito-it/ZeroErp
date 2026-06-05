# Brief BE — allineamento `listini_versioni` post-drop CHECK strict (gap "2 giorni")

> **Target team**: BE (`dev/backend-tid`)
> **Origine**: DB agent (`dev/db-tid`), sessione 2026-04-27 — landing PR drop CHECK ridondanti
> **Impatto**: `apps/vendite/services/listini_service.py` (guard pro-attiva + mapping errori) + 1 test Django
> **Priorita'**: media — non rompe runtime (la guard Python resta piu' restrittiva del DB), ma genera incoerenza DB↔BE che a regime e' debito da chiudere

## 1. Cosa abbiamo fatto lato DB

Migration `db/changelog/migrations_v2/00_schema/catalogo/20260427-02-drop-chk-valid-dates-redundant-data-driven-mctit.yaml` droppa **4 CHECK ridondanti** post-migrazione daterange:

| Tabella | Constraint droppato | Era |
|---|---|---|
| `catalogo.articoli_componenti` | `chk_articoli_componenti_valid_dates` | `valido_al > valido_dal` |
| `catalogo.unita_misura_conversioni` | `chk_uom_conv_valid_dates` | `valido_al > valido_dal` |
| `vendite.listini_versioni` | `chk_listini_versioni_date` | `valido_al > valido_dal` |
| `vendite.listini_associazioni` | `chk_listini_associazioni_date` | `valido_al > valido_dal` |

**Motivazione**: `script.trgfn_set_validita()` costruisce `daterange(valido_dal, COALESCE(valido_al, infinity), '[]')` BEFORE INSERT/UPDATE. PostgreSQL rifiuta con SQLSTATE **22000** quando `valido_al < valido_dal` *prima* che il CHECK scatti -> i CHECK strict `>` erano codice morto + rifiutavano erroneamente `valido_al = valido_dal` (range degenere [X, X+1) di 1 giorno) bloccando il pattern stato-terminale-data-driven (chiusura same-day ammessa).

Pattern identico al precedente `20260414-22-drop-check-date-redundant` che droppava gia' su `categorie_clienti_listini` e `promo_articoli`.

**3 tabelle su 4 sono drop puliti** (zero reference BE). **`listini_versioni` non lo era**: il service Python ha guard pro-attive tarate sul CHECK strict. Il drop e' stato comunque fatto in dev (no produzione, dati ricreabili), ma serve allineamento BE per chiudere il debito.

## 2. Punti BE da allineare

### 2.1 Rimuovere guard "gap >= 2 giorni" in `_plan_versione_state_change`

[`apps/vendite/services/listini_service.py:1422-1498`](backend/apps/vendite/services/listini_service.py#L1422-L1498) — la guard intera nasce da:

> Guard critico (CHK constraint vendite.chk_listini_versioni_date richiede `valido_al > valido_dal` STRETTAMENTE): se una precedente ha `valido_dal >= nuova.valido_dal - 1` (cioe' gap < 2 giorni), l'autoclose produrrebbe `valido_al <= valido_dal` e violerebbe il CHECK.

Dopo il drop il CHECK ammette `valido_al = valido_dal`. La guard Python diventa **piu' restrittiva del DB**:
- admin attiva versione il giorno dopo l'attivazione della precedente -> autoclose della precedente con `valido_al = nuova.valido_dal - 1 = OLD.valido_dal` -> range 1 giorno
- DB ammette, service Python blocca con `E_VENDITE_VALIDATION` "decorrenza minima ammessa: ..."

**Azione**: rimuovere il blocco `for row in candidates: ErrorManager.require(nuova_valido_al > prec_valido_dal, ...)` (righe 1474-1496). Resta utile il calcolo `nuova_valido_al = nuova_valido_dal - timedelta(days=1)` per l'autoclose.

Aggiornare anche:
- commento riga 1422-1430 (guard CHK -> non piu' valida)
- messaggio mappa errori riga 614 ("chiudi la vecchia (valido_al = nuova_valido_dal - 1) e poi attiva la nuova" — il pattern resta corretto, "decorrenza minima 2 giorni dopo" diventa "decorrenza ≥ 1 giorno dopo")

### 2.2 Rimuovere mapping `chk_listini_versioni_date`

[`apps/vendite/services/listini_service.py:617-621`](backend/apps/vendite/services/listini_service.py#L617-L621) — entry nella `constraint_map`:

```python
(
    "chk_listini_versioni_date",
    "Intervallo versione non valido.",
    "valido_al deve essere maggiore di valido_dal.",
),
```

Constraint droppato -> stringa mai presente nell'`error_text` di `IntegrityError`. Codice morto. **Azione**: eliminare la tupla.

In sostituzione, se serve preservare un messaggio user-friendly per `valido_al < valido_dal` (oggi catturato da SQLSTATE 22000 daterange), mappare la stringa SQLSTATE/messaggio Postgres `"range lower bound must be less than or equal to range upper bound"` -> `E_VENDITE_VALIDATION` con detail dedicato. Oppure lasciare al middleware generico — il caso e' di fatto irraggiungibile dal flow UI normale (pannello listini calcola autoclose autonomamente).

### 2.3 Aggiornare test `test_change_state_attiva_blocked_when_autoclose_violates_chk`

[`apps/vendite/tests/services/test_listini_service.py:717-754`](backend/apps/vendite/tests/services/test_listini_service.py#L717-L754) testa esattamente lo scenario "gap=1 giorno -> guard fail-fast". Dopo la rimozione di 2.1 il test diventa **logicamente obsoleto** (l'invariante non esiste piu').

**Azione**: eliminare il test. **Non** sostituirlo con uno equivalente "gap=0 -> guard fail-fast" — il drop CHECK ammette anche quel caso (versione di durata 0 giorni *non* ha senso applicativo, ma se serve un guard e' un'invariante di dominio nuova da definire, non un porting del test esistente).

Se vuoi conservare la copertura "il service NON tocca il DB quando la transizione e' invalida", ci sono altri test nello stesso file (es. precondizioni `count_active_righe_versione > 0`) — la rimozione del singolo test non scopre buchi.

### 2.4 Cleanup commento riga 1506-1508

[`listini_service.py:1506`](backend/apps/vendite/services/listini_service.py#L1506) cita "valido_al = nuova.valido_dal - 1 sulle precedenti" come pattern per non urtare `ex_listini_versioni_no_overlap`. Resta corretto: l'EXCLUDE GIST e' indipendente dal CHECK droppato. **Nessuna azione**, segnalo solo per chiarezza.

## 3. Rischio runtime durante la finestra DB-merged / BE-non-allineato

Nessuno bloccante. La guard Python resta in vigore -> admin che proverebbe gap=1 riceve fail-fast `E_VENDITE_VALIDATION` ("decorrenza minima 2 giorni"). Comportamento osservabile **invariato** dal punto di vista UI; cambia solo dopo la rimozione lato BE.

## 4. Conferma di land

Una volta mergiato il fix BE:

- riapri questo brief in `work-done/` con header LANDED
- DB non ha ulteriori azioni (il drop e' gia' on-branch)
- smoke UI consigliato: attivare versione ATTIVA con precedente che inizia il giorno prima -> autoclose deve funzionare end-to-end

## 5. Riferimenti

- DB migration: [20260427-02-drop-chk-valid-dates-redundant-data-driven-mctit.yaml](../../../../db/changelog/migrations_v2/00_schema/catalogo/20260427-02-drop-chk-valid-dates-redundant-data-driven-mctit.yaml)
- DB pgTAP esteso: [test-articoli-componenti-immutabilita.sql](../../../../db/pgtap/catalogo/test-articoli-componenti-immutabilita.sql) — casi 17-18 (regressione same-day)
- Precedente analogo (drop su altre tabelle): [20260414-22-drop-check-date-redundant-mctit.yaml](../../../../db/changelog/migrations_v2/00_schema/vendite/20260414-22-drop-check-date-redundant-mctit.yaml)
- Trigger trgfn_set_validita: [20260412-05-create-trgfn-set-validita-mctit.yaml](../../../../db/changelog/migrations_v2/20_code/script/20260412-05-create-trgfn-set-validita-mctit.yaml)
- Brief originario BE -> DB (BoM relax): contesto sessione 27-04-2026; la richiesta era `>` -> `>=`, abbiamo scelto drop (allineamento al precedente 20260414-22) e ampliato il perimetro alle 4 tabelle outlier.
