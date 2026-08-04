# Brief BE → DB — seed round 2: i 28 codici che il check ha fatto emergere

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Riferimento:** vostra risposta in
[brief-db-seed-messaggi-errore-mancanti.md](../work-done/brief-db-seed-messaggi-errore-mancanti.md) §9.6
(«Palla al BE — codici che nessun catalogo può indovinare»), passo 5 della
lavorazione §9.8.

**In una riga:** il check anti-ricaduta lato BE è scritto e verde, e nel farlo ha
fatto emergere **28 codici** che il backend fa arrivare al log senza che nessuno
dei due registri li conosca. Sono dichiarati; ora servono a catalogo.

---

## 1. Il check c'è, ed è costruito come avete chiesto

[`apps/core/tests/test_error_codes_declared_guardrail.py`](../../../../backend/apps/core/tests/test_error_codes_declared_guardrail.py)
— analisi AST, nessun DB, gira in CI.

Confronta i **punti di chiamata** (`code=` / `error_code=`, letterali **e**
costanti di modulo risolte) con le dichiarazioni di `error_policies.py`. Avevate
ragione sul perché: il confronto `error_policies.py` ↔ catalogo avrebbe dato
verde proprio su `E_PIPELINE_DRIVER_MAX_ITER`, che è il caso che vi ha fatto
scrivere il §9.6. Ora quel codice è dichiarato e il guardrail lo presidia.

Sulla vostra domanda «solo i nuovi o tutti»: **tutti**, come dicevate. L'allowlist
esiste ma è **vuota**, e un test separato impedisce che diventi una discarica
(ogni voce esige una motivazione scritta).

Resta a voi il gemello simmetrico lato DB (codici sollevati dalle funzioni vive
contro `messaggi_errore.csv`): i due registri si sfilano per vie diverse.

## 2. Cosa ha trovato il primo giro — 28 codici, tre categorie

| Categoria | Quanti | Esempio |
| --- | --- | --- |
| Codici di dominio legittimi, mai dichiarati | 24 | `E_PRATICA_INSERT`, `E_FATTURAZIONE_GIRO_PAYLOAD` |
| Un **generico** usato per entità diverse | 4 call-site | `E_NOT_FOUND` su note, allegati e competenze flusso |
| Un codice **del catalogo DB** usato dal BE senza policy | 2 call-site | `E_VALIDAZIONE` in `views_indirizzi_ruolo` |

Le ultime due categorie le abbiamo **corrette al punto di chiamata**, non
dichiarate: un 404 che non dice *cosa* manca non è diagnosticabile a valle, e
`E_VALIDAZIONE` è vostro (ha causa e soluzione scritte da voi ieri) — il BE ora
usa `E_ANAG_VALIDAZIONE`, che già esisteva. Da qui i due codici nuovi
`E_ALLEGATO_NOT_FOUND` e `E_COMPETENZA_NOT_FOUND`.

`E_OFFERTA_XXX`, che segnalavate come probabile segnaposto: **non è un codice**.
È il testo di un commento in `offerte_service.py` che documenta la convenzione
`RAISE EXCEPTION USING MESSAGE='E_OFFERTA_XXX'`. Nessun call-site lo usa — l'ha
raccolto il grep testuale, l'AST no.

## 3. Cosa chiediamo: seed dei 28 in `config.messaggi_errore`, lingua `it`

Stessa forma del round 1: il testo è il `user_message` che `error_policies.py`
già restituisce all'utente. Nessun messaggio inventato, nessun `%s` (sono frasi
finite, §9.7), `causa`/`soluzione` stringa vuota come le altre.

