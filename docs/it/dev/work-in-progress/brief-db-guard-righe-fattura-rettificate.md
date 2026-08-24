# Brief DB — una riga di fattura già accreditata non si disfa

> **Cos'è.** Il cantiere che chiude un difetto di integrità sulle **tre porte di
> reset** della fatturazione: `fn_riporta_lotto_a_draft`,
> `fn_annulla_lotto_da_draft`, `fn_elimina_fattura_da_lotto`. Tutte e tre
> cancellavano righe di fattura su cui era già stato registrato un accredito, e
> il risultato non era un rifiuto ma una **violazione di chiave esterna grezza**
> a metà lavoro.
>
> **Origine.** Non una segnalazione: la **baseline pgTAP**, lanciata il
> 2026-08-22 per verificare che il cantiere osservabilità non avesse rotto
> niente. `test-riporta-lotto-a-draft-v1` era rosso, e non per colpa di quel
> cantiere.
>
> **Stato:** ✅ **CHIUSO lato DB il 2026-08-22.** Cinque changeSet applicati,
> due file pgTAP estesi, **21 asserzioni verdi**. Restano due consegne fuori dal
> DB: §6.
>
> **Correlati:**
> [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md) §12.6
> (il modello delle rettifiche) ·
> [brief-db-event-log-scope-e-riga-parlante.md](../work-done/brief-db-event-log-scope-e-riga-parlante.md)
> (il cantiere che ha fatto girare la baseline; **nessun** rapporto tecnico).

---

## 1. Il difetto

```
23503: DELETE su "fatture_righe" viola fk_commesse_attivita_fattura_riga_rettificata
       CONTEXT: vendite.fn_cleanup_fatture_by_ids riga 94
                vendite.fn_riporta_lotto_a_draft riga 79
```

Una violazione di chiave esterna **dentro una funzione che i suoi tre chiamanti
danno per infallibile**.

⭐ **E non è una sorpresa: quella stessa funzione lo aveva previsto per
iscritto**, a proposito di un'altra tabella —

> *«Se un giorno una porta di reset ammettesse un documento numerato, questa
> funzione dovrebbe cancellare anche la coppia in `fatture_rettifiche`: la FK
> non è `ON DELETE CASCADE`, quindi il reset sbatterebbe su una violazione di
> chiave esterna grezza.»*
> *«⚠️ La garanzia sta nelle CONDIZIONI, non nei nomi delle funzioni.»*

È arrivato da **un'altra porta**, e la seconda frase spiega perché. La garanzia
che proteggeva `fatture_rettifiche` era: *quella tabella la scrive un task che
gira **dopo** la numerazione, e i documenti numerati le tre porte li rifiutano*.

⛔ `commesse_attivita.fattura_riga_rettificata_id` non ha quella protezione:
si popola **prima** della numerazione, perché `fn_accredita_riga_reso` àncora
l'accredito alla **coda dei resi** (`vw_resi_da_accreditare`), non al numero.
Misurato: le 8 attività che rettificano puntano tutte a righe di fatture
**EMESSA e non numerate**. Non è spazzatura di test — è merce resa su una
fattura emessa e non ancora numerata, uno stato legittimo e ripetibile.

### 1.1 ⚠️ E il sintomo era un quarto del problema

`vendite.fatture_righe` ha **sei figlie, quattro in `NO ACTION`**:

| Figlia | Vincolo | `ON DELETE` | |
| --- | --- | --- | --- |
| `vendite.commesse_attivita` | `fk_commesse_attivita_fattura_riga_rettificata` | NO ACTION | ⚠️ *quella che è esplosa* |
| `vendite.attivita_fatturabili` | `fk_attivita_fatturabili_fattura_riga_rettificata` | NO ACTION | ⚠️ |
| `vendite.resi_righe_accrediti` | `fk_resi_accrediti_fattura_riga` | NO ACTION | ⚠️ |
| `vendite.fatture_righe` | `fk_fatture_righe_riga_rettificata` | NO ACTION | ⚠️ *auto-riferimento* |
| `vendite.attivita_fatturabili` | `fk_attivita_fatturabili_fattura_riga` | SET NULL | ✅ |
| `vendite.note_fatture` | `fk_fatture_note_riga` | CASCADE | ✅ |

Il test ne ha colpita **una**, perché è quella che la sua fixture aveva. Le altre
tre aspettavano il proprio caso.

⭐ Ma sono **la stessa cosa vista da quattro lati**: *su questa riga di fattura è
già stato registrato un accredito*. Quindi un motivo solo, una domanda sola.

---

