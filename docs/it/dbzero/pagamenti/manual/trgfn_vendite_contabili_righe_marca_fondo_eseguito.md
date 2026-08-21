## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito`

### 🎯 Scopo Principale

(rev 2026-08-22)

Quando la riga contabile nata da un **fondo fattura** entra in uno stato
**registrato** (`POSTATA`), l'atto che l'ha generata passa a **`ESEGUITO`**.

In parole semplici: *appena il trasferimento è registrato in contabilità, il
fondo smette di essere una cosa da lavorare e diventa una cosa fatta.*

---

### ⭐ Perché un trigger e non una riga dentro la madre del posting

Perché **scatta sul fatto**, non su chi se lo ricorda. La madre del posting non
è l'unica strada per cui una riga contabile può finire registrata: c'è la
correzione a mano, arriverà l'import da flusso bancario, arriverà il
ri-posting. Una riga di codice dentro *una* di quelle strade protegge quella
strada; un trigger sulla tabella protegge **il dato**.

### ⭐ E il guadagno è strutturale

Tutti e tre i lettori dei fondi filtrano sullo **stato dell'atto**:

| Chi | Filtra | Effetto del quarto stato |
| --- | --- | --- |
| `vendite.fn_sync_contabili_fondo_fattura` | `ASSEGNATO` | il ciclo non vede più il fondo registrato |
| `vendite.fn_applica_fondi_fattura` | `DISPONIBILE` | non lo applica una seconda volta |
| `vendite.vw_fondi_fattura_da_decidere` | `DISPONIBILE` | non lo propone come «non più capiente» |

Un fondo che esce da `ASSEGNATO` **esce da tutti e tre gratis**, senza che
nessuno dei tre cambi. È così che i due difetti storici — il giro che
riscriveva una riga già registrata, e il fondo interamente registrato che si
auto-annullava — smettono di essere *raggiungibili* invece di essere tamponati
uno per uno.

---

### Quando si attiva

* `AFTER INSERT OR UPDATE OF stato_id` su `pagamenti.vendite_contabili_righe`.
* Fase **`z90`** e non `a10`: non è un guard che rifiuta, è un **effetto che
  segue**. Va dopo i guard, che devono poter rifiutare la riga prima che l'atto
  venga marcato.

### Tre condizioni, e nessuna è decorativa

| Condizione | Perché |
| --- | --- |
| `fondo_source_id IS NOT NULL` | la riga non viene da un fondo: niente da marcare — ed è il caso della stragrande maggioranza delle righe |
| `attivo IS TRUE` | una riga disattivata non è in nessun conto: dire che il denaro si è mosso sarebbe falso |
| l'atto è ancora `ASSEGNATO` | idempotenza: un ri-posting non cambia nulla, e un atto `ANNULLATO` o `DISPONIBILE` non viene resuscitato |

> ⚠️ **«Stato registrato» oggi è `POSTATA` e basta**, confrontato per
> `codice_interno` (la chiave immutabile, mai `codice`). Non si è aggiunta una
> quarta bandiera al catalogo accanto a `is_postabile` / `is_final` /
> `richiede_abbinamento`: sarebbe una colonna per un insieme di **uno**. Il
> giorno in cui gli stati registrati diventassero due, la bandiera diventa la
> mossa giusta.

---

### ⚠️ Scrive da `pagamenti` verso `vendite`: tre cose verificate

1. `vendite.fatture_fondi_fattura_source` **non ha RLS**, quindi il trigger non
   incontra il problema «il padre non lo vedo» — che avrebbe richiesto una
   `SECURITY DEFINER`;
2. il lock colonne su quella tabella blocca `importo`, `fattura_sorgente_id`,
   `tipo_fondo_fattura_id` e `origine`: **`stato` non è fra quelle**;
3. scrivendo `stato` fa scattare `vendite.trgfn_fondi_source_guard_transizione`
   — ed è la ragione dell'**ordine obbligato** con cui è stato applicato:
   prima il vocabolario (`CHECK`), poi la matrice, poi questo trigger.

### ⚠️ Error handling

Nessun errore proprio. Se il passaggio di stato non fosse ammesso, a parlare
sarebbe la matrice del fondo (`E_FONDO_STATO_NON_AMMESSO`, `CONFLITTO_STATO`) —
ma la condizione `stato = 'ASSEGNATO'` dell'`UPDATE` fa sì che non accada.

### Presidio

`db/pgtap/vendite/test-fondo-fattura-eseguito.sql` — compresa l'**invariante**
su cui regge `vendite.fn_saldo_sorgente_fondo`: *nessun fondo `ASSEGNATO` ha una
riga già registrata*.

{% include-markdown "signature-core.md" %}
