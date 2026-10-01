## 📘 Documentazione Concettuale – Tabella `pagamenti.transizioni_stati_contabile`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)
> • [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga)

### 🎯 Scopo Principale

(rev 2026-08-21)

La **matrice delle transizioni ammesse** fra gli stati della **distinta contabile**.
È il grafo che `pagamenti.trgfn_vendite_contabili_guard_transizione` legge per
decidere se un cambio di stato si può fare: **nessuna regola è scritta nel codice**.

⭐ **Perché esiste.** Fino al 2026-08-21 `pagamenti` era l'unico dominio del
progetto con degli **stati** e **nessuna regola su come ci si passa** — dieci
altri domini (DDT, ordini, preventivi, contratti, resi, pratiche, commesse,
offerte, documenti fiscali) avevano già la loro matrice. Qui qualunque salto era
ammesso, compreso **uscire da uno stato dichiarato finale**.

---

### Il percorso della distinta

```text
BOZZA ──────► VALIDATA ──────► CHIUSA      (finale)
  │              │  ▲
  │              │  └──── si riapre per correggere
  │              ▼
  └──────────► ANNULLATA                   (finale)
```

| Stato | Vuol dire |
| --- | --- |
| `BOZZA` | l'operatore sta inserendo — qui **nasce la manuale** |
| `IMPORTATA` | il file è arrivato e quadra — qui nascerà l'**automatica** |
| `VALIDATA` | «ho finito, è pronta da registrare» |
| `CHIUSA` | registrata *(finale)* — le righe si lavorano ancora: tardiva, «Riprendi» |
| `ANNULLATA` | non è mai successa *(finale)* — le righe si **leggono soltanto** (dal 30-09-2026) |

⚠️ **Le due finali sono opposte per le righe**, e la differenza non la dice
`is_final`: la dice la bandiera `righe_lavorabili` del
[catalogo degli stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)
(`false` solo su `ANNULLATA`). Sotto un'annullata ogni scrittura su una riga è
rifiutata (`E_RIGA_CONTABILE_DISTINTA_ANNULLATA`), e le sue righe escono dalle
code di lavoro.

⭐ **`VALIDATA` è il gesto «ho finito di inserire»**, ed è per questo che lì
scatta la quadratura col totale dichiarato: l'errore si vede mentre l'operatore è
ancora nel flusso, non al momento di registrare.

---

### ⚠️ Tre regole che questa tabella **non** porta

Una matrice `(stato_da, stato_a)` non esprime condizioni. Tre regole vivono
quindi nel guard `pagamenti.trgfn_vendite_contabili_guard_validazione`, e **chi
legge la sola matrice non le vede**:

* **`VALIDATA → BOZZA` è solo per la distinta `MANUALE`**: l'automatica è la copia
  di un file ed è immutabile, la generata si rigenera;
* entrando in `VALIDATA`, se `importo_dichiarato` è valorizzato la **somma delle
  righe deve corrispondere**;
* ⭐ **`→ ANNULLATA` è solo per la distinta `MANUALE`** (dal 30-09-2026, D-4): la
  generata la governa il giro che l'ha prodotta. Si toglie cancellando il fondo o
  annullando la sistemazione, non annullandone la testata
  (`E_CONTABILE_ANNULLO_NON_MANUALE`).

E una terza vive in `pagamenti.trgfn_vendite_contabili_guard_chiusura`: una
distinta **non si chiude** finché ha righe pronte da registrare.

---

### ⚠️ Che cosa non è seminato, ed è una decisione

Le transizioni in **uscita da `IMPORTATA`** non ci sono: quello stato lo produce
solo l'**import da flusso**, che non esiste ancora (`enti_incasso` è a zero
righe). *Un catalogo pieno di righe irraggiungibili insegna cose false* — è la
lezione pagata con lo stato `STORNATA`. Arrivano con l'import, e sono due righe
in più nel seed.

---

### ⚠️ Il `meta` è un contratto col frontend, e oggi è spento

Sulle matrici gemelle di `vendite` e `config` il `meta` regge i **pulsanti** di
cambio stato (`action_key`, `label_key`, severità; l'icona la sceglie il frontend
dall'`action_key`), e un `CHECK` impone
che se `manuale` è vero ci siano le due chiavi.

⛔ Qui tutte le righe sono **`{"manuale": false}`**, di proposito:
`scripts/check_i18n_keys.py` cerca le `label_key` nei file di traduzione del
frontend e **fallisce** se mancano — e l'interfaccia di `pagamenti` non esiste
ancora. **Non significa «transizione automatica»: significa «non ancora esposta
come pulsante»**, e si arricchisce quando arriva l'interfaccia.

---

### Come si cambia

La sede della matrice è il changeSet `80_data/20260821-31`, che risolve gli stati
per `codice_interno` — **non** un CSV con gli id, perché gli id del catalogo delle
righe non sono un contratto. È `runOnChange`, quindi si ri-afferma a ogni migrate.

{% include-markdown "signature-core.md" %}
