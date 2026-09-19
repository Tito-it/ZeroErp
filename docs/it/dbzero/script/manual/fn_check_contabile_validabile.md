## 📘 Documentazione Concettuale – Funzione `script.fn_check_contabile_validabile()`

> 👀 **Vedi anche**
>
> **Chi la chiama:**
>
> • [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — il guard che solleva il primo motivo entrando in `VALIDATA`
> • il backend, nel dettaglio della distinta (`can_validare` / `validazione_blocco_reason` / `_reason_key` / `_dettaglio`) — *passo BE-1 del brief*
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — la bandiera `lavorata`
>
> **La gemella:** [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile) · la regola: [linee-guida-sql §12.5](/linee-guida-sql)
>
> **Piano:** [brief-db-validata-e-registrazione-tardiva](/dev/work-done/brief-db-validata-e-registrazione-tardiva) §2.1 (D20-a), §4 P-3

---

### 🎯 Scopo Principale
(scritta il 18-09-2026)

Elenca i motivi, **ordinati**, che impediscono di portare una distinta contabile
a `VALIDATA` — il gesto *«ho finito di inserire, è pronta da registrare»*
(D14-a-bis). Risponde `[]` quando si può.

È la risposta al terzo collaudo in-app (Tid, 18-09-2026): si validava — e si
registrava — con righe **ancora da abbinare** sotto, che alla chiusura restavano
senza strada. **`VALIDATA` = «ogni riga è stata guardata»**: una riga che nessuno
ha guardato è lavoro non finito, e dopo la registrazione non avrebbe più nessuno
che la guardi.

---

### I due motivi, nell'ordine in cui li nomina

L'ordine è il **contratto**: il guard solleva il primo — prima il lavoro non
finito, poi i conti.

| # | `reason` | Quando | `codice` | `valori` |
| --- | --- | --- | --- | --- |
| 1 | `RIGHE_NON_LAVORATE` | righe **attive** in uno stato con `lavorata = false` (`IMPORTATA`, `DA_ABBINARE`) | `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` (nuovo) | `(codice distinta, quante)` — il dettaglio porta anche gli id |
| 2 | `TOTALE_NON_QUADRA` | `p_importo_dichiarato` non è `NULL` e la somma delle righe attive — **`SCARTATA` compresa** — non corrisponde | **riuso** `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` | `(codice distinta, dichiarato, somma)` — gli stessi tre di prima; il dettaglio porta `campo = importo_dichiarato` |

⭐ **Quali stati siano «non lavorati» lo dice il catalogo**, non un elenco
scritto qui: la bandiera `lavorata` di `vendite_contabili_righe_stati` (D20-a).
La **sospesa è stata guardata** — ha un motivo, sta nella coda «Sospese», e con
D20-b si registra anche in ritardo: passa. `IS NOT TRUE` e non `= false`: uno
stato nuovo non classificato cade nel rifiuto, non nel silenzio.

Le `reason_key` sono `pagamenti.distinte.validazione_reason.{righe_non_lavorate,
totale_non_quadra}` — un **debito verso il frontend** (FE-6): senza la voce nei
locales il pulsante spento mostra il codice macchina.

---

### ⭐ Perché il dichiarato è un parametro, e non si rilegge per id

`fn_check_contabile_validabile(p_contabile_id, p_importo_dichiarato)`: due
parametri, **nessun default**.

Il guard di validazione gira `BEFORE ROW`: quando chiama la check, il dichiarato
che sta **entrando** nella riga non è ancora nella tabella. Con
`UPDATE … SET importo_dichiarato = 199, stato_id = VALIDATA` in un'istruzione sola
— ed è così che il collaudo e i pgTAP la scrivono — una check che rileggesse il
dichiarato per id verificherebbe il totale di **ieri**: passerebbe un dichiarato
sbagliato scritto nello stesso gesto, senza nessun errore.

⇒ Chi chiama passa il dichiarato che **vede**: il guard `NEW.importo_dichiarato`,
il backend `c.importo_dichiarato`. `NULL` è un valore legittimo (*«questa
distinta non dichiara niente»*: sulla `MANUALE` il dichiarato è facoltativo, D12)
e per questo il parametro non ha un default — dimenticarlo deve **non compilare**,
non voler dire «nessun totale». È la forma di `fn_check_scadenza_di_fattura` e di
`fn_check_riga_magazzino`: una check si scrive sui **valori** che le interessano e
legge dalla tabella il resto.

Presidio: `test-contabile-validabile-v1` test 11 — e una mutazione (`OLD` al
posto di `NEW` nel guard) lo fa cadere da solo.

---

### ⭐ Una sede sola per il predicato

Il guard **non riscrive** il predicato: la **chiama** e solleva il codice del
primo motivo con `script.fn_raise_primo_motivo_se_presente`. Il backend legge lo
stesso elenco per spegnere «Porta a VALIDATA» col perché e per mostrare *righe per
stato* nel dialog di validazione. Tooltip e rifiuto non «coincidono oggi»: **non
possono divergere**.

⚠️ La madre del posting **ripete** la quadratura al momento di registrare
(passo 4 di `fn_posta_contabile`): fra la validazione e la registrazione le righe
possono essere cambiate. Non è una seconda sede della regola di validazione — è
la stessa domanda fatta in un altro momento, ed era già così.

---

### ⚠️ `SECURITY INVOKER`, e legge sotto la row security

Legge la testata e le sue righe con la RLS del perimetro incassi. Una distinta
che **non si legge** — inesistente, o di un altro — solleva
`E_CONTABILE_NON_TROVATA` (404), con la stessa risposta per i due casi. ⛔
Rispondere `[]` sarebbe *«si può validare»* detto di una cosa che non si vede.

---

### Codici errore

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` | `CONFLITTO_STATO` | motivo 1 |
| `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` | `DATO_ERRATO` | motivo 2 — riusato, stessi valori del guard che lo sollevava prima |
| `E_CONTABILE_NON_TROVATA` | `NON_TROVATO` | la distinta non si legge |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | `TECNICO` | `p_contabile_id` nullo o `<= 0`: un chiamante rotto |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio (salvo i
due guard di chiamata). Ritorna `[]` se l'azione è permessa, altrimenti un array
JSONB **ordinato** di `{codice, reason, reason_key, dettaglio, valori}` — chi
solleva prende il **primo**. ⛔ Il `reason` non porta il prefisso `E_`.

Presidio: `db/pgtap/pagamenti/test-contabile-validabile-v1.sql` (16 asserzioni).

{% include-markdown "signature-core.md" %}
