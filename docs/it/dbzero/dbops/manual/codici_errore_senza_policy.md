## 📘 Documentazione Concettuale – Tabella `dbops.codici_errore_senza_policy`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — il catalogo dei codici, da cui il backend ricava la classe
> * [config.classi_errore](/dbzero/config/tabelle/classi_errore) — le classi, che decidono il tipo di risposta
> * [dbops.messaggi_errore_codici_legacy](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy) — l'altro registro, da non confondere
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura che questo registro confronta
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — misura e registro

---

### 🎯 Scopo Principale

Il registro del debito del «terzo lato» del presidio sui codici errore: i codici che una funzione
PL/pgSQL viva può nominare e per cui il backend non ha una regola di risposta. È a zero, e resta
come registro in pari.

L'effetto del difetto è preciso e limitato: l'operatore legge comunque la frase giusta, che viene
dal catalogo, ma il **tipo** di risposta HTTP resta appiattito su `400` anche quando la verità è
`404` o `403` — e chi deve reagire (una pagina che riporta indietro, un allarme, un ritentativo)
non può.

---

### ⭐ Perché un registro invece della bonifica subito

Perché il cancello potesse accendersi **subito**, invece che a bonifica finita. Un presidio rosso
dal primo giorno viene disattivato. Registrando il debito noto il cancello nasce verde e diventa
rosso solo su ciò che peggiora: un codice nuovo senza regola. La bonifica dell'esistente è
proceduta a lotti per dominio, partendo dai codici `da_trigger`, che sono sul percorso di una
richiesta.

---

### ⚠️ È un debito, non una whitelist

Deve calare. Il cancello del backend pretende tre versi: nessun codice nuovo senza regola e fuori
registro; nessuna voce che abbia ottenuto la sua regola; nessuna voce che il database non nomina
più. Senza gli ultimi due il registro potrebbe solo allungarsi.

`da_trigger` è l'ordine di lavoro; `data_registrazione` l'orologio del debito.

---

### ⚠️ Due registri che si escludono

| Registro | Che debito misura |
| --- | --- |
| `dbops.codici_errore_senza_policy` | un codice **conforme** alla convenzione ma senza regola di risposta nel backend |
| `dbops.messaggi_errore_codici_legacy` | un codice **fuori convenzione** di nome |

Il database li tiene separati: qui entra solo un codice `E_` conforme, là solo un codice che non lo
è. Un codice non può stare in tutti e due, e non si capisce mai quale debito si sta pagando.

---

### La misura non è il registro

La misura è [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare):
ogni codice che il database può nominare, e cresce a ogni regola nuova e legittima. Il debito è
questo registro. Contare la vista come se fosse il debito è un errore di lettura.

---

### Il cancello sta nel backend

Il confronto è con le regole di risposta del backend, quindi il cancello è un test del backend,
`backend/apps/core/tests/test_error_codes_db_policy_guardrail.py`, che gira in CI sul database
appena costruito: i tre versi qui sopra e la sanità della misura. Nessun pgTAP legge questo
registro.

---

### Note di migrazione

* 2026-08-05 — nasce con `brief-db-be-terzo-lato-presidio-codici`, con una decisione unica: non è
  una regressione, è debito preesistente reso visibile.
* 2026-08-07 — il registro arriva a zero voci.
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
