### 🔑 La chiave unica del cliente manuale

> **Ultimo aggiornamento**: 26 novembre 2026

Fra i clienti delle **istanze fittizie** (quelle della creazione manuale, senza punto di fornitura), due
clienti con lo stesso **soggetto**, lo stesso **servizio** (la utility) e la stessa **azienda**, con periodi
che si sovrappongono, sono la stessa fornitura scritta due volte: il database rifiuta il secondo con
`E_CLIENTE_STESSA_CHIAVE`. È la regola sorella di quella sul punto di fornitura, dove un PDP ha un solo
cliente alla volta (`ex_clienti_no_overlap_stesso_pdp`).

#### ⭐ Perché la chiave è soggetto, servizio e azienda

Ogni creazione manuale fa nascere un'istanza e un billing account nuovi: il vincolo «un cliente per billing
account» (`uq_clienti_billing_account`) non distingue niente, perché ogni doppione ha il suo. Senza un punto
fisico, ciò che resta di una fornitura è chi la riceve, che cosa riceve e chi gliela fornisce. Un altro
servizio o un'altra azienda sono un'altra fornitura, e convivono.

#### Chi occupa la chiave

Una sola lettura dice chi occupa una chiave, `anagrafiche.fn_clienti_stessa_chiave`, e la usano tutti: il
rifiuto, l'avviso che l'applicazione dà mentre si prepara un pre-contrattuale, e la catena delle istanze
fittizie (`anagrafiche.trgfn_clienti_set_parent_istanza`), che collega l'istanza di una fornitura che
riparte a quella del cliente precedente. Con due letture, prima o poi l'avviso e il rifiuto direbbero due
cose diverse.

* Occupa la chiave un cliente che **è o è stato una fornitura**: attivo, in richiesta di sospensione,
  sospeso (fatturabile o no), chiuso in una qualunque delle sue forme (`AT`, `RS`, `SF`, `SC`, `CH`, `CM`,
  `CW`, `CF`), e con un periodo.
* Non la occupano l'annullato (`AN`), che non è mai esistito come fornitura; il pre-contrattuale (`PR`),
  che si sta preparando e si prepara anche accanto a un attivo: il rifiuto arriva quando lo si attiva;
  l'aggregante (`AG`), che non è una fornitura.
* Il periodo va dalla data di attivazione alla data di chiusura, che ne è esclusa: un cliente chiuso
  libera la chiave **dalla sua data di chiusura**, e la fornitura nuova può partire quel giorno.

#### L'azienda è quella dell'installazione

L'azienda di un billing account è quella del suo collegamento in
`anagrafiche.emittenti_fiscali_billing_account`, che ogni billing account ha sempre, e si legge per
l'installazione (`script.fn_get_ba_emittente_sr_id_installazione`). Non dipende da chi sta lavorando: due
operatori di aziende diverse vedono la stessa chiave. L'azienda predefinita decide solo l'azienda dei billing
account che nasceranno: spostarla non cambia la chiave di nessun cliente.

#### Le strade che toccano la chiave

La chiave è fatta di dati di quattro tabelle, e ognuna delle strade che la cambiano ha il suo controllo:

| Che cosa cambia | Chi controlla | Quali clienti |
| --- | --- | --- |
| si scrive un cliente: nascita, stato, date | `anagrafiche.trgfn_clienti_guard_chiave_unica` | quello scritto |
| il collegamento di un billing account nasce o cambia azienda | `anagrafiche.trgfn_efba_guard_clienti_chiave` | quelli del billing account |
| un'istanza diventa fittizia, o smette di esserlo | `anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave` | quelli dell'istanza |

Il controllo di un cliente è uno solo, `anagrafiche.fn_guard_cliente_chiave_unica`; le altre strade gli
passano i clienti da guardare con `anagrafiche.fn_guard_clienti_chiave_unica_di` (i clienti di un billing
account o di un'istanza).

Un collegamento non si cancella e non passa a un altro billing account (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`,
`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`), e lo spostamento della predefinita non tocca l'azienda di nessun billing
account: sono strade che la chiave non deve più guardare.

Le altre parti della chiave non hanno una strada: soggetto, servizio, billing account e istanza di un
cliente non si cambiano dopo la nascita (`E_CLIENTE_FORNITURA_IMMUTABILE`), e soggetto e servizio sono
copie del billing account, a sua volta bloccato su quelle colonne (`E_BA_ISTANZA_IMMUTABILE`).

#### Il controllo scatta al COMMIT

I tre trigger sono constraint trigger **differiti**: il controllo avviene alla conferma dell'operazione, o
prima se chi scrive chiede di anticipare i vincoli differiti. Dentro la stessa operazione si
può chiudere il cliente vecchio e attivare il nuovo in qualunque ordine, e conta solo il risultato.

#### ⭐ Perché le funzioni sono privilegiate

Clienti e billing account sono visibili per azienda. Con i permessi di chi scrive, un cliente fuori dal suo
perimetro sarebbe invisibile, e il controllo direbbe «a posto» proprio nel caso da rifiutare. La lettura e
le due funzioni del controllo girano quindi coi privilegi del proprietario; le trigger function non lo
sono, perché delegano soltanto.

#### Il rifiuto

`E_CLIENTE_STESSA_CHIAVE` porta il codice del billing account del cliente che occupa già la chiave: il
cliente non ha un codice suo. Se i clienti in conflitto sono più d'uno, nomina quello attivato per primo.

#### Il test

`db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` prova la regola su tutte le strade: il
doppione rifiutato col codice del billing account, un'altra utility e un'altra azienda ammesse, il sospeso
che occupa, il pre-contrattuale e l'annullato che non occupano, il pre-contrattuale rifiutato quando si
attiva, la catena nuova che parte dalla chiusura e si collega alla precedente, le strade che cambiano la
chiave (l'azienda di un billing account, un'istanza che diventa fittizia), e lo spostamento della
predefinita che non cambia la chiave di nessuno.
