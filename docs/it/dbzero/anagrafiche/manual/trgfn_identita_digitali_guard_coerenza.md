## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_coerenza`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti che il guard controlla
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo d'impresa a cui la veste punta
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — i codici dei ruoli attesi
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo del tipo di ruolo, a cui il guard delega
> * [script.fn_guard_soggetto_pf_pura](/dbzero/script/funzioni/fn_guard_soggetto_pf_pura) — il controllo della persona fisica pura
> * [anagrafiche.trgfn_identita_digitali_guard_natura_credenziale](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_natura_credenziale) — il guard che scatta dopo, sulla natura della credenziale
>
> Guide:
>
> * [Architettura multi-face auth](/guide/architettura-multi-face-auth) — le porte del software e le loro vesti
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_identita_digitali_guard_coerenza` impedisce che una veste stia su un ruolo d'impresa che non è
il suo: l'operatore su una risorsa umana o su un processo, il portale dei clienti e lo shop su un cliente, il
portale dei fornitori su un fornitore.

---

### Quale ruolo pretende ogni veste

| Tipo di veste | Ruolo atteso | In più |
| --- | --- | --- |
| `OPERATORE`, `tecnica = false` | `RIS_UMANA` | il soggetto è una persona fisica pura: codice fiscale sì, partita IVA no |
| `OPERATORE`, `tecnica = true` | `PROC_AUTO` | nessuno: un processo non ha codice fiscale |
| `CLIENTE_PORTALE`, `SHOP_CUSTOMER` | `CL` | — |
| `FORNITORE_PORTALE` | `FO` | — |
| `API_CLIENT` | nessuno | il guard esce subito |
| `DISABILITATO` | rifiutato | non è più un tipo di veste |

Il portale dei clienti e lo shop pretendono lo stesso ruolo: la differenza fra i due sta nella porta e nel
profilo, non nell'anagrafica. Un tipo di veste aggiunto all'enum senza una riga qui viene rifiutato: il guard non
apre per omissione.

---

### Scatta a ogni scrittura, anche sulla veste spenta

Il guard scatta prima di ogni inserimento e di ogni modifica della veste, qualunque colonna cambi, e controlla la
veste spenta come quella accesa: una veste che si sposta su un ruolo sbagliato si rifiuta anche se è spenta.

Fra i guard della veste è il primo: un tipo ritirato si ferma qui, prima che il guard sulla natura della
credenziale se ne chieda la natura, e prima del CHECK `chk_identita_digitali_ruolo_non_ritirato`, che dice la
stessa cosa alla tabella.

---

### ⛔ Il flag `tecnica` è un cancello, non una comodità

Per l'operatore il guard si sdoppia sul flag `tecnica`, in due mondi disgiunti: la persona vuole un ruolo
`RIS_UMANA` e una persona fisica pura, il processo vuole il ruolo dedicato `PROC_AUTO`. Il flag non apre il
controllo, scambia un requisito chiuso con un altro: marcare tecnica la veste di una persona non passa, perché il
ruolo di una persona è `RIS_UMANA`, e un ruolo `PROC_AUTO` non riceve una veste di persona.

Serve perché ogni regola di visibilità per azienda pretende una veste `OPERATORE`: senza lo sdoppiamento un
processo automatico non potrebbe avere un perimetro.

---

### ⚠️ Che cosa oggi non copre

* **Il flag `tecnica` fuori dall'operatore.** Il guard lo legge solo per `OPERATORE`: una veste del portale o dello
  shop con `tecnica = true` passa, e per il guard sulla natura della credenziale diventa una veste di macchina.
* **Il ruolo che cambia tipo.** Il guard scatta sulla veste, non su `soggetti_ruoli`: un ruolo a cui si cambia
  `tipo_ruolo_id` lascia le sue vesti su un tipo che non è più il loro, finché la veste non si riscrive.

---

### Codici errore

* `E_RUOLO_APPLICATIVO_RITIRATO` — la veste è `DISABILITATO`.
* `E_SOGGETTI_RUOLI` — il ruolo non esiste o non è del tipo atteso.
* `E_AUTH_USER_SOGGETTO_CON_PIVA`, `E_AUTH_USER_SOGGETTO_SENZA_CF` — la veste dell'operatore umano su un soggetto che
  non è una persona fisica pura (da `script.fn_guard_soggetto_pf_pura`).
* `E_COD_INT_RUOLO` — il codice del ruolo atteso manca in `config.tipi_ruoli`: un difetto di configurazione.
* `E_RUOLO_APPLICATIVO_NON_GESTITO` — un tipo di veste che il guard non conosce.

---

### Test

* `db/pgtap/anagrafiche/test-identita-digitali-guard-coerenza.sql` — ogni tipo di veste sul ruolo giusto e su quello
  sbagliato. È **rosso** in baseline, e la sua fixture non soddisfa un vincolo differito.
* `db/pgtap/anagrafiche/test-veste-operatore-spenta-v1.sql` — `DISABILITATO` rifiutato in inserimento e in modifica,
  e la veste spenta spostata su un ruolo sbagliato rifiutata.
* `db/pgtap/anagrafiche/test-identita-tecnica.sql` — il flag `tecnica` e il ruolo `PROC_AUTO`.

Nessun test prova il rifiuto di un tipo di veste non gestito.

---

### Note di migrazione

* 2026-04 — nasce come gemello generale del controllo sul ponte degli operatori, che vincolava la sola persona
  fisica; condivide quel controllo con `script.fn_guard_soggetto_pf_pura`.
* 2026-09-04 — il ramo dell'operatore si sdoppia sul flag `tecnica`.
* 2026-10-02 — `DISABILITATO` si rifiuta. Fino a quel giorno il guard usciva in anticipo su quel tipo, e la veste
  spenta dell'operatore, che lo portava, non veniva controllata.

---

{% include-markdown "signature-core.md" %}
