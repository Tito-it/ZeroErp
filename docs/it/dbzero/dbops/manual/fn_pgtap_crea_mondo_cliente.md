## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_mondo_cliente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il legame del cliente all'azienda, che il mondo verifica
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'azienda e l'operatore, quando nessun contesto è aperto
> * [dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) — l'azienda, quando il contesto è già aperto
> * [dbops.fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) — il cliente fatturabile
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto che il mondo apre
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — i builder di documento, che partono dal mondo
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — la composizione delle fixture e l'ordine fra mondo e contesto

---

### 🎯 Scopo Principale

Il mondo minimo di un test di dominio, in una chiamata: l'azienda con il suo operatore, il
contesto di sessione aperto su di lui, e un cliente fatturabile legato a quell'azienda. Torna
tutte le chiavi — emittente, operatore, identità, billing account, istanza, cliente, utility
— così il test non deve pescarle da nessuna parte.

---

### ⭐ Esiste per la regola d'ordine

Le fixture atomiche sanno costruire bene ciascuna la sua entità. Il mondo è la
**composizione**, cioè il pezzo che conosce l'ordine in cui vanno chiamate:

1. prima l'azienda e l'operatore, **poi** il contesto;
2. il cliente **dopo** il contesto, e senza chiedere il legame all'azienda: con un operatore
   in sessione il legame lo scrive da sé il trigger del conto, verso l'azienda di chi agisce,
   che qui è quella giusta per costruzione;
3. si esce con i vincoli differiti **richiusi**, e chi li rivuole aperti lo dichiara.

Finché quella regola stava scritta a mano in ogni test, un test scritto prima che la regola
fosse nota non la rispettava: sulla macchina di sviluppo non si vedeva (i dati ci sono già),
su un database ricostruito il test moriva nella fixture, con copertura **zero**.

---

### 🔀 Due rami, e il secondo non è un'ottimizzazione

| Situazione | Che cosa fa |
| ---------- | ----------- |
| **Nessun contesto** (CI, installazione nuova, il test che la chiama per prima) | costruisce azienda e operatore, apre il contesto su di lui, poi il cliente |
| **Contesto già aperto** (macchina di sviluppo, o la riga di contesto del template chiamata prima) | prende **l'azienda di chi agisce** e le aggiunge un cliente |

La domanda «c'è un contesto?» si fa alla variabile di sessione che le policy leggono davvero
(`app.current_user_id`), non a un helper che risponderebbe un emittente anche senza contesto.

Con il contesto aperto, l'azienda la decide
[fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce), con la
regola di produzione: l'azienda scelta in alto, se l'utente la può usare, altrimenti quella
assegnata. Così anche un super admin che ha scelto l'azienda ha il suo mondo; è il caso
dell'utente degli smoke Python.

⚠️ Prendere l'azienda di chi agisce non serve a risparmiare tempo: serve a non sbagliare.
Costruendone una nuova, il cliente resterebbe legato a quella di chi agisce — perché il
legame lo scrive il trigger guardando chi agisce — e il mondo tornato non sarebbe coerente.

---

### 🛑 Dove il mondo non è coerente, parla

* una **sigla** chiesta con il contesto già aperto è rifiutata: lì l'azienda non si sceglie.
  Per una seconda azienda si chiamano le fixture atomiche, prima del contesto;
* un contesto aperto su un utente **senza un'azienda su cui scrivere** (l'operatore senza
  assegnazione, il super admin che non ne ha scelta una) o senza identità OPERATORE attiva è
  rifiutato da [fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce);
* il **legame** del cliente si verifica: se il trigger l'ha legato a un'altra azienda, il
  mondo solleva subito invece di lasciar morire il test venti righe più in là su una policy.

---

### 🚫 Che cosa non comprende, e il criterio è uno

Entra ciò che ha una **trappola d'ordine**, non ciò che serve spesso:

* il **registro di fatturazione** no: `script.fn_pgtap_registro_fattura()` si ricava dal
  contesto e lo crea se manca;
* l'**articolo** no: i suoi flag (gestito a magazzino, per lotti, per seriale) sono il caso
  del test;
* i **cataloghi** (valute, IVA, stati, tipi documento) no: ci sono anche su un database
  ricostruito, e si scelgono con un ordinamento stabile;
* **due aziende o due clienti** no: sono le fixture atomiche, chiamate due volte.

---

### ⚠️ Il contratto sui vincoli differiti

La funzione esce con i vincoli **immediati**, come ogni fixture. Un test che ha bisogno della
finestra differita fino a un punto suo la riapre subito dopo e lo dichiara in testa. Contare
sulla finestra «di default» è verde sulla macchina di sviluppo e rosso in CI.

---

### ⚠️ Il contesto resta aperto sulla sessione

Nel ramo senza contesto il mondo lo apre a livello di sessione, come la riga di contesto del
template: dopo il `ROLLBACK` del test la variabile resta valorizzata su un utente che non
esiste più. Non dà fastidio perché il runner lancia un processo per file.

---

### Codici errore

Nessun codice registrato: la sigla chiesta a contesto aperto e il legame verso un'altra
azienda sono eccezioni senza codice, sollevate dal mondo; gli altri rifiuti sono quelli delle
fixture che compone.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql` — il contratto, non
  l'implementazione: il ramo che costruisce (azienda nuova, contesto aperto sull'operatore
  tornato), il legame del conto verso l'azienda del mondo, l'identità OPERATORE attiva, il
  ramo che riusa l'azienda, e i due rifiuti (sigla a contesto aperto, utente senza azienda).
* `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-risolutore-v1.sql` — l'azienda di chi
  agisce è quella del risolutore di produzione: il super admin senza azienda scelta è
  rifiutato, quello con l'azienda scelta ha il mondo e la fattura su quella, l'operatore
  normale con un'azienda altrui scelta resta sulla sua.

---

### Note di migrazione

* 2026-09-22 — nasce come building block di composizione delle fixture
  (`brief-db-fixture-che-costruiscono-giro-2`, §3).
* 2026-10-21 — con il contesto aperto l'azienda la decide il risolutore di produzione, anche
  per il super admin che l'ha scelta in alto (richiesta BE R-2). Prima leggeva solo l'azienda
  assegnata.
* 2026-10-24 — il ramo con il contesto passa da `dbops.fn_pgtap_azienda_di_chi_agisce`,
  estratta da qui (`brief-modello-documento-vendita`, §4-octies).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
