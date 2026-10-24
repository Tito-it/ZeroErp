# Brief DB — Il reso confermato e la bolla di ri-consegna nei pgTAP: una strada, non venti copie

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: team DB**, col giro 2 del lavoro aperto in
[brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md): il via di Tid
(2026-10-25) copriva i due giri, e la forma del builder ha già i default approvati (§3).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB + Tid | Problema, proposta e via (nel brief del giro 1) | §1, §3 | — |
| 2 | team DB | Censimento fine dei file: quale blocco è la strada del reso, quale è il caso | §4 | 1 |
| 3 | team DB | Il builder del reso (con la ri-consegna a richiesta), presidio, porting, regressione prima/dopo | §3, §4 | 2 |
| 4 | **Tid** | Apply e corsa pgTAP come app; archiviazione | — | 3 |

Decisioni aperte di Tid: nessuna (i default del §3 sono approvati; se il censimento ne fa emergere una, si
scrive qui). Lavoro da committare: questo documento.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** il team DB; Tid per l'apply.
> **Origine:** giro 2 di [brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md),
> archiviato il 2026-10-25 a giro 1 chiuso (§7 di quel brief), con la decisione D-3 di Tid (la bolla di ri-consegna
> entra qui).
> **Perimetro:** solo DB — i pgTAP (`db/pgtap/`) e i builder di fixture (`dbops`). Nessuna ricaduta su backend o
> frontend, nessun cambio al modello del dominio.
> **Brief vicini verificati:** nessuno aperto sul tema; il giro 1 è chiuso e il suo builder
> (`dbops.fn_pgtap_crea_ddt_da_ordine`) è la base su cui questo si appoggia.

---

## 1. Il problema, in parole semplici

Sopra una bolla consegnata molti test costruiscono un **reso**: la merce che torna indietro. Lo scrivono a mano:
la testata legata alla bolla, la riga legata alla riga della bolla, la conferma (`vendite.fn_conferma_reso`, il
verbo del dominio, che vuole l'azione `conferma_reso`). Il reso ha regole sue — la riga deve corrispondere a merce
davvero consegnata, la quantità non può superarla, la conferma pretende i suoi dati — e ogni file le soddisfa da
sé. Quando una regola cambia, le copie restano indietro in silenzio.

Dopo un reso per ri-consegna, diversi test generano la **bolla di ri-consegna** (`vendite.fn_genera_ddt_riconsegna`)
e le scrivono a mano indirizzo e causale per portarla a consegnata: la stessa trappola d'ordine che il giro 1 ha
tolto alla bolla da ordine (D-3).

⚠️ Del reso il database ha il **verbo di conferma** ma non una madre di creazione: testata e righe in produzione le
scrive il backend (`resi_service`). Il builder le scrive coi suoi INSERT, come i test, e passa dal verbo vero per
la conferma.

---

## 2. Che cosa NON cambia

* Il modello del dominio: nessun guard, nessun verbo, nessuna tabella.
* I test in cui la strada è il caso: le regole del reso, i suoi errori, la conferma dentro `lives_ok`, il reso
  annullato, la riga spenta in bozza, il legame `resi_righe_riconsegne`. Restano scritti a mano.
* Le asserzioni: si cambia la fixture, non ciò che il test prova.

---

## 3. La forma del builder (default approvati col via del 2026-10-25)

`dbops.fn_pgtap_crea_reso(etichetta, ddt_id, quantità, stato, …)`:

* sopra una bolla consegnata (quella di `dbops.fn_pgtap_crea_ddt_da_ordine`, o una che il test passa);
* testata e riga col collegamento alla riga della bolla e alla riga d'ordine che essa evade (dal legame, con un
  ordine dichiarato); la quantità chiesta (default: una parte del consegnato, così il residuo resta misurabile);
* il tipo di reso per codice (`RESO_A_CREDITO`, `RESO_PER_RICONSEGNA`);
* la conferma dal verbo `vendite.fn_conferma_reso` se lo stato chiesto lo vuole (default: confermato);
* **D-3**: a richiesta, la bolla di ri-consegna dal verbo `vendite.fn_genera_ddt_riconsegna`, con ciò che la
  consegna pretende, portata allo stato chiesto per la matrice (o un builder suo, se il censimento mostra che le
  due strade si usano separate).

Da decidere nel censimento, e da scrivere qui: più righe in un reso (riga della bolla e quantità per ciascuna),
più resi sulla stessa riga, l'azione `conferma_reso` concessa dal builder o dal test.

---

## 4. Il materiale del giro 1 (fatto datato, 2026-10-25)

I quattro agenti del porting del giro 1 hanno descritto la strada del reso file per file
([brief del giro 1](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md) §6.6). In sintesi:

* testata `vendite.resi` (stato DRAFT, sorgente `DDT_VENDITA`, `sorgente_uid` = uid della bolla, `storicizza`
  false); emittente e cliente li mette il normalize;
* righe `vendite.resi_righe` (riga della bolla, `ordine_riga_id` dal legame — in sei file con `LIMIT 1` senza
  ordine —, articolo, descrizione, unità e fattore copiati dalla riga della bolla, quantità, tipo reso);
* conferma da `vendite.fn_conferma_reso`, con l'azione `conferma_reso` concessa prima;
* circa 20 file la ripetono (gruppi B, C, D del giro 1: accrediti, rinunce, motore dei resi, partite e
  situazione della merce, contatori, dashboard); la bolla di ri-consegna con indirizzo e causale a mano in almeno
  quattro (partite merce chiusura, situazione merce chiusura, partite merce dopo nota di credito, contatore).

Il censimento fine — quale blocco di ogni file è una copia e quale è il caso — è il primo passo (§ «Chi riparte»).