| Codice | HTTP | Messaggio |
| --- | --- | --- |
| `E_ALLEGATO_INSERT` | 500 | Errore durante l'inserimento dell'allegato. |
| `E_ALLEGATO_NOT_FOUND` | 404 | Allegato non trovato. |
| `E_AMM_OPERATORE_NOT_FOUND` | 404 | Operatore non trovato. |
| `E_COMPETENZA_INSERT` | 500 | Errore durante l'inserimento della competenza del flusso. |
| `E_COMPETENZA_NOT_FOUND` | 404 | Competenza del flusso non trovata. |
| `E_EMAIL_ADMIN` | 400 | Operazione sulla configurazione email non riuscita. |
| `E_EMAIL_OP` | 400 | Operazione email non riuscita. |
| `E_EMITTENTE_ATTIVO_NON_VALIDO` | 403 | Emittente non selezionabile: inesistente, disattivato o fuori dal tuo perimetro. |
| `E_EMITTENTE_ATTIVO_TOKEN` | 400 | Refresh token richiesto per applicare il cambio di emittente. |
| `E_EMITTENTE_NON_RISOLTO` | 500 | Emittente fiscale non risolvibile per il documento. |
| `E_FATTURAZIONE_GIRO_NESSUN_LOTTO` | 422 | Nessun lotto da fatturare nel perimetro indicato. |
| `E_FATTURAZIONE_GIRO_PAYLOAD` | 400 | Parametri del giro di fatturazione non validi. |
| `E_FATTURAZIONE_NUMERA_PAYLOAD` | 400 | Parametri della numerazione non validi. |
| `E_FLUSSO_ID_INVALIDO` | 400 | Flusso non valido. |
| `E_FLUSSO_ID_OBBLIGATORIO` | 400 | Flusso obbligatorio. |
| `E_FLUSSO_INSERT` | 500 | Errore durante l'inserimento del flusso. |
| `E_FLUSSO_PRESA_IN_CARICO` | 500 | Errore durante la presa in carico del flusso. |
| `E_GENERAZIONE_PRATICA` | 500 | Errore durante la generazione della pratica dal flusso. |
| `E_GIORNALE_QUERY` | 500 | Errore durante la lettura del giornale. |
| `E_HANDLER_NON_REGISTRATO` | 500 | Handler di flusso non registrato: configurazione incompleta. |
| `E_NOTA_INSERT` | 500 | Errore durante l'inserimento della nota. |
| `E_PIPELINE_DRIVER_MAX_ITER` | 500 | Pipeline interrotta: superato il numero massimo di iterazioni. |
| `E_PRATICA_ID_INVALIDO` | 400 | Pratica non valida. |
| `E_PRATICA_ID_OBBLIGATORIO` | 400 | Pratica obbligatoria. |
| `E_PRATICA_INSERT` | 500 | Errore durante l'inserimento della pratica. |
| `E_PRATICA_QUERY` | 500 | Errore durante la lettura delle pratiche. |
| `E_PRATICA_SORGENTE_TIPO_INVALIDO` | 400 | Codice sorgente non presente in configurazione. |
| `E_SOSPENSIONE_INSERT` | 500 | Errore durante l'inserimento della sospensione. |

La colonna HTTP è lì per informazione (vive in `error_policies.py`, resta
nostra, §9.7): serve a voi solo per capire la natura della riga.

⚠️ **Due note su cosa NON è pulito, e lo sappiamo.**

1. `E_EMAIL_OP` e `E_EMAIL_ADMIN` sono **codici-modulo**: la stessa etichetta
   copre validazione, not-found e accesso negato. Andrebbero spacchettati per
   verbo, ma cambiarli ora significa cambiare lo status HTTP di endpoint già in
   uso — debito annotato nel codice, non risolto qui.
2. I due `E_EMITTENTE_ATTIVO_*` appartengono al cantiere impersonazione di scope
   (il vostro `20260804-13..15`), che lato BE non è ancora committato. Li abbiamo
   dichiarati noi perché il guardrail nascesse verde: se quel cantiere cambia
   idea sui nomi, il seed va rifatto per quelle due righe.

## 4. Cosa NON chiediamo

* **Niente `en`**: vale la conclusione del round 1, ora anche per la ragione
  giusta — la cascata l'avete messa in `fn_log_error_only` (`20260803-11`).
* **Niente bonifica** delle righe già degradate: si purgano da sole (§9.5) e da
  ieri il ripiego conserva comunque `context->>'codice_errore_originale'` (§9.9)
  — che, va detto, rende questo seed **meno urgente del primo**: senza, i 28
  sarebbero già oggi diagnosticabili, solo scomodi.
* **Nessun cambio a `error_policies.py` da parte vostra**: resta il registro
  applicativo, come da §9.7.

## 5. Definizione di «fatto»

- [ ] i 28 codici sono in `messaggi_errore.csv` (non solo nella tabella di un DB);
- [ ] il gemello lato DB del check esiste, così i due registri si presidiano a vicenda;
- [ ] controprova su uno dei 28 (`E_PIPELINE_DRIVER_MAX_ITER` è il candidato
      naturale: è il codice che ha motivato il §9.6) — compare in `error_log`
      col proprio nome.
