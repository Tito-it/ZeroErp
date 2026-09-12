## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_commesse_emittibili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
> • [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)  
>
### 🎯 Scopo Principale
(latest review 12-09-2026)  
Elenca le commesse candidate all'emissione verso `attivita_fatturabili`, applicando i criteri minimi di prontezza operativa.

> ⭐ **Dal 2026-09-09 il criterio non è più «righe `NON_EMESSA`»: si legge la
> CLASSE** da [vw_commesse_attivita_emittibilita](/dbzero/vendite/manual/vw_commesse_attivita_emittibilita)
> (whitelist `PRONTA`, `RIFIUTATA`, `NON_APPROVATA`). E **dal 2026-09-12 la
> classe è quella vista dal giro**: vedi la sezione in fondo.

---

### Regole principali

* Funzione read-only (`STABLE`).
* Restituisce solo commesse con:
  * stato `emittibile = true` in `vendite.stati_commessa`
  * almeno una riga `commesse_attivita` con `stato_emissione = NON_EMESSA`.
* `p_competenza_mese` e` opzionale:
  * se presente, viene normalizzato al primo giorno del mese
  * filtra le righe attivita` sulla stessa competenza.
* Filtri opzionali di perimetro:
  * `p_billing_account_id`
  * `p_utility_id`
* `p_limit` normalizzato:
  * default `1000`
  * massimo `10000`.

---

### Output

Per ogni commessa idonea restituisce:

* identificativi principali (`commessa_id`, `codice`, `stato_commessa_id`, `stato_commessa`)
* perimetro billing (`billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`)
* competenza testata (`competenza_dal`, `competenza_al`)
* `total_non_emesse` (numero righe ancora da emettere)

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_commesse_emittibili(
  p_competenza_mese => DATE '2026-02-01',
  p_billing_account_id => NULL,
  p_utility_id => NULL,
  p_limit => 500
);
```

---

---

### ⭐⭐ Il rilancio rivede le proprie commesse: `p_emit_batch_id` (rev 2026-09-12)

Il pull ha **due cancelli in serie**: questa funzione decide **quali commesse
visitare**, [fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa)
decide **quali righe emettere**. Entrambi escludono le righe **trattenute** da un
lotto in gioco, con un'eccezione: il lotto che sta girando non esclude **sé
stesso** — al rilancio di un pull fallito i propri documenti sono `TRATTENUTA`
(l'esito `ERRORE` è scritto fuori dal savepoint che ha rimesso le righe a
`NON_EMESSA`), e vanno ripresi.

⛔ **Fino al 12-09-2026 l'eccezione stava solo nel secondo cancello.** Questa
funzione aveva la whitelist secca e nessuna identità: al rilancio scartava la
commessa coi propri documenti, il pull visitava **zero** commesse, chiudeva
`COMPLETATO`, ritirava le proprie segnalazioni — e non emetteva niente. In
silenzio. Provato il 12-09 su LTF-0010972/3.

Da oggi:

* **`p_emit_batch_id uuid DEFAULT NULL`**, in coda — stesso nome e stessa
  semantica dell'emit, così il backend consegna **un** dato a **due** funzioni.
  Il lotto si risolve con [fn_lotto_da_emit_batch](/dbzero/vendite/manual/fn_lotto_da_emit_batch);
* la whitelist si applica alla **classe vista dal giro**,
  [fn_classe_emittibilita_per_giro](/dbzero/vendite/manual/fn_classe_emittibilita_per_giro):
  una riga `TRATTENUTA` soltanto dal lotto corrente è `PRONTA`. È la **stessa**
  riga che legge l'emit: la regola vive in un posto solo;
* trattenuta da un **altro** lotto in gioco → la commessa non si visita (niente
  pull a vuoto registrato come lavorato, che era l'effetto voluto);
* `p_emit_batch_id` `NULL` → nessuna auto-esclusione, il comportamento
  precedente. ⛔ **Il pull deve passarlo**: senza, scarta i propri documenti in
  silenzio. Il backend fa il guard su `lock_batch_id` **prima** di chiamare
  questa funzione.

`RETURNS TABLE` invariato; i chiamanti a sette argomenti non cambiano
comportamento (`DROP` + `CREATE`: un parametro in più con default è un
**overload**, non una sostituzione).

Presidio: `db/pgtap/vendite/test-pull-non-prende-trattenuti-v1.sql`, test 5-9
— la discovery da sola (P-5-bis) **e** il percorso intero discovery → emit
(P-5-ter), che è il test che mancava. Brief:
`brief-db-rilancio-step-non-rivede-le-proprie-commesse` (D1).

---

### Emissione mirata: `p_gruppi` (rev 2026-07-27)

Parametro `text[]`, default `NULL`. Restringe alle commesse che contengono
almeno una riga di un gruppo richiesto.

**Perché.** Questa è la discovery dello step di *pull*: il task cicla commessa
per commessa con un savepoint ciascuna. Senza filtro, un'emissione mirata su un
preventivo farebbe comunque il giro di tutte le commesse emittibili del
perimetro — savepoint, chiamata all'emit (già filtrato), zero righe. Nessun
danno ai dati, ma un log che dice «ho lavorato 40 commesse» per un'operazione
che ne riguardava una sola è fuorviante quando poi si va a leggere cos'è
successo.

⚠️ **Non sostituisce il filtro per riga dentro l'emit.** Qui si sceglie *quali
commesse* visitare, lì *quali righe* emettere. Una commessa multi-sorgente che
contiene sia il preventivo richiesto sia il contratto non richiesto passa
comunque il filtro: sarà l'emit a prendere solo le righe giuste.

Con `p_gruppi` valorizzato anche `total_non_emesse` segue il filtro: è il numero
di righe che l'emit lavorerà davvero su quella commessa.

> **Prerequisito di entrambe le discovery**: la commessa deve essere in uno
> stato **emittibile** (`stati_commessa.emittibile = true`). È il criterio 1,
> valutato prima di ogni filtro di perimetro.

{% include-markdown "signature-core.md" %}
