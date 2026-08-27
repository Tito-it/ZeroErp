# Brief DB — il DDT di ri-consegna nasce nudo: la testata che non eredita, e le due cose che NON vanno copiate

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Collaudo in-app di Tid del 2026-08-27, prova **9** di
> [collaudo-in-app-ddt-righe-senza-prezzo.md](collaudo-in-app-ddt-righe-senza-prezzo.md)
> (ri-consegna standalone, casella **6** del §19 di
> [brief-ddt-righe-senza-prezzo.md](brief-ddt-righe-senza-prezzo.md)):
> reso generato dal DDT `DDT0023451`, ri-consegna generata → il DDT nuovo arriva
> **senza causale di trasporto e senza indirizzi**, e l'operatore li deve
> ridigitare a mano su un documento che il DB ha generato da sé.
>
> **Stato.** 2026-08-27 — analisi sulla **struttura** (corpo delle due funzioni
> madri, colonne di `vendite.ddt`, seed di `config.sorgenti`). Nessun file
> scritto, nessuna migrazione. **Due domande di modello** prima di qualunque riga
> di SQL (§3.2 e §4.3): non sono dettagli di copia, cambiano cosa il documento
> dichiara.
>
> **Correlati:**
> [fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) ·
> [fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) ·
> [trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) ·
> [brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md)

---

## 0. Le tre voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | Il generatore che parte dalla sorgente **più ricca** (un DDT) copia **meno** di quello che parte dalla più povera (un ordine): niente indirizzi, niente blocco trasporto | 🔴 asimmetria del modello, già incontrata in-app | ogni operatore che genera una ri-consegna |
| **2** | `fatturazione_immediata` **non si copia e basta**: ereditarla da un DDT già fatturato ri-fattura merce già fatturata | 🔴 domanda di modello — la risposta decide se si emette una fattura di troppo | nessuno finora: la colonna oggi resta al default `false` |
| **3** | La ri-consegna **standalone** non dichiara nessuna sorgente: nasce orfana, mentre `RESO_VENDITA` esiste a catalogo e `vendite.resi` ha lo `uid` | 🟠 dato vero non rappresentato | chi guarda «Transito»/«Passaggi» su quel DDT |

⭐ **Cosa hanno in comune**: la cura sta tutta dentro **`fn_genera_ddt_riconsegna`**
— una funzione, un changeSet. Nessuna vista, nessun trigger, nessun BE, nessun
FE: il drawer del DDT mostra già tutti i campi in questione, sono vuoti perché
nessuno li scrive.

---

## 1. Il fatto, letto dal contratto

`vendite.fn_genera_ddt_riconsegna`, passo 4, inserisce la testata con **nove**
colonne:

```sql
INSERT INTO vendite.ddt (
    data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
    sorgente_tipo_id, sorgente_uid, billing_account_id,
    utility_id, valuta_id, emittente_fiscale_id)
```

`vendite.ddt` ne ha **quaranta**. Restano fuori, fra le altre:
`causale_trasporto_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id`,
`mittente_soggetto_ruolo_id`, `vettore_soggetto_ruolo_id`,
`fatturazione_immediata`. E **non c'è nessun `INSERT INTO vendite.ddt_indirizzi`**.

`trgfn_ddt_normalize` non tappa il buco e non è pensato per farlo: eredita
`billing/utility/valuta/emittente` e **solo** da una sorgente `ORDINE_VENDITA`.

### 1.1 ⭐ L'argomento non è la comodità, è la simmetria

La funzione gemella `fn_genera_ddt_da_ordine`, al passo **4-bis**, fa questo:

```sql
-- 4-bis) Cascata indirizzi (D-1): copia 1:1 gli snapshot dell'ordine
--   filtrati sui tipi ammessi in ambito DDT (di fatto solo CON).
INSERT INTO vendite.ddt_indirizzi (
    ddt_id, tipo_indirizzo_id, snapshot,
    origine_indirizzo_id, origine_soggetto_ruolo_id)
SELECT ... FROM vendite.ordini_indirizzi oi
  JOIN config.tipi_indirizzi_allowed a
    ON a.tipo_indirizzo_id = oi.tipo_indirizzo_id AND a.ambito = 'DDT'
 WHERE oi.ordine_id = p_ordine_id
ON CONFLICT (ddt_id, tipo_indirizzo_id) DO NOTHING;
```

Un **ordine** non ha nessun blocco trasporto — causale, aspetto, addebito non
esistono proprio su `vendite.ordini` — e ciononostante il generatore da ordine
fa cascadere gli indirizzi. Il generatore da **reso** parte da un `vendite.ddt`,
cioè dall'unico documento che il blocco trasporto ce l'ha **tutto**, e non copia
né quello né gli indirizzi.

> Non è «una dimenticanza in un caso di nicchia»: è che la stessa cosa — «il
> documento figlio eredita la testata del padre» — è scritta in un posto e non
> nell'altro. Il modello la ammette in entrambi. Va resa **simmetrica subito**,
> non rinviata (`feedback_simmetria_modello_no_meta_scope`).

### 1.2 ⚠️ E il design-of-record la causale l'aveva già nominata

