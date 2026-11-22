### ⭐ Il contatto predefinito: uno per soggetto e contesto

> **Ultimo aggiornamento**: 22 novembre 2026

Ogni contatto ha un **contesto**, e lo dice la riga stessa: con un'istanza è `istanza`, altrimenti con un ruolo
è `ruolo`, altrimenti è `soggetto`. In ogni contesto di un soggetto c'è al più un contatto predefinito
(`is_default`), e la regola la tiene `anagrafiche.trgfn_contatti_set_default_contatto` a ogni nascita e a ogni
modifica di un contatto.

#### La chiave è il soggetto più il contesto

Il predefinito non scende al singolo ruolo né alla singola istanza: un soggetto ha al più **tre** predefiniti,
uno fra i contatti del soggetto, uno fra **tutti** i contatti di ruolo, uno fra **tutti** i contatti di
istanza. Due ruoli dello stesso soggetto (il cliente e il fornitore) condividono quindi un predefinito:
marcare quello del fornitore toglie il segno a quello del cliente.

`default_context` dice in quale contesto il contatto è predefinito, ed è valorizzato **solo** sul predefinito;
sugli altri è vuoto. La scrive il trigger a ogni scrittura, e un valore passato da chi scrive è sostituito.

#### Il primo è predefinito, l'ultimo marcato vince

* Il primo contatto scritto in un contesto che non ha un predefinito **diventa** il predefinito, anche se chi
  scrive non lo chiede.
* Un contatto scritto col segno toglie il segno al predefinito di prima nello stesso contesto.
* Un contatto scritto senza segno accanto a un predefinito resta com'è.

#### Il soggetto punta al suo predefinito

`anagrafiche.soggetti.default_contatto_id` è il predefinito del contesto `soggetto`. Lo scrive lo stesso
trigger, ogni volta che un contatto è o diventa predefinito in quel contesto: anche nella nascita del contatto,
prima che la riga esista, perché la chiave esterna verso il contatto è differita al COMMIT. La colonna si scrive
e non si svuota mai: il trigger non la tocca quando il predefinito perde il segno o esce dal contesto.

#### Che cosa la regola non fa

* **Togliere il segno** all'unico predefinito lascia il contesto senza, fino alla prossima scrittura di un
  contatto di quel contesto (anche lo stesso), che torna predefinito.
* **Cancellare** un contatto non promuove nessuno: il trigger non scatta sulla cancellazione. Cancellare il
  predefinito a cui il soggetto punta è rifiutato al COMMIT dalla chiave esterna, finché un altro contatto non
  diventa predefinito al suo posto.
* **Spostare** il predefinito del soggetto su un ruolo o su un'istanza lo fa predefinito del contesto nuovo; il
  soggetto continua a puntarlo.
