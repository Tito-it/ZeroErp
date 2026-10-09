## 📘 Documentazione Concettuale – Funzione `script.fn_cliente_dal_billing_account`

> 👀 **Vedi anche**
>
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la fonte: ogni billing account sa di quale cliente e di quale utility è
> [anagrafiche.trgfn_clienti_sync_utility_from_ba](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba) · [vendite.trgfn_ordini_normalize](/dbzero/vendite/funzioni/trgfn_ordini_normalize) · [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) — i tre chiamanti
> [vendite.trgfn_resi_guard_cliente_ddt](/dbzero/vendite/funzioni/trgfn_resi_guard_cliente_ddt) — il reso, che le copie le prende dal suo DDT e non da qui

---

### 🎯 Scopo Principale

**Il cliente e la utility di un documento sono quelli del suo billing account.**

Un billing account è *una fornitura* di un cliente: un luogo (l'istanza) e un
servizio (la utility, per esempio gas o energia elettrica), intestati a un
ruolo CLIENTE. Cliente, ordine e DDT portano, oltre al billing account, due
colonne che dicono le stesse cose: il ruolo del cliente e la utility. Sono
**copie**, comode per le liste e i filtri.

Questa funzione è l'unico posto che dice quanto valgono:

* se il chiamante non le scrive (`NULL`), le **mette** il billing account;
* se le scrive **diverse**, è un errore: `E_DOC_CLIENTE_DIVERSO_DA_BA`, con una
  frase che dice quale delle due non torna e di quale billing account si
  parla.

```sql
SELECT f.soggetto_ruolo_id, f.utility_id
  INTO NEW.destinatario_soggetto_ruolo_id, NEW.utility_id
  FROM script.fn_cliente_dal_billing_account(
           NEW.billing_account_id,
           NEW.destinatario_soggetto_ruolo_id,   -- NULL = «non detto»
           NEW.utility_id,                       -- NULL = «non detta»
           'DDT ' || COALESCE(NEW.numero, '#' || NEW.id::text),
           'destinatario_soggetto_ruolo_id',     -- il campo che il backend evidenzia
           NEW.tx_id) f;
```

| Parametro | Cosa |
| --- | --- |
| `p_billing_account_id` | il billing account del documento. `NULL`: il documento non ha cliente (un DDT di trasferimento) e le copie restano come sono |
| `p_soggetto_ruolo_id`, `p_utility_id` | le copie proposte dal chiamante; `NULL` vuol dire «non detta» |
| `p_documento` | come chiamare il documento nella frase d'errore |
| `p_colonna_ruolo` | il nome della colonna del ruolo sul documento (`destinatario_soggetto_ruolo_id` sul DDT), per il campo dell'errore |
| `p_tx_id` | per il log |

---

### ⭐ Da dove nasce: tre copie, tre risposte

Fino al 9 ottobre 2026 la stessa regola era scritta tre volte, e dava tre
risposte diverse allo stesso errore:

| Documento | Cosa copiava | Se il dato era sbagliato |
| --- | --- | --- |
| cliente | solo la utility | `E_CLIENTE_UTILITY_MISMATCH_BA`; il ruolo sbagliato usciva come errore tecnico della chiave esterna |
| ordine | solo la utility | errore tecnico della chiave esterna (23503) |
| DDT | utility e destinatario | errore tecnico della chiave esterna (23503) |

Dal 10 ottobre (brief `brief-db-esecutivi-ba-coppia`, decisione di Tid) la
regola sta qui, e tutti e tre rispondono con la stessa frase. Le chiavi
esterne composte verso il billing account restano: sono la rete sotto, per
chi scrivesse senza passare dai trigger.

---

### 🔀 Il «quando» resta al documento

La funzione dice **cosa** valgono le copie, non **quando** guardarle: questo
dipende dal documento, e lo decide il chiamante.

* **Cliente** e **ordine**: alla nascita, e se qualcuno prova a cambiare una
  delle colonne (ma lì parla prima il blocco di colonna, perché fornitura e
  cliente non cambiano).
* **DDT**: alla nascita, e in bozza quando cambia il billing account. Allora la
  copia che chi scrive non ha toccato arriva qui come `NULL`, e segue il
  billing account nuovo. Fuori bozza il cliente della bolla è bloccato.

Per questo è una funzione e non un trigger: sul DDT le copie si risolvono
**dopo** che il normalize ha ereditato il billing account dall'ordine, e fra
quel trigger e i guard finali non c'è una fascia libera.

---

### ⚠️ Un billing account che non si vede

Il billing account si legge con i permessi di chi scrive, sotto la RLS. Uno
inesistente e uno di un'altra azienda rispondono allo stesso modo: `E_CODICE`
(«il codice … non è stato trovato nella tabella anagrafiche.billing_account»).
Non viene scritto niente di sbagliato in nessuno dei due casi.

---

### 🧪 Test

`db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql`: test 5 (ordine col ruolo di
un altro cliente), 9 (DDT col destinatario di un altro cliente), 10 (in bozza
il billing account si cambia e le copie lo seguono), 31 (ordine con la utility
sbagliata), 32 (cliente col ruolo di un altro soggetto), 33 (billing account
tolto in bozza: la utility se ne va, il destinatario resta).
