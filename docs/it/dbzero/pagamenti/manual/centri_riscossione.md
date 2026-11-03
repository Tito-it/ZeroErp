## 📘 Documentazione Concettuale – Tabella `pagamenti.centri_riscossione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — ogni movimento dice da quale centro è arrivato il denaro
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali, ciascuno appoggiato a un centro
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta porta il centro di riscossione
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — usa i due flag per separare `incassato` da `saldo`
> * [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — sceglie il centro dei fondi fattura

---

### 🎯 Scopo Principale

La tabella **`pagamenti.centri_riscossione`** è il catalogo delle **origini di incasso** dei
movimenti di vendita: i canali di cassa (banca, posta, cassa) e i due centri interni, fondo
fattura e compensazione.

È condivisa per costruzione: non ha una colonna di emittente, e quindi nemmeno una row
security. Un proprietario andrebbe prima inventato, e il modello non ce l'ha.

---

### ⚠️ I due flag marcano i centri **non di cassa**

`is_fondo_fattura` e `is_compensazione` identificano i due centri interni. Un movimento su
uno di questi centri registra denaro **spostato** da un documento a un altro, non incassato
da un canale.

| Domanda | Che cosa si somma |
| --- | --- |
| «questa fattura è ancora da pagare?» | **tutti** i movimenti: il trasferimento la salda davvero |
| «quanto è **entrato**?» | solo i centri di cassa: questi due vanno **esclusi** |

🔴 La distinzione va messa nella **prima** misura che si scrive, non aggiunta dopo: un
cruscotto di incassato che somma tutto conta come denaro arrivato qualcosa che è stato solo
spostato, e l'errore non si vede, perché il numero è plausibile e cresce nel verso
giusto. **I due flag esistono anche per questo.** Le funzioni dei saldi li usano così: la colonna
`incassato` somma solo i movimenti su un centro di cassa.

---

### ⭐ Un solo centro per ruolo, e mai tutti e due i ruoli

| Vincolo | Dice |
| --- | --- |
| `uq_centri_riscossione_compensazione` *(parziale)* | **un solo** centro di compensazione |
| `uq_centri_riscossione_fondo_fattura` *(parziale)* | **un solo** centro per i fondi fattura |
| `chk_centri_riscossione_ruolo_esclusivo` | un centro è di compensazione **oppure** di fondo fattura, mai tutti e due |
| `uq_centri_riscossione_codice` | il `codice` è univoco |

I due indici unici sono **parziali**: valgono solo sulle righe col flag acceso, quindi i
centri di cassa possono essere quanti servono. Chi cerca il centro dei fondi fattura legge
una riga che il database garantisce unica.

⭐ **Un vincolo saturo e un vincolo rispettato hanno lo stesso aspetto finché non si prova ad
aggiungere.** Per questo il test di questa tabella prova il comportamento (un terzo centro
neutro entra, un secondo centro di compensazione no) e non l'esistenza dei vincoli.

`codice_interno` non si modifica dopo la creazione (`E_CODICE_NON_MODIFICABILE`), e un centro
non si disattiva finché canali, distinte o movimenti attivi lo usano.

---

### ⛔ I centri si seminano, non si inseriscono a mano

La sede delle righe è il CSV `80_data/sql/pagamenti/centri_riscossione.csv`: i due centri
interni (`FONDI_FATTURA`, `COMPENSAZIONI`) e i tre centri reali (`BANCA`, `POSTE`, `CASSA`),
senza i quali una contabile di incasso vero non è creabile. Su un database ricostruito da zero
ci sono tutti.

⛔ Il dato si cambia **dal CSV**: un `UPDATE` diretto creerebbe una seconda sorgente di
verità, e le due divergerebbero fra sviluppo e integrazione.

---

### Test

* `db/pgtap/pagamenti/test-centri-riscossione-vincoli-ruolo.sql` — i cinque centri del seed ci
  sono dopo il solo giro delle migrazioni; un solo centro per ruolo, nessuno con entrambi; un
  terzo centro neutro entra, un secondo centro di compensazione o di fondo fattura no, un centro
  con entrambi i ruoli no.

---

### Note di migrazione

* 2026-02-17 — le due righe interne (`FONDI_FATTURA`, `COMPENSAZIONI`) vengono inserite a
  mano: su un database ricostruito da zero la tabella restava vuota, e non funzionavano né i
  fondi fattura né le compensazioni.
* 2026-08-21 — si scopre che due vincoli dichiarati nelle migrazioni non esistevano.
  `uq_centri_riscossione_compensazione` era un `UNIQUE` **totale** sul booleano (il `where:`
  era stato scritto su un `addUniqueConstraint`, che quell'attributo non ha, ed era stato
  ignorato in silenzio): la tabella non poteva contenere più di due righe, e nessuno se ne era
  accorto perché ne aveva esattamente due. Il `CHECK` di esclusività, dichiarato in un changeSet
  del 2026-02-11, non era mai stato eseguito: il blocco SQL era annidato nell'elenco delle
  colonne. Entrambi vengono rimessi in piedi, e nasce l'unicità del centro fondo fattura, mai
  dichiarata prima: fino ad allora chi sceglieva quel centro prendeva il primo per id.
* 2026-08-21 — la sede delle righe diventa il CSV, che porta anche `BANCA`, `POSTE` e `CASSA`.

---

{% include-markdown "signature-core.md" %}
