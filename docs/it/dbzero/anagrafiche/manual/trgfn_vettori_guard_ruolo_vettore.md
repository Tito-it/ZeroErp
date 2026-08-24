## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_vettori_guard_ruolo_vettore()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori)
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> • [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
>
Approfondimento funzioni:
> • [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)
> • [anagrafiche.trgfn_vettori_normalize](/dbzero/anagrafiche/funzioni/trgfn_vettori_normalize)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Impedisce che una riga di `anagrafiche.vettori` si agganci a un `soggetto_ruolo_id`
che **non è un vettore**. La tabella `vettori` è il dettaglio 1:1 del ruolo `VT`
(rivenditore/vettore): senza questo guard nulla vieterebbe di puntare al ruolo cliente
o fornitore dello stesso soggetto, e il documento di trasporto finirebbe intestato al
ruolo sbagliato.

Il controllo non è scritto qui: è delegato per intero a
`script.fn_guard_soggetto_ruolo(..., p_cd_int_ruolo := 'VT')`, la stessa funzione usata
dagli altri dettagli di ruolo. La regola vive in un posto solo.

---

### Aggancio

Trigger `trg_vettori_guard_ruolo_vettore_ins_upd` — `BEFORE INSERT OR UPDATE`
su `anagrafiche.vettori`.

---

### Regole applicate

`script.fn_guard_soggetto_ruolo` verifica, nell'ordine:

1. `soggetto_ruolo_id` valorizzato e `> 0` (un `NULL` o uno zero non passano);
2. esistenza del ruolo `VT` in `config.tipi_ruoli` (risoluzione `codice_interno → id`);
3. esistenza in `anagrafiche.soggetti_ruoli` di una riga con **quell'id** e
   **quel tipo ruolo**.

Il soggetto **non** viene verificato: il trigger passa `p_soggetto_id := NULL`, quindi il
controllo è «questo legame esiste ed è di tipo `VT`», non «appartiene al soggetto X».

---

### ⚠️ Il commento nel corpo promette più di quel che fa

Il codice dice «*Sostituisco `NEW.soggetto_ruolo_id` con l'ID vero (esistente)*», e in effetti
scrive `NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(...)`. Ma quella funzione, nel
ramo di successo, fa `RETURN p_soggetto_ruolo_id`: **restituisce esattamente ciò che ha
ricevuto**. Non c'è nessuna risoluzione, nessun ID che cambia.

L'assegnazione è quindi solo la forma con cui è invocato un guard che o passa o solleva.
Chi legge il commento aspettandosi che il trigger sappia *ricavare* il ruolo `VT` a partire dal
soggetto resta deluso: quel comportamento non esiste, e va fornito il `soggetto_ruolo_id`
già corretto.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SOGGETTI_RUOLI` | `script.fn_guard_soggetto_ruolo` | `soggetto_ruolo_id` nullo/non positivo, **oppure** legame inesistente o di ruolo diverso da `VT` |
| `E_COD_INT_RUOLO` | `script.fn_guard_soggetto_ruolo` | Il codice interno `VT` non esiste in `config.tipi_ruoli` (configurazione rotta) |

Entrambi passano da `script.fn_log_and_raise_error`: sono registrati in `error_log` prima
di essere sollevati.

⚠️ `E_SOGGETTI_RUOLI` copre **due cause diverse** — parametro non valido e legame
incoerente. Per distinguerle serve il `context` JSONB nel log, non il solo codice.

---

{% include-markdown "signature-core.md" %}
