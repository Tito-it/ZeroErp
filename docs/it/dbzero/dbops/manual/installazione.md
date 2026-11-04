## 📘 Documentazione Concettuale – Tabella `dbops.installazione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il default di accensione per ambiente
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la scelta a mano, che in produzione ha un divieto
>
> Approfondimento viste:
>
> * [dbops.vw_ambiente_non_dichiarato](/dbzero/dbops/views/vw_ambiente_non_dichiarato) — il presidio dell'ambiente mancante
>
> Approfondimento funzioni:
>
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore di chi decide: fallisce se l'ambiente manca
> * [script.fn_ambiente_dichiarato](/dbzero/script/funzioni/fn_ambiente_dichiarato) — il lettore di chi descrive: vuoto se l'ambiente manca
> * [dbops.trgfn_installazione_guard_immutabile](/dbzero/dbops/funzioni/trgfn_installazione_guard_immutabile) — l'immutabilità
> * [dbops.fn_dati_di_sviluppo_ammessi_su_valori](/dbzero/dbops/funzioni/fn_dati_di_sviluppo_ammessi_su_valori) — i dati di sviluppo, ammessi solo in sviluppo

---

### 🎯 Scopo Principale

**Questo database è di sviluppo o di produzione?** Una riga sola, con il valore `SVILUPPO` o
`PRODUZIONE`, scritta una volta all'installazione e mai più cambiata.

Prima il modello non lo sapeva: lo smoke notturno, che scrive dati di prova, era «solo sviluppo»
per accorgimenti messi a mano. Ora l'ambiente è un dato, e lo chiedono la sveglia dei processi
automatici (il default di accensione, il divieto di accendere in produzione) e la porta dei dati
di sviluppo.

---

### ⭐ Si sceglie all'installazione, e non cambia più

| Momento | Che cosa succede |
| --- | --- |
| il changeSet crea la tabella | **vuota**: nessun valore di default |
| la fase `post` del provisioning | scrive l'ambiente col parametro `ambiente`; se manca la prima volta, si ferma e chiede di scegliere |
| dopo | il valore non cambia: modifica, cancellazione e svuotamento sono rifiutati, anche allo stesso valore |

Una riga sola per costruzione: l'id è sempre 1 (`chk_installazione_riga_unica`) e l'ambiente è uno
dei due valori (`chk_installazione_ambiente`).

**Perché nessun default.** Un valore scritto da un changeSet troverebbe database già esistenti e
li dichiarerebbe al posto di chi li conosce: un database di sviluppo nato prima della tabella
sarebbe diventato produzione per sempre.

**Perché immutabile, nei due versi.**

* Da sviluppo a produzione no: un database di sviluppo contiene dati nati fuori da ogni regola, e
  nessun controllo può certificarlo pulito. Una produzione nasce dal provisioning, vuota.
* Da produzione a sviluppo no: protegge dall'errore di chi lavora sul database sbagliato. Una copia
  della produzione per fare prove **resta produzione**: lì smoke e dati di prova non partono, ed è
  giusto, perché contiene dati veri.

| Database | Ambiente | Chi lo dichiara |
| --- | --- | --- |
| il database di sviluppo | `SVILUPPO` | a mano, una volta, con la fase `post` |
| lo scratch locale | `SVILUPPO` | lo script della CI locale |
| la CI | `SVILUPPO` | il workflow, nel bootstrap |
| un'installazione nuova | scelto da chi installa | la guida d'installazione |

⚠️ La CI è sempre `SVILUPPO`, e l'ambiente non cambia: le regole che dipendono dall'ambiente sono
scritte **pure sui valori**, così i test provano il ramo `PRODUZIONE` passandolo. I pochi test che
lo costruiscono sul dato spengono il guard dentro la transazione, e il rollback lo rimette.

---

### ⛔ L'applicazione legge, non scrive

Se l'applicazione potesse cambiare l'ambiente, un amministratore potrebbe metterlo a sviluppo,
lanciare un comando riservato allo sviluppo e rimetterlo a posto. Per questo il ruolo applicativo
ha **solo lettura**, dichiarata in tre sedi (un changeSet di `90_end`, il giro dei grant, la
postura della fase `post` del provisioning), che il test tiene allineate.

L'ambiente sta qui e non fra i parametri di configurazione: il loro mirror dal seed lo
riscriverebbe, e l'applicazione lo potrebbe cambiare.

Contro un amministratore del database malintenzionato nessuna regola del database regge: il
proprietario può disattivare il guard. Quella difesa sono i ruoli.

---

### Come si legge

| Chi | Funzione | Se manca l'ambiente |
| --- | --- | --- |
| chi **decide** in base all'ambiente | `script.fn_ambiente_installazione` | errore `E_CONFIG_MANCANTE`, nessun ripiego |
| chi **descrive** (panorami, presidi) | `script.fn_ambiente_dichiarato` | vuoto |

Il presidio [vw_ambiente_non_dichiarato](/dbzero/dbops/views/vw_ambiente_non_dichiarato) ha una
riga finché l'ambiente non è dichiarato.

---

### Codici errore

* `E_AMBIENTE_IMMUTABILE` — modifica, cancellazione o svuotamento della tabella, dal guard
  [trgfn_installazione_guard_immutabile](/dbzero/dbops/funzioni/trgfn_installazione_guard_immutabile).

---

### Test

* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — i due CHECK, la sola lettura per
  l'applicazione, i due trigger del guard; modifica, cancellazione, svuotamento e seconda riga
  rifiutati; l'ambiente non dichiarato costruito: i due lettori, il presidio, la sveglia, il
  panorama.
* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` e
  `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — costruiscono una produzione per provare i
  divieti che ne dipendono.

---

### Note di migrazione

* 2026-10-16 — nasce, vuota, con l'accensione dei processi per ambiente (`brief-db-processi-accensione-per-ambiente`);
  l'immutabilità nei due versi è una decisione di Tid dello stesso giorno.

---

{% include-markdown "signature-core.md" %}
