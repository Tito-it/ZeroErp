## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_cliente()`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/manual/fn_crea_billing_account) ·
> [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/manual/fn_crea_contatto) ·
> [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo)

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 5)

**Fare di un soggetto un cliente**, in un'operazione sola: il ruolo cliente
(creato se manca), il conto di fatturazione, la riga del cliente, il suo
contatto e i suoi indirizzi.

È la sede unica della creazione: la usano il backend (dal drawer dei
clienti), le fixture dei test e il provisioning dei dati di sviluppo.

### La fornitura

* **Un conto nuovo**: si indica la utility e i campi del conto (almeno la
  categoria). Il conto nasce con
  [fn_crea_billing_account](/dbzero/anagrafiche/manual/fn_crea_billing_account),
  su un'istanza esistente o su una fittizia nuova.
* **Un conto esistente**: si indica il conto, e il cliente è suo. Insieme a un
  conto esistente non si passano i dati di uno nuovo.

### Lo stato in cui nasce

* **Senza stato**, il cliente nasce **attivo**, con la data di attivazione di
  oggi (il giorno dell'azienda).
* **Con uno stato indicato** (per esempio un pre-contratto), le date le dà chi
  chiama, e le pretende il controllo sugli stati del cliente.

⚠️ Il modello non dice ancora **in quali stati** un cliente può nascere: è la
stessa domanda aperta dei documenti (registro D32).

### I campi del cliente

Pagamento (termine e modalità), garanzia, servizio da fatturare, stato e date.
Un campo diverso è rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`). Contatto e
indirizzi seguono le regole dei loro verbi; gli indirizzi obbligatori si
controllano al commit.

### Che cosa non controlla

* **Il permesso**: lo decide il backend.
* Una utility che richiede il punto di prelievo (PDP), senza PDP, la rifiuta
  già il controllo sulla riga del cliente.
* I duplicati (un secondo cliente sullo stesso conto) escono dai vincoli.

### Test

`db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
