## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_lista_definizione_guard_multi_emittente`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la tabella che porta il contrassegno
>
> Approfondimento viste:
>
> * [dbops.vw_liste_multi_emittente_non_certificate](/dbzero/dbops/views/vw_liste_multi_emittente_non_certificate) — le liste che si dicono multi-emittente senza la colonna dell'emittente
>
> Approfondimento funzioni:
>
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — chi scrive è il proprietario della tabella?
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — il bollino «multi-emittente»

---

### 🎯 Scopo Principale

Il trigger impedisce all'applicazione di cambiare il contrassegno `multi_emittente` di una lista: lo
cambia solo il proprietario della tabella, cioè la migrazione che carica il seed del catalogo.

---

### Che cosa dichiara il contrassegno

`multi_emittente` dice che la schermata **sa dire da quale azienda arriva ogni riga**. È una
capacità del software, non una preferenza di chi la usa: si guadagna mostrando l'emittente nelle
righe, e si dichiara nel seed insieme a quel lavoro, o dopo.

Se fosse un interruttore dell'interfaccia, il primo che trova fastidiosa la scelta dell'azienda lo
accenderebbe, e la lista mescolerebbe aziende senza dirlo, col bollino «collaudato» addosso.

---

### Che cosa conta come scrittura

* Alla nascita di una lista, solo un contrassegno acceso: nascere spenta è il default e non dichiara
  niente.
* All'UPDATE, ogni cambio di valore, in un verso o nell'altro: anche spegnerlo è rifiutato
  all'applicazione.

Un UPDATE che non tocca la colonna non fa partire il trigger.

---

### ⭐ Perché un trigger e non un permesso di colonna

Togliere all'applicazione il diritto di scrivere la colonna sarebbe la difesa più forte, ma non
tiene: il giro dei permessi che gira a ogni migrazione riconsegna all'applicazione UPDATE su ogni
tabella dello schema, e la revoca verrebbe restituita. Su dbdev sembrerebbe funzionare fino alla
migrazione successiva; in CI, dove il database si ricostruisce da zero, non funzionerebbe mai.

Il trigger chiede se chi scrive è il proprietario della tabella al building block
[fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella), che lo legge dal
catalogo: nessun nome di ruolo è scritto a mano. Non c'è un interruttore che lo spenga: la condizione
è su chi sei, non c'è niente da accendere.

---

### ⚠️ Che cosa oggi non copre

* **Sorveglia una colonna sola.** È il baratto scelto: una difesa che tiene su una colonna, invece di
  un permesso che sulla carta le copre tutte e in pratica nessuna.
* **Non guarda `perimetro_emittente`**, che porta la lista nello stesso stato: una lista con
  perimetro portata a `false` dall'applicazione si apre senza chiedere l'azienda, come una
  certificata.
* **Non guarda codice né vista.** Cambiare `codice`, `vista_sql` o `schema_dati` di una lista
  certificata sposta la certificazione su un'altra schermata o su un'altra vista, senza che il
  trigger parta.

---

### Codici errore

* `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` — l'applicazione accende il contrassegno alla nascita, o lo
  cambia dopo.

---

### Test

* `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql` — gira come applicazione e lo verifica
  in testa; l'applicazione non accende il contrassegno né crea una lista già accesa.
* `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — sulla lista globale delle
  famiglie di documento a rifiutare è il trigger, prima del CHECK di coerenza.
* `db/pgtap/script/test-fn-is-proprietario-tabella-v1.sql` — l'applicazione che accende o spegne il
  contrassegno è rifiutata, e il trigger passa dal building block.

---

### Note di migrazione

* 2026-08-18 — nasce, insieme alla colonna; il piano di partenza era un permesso di colonna.
* 2026-09-25 — la domanda sul proprietario passa al building block `fn_is_proprietario_tabella`; il
  contesto dell'errore non porta più il proprietario atteso.

---

{% include-markdown "signature-core.md" %}
