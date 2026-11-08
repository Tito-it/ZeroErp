## 📘 Documentazione Concettuale – Funzione `pratiche.fn_fork_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni del workflow, con la provenienza
>
> Approfondimento viste:
>
> * [pratiche.vw_definizioni_drift](/dbzero/pratiche/views/vw_definizioni_drift) — il rilevamento della deriva dal preset, che legge la provenienza
>
> Approfondimento funzioni:
>
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — la copia vera e propria
> * [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) — la nuova versione dello stesso scope
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — valida e attiva la bozza
> * [pratiche.fn_risolvi_definizione](/dbzero/pratiche/funzioni/fn_risolvi_definizione) — quale edizione usa una pratica

---

### 🎯 Scopo Principale

`pratiche.fn_fork_definizione` crea l'edizione di un emittente a partire da una definizione di
workflow, di solito il preset: ne copia testata, template e figli in una nuova `BOZZA`, con la
provenienza valorizzata (`preset_origine_id`, `versione_origine`) per il rilevamento della deriva.

È il gesto con cui una società ottiene il **suo** workflow, divergente dal preset condiviso. Ritorna
l'id della nuova bozza.

---

### Le regole

* La funzione è un involucro sottile di `pratiche.fn_copia_definizione`, chiamata in modalità fork.
* **L'emittente è obbligatorio.** Un fork ha per definizione uno scope di emittente; per una nuova
  versione dello stesso scope, preset compreso, si usa `pratiche.fn_nuova_versione_definizione`.
* **Una sola bozza per scope.** Se lo scope di destinazione (tipo di prestazione della sorgente,
  emittente) ha già una bozza aperta, il fork si rifiuta con `E_DEFINIZIONE_BOZZA_ESISTENTE` invece
  della violazione grezza dell'indice di unicità: una sola edizione in lavorazione per scope alla
  volta. L'errore porta come bersaglio le bozze che bloccano: la frase nomina lo scope, e una bozza
  un nome utile non ce l'ha, quindi il bersaglio dà un'informazione che la frase non può dare. È un
  elenco perché, se le bozze fossero più d'una, l'operatore deve vederle tutte.
* Se la definizione sorgente non esiste, il controllo sulla bozza si salta e la copia solleva
  `E_VALORE_MANCANTE`.
* La bozza prodotta si valida e si attiva con `pratiche.fn_pubblica_definizione`; da quel momento le
  pratiche di quell'emittente usano il fork, perché `pratiche.fn_risolvi_definizione` preferisce
  l'edizione dell'emittente al preset.

---

### 🔒 Accesso

La funzione è `SECURITY DEFINER` con un `search_path` fisso: la scrittura interna, attraverso la copia,
gira coi privilegi del proprietario, e il ruolo applicativo la esegue senza permessi di scrittura
diretti sulle definizioni e sui figli. L'esecuzione è concessa al solo ruolo applicativo, non a
`PUBLIC`. Chi può fare un fork lo decide il backend (gesto da super admin). Il `search_path` comprende
gli schemi fidati toccati dalla catena dei trigger (`pratiche`, `script`, `config`, `dbops`).

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — emittente assente o non positivo.
* `E_DEFINIZIONE_BOZZA_ESISTENTE` — lo scope di destinazione ha già una bozza aperta.
* `E_VALORE_MANCANTE` — la definizione sorgente non esiste (dalla copia).

---

### Test

* `pratiche/test-workflow-definizioni-fase2` — fork, copia e provenienza.
* `pratiche/test-definizione-bozza-unica` — il rifiuto quando lo scope ha una bozza aperta.

---

### Note di migrazione

* 2026-07-03 — nasce con le edizioni per emittente; lo stesso giorno diventa `SECURITY DEFINER` e
  l'esecuzione si restringe al ruolo applicativo.
* 2026-07-04 — arriva il controllo «una sola bozza per scope».
* 2026-08-24 — `E_DEFINIZIONE_BOZZA_ESISTENTE` porta le bozze che bloccano come bersaglio
  (brief-db-bersaglio-errore).

---

{% include-markdown "signature-core.md" %}