Il **§R-3** di `brief-ddt-righe-senza-prezzo.md` scrive, testualmente:

> *«E la causale giusta per quel documento è **VENDITA**: il §N7 di
> `vw_partite_merce` dice che la quota accreditata torna ri-fatturabile, quindi
> quella ri-consegna si vende.»*

La causale era **già decisa** sul modello. Non è mai stata cablata: la funzione
lascia `causale_trasporto_id` a `NULL` e il documento arriva all'operatore muto.

⭐ **Corollario sul collaudo**: la prova 9 chiede oggi di *impostare* VENDITA a
mano prima di verificare che l'emissione blocchi in modo parlante. Con l'eredità,
quella casella si accende da sé — e la prova diventa fedele a com'è il processo
invece che a com'è il rimedio manuale.

---

## 2. ✅ Cosa va ereditato — «la relazione»

Colonne che descrivono **con chi e perché** la merce si muove. Sono le stesse per
il viaggio di andata e per la ri-consegna, perché è la stessa relazione
commerciale eseguita una seconda volta.

| Colonna | Perché eredita |
| --- | --- |
| `causale_trasporto_id` | il *perché* del movimento non cambia. ⚠️ È **immutabile dopo l'emissione** (`trgfn_ddt_guard_causale_immutabile`) e **obbligatoria** all'emissione: lasciarla nulla non rimanda una scelta, la sposta su un operatore che non ha il contesto |
| `aspetto_bene_id` | la merce è **la stessa merce**, tornata indietro |
| `modalita_addebito_trasporto_id` | patto sulle spese, non fatto del viaggio |
| `mittente_soggetto_ruolo_id` | spedisce lo stesso soggetto |
| **indirizzi** (`ddt_indirizzi`, ambito `DDT`) | cascata 1:1 come al passo 4-bis del gemello, `origine_*` propagati, `ON CONFLICT DO NOTHING`. È il pezzo che oggi **blocca l'emissione**: `trgfn_ddt_guard_indirizzi_obbligatori` alza `E_INDIRIZZO_DOC_OBBLIGATORIO` su un documento generato dal DB |

---

## 3. ⛔ Cosa NON va ereditato — «il viaggio»

Qui la richiesta *«tutte le informazioni duplicate dal DDT da cui è nato»* va
ristretta, e non per prudenza: **copiare queste colonne scrive fatti falsi su un
documento fiscale di trasporto.**

| Colonna | Perché **non** eredita |
| --- | --- |
| `num_colli`, `peso_lordo`, `peso_netto`, `volume` | ⛔ **sbagliati per costruzione, non «stantii»**: la ri-consegna porta un **sottoinsieme** delle righe del DDT origine, e su quelle righe una **frazione** della quantità (il residuo di ri-consegna, `fn_resi_riga_residuo_riconsegna`). Un peso copiato è il peso di un collo che non è quello che parte |
| `targa`, `autista` | il mezzo e la persona di un viaggio **già avvenuto**. Sono una misura, non una scelta |
| `data_ora_partenza`, `data_ora_consegna_prev` | date di un viaggio concluso su un documento ancora in `DRAFT` |
| `tracking_code` | ⛔ il peggiore: punta il cliente al **collo precedente**. Un codice di tracciamento copiato non è un campo vuoto, è un'informazione sbagliata data a un terzo |

### 3.1 Il criterio, in una riga

> **Eredita ciò che è una scelta; non ereditare ciò che è una misura.**
> Una scelta vale finché non la si cambia; una misura vale per il viaggio in cui
> è stata presa.

### 3.2 ❓ Domanda di modello — `vettore_soggetto_ruolo_id`

