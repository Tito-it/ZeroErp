## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_mondo_cliente`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore), [dbops.fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) — i due builder che questa funzione compone
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — la riga di contesto del template, che apre la sessione ma non costruisce il cliente
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-che-costruiscono-giro-2` (§3)

---
### 🎯 Scopo Principale

(rev 2026-09-22 — D7, il giro del building block)

**Il mondo minimo di un test di dominio, in una chiamata sola**: l'azienda con il suo
operatore, il contesto di sessione aperto su di lui, e un cliente fatturabile legato a
quella azienda. Torna tutte le chiavi — emittente, operatore, identità, billing account,
istanza, cliente — così il file non deve più pescarle da nessuna parte.

```sql
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('dash aperto');
```

---
### 🧭 Perché esiste — la regola d'ordine, non l'elenco della spesa

I builder atomici c'erano già, e ognuno sa costruire bene la sua entità. Quello che non
c'era è **la composizione**, cioè il pezzo che conosce l'ordine in cui vanno chiamati:

1. prima si costruisce il mondo, **poi** si apre il contesto;
2. con un operatore in sessione il legame «questo billing account è di quell'azienda» lo
   scrive da sé un trigger, verso l'azienda di **chi sta agendo**: chiederlo anche a mano
   fa scontrare i due;
3. gli helper escono con i vincoli differiti **richiusi**, e chi li rivuole aperti lo
   dichiara.

Finché quella regola non sta in un oggetto, sta scritta a mano in ogni file di test — e un
file scritto prima che la regola fosse nota non la rispetta. Sul database di sviluppo non
si vede (i dati ci sono già); su un database ricostruito da zero il file muore nella
fixture, e la sua copertura vale **zero**, non «parziale».

---
### 🔀 I due rami, e il secondo non è un'ottimizzazione

| Situazione | Cosa fa |
| ---------- | ------- |
| **Nessun contesto** (CI, installazione nuova, o il file chiama questa funzione per prima) | costruisce azienda + operatore, apre il contesto su di lui, poi crea il cliente |
| **Contesto già aperto** (macchina di sviluppo, o la riga del template chiamata prima) | **riusa l'azienda di chi agisce** e le aggiunge un cliente |

⭐ **«L'azienda di chi agisce» la dice la regola di produzione** (rev 2026-10-21):
`script.fn_resolve_emittente_for_user`, la stessa che usa il trigger quando lega il cliente.
È l'azienda **scelta in alto** (`app.current_emittente_id`), se l'utente la può usare,
altrimenti quella assegnata all'utente. Così anche un **super admin** che ha scelto l'azienda
ha il suo mondo: è il caso dell'utente degli smoke Python (`dev.smoke`), che sceglie l'azienda
di prova come la sceglie l'operatore in alto. Prima il builder leggeva solo l'azienda
assegnata, e rifiutava il super admin a cui il trigger il cliente l'avrebbe legato.

⚠️ Riusare l'azienda non serve a risparmiare tempo: serve a non sbagliare. Costruendone
una nuova, il cliente resterebbe legato a quella **vecchia** — perché il legame lo scrive
il trigger guardando chi agisce — e sotto le regole di visibilità per riga quel cliente
non si vedrebbe più.

---
### 🛑 Due guard che parlano

* chiedere una **sigla** con il contesto già aperto è rifiutato: lì l'azienda non si
  sceglie, è quella di chi agisce. Per una **seconda** azienda si chiamano i builder
  atomici, prima del contesto;
* un contesto aperto su un utente **senza un'azienda su cui scrivere** è rifiutato:
  l'operatore senza azienda assegnata, o il super admin che non ne ha scelta una. Quella
  fixture non potrebbe scrivere niente, e il file morirebbe venti righe più in là su una
  regola di visibilità invece che sulla sua causa.

---
### 🚫 Cosa NON comprende, e il criterio è uno

Entra ciò che ha una **trappola d'ordine**, non ciò che serve spesso:

* il **registro di fatturazione** no: `script.fn_pgtap_registro_fattura()` si ricava già
  dal contesto e lo crea se manca;
* l'**articolo** no: i suoi flag (gestito a magazzino, per lotti, per seriale) sono il caso
  del test, non un default;
* i **cataloghi** (valute, IVA, stati, tipi documento) no: quelli ci sono anche su un
  database ricostruito — non si costruiscono, si scelgono, con un ordinamento stabile;
* **due aziende o due clienti** no: sono i builder atomici, chiamati due volte.

---
### ⚠️ Il contratto sui vincoli differiti

La funzione **esce con i vincoli richiusi** (`IMMEDIATE`), come ogni helper di fixture. Un
file che ha bisogno della finestra differita fino a un punto suo la riapre subito dopo con
`SET CONSTRAINTS ALL DEFERRED`, e lo dichiara in testa. Contare sulla finestra «di
default» è verde sulla macchina di sviluppo e rosso in CI: è successo il 2026-09-21.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql` (9 casi) pinna il **contratto**,
non l'implementazione: il ramo che costruisce, il ramo che riusa, il legame del billing
account verso l'azienda giusta, e i due guard.
