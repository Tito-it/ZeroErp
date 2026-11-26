## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_provisiona_dati_di_sviluppo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.credenziali_di_prova](/dbzero/dbops/tabelle/credenziali_di_prova) — l'etichetta delle credenziali di prova
> * [dbops.soggetti_di_prova](/dbzero/dbops/tabelle/soggetti_di_prova) — l'etichetta dei soggetti di prova
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti degli utenti di prova
>
> Approfondimento funzioni:
>
> * [dbops.fn_dati_di_sviluppo_ammessi_su_valori](/dbzero/dbops/funzioni/fn_dati_di_sviluppo_ammessi_su_valori) — la regola dell'ambiente
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — l'ambiente dichiarato dell'installazione
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — crea gli operatori di prova
> * [anagrafiche.fn_crea_auth_user](/dbzero/anagrafiche/funzioni/fn_crea_auth_user) — crea le credenziali dei portali di prova
> * [anagrafiche.fn_crea_veste_portale](/dbzero/anagrafiche/funzioni/fn_crea_veste_portale) — crea le vesti dei portali di prova
> * [anagrafiche.fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste) — riaccende le vesti a ogni corsa
> * [dbops.trgfn_etichette_di_prova_guard](/dbzero/dbops/funzioni/trgfn_etichette_di_prova_guard) — un'etichetta di prova non nasce in produzione

---

### 🎯 Scopo Principale

`anagrafiche.fn_provisiona_dati_di_sviluppo` crea, o rimette a posto, gli utenti e i dati di prova di
un'installazione di sviluppo, e restituisce una riga per ognuno. In un'installazione che non è di sviluppo non
parte.

La chiama il comando del backend che prepara gli utenti di sviluppo; dentro il database non la chiama nessuno.

---

### ⛔ Fuori dallo sviluppo non parte

Per prima cosa la funzione legge l'ambiente dichiarato dell'installazione: se non è `SVILUPPO` si ferma con
`E_DATI_DI_SVILUPPO_IN_PRODUZIONE`, e se l'ambiente non è dichiarato con `E_CONFIG_MANCANTE`. È la stessa regola
che impedisce a un'etichetta di prova di nascere in produzione.

---

### Che cosa crea

* due aziende emittenti di prova, `DEVA` e `DEVB`, ciascuna col suo magazzino predefinito;
* i clienti di prova 1, 2 e 3 sull'azienda A e il cliente B sull'azienda B, ciascuno col suo conto di fatturazione
  legato alla sua azienda;
* il fornitore di prova 1;
* due profili di prova su tutte le aree che ci sono: `DEV_LETTURA` (lettura) e `DEV_OPERATIVO` (tutto);
* gli operatori, ciascuno con la sua persona:
  * `dev.smoke`, super admin, senza limiti di azienda;
  * `dev.lettura`, col profilo di lettura;
  * `dev.bloccato`, col profilo di lettura e i contratti di vendita bloccati;
  * `dev.emittente`, col profilo operativo;
  * `dev.multiveste`, col profilo di lettura;

  tutti tranne `dev.smoke` limitati all'azienda A, e tutti con l'azienda A come azienda attiva;
* gli utenti dei portali: `dev.portale1` e `dev.portale2` sui clienti 1 e 2, `dev.fornitore` sul fornitore 1, e
  la veste del portale di `dev.multiveste` sul cliente 3. Un ruolo cliente ha una sola veste del portale accesa:
  per questo `dev.multiveste` ha un cliente suo.

Le aziende, i clienti, il fornitore, le persone degli operatori e le credenziali portano l'**etichetta di prova**
(`dbops.soggetti_di_prova`, `dbops.credenziali_di_prova`); i profili, i magazzini e l'indirizzo di prova no.

---

### ⭐ Si può rilanciare

Una seconda corsa ritrova ogni soggetto e ogni credenziale dalla sua etichetta e lo rimette a posto: i profili
riscritti su tutte le aree che ci sono in quel momento, le vesti accese, i profili legati, le aziende, le eccezioni,
l'azienda attiva, le vesti dei portali che mancano, i magazzini che mancano. Ciò che c'è già non si ricrea.