È il caso di confine, e per questo **non lo decido qui**: il vettore è insieme
una scelta (l'accordo con quel corriere) e un fatto del viaggio. Se eredita, sono
coerenti `targa`/`autista` che **non** ereditano — chi spedisce è una scelta,
quale furgone parte è una misura. Se non eredita, la testata resta più vuota ma
non dice mai niente di non verificato.

**Serve la risposta di Tid**, non del DB: è una convenzione di processo.

---

## 4. 🔴 `fatturazione_immediata` — non è una copia, è una decisione

`vendite.ddt.fatturazione_immediata` è `NOT NULL DEFAULT false`, ed è
**immutabile fuori dalla bozza** (`trgfn_guard_fatturazione_immediata_immutabile`).

### 4.1 Il rischio, sul modello

Se la ri-consegna eredita `true` da un DDT origine a fatturazione immediata, il
documento nuovo **genera una seconda fattura** sulla stessa merce.

### 4.2 Perché non si risolve con «copiala» né con «lasciala falsa»

Perché la risposta **dipende da cosa è successo al reso**, e il modello lo sa già
dire: il §N7 di `vw_partite_merce` stabilisce che *la quota accreditata torna
ri-fatturabile*.

* reso **accreditato** (nota di credito emessa) → la merce è uscita dal fatturato:
  ri-consegnarla e ri-fatturarla è **corretto**;
* reso **non accreditato** → la merce è ancora fatturata: ri-fatturarla è una
  **doppia fatturazione al cliente**.

Copiare la colonna sbaglia nel secondo caso; forzarla a `false` sbaglia nel primo
(e l'immutabilità post-bozza rende la correzione cara).

### 4.3 ❓ Domanda al team DB

La condizione «questa quota è stata accreditata» è già leggibile in modo
affidabile al momento della generazione (`fn_accredita_riga_reso` /
`vw_partite_merce`)? Se sì la colonna si **deriva**, non si copia. Se no, va
detto — e allora la scelta esplicita è `false`, con il perché scritto nel corpo
della funzione, non un default silenzioso.

⚠️ Segnalo che questa è la voce che vale più della prova 9: le altre costano
digitazione all'operatore, questa può costare **una fattura sbagliata** — ed è
esattamente la forma del caso di `feedback_whitelist_dal_percorso_reale`.

---

## 5. 🟠 La ri-consegna standalone nasce senza sorgente

Al passo 3 la funzione cerca un ordine dietro le righe di reso; **solo** se lo
trova valorizza `sorgente_tipo_id`/`sorgente_uid` (a `ORDINE_VENDITA` + `uid`
dell'ordine). Nel caso **standalone** — quello della prova 9 — restano entrambi
`NULL`: il DDT dichiara di non venire da nessuna parte, mentre viene da un reso.

Il materiale per dirlo c'è già, e non va inventato:

* `config.sorgenti` ha `RESO_VENDITA` (id 15, `categoria = DOCUMENTO`,
  `scope = REVERSE_FLOW`, attivo);
* `vendite.resi` ha `uid uuid NOT NULL DEFAULT uuidv7()`, cioè la forma che
  `ddt.sorgente_uid` si aspetta.

⚠️ Due cose da guardare prima di scrivere, e le lascio al team DB perché toccano
un contratto pubblicato:

1. il seed di `RESO_VENDITA` porta `key_selector = 'id'` mentre `PREVENTIVO`
   porta `'uid'`: se il puntatore diventa `resi.uid`, i due vanno riconciliati o
   il selettore mente;
2. l'order-backing esistente **non va perso**: oggi la sorgente `ORDINE_VENDITA`
   è ciò che tiene insieme la ri-consegna e il residuo d'ordine. Se la sorgente
   diventa il reso, il legame con l'ordine resta comunque su
   `ordini_righe_fulfillment` (passo 5) — ma va **detto**, non dedotto.

Questa voce tocca lo stesso nervo di
[brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md)
§2 («commesse che dichiarano di non avere origine»): vale la pena che i due
cantieri si guardino prima di scrivere.

---

## 6. La richiesta, in ordine

| # | Cosa | Blocca il collaudo? |
| --- | --- | --- |
| **R1** | `fn_genera_ddt_riconsegna` eredita dal DDT origine il blocco «relazione» del §2 — causale, aspetto, modalità addebito, mittente | 🔴 sì — prova 9 |
| **R2** | Cascata indirizzi ambito `DDT`, modellata sul passo 4-bis di `fn_genera_ddt_da_ordine` | 🔴 sì — senza, l'emissione è bloccata dal guard |
| **R3** | ⛔ **Nessuna** eredità del blocco «viaggio» del §3 — e scritto nel corpo della funzione **perché** (un `-- non si copia` senza motivo lo rimette dentro il prossimo che passa) | — |
| **R4** | Risposta alla domanda §4.3 su `fatturazione_immediata`, poi la riga conseguente | 🔴 potenzialmente sì, e in peggio |
| **R5** | Decisione di Tid sul vettore (§3.2) | no |
| **R6** | Sorgente `RESO_VENDITA` sulla ri-consegna standalone (§5) | no — cantiere suo, se il team DB preferisce |

**pgTAP attesi** (il perimetro si legge dai test, non dalla descrizione della
funzione — `feedback_ripiego_ogni_codice_vivo`):

* ri-consegna **order-backed**: la testata generata ha causale/aspetto/addebito/
  mittente **uguali** al DDT origine, e gli indirizzi ambito DDT copiati;
* ri-consegna **standalone**: idem — è il caso della prova 9, e va **costruito**,
  non cercato fra le righe esistenti;
* ⛔ **il test che manca sempre**: la testata generata ha `num_colli`,
  `peso_lordo`, `peso_netto`, `volume`, `targa`, `autista`, `tracking_code`,
  `data_ora_partenza` **a `NULL`** anche quando il DDT origine li ha valorizzati.
  Senza questo, «non copiare» è un commento, e il primo che allarga la `INSERT`
  li porta dentro senza che niente si accenda.

---

## 7. Cosa NON serve

* **niente BE**: `resi_repository.genera_ddt_riconsegna` chiama la madre e ne
  ritorna l'id — la firma non cambia;
* **niente FE**: il drawer DDT rende già causale, aspetto, addebito, mittente,
  vettore e la sezione indirizzi (`DocumentoIndirizziSection`). Oggi sono vuoti
  perché nessuno li scrive, non perché non si vedano;
* **nessuna colonna nuova**, **nessuna vista**, **nessun trigger**: una funzione,
  un changeSet con numerazione successiva, corpo preso dalla doc auto-gen.
