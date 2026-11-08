## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_esito_classe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso che si completa
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la `modalita_esito` del passo
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — la classe di ogni esito (`is_verdetto`)
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_template_flussi_guard_modalita_esito](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_modalita_esito) — la coerenza della modalità sul passo
> * [pratiche.trgfn_flussi_guard_esito_completato](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_completato) — l'esito obbligatorio al completamento
> * [pratiche.trgfn_flussi_guard_transizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_transizione) — la matrice delle transizioni

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_esito_classe` controlla, quando un flusso si
completa, che la classe dell'esito corrisponda alla `modalita_esito` del suo passo.

È la difesa autoritativa dei passi a esito di dominio: vale per qualunque strada di scrittura, il
building block di dominio, il percorso generico o una modifica diretta.

---

### La regola

| Modalità del passo | Esito ammesso al completamento |
| --- | --- |
| `DOMINIO` | solo un esito di **ramo** (`is_verdetto` falso, per esempio `MERCE_PRESENTE`, `SOLO_SERVIZI`) |
| ogni altra (`MANUALE`, `AUTOMATICO`, `CONTESTUALE`) | solo un **verdetto** (`is_verdetto` vero, per esempio `POSITIVO`, `NEGATIVO`) |

Le due direzioni hanno lo stesso peso. Un verdetto generico su un passo che fa da bivio lascia il ramo
mai attivato, in silenzio: la pratica si chiude come se il lavoro a valle non servisse. Un esito di
ramo su un passo normale è un valore che quel passo non sa leggere.

---

### Quando scatta

* Solo alla transizione verso `COMPLETATO`: un inserimento già completato, o una modifica che cambia
  davvero lo stato. Le righe già completate restano modificabili sulle altre colonne: una riga storica
  che porta un verdetto su un passo diventato `DOMINIO` non diventa intoccabile.
* Un completamento senza esito non lo riguarda: lo ferma
  `pratiche.trgfn_flussi_guard_esito_completato`, che scatta dopo questo nella fase dei guard e solleva
  il suo errore.
* Un flusso senza passo di riferimento vale come `MANUALE`, come nel backend: ammette solo verdetti.

---

### ⭐ Valore nel database, autorizzazione nel backend

Il guard difende l'invariante di **valore**: la classe giusta per il passo. Il backend difende quella
di **autorizzazione**: a mano l'operatore invia solo verdetti. Il database non distingue chi scrive.
Insieme, un bivio `DOMINIO` si completa solo attraverso il building block del suo dominio.

---

### Codici errore

* `E_FLUSSI_ESITO_NON_AMMESSO` — l'esito non è della classe che il passo ammette. Il contesto porta
  l'esito, il codice del passo e la modalità. ⚠️ Il messaggio contiene la frase stabile «non ammesso per
  lo step», che il backend riconosce fra gli errori noti del database: non si riformula senza
  coordinarsi.

---

### Test

* `pratiche/test-guard-esito-classe` — le due direzioni, la riga storica già completata e
  l'inserimento diretto.

---

### Note di migrazione

* 2026-07-02 — nasce dopo una pratica in cui il passo di smistamento, un bivio a esito calcolato dal
  dominio, fu chiuso con `POSITIVO` dal percorso generico: il ramo merce non si attivò, la pratica si
  chiuse da sola e il seguito fu completato a mano fuori pratica. La direzione opposta era fermata solo
  dal backend (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}