Un omonimo nato altrove **non si adotta**: se uno username o la sigla di un'azienda dell'elenco esistono già senza
etichetta, la funzione si ferma con `E_RADICE_DI_PROVA_SENZA_ETICHETTA`. L'etichetta la mette solo lei, quando crea:
è l'unico scrittore delle etichette, e per questo gira coi diritti del proprietario, con un percorso di ricerca
fissato.

Gli oggetti li scrive solo attraverso i building block e le madri dei rispettivi domini; suoi sono soltanto le
etichette e la password di una credenziale rimessa a posto. Dove la madre è un verbo che chiede il SUPER_ADMIN
(l'operatore, il profilo, il legame, lo scope), chiama la sua primitiva: il comando del backend la lancia senza un
utente in sessione, e il verbo si fermerebbe.

---

### Le password e il secondo fattore

Le password arrivano già cifrate dal comando, come un oggetto da username a hash. Un utente nuovo senza password
nasce con una password inutilizzabile, e non entra finché non la si dà; uno esistente senza password tiene la sua.
Un argomento che non è un oggetto si rifiuta con `E_SCRIPT_CHIAMATA_NON_VALIDA`.

Il secondo fattore lo configura il comando dopo: la funzione dice solo chi deve averlo (`dev.smoke`).

---

### Il contesto della sessione torna com'era

Per creare le cose che hanno un padrone la funzione imposta da sé l'utente e l'azienda della sessione (vuoti per i
conti di fatturazione, `dev.smoke` dentro la sua azienda per i magazzini), e alla fine li rimette com'erano.

---

### Che cosa restituisce

Una riga per ogni soggetto e ogni credenziale: che cos'è, la chiave dell'elenco, l'identificativo, se è stato creato
o rimesso a posto e, per le credenziali, se deve avere il secondo fattore. Una credenziale con più vesti
(`dev.multiveste`) compare una volta sola.

---

### ⚠️ Che cosa oggi non copre

* **Il super admin non si rimette a posto.** Il profilo SUPER_ADMIN di `dev.smoke` nasce con l'operatore; una corsa
  successiva non lo riaggiunge se nel frattempo è stato tolto.
* **Rimettere a posto è riaccendere, non rendere utilizzabile.** Una corsa riaccende le vesti, ma non tocca le date
  della veste, il rapporto di lavoro dell'operatore né lo stato del soggetto: un utente di prova scaduto o con la
  persona spenta resta senza accesso anche dopo il rilancio.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` | l'installazione non è di sviluppo |
| `E_CONFIG_MANCANTE` | l'ambiente dell'installazione non è dichiarato (da `script.fn_ambiente_installazione`) |
| `E_SCRIPT_CHIAMATA_NON_VALIDA` | le password non sono un oggetto da username a hash |
| `E_RADICE_DI_PROVA_SENZA_ETICHETTA` | uno username o la sigla di un'azienda dell'elenco esistono già senza l'etichetta di prova |

Più quelli dei building block e delle madri che chiama.

---

### Test

* `db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql` (gira da proprietario) — la forma (diritti del
  proprietario, percorso di ricerca fissato); la prima corsa: le radici create o rimesse a posto, le etichette, il
  secondo fattore, il super admin, le vesti accese, profili, aziende, eccezioni, azienda attiva, conti di
  fatturazione, magazzini, il contesto rimesso com'era; la seconda corsa: tutto rimesso a posto senza etichette
  nuove, la password data che si scrive, un'area nuova che entra nel profilo; l'omonimo senza etichetta rifiutato e
  non adottato. Dove lo schema di Django è vuoto (la CI) i casi che creano credenziali si saltano, e resta la forma.
* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — il rifiuto in produzione.
* Nessun test prova l'ambiente non dichiarato, le password che non sono un oggetto, né che il super admin tolto non
  torni al rilancio.

---

### Note di migrazione

* 2026-10-18 — nasce insieme al comando del backend per gli utenti di sviluppo; gli indirizzi dei soggetti di prova
  passano a `fn_crea_indirizzo_soggetto` nel contratto nuovo della madre.

---

{% include-markdown "signature-core.md" %}