## 2. La decisione: rifiutare, non azzerare

L'alternativa era un `SET NULL` sul legame, e avrebbe fatto passare il reset.

⛔ Ma quella colonna non è una decorazione. Il changeSet che l'ha creata
(`20260818-27`, punto 2) la definisce **un secondo tetto all'accredito** —
*«questa riga ha fatturato 10 pezzi, non se ne possono accreditare 11»* — più il
`DatiFattureCollegate` della TD04. Azzerarla toglierebbe quel tetto **proprio
mentre le quantità vengono ri-derivate**.

> **Non si distrugge la prova per far riuscire l'operazione.**

*(Decisione di Tid, 2026-08-22.)* La via d'uscita per l'operatore esiste ed è
esplicita: `vendite.fn_annulla_accredito_riga_reso`, poi il reset.

⚠️ Classe del codice: **`CONFLITTO_STATO`** e non `NON_PERMESSO`. Il diritto c'è;
è la situazione a non consentirlo, e tolto l'accredito l'operazione passa — lo
stesso criterio del gemello `E_DELETE_BLOCKED_FUL`.

---

## 3. Cosa è stato fatto

| # | ChangeSet | Cosa |
| --- | --- | --- |
| 48 | `create-fn-check-fatture-con-rettifiche` | `script.fn_check_fatture_con_rettifiche(bigint[])` → jsonb. La domanda in **un posto solo**, sullo stampo di `fn_check_lotto_fatture_pre_fiscali`: le porte sono tre e la correttezza di ognuna dipende dal fatto che facciano la stessa cosa. Guarda tutte e quattro le figlie `NO ACTION` |
| 49 | `update-fn-check-lotto-riportabile-a-draft-rettifiche` | Motivo 4 |
| 50 | `update-fn-check-lotto-annullabile-rettifiche` | Motivo 4. ⚠️ Qui il caso è **meno probabile** (la porta vuole il DRAFT) ma **più grave**: `ANNULLATA` è terminale, e un annullamento passato per errore toglierebbe anche la via d'uscita |
| 51 | `update-fn-check-fattura-eliminabile-rettifiche` | Motivo 5. ⚠️ **La porta più esposta**: lavora su una fattura sola e la ammette anche a lotto `EMESSA`, cioè proprio lo stato in cui vive un accredito pre-numerazione |
| 52 | `guard-cleanup-fatture-righe-rettificate` | Il **guard fail-loud** dentro `fn_cleanup_fatture_by_ids` |
| — | `codici_errore.csv` · `messaggi_errore.csv` | `E_FATTURE_RIGHE_RETTIFICATE` (`CONFLITTO_STATO`) + messaggio id 981, con `causa` e `soluzione` scritte per chi legge |

### 3.1 ⭐ Perché un guard nella primitiva, oltre alle tre `fn_check_*`

Le tre `fn_check_*` servono all'**interfaccia**: spiegano *prima* del click, ed è
giusto che stiano lì. Ma `fn_cleanup_fatture_by_ids` è **l'unico punto che tutte
e tre attraversano**: il guard lì presidia **la quarta porta, quella che nessuno
ha ancora scritto** — ed è letteralmente ciò che il commento di quella funzione
chiedeva.

⚠️ **Il limite, detto.** La funzione è `SECURITY INVOKER` e legge
`commesse_attivita` sotto row security: un chiamante fuori perimetro potrebbe non
vedere le righe che rettificano e superare il guard. In quel caso però **non si
perde niente in silenzio** — è la chiave esterna a fermare la cancellazione, e si
torna al `23503`, cioè al comportamento di prima, non a un peggioramento.

---

## 4. Il presidio — e il suo secondo punto cieco

`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` **esisteva già ed
è ottimo**: legge il catalogo delle FK invece di tenere un elenco a mano, e
classifica ogni figlia in quattro categorie con la motivazione scritta. Aveva due
punti ciechi, ed è il motivo per cui non ha visto arrivare questo difetto:

1. guardava le figlie di `vendite.fatture`, **non quelle di `fatture_righe`**;
2. ⛔ ed è indicizzato **per tabella, non per vincolo**. `attivita_fatturabili`
   risultava già classificata come figlia di `fatture`: anche se avesse guardato
   il secondo livello, **avrebbe dato verde su una FK non coperta**, perché la
   *tabella* era classificata mentre una delle sue due chiavi non lo era.

➡️ Aggiunto un secondo inventario **indicizzato per nome del vincolo** (test
6-9), col test 9 che presidia l'esistenza del guard: *un blocco senza spiegazione
è un incidente, con la spiegazione è una risposta*. Il primo inventario non è
stato riscritto — è un **debito dichiarato in testata**, non una svista.

