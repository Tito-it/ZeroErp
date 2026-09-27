# Collaudo in-app · Il consenso al riuso della credenziale

> **Cos'è.** Il copione della validazione a video, da tenere aperto accanto
> all'applicazione e da spuntare. Il *perché* di ogni scelta sta nel
> [brief](../work-done/brief-db-credenziale-per-email.md) (§1 il problema, §2.1
> l'esecuzione DB, §3.1 quella BE/FE). Qui c'è solo **cosa fare, cosa deve
> succedere, e cosa fare se non succede**.
>
> **Cosa è cambiato, in tre righe:**
>
> - creando un operatore con l'email di una persona che **ha già un accesso**,
>   il pannello non mostra più un errore: apre un **dialog** con il nome utente
>   e le vesti di quella credenziale, e chiede se usarla;
> - confermando, la creazione si ripete **dichiarando** quella credenziale:
>   l'operatore entrerà con il nome utente e la password che ha già;
> - il dialog e il rifiuto del database leggono **la stessa funzione**
>   (`script.fn_get_credenziale_per_email`): non possono dire cose diverse.
>
> **Stato**: ✏️ scritto il 2026-09-27, da eseguire.
> **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **super admin** (la gestione operatori è solo sua).
> **Dove**: Amministrazione software → Operatori → *Nuovo*; e Anagrafiche →
> Clienti per preparare i dati.

---

## ⛔ Prima di cominciare

| | Cosa | Perché conta |
| --- | --- | --- |
| **Backend ricaricato** | `kill -HUP` sul master gunicorn | Senza autoreload il backend non ha l'endpoint nuovo né la `ui_action` nuova: il 409 arriverebbe come banner rosso, e il collaudo proverebbe il codice di prima |
| **Frontend aggiornato** | build o dev server con il codice del 27-09 | Il dialog vive nell'`OperatoreDrawer` |
| **Due email nuove** | Per esempio `collaudo-riuso-azienda@example.invalid` e `collaudo-riuso-pf@example.invalid` | Un'email che nessuno usa: il caso si costruisce, non si cerca fra i dati |
| **Un cliente azienda** e **un cliente persona fisica** | Due clienti qualunque di Anagrafiche → Clienti, uno per tipo | L'azienda dà la **domanda** (§2), la persona fisica il **rifiuto** (§4) |

📌 *Fatto datato (2026-09-27, `dbdev`), non motivo:* oggi nessuna credenziale ha
una veste cliente **senza** essere anche operatore (le due vesti cliente sono di
`tid` e `pochi`), quindi il caso non esiste già: si prepara al §1. Le tre
credenziali con email e senza vesti sono residui dei pgTAP (`_pgtap_sync_*`) e
non vanno usate.

La query di controllo, da tenere pronta in `dbshell`:

```sql
-- Cio' che il dialog deve mostrare per quell'email
SELECT * FROM script.fn_get_credenziale_per_email('collaudo-riuso-azienda@example.invalid');
```

⚠️ Le vesti si leggono con i `JOIN` sui soggetti, sotto RLS: in una `dbshell`
senza contesto operatore la riga c'è, ma le vesti possono uscire vuote. Il
confronto che conta è col dialog, aperto da super admin.

---

## 1. Preparare la persona che ha già un accesso

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Anagrafiche → Clienti → il **cliente azienda** → *Invita al portale*, con la prima email | Invito inviato | Se il cliente non è invitabile, sceglierne un altro: qui serve solo una credenziale con una veste cliente |
| **1.2** | Query di controllo con quell'email | Una riga: `auth_user_id`, uno `username`, una veste `CLIENTE_PORTALE` | Zero righe: l'invito non ha creato la credenziale, e il resto del collaudo non ha soggetto |

---

## 2. La domanda: il dialog del riuso

Operatori → *Nuovo*. Soggetto **nuovo** (cognome, nome, un codice fiscale
valido qualunque), nome utente a piacere, **la prima email**, una qualifica.
*Salva*.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | *Salva* | Si apre il dialog **«Questa email ha già un accesso»**. ⛔ Nessun toast rosso | Toast rosso con `E_CREDENZIALE_DA_CONFERMARE`: la `ui_action` non è arrivata (backend non ricaricato, o `error_ui_overrides.py`). Nessuna domanda e operatore creato: il riuso è tornato silenzioso, ⛔ fermati |
| **2.2** | Leggi il dialog | In alto la frase del database, con l'email e il nome utente; sotto il **nome utente** e l'elenco delle vesti: *Cliente (portale) — \<ragione sociale\> (attiva/spenta)* | Vesti vuote con la query che ne mostra una: l'endpoint non decodifica `vesti` (il difetto trovato il 27-09) |
| **2.3** | Confronta con la query di controllo | Stesso nome utente, stesse vesti | Una differenza vuol dire che dialog e rifiuto leggono due cose diverse |
| **2.4** | *Annulla* | Il dialog si chiude, il **form resta** compilato, l'operatore **non** è creato | Form svuotato: la rinuncia fa perdere il lavoro. Operatore creato: la rinuncia non ferma niente, ⛔ |
| **2.5** | *Salva* di nuovo | Il dialog si **riapre** | — |

---

## 3. La conferma

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Nel dialog: **«Usa questo accesso»** | Operatore creato; avviso giallo *«Questa persona ha già un accesso: entrerà con il nome utente «…»…»* con lo username **della credenziale**, non quello scritto nel form | Un nuovo dialog con gli stessi dati: il secondo tentativo non ha portato `riusa_auth_user_id` |
| **3.2** | Apri l'operatore creato | Nome utente = quello della credenziale; accesso **spento** (la veste operatore nasce spenta); il pulsante *Invita* disponibile | — |
| **3.3** | Query di controllo di nuovo | Due vesti: `CLIENTE_PORTALE` e `OPERATORE` (spenta) | — |

---

## 4. Il rifiuto: l'email di un'altra persona

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Invita al portale il **cliente persona fisica**, con la seconda email | Invito inviato | — |
| **4.2** | Operatori → *Nuovo*: soggetto nuovo con un codice fiscale **diverso** da quello del cliente, la seconda email, *Salva* | Messaggio di errore **«L'email … appartiene all'accesso di un'altra persona.»** (`E_CREDENZIALE_ALTRA_PERSONA`, 400). ⛔ **Nessun dialog**: questo non si conferma, si corregge l'email | Il dialog si apre: si potrebbe collegare la veste all'accesso di un'altra persona, ⛔ fermati |

---

## 5. Non-regressione

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **5.1** | Operatore nuovo con un'email **mai usata** | Creato al primo *Salva*, nessun dialog, nessun avviso di riuso | Un dialog qui è una domanda senza credenziale |
| **5.2** | Pagamenti → una distinta → *Abbina* una riga con un importo **oltre** il residuo della rata | La domanda della capienza con il campo motivo; *Forza* registra la riga con la forzatura e il motivo | Il BB del doppio tempo è stato generalizzato il 27-09: se la forzatura non parte più, i pagamenti non passano `forzaturaConMotivo` |
| **5.3** | (F-3, rimasto dal brief di origine) Apri un operatore con la veste già attiva, e `tid` se è l'ultimo super admin attivo | *Invita* spento con il motivo sotto; i toggle «super admin» / «accesso attivo» spenti col motivo sotto | Motivo assente: la chiave i18n del motivo non è risolta (si vedrebbe il codice) |

---

## 6. Cosa questo collaudo non può mostrare, e dove è provato

| Caso | Perché non si vede a video | Dove è provato |
| --- | --- | --- |
| La credenziale **cambia** fra la lettura del dialog e la conferma: il database chiede di nuovo e il dialog si ripropone coi dati nuovi | Servirebbero due sessioni sincronizzate al secondo | `useForzaturaConfermata.spec.js` («un nuovo rifiuto confermabile al secondo tempo ripropone la domanda») e `test_login_credenziale_db` (la dichiarazione di un'altra credenziale rifiutata) |
| Due credenziali con la stessa email → `E_CREDENZIALE_EMAIL_AMBIGUA` | L'indice unico sull'email lo impedisce | pgTAP del P-2 (brief di origine §12) |

---

## 7. Esito

| Esito | Allora |
| --- | --- |
| Tutto verde | Si segna qui la data, e questo documento va in `work-done/` accanto al brief |
| Rosso al §2, §3 o §4 | Difetto su un gesto di sicurezza (chi entra con quale accesso): si apre prima di tutto. La query di controllo dice se il difetto sta a DB o nel pannello |
| Rosso al §5.2 | Regressione dei pagamenti portata dalla generalizzazione del BB: si annota la riga e il comportamento visto |
| Rosso al §5.1 o §5.3 | Regressione: si annota la riga e il comportamento visto |

