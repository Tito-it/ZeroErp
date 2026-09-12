## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_commesse_respinte`

> 👀 **Vedi anche**
>
[vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
> [vw_dash_competenza_errori](vw_dash_competenza_errori.md)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Una riga per **commessa respinta** da un giro di fatturazione, con il **suo**
motivo. Risponde alla domanda che il cruscotto non sapeva ancora fare: non
«quante ne sono fallite», ma **quali, e perché** — che è l'unica forma su cui
qualcuno può agire.

Il pull delle attività lavora una commessa alla volta, ognuna dentro il proprio
savepoint: se una fallisce, il giro prosegue. Il task si chiude in errore
*parziale* e l'elenco delle respinte esisteva solo nel diario. Da qui si legge.

---

### Semantica

| Colonna | Che cos'è |
| --- | --- |
| `commessa_id`, `commessa_codice` | la commessa respinta. L'id arriva da `meta -> 'context' ->> 'commessa_id'`, cioè da un **campo strutturato** del log |
| `error_code` | il codice con cui il giro l'ha rifiutata (oggi `E_PULL_COMMESSA`) |
| `messaggio` | la frase del diario: dice *quale* commessa |
| `dettaglio` | il perché. ⚠️ Oggi è un **dump tecnico** — vedi le note |
| `respinta_il` | quando. È un **fatto con la sua data**, non uno stato |
| `lotto_id`, `lotto_codice`, `stato_lotto`, `competenza_mese` | il giro in cui è successo |
| `emittente_soggetto_ruolo_id`, `emittente_ragione_sociale` | per chi |

Scope emittente in-vista da GUC (**fail-closed**), `security_invoker = on`.

---

### ⛔ Perché legge il diario e non il `meta` del task

La sorgente che sembra ovvia è `fatturazione_lotti_task_runs.meta ->
'commesse_fallite'`: è lì che il pull scrive l'elenco. **Ed è la sorgente
sbagliata.** Il backend lo scrive troncato:

```python
"commesse_fallite": [e.item for e in esito.errori][:5]
```

e lo dichiara nel proprio commento — *«il meta è una traccia per il cockpit, il
dettaglio completo sta sui log di lotto»*. Con **sei** commesse respinte
l'operatore ne vedrebbe cinque, e la sesta sparirebbe senza che niente lo dica.

⭐ Il log di lotto è invece completo, e porta il `commessa_id` in un campo
strutturato: ci si aggancia **per chiave**, non leggendo il numero dentro la
frase «Errore emissione commessa 34137» — che è prosa, e cambia il giorno che
qualcuno la riscrive meglio.

⚠️ Presidiato da `db/pgtap/vendite/test-vw-dash-commesse-respinte-v1.sql`, che
costruisce **sei** respinte e pretende di vederle tutte e sei.

---

### Esempio d'uso

```sql
-- Che cosa non è passato nella competenza di settembre, e perché?
SELECT commessa_codice, error_code, respinta_il, messaggio
FROM vendite.vw_dash_commesse_respinte
WHERE competenza_mese = DATE '2026-09-01'
ORDER BY respinta_il DESC;
```

---

### Note operative

* ⚠️ **`dettaglio` è ancora un dump tecnico** — eccezione Python, `DETAIL`,
  `HINT`, `CONTEXT` e stack PL/pgSQL in una stringa sola. Il motivo di dominio
  («ROOT source mancante per commessa 34137») c'è dentro, ma a metà: perché sia
  leggibile **a video** deve arrivare in un campo suo da `item_failed`, lato
  backend. La colonna è già pronta ad accoglierlo.
* ⭐ **`respinta_il` è una data, non uno stato.** Non esiste una colonna
  `esito = 'RESPINTA'`, ed è una scelta: uno stato derivato resterebbe acceso
  anche dopo che un giro successivo ha ripreso la commessa, e chi legge non
  avrebbe modo di sapere che sta guardando una fotografia vecchia.
* ⚠️ **Zero righe non significa «nessuna respinta».** Senza
  `app.current_user_id` lo scope è vuoto e la vista è vuota: è fail-closed, non
  un dato. Interrogandola da `psql` va impostato il contesto.
* La vista **non ha dipendenti** ed è ritirabile con un `DROP`. È il motivo per
  cui esiste invece di due colonne su `vw_dash_competenza_gruppi`: là il
  rollback avrebbe dovuto ricreare da una copia congelata
  `vw_dash_competenza_gruppi_riepilogo`, che da quella vista dipende.
* Il drill-down mostra la bandiera con un **join** a questa vista: nessuna
  colonna aggiunta a una vista da 30 colonne.

Origine: `docs/it/dev/work-done/brief-residuo-fatturabili-e-bandiere-esito-parziale.md`, D3.