### 4.1 ⚠️ E due fixture che ri-elencavano i motivi a mano

Correggere il difetto ha reso rossi **altri due test**, e per il motivo opposto:
le loro fixture sceglievano un soggetto che la funzione ora rifiuta **a ragione**.
Entrambe copiavano a mano *un solo* motivo ostativo (le fatture numerate), e
hanno smesso di bastare quando ne è nato un altro.

➡️ Ora **chiedono**, invece di ri-elencare:

```sql
AND script.fn_check_lotto_riportabile_a_draft(fl.id) = '[]'::jsonb
AND script.fn_check_fatture_con_rettifiche(ARRAY[f.id]) = '[]'::jsonb
```

⚠️ Non rende i test ciechi: ciò che verificano è il **comportamento** della
porta, non l'elenco dei motivi — e il caso del **rifiuto** ha il suo presidio
esplicito (test 11 di `riporta-lotto-a-draft`, test 12 di
`elimina-fattura-da-lotto`), entrambi con `throws_like`/il codice e non con «l'array non
è vuoto», che passerebbe su qualunque altro motivo.

**Consuntivo: 21 asserzioni verdi, zero skip.**

| File | Test |
| --- | ---: |
| `test-cleanup-fattura-copertura-figlie-v1.sql` | 9 *(era 5)* |
| `test-riporta-lotto-a-draft-v1.sql` | 11 *(era 10)* |
| `test-elimina-fattura-da-lotto-v1.sql` | 12 *(era 11)* |

Verificato che nessun altro test tocchi le tre porte: gli altri sei che le
nominano sono verdi.

---

## 5. Cosa NON si è fatto

| Non fatto | Perché |
| --- | --- |
| `SET NULL` sul legame | §2: toglierebbe il secondo tetto dell'accredito nel momento peggiore |
| Riscrivere il primo inventario del presidio per chiave-vincolo | Un presidio che funziona non si tocca per simmetria. Debito dichiarato in testata al file |
| Estendere il guard alle figlie di `vendite.fatture` | Quelle sono già classificate e coperte: il buco era **un livello più giù** |

---

## 6. Residui — fuori dal DB

| # | A carico | Cosa |
| --- | --- | --- |
| **FE-1** | frontend | La `reason_key` **`vendite.lotti.azione_reason.righe_rettificate`** non ha ancora la voce i18n. Finché manca, `fn_available_actions_lotto` espone un motivo che il drawer non sa scrivere — ⚠️ è il debito che le `reason_key` portano per costruzione, non una dimenticanza di questo cantiere |
| **BE-1** | backend | Il nuovo codice `E_FATTURE_RIGHE_RETTIFICATE` va mappato in `error_policies.py` (`CONFLITTO_STATO` → 409). Senza, l'envelope lo tratta come non riconosciuto |
| **DB-1** | team DB | ⚠️ **Debito `%TYPE` dichiarato.** Le quattro funzioni riscritte da questo cantiere hanno la firma a **tipi nudi**, ereditata dal corpo vivo che è stato riprodotto: `p_lotto_id bigint` (su tre `fn_check_*`) e `p_lock_batch_id uuid` (su `fn_cleanup_fatture_by_ids`). Cinque parametri in tutto, tutti id. ⛔ **Non si sanano con un changeSet apposta**: costringerebbe a riprodurre quattro corpi lunghi per cambiare cinque parole, e la riproduzione è proprio il gesto che genera l'errore. Si ancorano **alla prossima volta che una di quelle funzioni si tocca** |

---

## 7. Registro

### 2026-08-22 · Nascita e chiusura DB

Trovato dalla **baseline pgTAP**, non da una segnalazione: è la differenza fra un
difetto che si scopre lanciando i test e uno che si scopre in esercizio, e vale
la pena scriverlo perché è il ritorno dell'investimento di quel registro.

La misura che ha deciso il rimedio — *le 8 attività che rettificano puntano tutte
a fatture non numerate* — è stata fatta **prima** di scegliere fra guard e
`SET NULL`: senza, la scelta ovvia sarebbe stata azzerare il legame, e avrebbe
tolto in silenzio il secondo tetto dell'accredito.

⭐ E la lezione che resta, oltre al caso: **una garanzia che poggia su una
condizione va riscritta quando la condizione cambia.** Qui la condizione era
«esiste solo su documenti numerati», ed è caduta senza che nessun nome di
funzione cambiasse — esattamente come il commento di `fn_cleanup_fatture_by_ids`
aveva avvertito.
