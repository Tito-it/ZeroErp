## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_reso`

> 👀 **Vedi anche**
>
> • [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — il verbo che conferma il reso
>
> • [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — la bolla consegnata su cui si appoggia
>
> • [dbops.fn_pgtap_crea_ddt_riconsegna](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_riconsegna) — la bolla di ri-consegna dopo un reso per ri-consegna
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-reso-costruito`

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**Un reso su una bolla, confermato, in una chiamata sola**: la merce che torna indietro,
con la testata legata alla bolla, la riga legata alla riga della bolla e alla riga d'ordine
che essa evade, e la conferma dal verbo del dominio.

```sql
-- un reso a credito di 3 sulla bolla del test
CREATE TEMP TABLE tmp_r AS
SELECT * FROM dbops.fn_pgtap_crea_reso('accrediti', (SELECT ddt_id FROM tmp_b), 3);

-- un reso per ri-consegna a due righe: la prima in bozza, la seconda sullo stesso reso
CREATE TEMP TABLE tmp_r1 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('due righe', v_ddt, 3, 'RESO_PER_RICONSEGNA', 'DRAFT',
                                       p_ddt_riga_id => v_riga1);
SELECT * FROM dbops.fn_pgtap_crea_reso('due righe', NULL, 2, 'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id => v_riga2,
                                       p_reso_id => (SELECT reso_id FROM tmp_r1));
```

---
### 🧭 Perché esiste

Una ventina di test scrivevano il reso a mano: la testata, la riga con articolo, descrizione,
unità e fattore copiati dalla bolla, la riga d'ordine ricavata dal legame (spesso senza un
ordine dichiarato), l'azione di conferma concessa, il verbo. Le regole del reso — merce
davvero consegnata, quantità che non la supera, conferma che pretende i suoi dati — le
soddisfaceva ogni file da sé. Ora la strada ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **La bolla** è quella del test (`p_ddt_id`), quella del reso a cui si aggiunge una riga
  (`p_reso_id`), o una bolla consegnata costruita da `dbops.fn_pgtap_crea_ddt_da_ordine`.
* **La testata** porta solo i dati del reso: la bolla d'origine e la data (`p_data`).
  Cliente, azienda, numero, stato iniziale e magazzino li mettono i trigger del dominio. Del
  reso il database non ha una funzione di creazione (testata e righe le scrive
  l'applicazione): il builder fa gli inserimenti, come facevano i test.
* **La riga** punta alla riga della bolla (`p_ddt_riga_id`, o la prima) e alla riga d'ordine
  del legame (`p_ordine_riga_id`, o la prima; nessuna se la bolla non nasce da un ordine).
  La quantità è `p_quantita`, in unità operative (default: metà della riga della bolla,
  arrotondata in su); il tipo si sceglie per codice (default `RESO_A_CREDITO`).
* **La coerenza** — quantità oltre il consegnato, origine sbagliata, bolla non consegnata —
  la giudicano i controlli veri del dominio, non il builder.
* **Lo stato** (default `CONFERMATO`) lo raggiunge il verbo `vendite.fn_conferma_reso`, dopo
  aver concesso all'operatore in sessione l'azione `conferma_reso` che il verbo pretende.

---
### 🚫 Cosa NON fa

* **Non annulla**: uno stato abortito (`ANNULLATO`) si rifiuta prima di costruire. L'annullo
  è del verbo `vendite.fn_annulla_reso`: si chiede il reso in bozza o confermato e si annulla
  dal test.
* **Non scrive i rientri di magazzino** né la bolla di ri-consegna: quella è di
  `dbops.fn_pgtap_crea_ddt_riconsegna`.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-reso-v1.sql` (11 casi): firma; reso di default confermato
a credito per metà riga; i legami della riga; la testata dal dominio; la bozza; la seconda
riga sullo stesso reso; il tipo per codice; quantità oltre il consegnato e bolla non
consegnata rifiutate dai controlli veri; due errori del chiamante rifiutati.
