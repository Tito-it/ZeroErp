## 📘 Documentazione Concettuale – Funzione `vendite.fn_applica_cancellazione_fondo_fattura`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — l'atto che si cancella
> * [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura) — il fondo applicato alla fattura figlia
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe contabili nate dall'atto
>
> Approfondimento funzioni:
>
> * [vendite.fn_check_fondo_cancellabile](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile) — il criterio, che sta altrove
> * [vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura) — chiamante: il gesto «cancella il fondo», con `governa_fondo_fattura`
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — chiamante: l'annullo del riporto, col livello sull'area `pagamenti`
> * [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — chiamante: il reset dei fondi, dentro i verbi del reset del lotto
> * [pagamenti.trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto) — il guard delle righe contabili, di cui apre la porta
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — chi decide su un fondo, e come
> * [Architettura permessi](/guide/architettura-permessi-e-autorizzazioni) §7.4 — l'app esegue i verbi, non le primitive

---

### 🎯 Scopo Principale

La **primitiva** del gesto «cancella il fondo»: cancella un atto di fondo fattura **che non è
ancora diventato un fatto**, oppure **rifiuta, dicendo perché**. Non chiede permessi: lo fa chi
la chiama.

---

### Chi la chiama, e con quale permesso

È riservata al proprietario: l'applicazione non la può eseguire. Ci si arriva da tre verbi, e
ognuno chiede il suo permesso prima di chiamarla:

| Chi la chiama | Il permesso che chiede |
| --- | --- |
| [`vendite.fn_cancella_fondo_fattura`](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura), il gesto dell'elenco «Fondi da decidere» | l'azione `governa_fondo_fattura` |
| [`pagamenti.fn_annulla_sistemazione`](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione), sul riporto confermato | il livello `TUTTO` sull'area `pagamenti` |
| [`vendite.fn_reset_fondi_fattura`](/dbzero/vendite/funzioni/fn_reset_fondi_fattura), dentro i verbi del reset del lotto | il permesso del verbo del reset |

⭐ È il motivo per cui la primitiva esiste: se il permesso stesse qui, chi annulla una sistemazione
dovrebbe avere anche `governa_fondo_fattura`.

**Il perimetro.** Gira come proprietario, fuori dalla row security, quindi il perimetro lo rimette
lei, una volta, sull'atto: l'azienda dell'atto dev'essere fra quelle di chi agisce. Fuori dal
perimetro l'atto «non c'è» (`E_FONDO_NON_TROVATO`, la stessa risposta di un atto inesistente).
Tutto il resto discende dall'atto.

---

### ⭐ Si CANCELLA, non si annulla

Il piano originale proponeva il passaggio ad `ANNULLATO` con motivo obbligatorio. È superato:
il reset dei fondi cancella già l'atto non eseguito invece di riportarlo a `DISPONIBILE`, perché
`ANNULLATO` portava tre significati diversi.

> *Un atto che non è mai diventato un fatto non lascia una riga di registro:
> lascia il posto vuoto che aveva prima.*

---

### Il criterio non è qui

Sta in [`vendite.fn_check_fondo_cancellabile`](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile),
che la primitiva legge **una volta sola** e mappa su quattro codici:

| Motivo del criterio | Codice sollevato | Che cosa dice all'operatore |
| --- | --- | --- |
| `ATTO_NON_TROVATO` | `E_FONDO_NON_TROVATO` | non esiste, o non è tuo: indistinguibili di proposito |
| `ATTO_ESEGUITO` · `RIGA_REGISTRATA` · `CONTABILE_CHIUSA` | `E_FONDO_NON_CANCELLABILE` | il denaro si è già mosso; la `cause` viaggia nel contesto |
| `FIGLIA_CONGELATA` | `E_FONDO_FIGLIA_CONGELATA` | la fattura che lo ha ricevuto non è più modificabile |
| `SISTEMAZIONE_ATTIVA` | `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` | **si disfa annullando la sistemazione**, non da qui |

⚠️ **Il criterio si legge una volta sola.** Leggerlo due volte sulla stessa riga vuol dire
accettare metà condizione e rifiutare l'altra.

⭐ **`E_FONDO_FIGLIA_CONGELATA` non riusa `E_FATTURA_SATELLITE_CONGELATO`.** È la stessa regola
sulla stessa soglia, ma il messaggio esistente riceve il nome della tabella, e lo metterebbe nella
frase che l'operatore legge.

---

### I tre `DELETE`, nell'ordine che le chiavi esterne impongono

```text
1. pagamenti.vendite_contabili_righe     ← le righe contabili dell'atto
2. vendite.fatture_fondi_fattura         ← il fondo applicato alla figlia
3. vendite.fatture_fondi_fattura_source  ← l'atto
```

Le chiavi esterne sono `NO ACTION` di proposito: cancellare un atto pretende di aver prima
cancellato le sue righe, e una chiave differita nasconderebbe l'ordine invece di dirlo. ⭐ Questa
funzione è la **sede unica** di quest'ordine: nessun altro lo riscrive.

> ℹ️ Il legame verso `vendite.fatture_fondi_fattura` non è una chiave esterna: quella tabella non
> ha l'id dell'atto. La riga si ritrova dalla terna (figlia, sorgente, tipo), come la scrive
> `vendite.fn_applica_fondi_fattura`.

---

### La porta delle righe contabili, sulla riga

Le righe contabili dell'atto stanno sotto una distinta `GENERATA`. Lì il guard del contenuto
([`pagamenti.trgfn_vendite_contabili_righe_guard_contenuto`](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto))
rifiuta il `DELETE` con *«non è compilata a mano»*: quel controllo è il cestino dell'operatore, e
qui non c'è un operatore. C'è il giro che ha prodotto quelle righe, e che ha già letto il suo
criterio.

Per questo la primitiva apre la porta del guard: accende `zeroerp.allow_contabile_riga_delete_override`
con **l'id dell'atto** che sta cancellando, cancella le sue righe, e la richiude subito dopo. Il
guard onora la porta solo sul `DELETE`, solo sulle righe di quell'atto, e solo se chi scrive è il
proprietario della tabella. L'applicazione che accende la GUC da sé non apre niente. In errore la
riporta indietro l'annullamento della transazione.

---

### ⚠️ Due conseguenze da conoscere prima di chiamarla

1. **La tabella non è storicizzata**: il `DELETE` è definitivo. Per il riporto la traccia resta su
   `pagamenti.sistemazioni`, che diventa `ANNULLATA` **con il motivo**. *È il registro a ricordare,
   non la conseguenza.* ⛔ Per il fondo `AUTOMATICA` della lista «da decidere» non c'è registro, e
   non se ne inventa uno: quell'atto non ha mai mosso denaro.
2. **Cancellare RIAPRE la rigenerazione automatica.** L'«atto unico» di
   `fn_fondo_fattura_proponibile` guarda se un atto esiste in qualunque stato, quindi il giro
   successivo ne rifà uno leggendo il residuo di adesso. Sul riporto è il comportamento giusto, ma
   va saputo.

---

### Regole

* `SECURITY DEFINER`, con il `search_path` fissato. Il perimetro lo rimette lei, sull'atto.
* `FOR UPDATE` sull'atto: due gesti in parallelo sullo stesso atto arriverebbero entrambi ai
  `DELETE`, e il secondo ne cancellerebbe zero dicendo di aver fatto qualcosa.
* Guard di parametro con `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`).
* Il bersaglio dell'errore è la **fattura** (sorgente o figlia, secondo il motivo), mai un nome di
  tabella. ⛔ Su `SISTEMAZIONE_ATTIVA` non c'è bersaglio: il catalogo dei tipi di entità non ha un
  codice per le sistemazioni.
