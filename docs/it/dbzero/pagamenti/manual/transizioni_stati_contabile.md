## 📘 Documentazione Concettuale – Tabella `pagamenti.transizioni_stati_contabile`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta di cui regola gli stati
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — gli stati, con le bandiere che la matrice non porta
> * [pagamenti.transizioni_stati_contabile_riga](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) — la matrice gemella, per le righe
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) — il guard che la legge
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — le condizioni che la matrice non sa esprimere
> * [pagamenti.trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) — la condizione sulla chiusura

---

### 🎯 Scopo Principale

La matrice delle transizioni ammesse fra gli stati della distinta contabile. È il grafo
che [trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione)
legge per decidere se un cambio di stato si può fare: **nessun grafo è scritto nel codice**.

⭐ Senza matrice qualunque salto sarebbe ammesso, compreso **uscire da uno stato
dichiarato finale**: è la stessa ragione per cui ce l'hanno gli altri domini con degli
stati (DDT, ordini, preventivi, contratti, resi, pratiche, commesse, offerte, documenti
fiscali).

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
| `BOZZA` | l'operatore sta inserendo: qui **nasce la manuale** |
| `IMPORTATA` | il file è arrivato e quadra: qui nascerà l'**automatica** |
| `VALIDATA` | «ho finito, è pronta da registrare» |
| `CHIUSA` | registrata *(finale)*: le righe si lavorano ancora (tardiva, «Riprendi») |
| `ANNULLATA` | non è mai successa *(finale)*: le righe si **leggono soltanto** |

⚠️ **Le due finali sono opposte per le righe**, e la differenza non la dice `is_final`: la
dice la bandiera `righe_lavorabili` del
[catalogo degli stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) (`false` solo su
`ANNULLATA`). Sotto un'annullata ogni scrittura su una riga è rifiutata
(`E_RIGA_CONTABILE_DISTINTA_ANNULLATA`), e le sue righe escono dalle code di lavoro.

⭐ **`VALIDATA` è il gesto «ho finito di inserire»**, ed è per questo che lì scatta la
quadratura col totale dichiarato: l'errore si vede mentre l'operatore è ancora nel flusso,
non al momento di registrare.

⚠️ La matrice vale sui **cambi** di stato, non sulla nascita: una distinta può nascere in
uno stato qualunque, e il giro dei fondi fattura crea le sue direttamente in `VALIDATA`.

---

### ⚠️ Le regole che questa tabella non porta

Una matrice `(stato_da, stato_a)` non esprime condizioni. Tre regole vivono quindi in
[trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione),
e **chi legge la sola matrice non le vede**:

* entrando in `VALIDATA`, nessuna riga può essere ancora da lavorare e, se
  `importo_dichiarato` è valorizzato, la **somma delle righe deve corrispondere**;
* **`VALIDATA → BOZZA` è solo per la distinta `MANUALE`**: l'automatica è la copia di un
  file ed è immutabile, la generata si rigenera;
* ⭐ **`→ ANNULLATA` è solo per la distinta `MANUALE`**: la generata la governa il giro che
  l'ha prodotta. Si toglie cancellando il fondo o annullando la sistemazione, non
  annullandone la testata (`E_CONTABILE_ANNULLO_NON_MANUALE`).

Una quarta vive in
[trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura):
una distinta **non si chiude** finché ha righe pronte da registrare.

---

### ⚠️ Le uscite da `IMPORTATA` non sono seminate, ed è una decisione

Quello stato lo produce solo l'**import da flusso**, che non esiste ancora. *Un catalogo
pieno di righe irraggiungibili insegna cose false*: è la lezione pagata con lo stato
`STORNATA`. Le transizioni arrivano con l'import, e sono due righe in più nel seme.

---

### ⚠️ Il `meta` è un contratto col frontend, e oggi è spento

Sulle matrici gemelle di `vendite` e `config` il `meta` regge i **pulsanti** di cambio stato
(`action_key`, `label_key`, severità; l'icona la sceglie il frontend dall'`action_key`), e un
`CHECK` impone che se `manuale` è vero ci siano le due chiavi.

⛔ Qui tutte le righe dichiarano `manuale` falso, di proposito: lo script dei controlli i18n
cerca le `label_key` nei file di traduzione del frontend e fallisce se
mancano. **Non significa «transizione automatica»: significa «non esposta come pulsante»**, e si
arricchisce quando i pulsanti di cambio stato della distinta passeranno dalla matrice.

---

### La matrice si cambia nel seme

La sede della matrice è un changeSet di dati che risolve gli stati per `codice_interno`
— **non** un CSV con gli id, perché gli id del catalogo delle righe non sono un contratto. È
`runOnChange`: si ri-afferma quando il seme cambia.

---

### Test

`db/pgtap/pagamenti/test-transizioni-stati-contabili.sql` — il grafo seminato, le uscite da
`IMPORTATA` assenti, `STORNATA` in nessuna transizione, nessuna transizione dichiarata
«manuale», una transizione ammessa che passa e una che no, nessuna uscita da uno stato
finale, la nascita non vincolata dalla matrice.

---

### Note di migrazione

* 2026-08-21 — nasce la matrice: fino ad allora `pagamenti` era l'unico dominio con degli
  stati e nessuna regola su come ci si passa.
* 2026-09-18 — entrando in `VALIDATA` si chiede anche che ogni riga sia stata guardata; la matrice non cambia.
* 2026-09-30 — l'annullo diventa un gesto della sola distinta manuale; la matrice non
  cambia, la regola è nel guard di validazione.

---

{% include-markdown "signature-core.md" %}
