## 📘 Documentazione Concettuale – Funzione `vendite.fn_contratto_sovrapposto(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
>
> Funzioni correlate:
> [vendite.fn_chiudi_contratto_per_successione](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione)
> [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)
>
> Contesto di sviluppo:
> [Brief DB — successione contratti su overlap](/dev/work-done/brief-db-offerta-push-successione-contratto-overlap)

---

### 🎯 Scopo Principale

`vendite.fn_contratto_sovrapposto(...)` risponde a una sola domanda, **senza
modificare nulla**: *«per questo cliente/utility e in questo periodo esiste già
un contratto attivo?»*. È il **rilevamento** del meccanismo generico di
successione contratti (il "chiudi il vecchio e apri il nuovo").

Restituisce l'`id` del contratto che si sovrappone, oppure `NULL` se la finestra
è libera. Essendo di **sola lettura** (`STABLE`), può essere usata anche dal
backend come *pre-check* per mostrare il conflitto all'utente **prima** di
tentare la creazione del nuovo contratto (anteprima FE), senza rischiare l'errore
grezzo del database.

È un meccanismo **di dominio contratti**, non legato all'offerta. I consumatori
sono due: il push offerta→contratto, e l'attivazione del contratto attraverso
[`script.fn_check_contratto_sovrapposto`](/dbzero/script/funzioni/fn_check_contratto_sovrapposto),
che la leggono sia il pulsante «Attiva» sia il guard di transizione.

⚠️ «Attivo» qui sopra vuol dire **vincolante**: conta anche un contratto
**cessato**, perché il criterio è `partecipa_overlap_snapshot` (né bozza né
annullato), lo stesso del vincolo di esclusione.

---

### Come decide

Il contratto è considerato "in conflitto" quando coincidono **tutti** gli
attributi della chiave del vincolo di esclusione `ex_contratti_no_overlap` e i
periodi si sovrappongono:

- stesso `billing_account_id`, `istanza_utility_id`, `utility_id`, `ambito`;
- contratto **non abortito** (`NOT is_abortito_snapshot`): i contratti annullati
  non contano, esattamente come per il vincolo di esclusione;
- le due finestre temporali si sovrappongono (operatore `&&`).

**Finestra del nuovo contratto** — costruita internamente con la **stessa
formula** della colonna generata `contratti.validita`:

```sql
daterange(COALESCE(p_valido_dal, '-infinity'), COALESCE(p_valido_al, 'infinity'), '[]')
```

Il `COALESCE` simmetrico è essenziale (linee-guida-sql §7b): garantisce che il
confronto `&&` lavori su rappresentazioni interne identiche anche quando
`valido_al` è `NULL` (contratto perpetuo), evitando falsi negativi.

**Quale contratto restituisce** — il vincolo di esclusione garantisce che i
contratti non abortiti **esistenti** non si sovrappongano tra loro, ma una
finestra candidata ampia può sovrapporne più d'uno. In quel caso la funzione
restituisce l'**incumbent**: prima il contratto la cui validità *contiene* la
data di decorrenza del nuovo, poi il più recente (`ORDER BY ... LIMIT 1`).
Eventuali conflitti residui sono comunque intercettati dal *backstop* del
consumatore (vedi `fn_push_offerta_a_contratto`).

---

### Parametri

| Parametro              | Tipo      | Note                                                                 |
| ---------------------- | --------- | -------------------------------------------------------------------- |
| `p_billing_account_id` | `bigint`  | Dichiarato `bigint` (non `integer`) per accettare via *widening* sia i chiamanti `contratti` (integer) sia `offerte_commerciali` (bigint). |
| `p_istanza_utility_id` | `bigint`  | Come sopra.                                                          |
| `p_utility_id`         | `integer` | Coincide con il tipo in entrambe le tabelle.                         |
| `p_ambito`             | `varchar` | Tipicamente `'COMMODITY'` (default di `contratti.ambito`).           |
| `p_valido_dal`         | `date`    | Data inizio della finestra candidata.                               |
| `p_valido_al`          | `date`    | Data fine; `NULL` = contratto perpetuo.                             |

---

### 📦 Output

| Campo            | Tipo     | Descrizione                                                       |
| ---------------- | -------- | ----------------------------------------------------------------- |
| `RETURNS bigint` | bigint   | `id` del contratto sovrapposto (incumbent), oppure `NULL`.        |

---

### Codici errore

Nessuno: la funzione **non solleva mai** errori. È un puro rilevamento. La
gestione del conflitto (errore parlante o successione) spetta al chiamante.

---

### Esempio d'uso

```sql
-- C'è già un contratto attivo per questa quintupla nel 2026?
SELECT vendite.fn_contratto_sovrapposto(
    173, 197, 5, 'COMMODITY', DATE '2026-05-26', NULL
);
-- 4821  -> esiste il contratto 4821 sovrapposto
-- NULL  -> finestra libera, si può creare senza successione
```

---

{% include-markdown "signature-core.md" %}