* Restituisce quante righe contabili, quanti fondi applicati e quanti atti ha cancellato.

---

### Codici errore

* `E_FONDO_NON_TROVATO` — l'atto non esiste o è fuori dal perimetro di chi agisce.
* `E_FONDO_NON_CANCELLABILE` — il denaro si è già mosso (atto eseguito, riga registrata, distinta
  chiusa).
* `E_FONDO_FIGLIA_CONGELATA` — la fattura che ha ricevuto il fondo è oltre la soglia fiscale.
* `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` — una sistemazione trattiene l'atto.
* `E_VENDITE_CHIAMATA_NON_VALIDA` — l'id dell'atto manca o non è positivo.

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: l'app non
  esegue la primitiva; l'atto di fondo di un'altra azienda risponde `E_FONDO_NON_TROVATO` e resta
  com'era.
* `db/pgtap/vendite/test-fondo-fattura-cancellazione.sql` — il gesto, i quattro rifiuti e i tre
  `DELETE`.

---

### Note di migrazione

* 2026-11-25 — nasce dal corpo di `vendite.fn_cancella_fondo_fattura`, che diventa il verbo pubblico
  col suo permesso. Il perimetro, che prima dava la row security, lo rimette la primitiva sull'atto;
  la porta delle righe contabili passa da un interruttore (`on`) all'id dell'atto
  (brief-db-porte-aperte-dalla-sola-guc, giro 8, D-T b).

---

{% include-markdown "signature-core.md" %}
