-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- PROPOSTA seed template email INVITO_SHOP (B1 §13.7 admin-driven)
--
-- Da applicare sul branch `dev/db-tid`: aggiungere una riga al file
-- `db/changelog/migrations_v2/80_data/sql/config/email_template.csv`
-- con id successivo all'ultimo presente (es. id=6 se l'ultimo e' 5
-- INVITO_PORTALE). Il changelog `20260329-61-upsert-config-email-
-- template-mctit.yaml` e' gia' `runOnChange: true` + UPSERT, quindi al
-- prossimo `make db-migrate` il template viene caricato automaticamente.
--
-- Variabili disponibili nel template (identiche a INVITO_PORTALE):
--   nome, entita, azienda, link, scadenza_ore, invitato_da,
--   ruolo_applicativo (= "SHOP_CUSTOMER"), is_cross ("0" | "1")
--
-- Il campo `link` punta a `{{FRONTEND_URL}}/attivazione-shop/{{token}}`
-- (branching config veste in InvitoPortaleService._VESTE_CONFIG).
-- ------------------------------------------------------------

-- Alternativa stand-alone (se si preferisce un INSERT diretto invece che
-- via CSV) — idempotente grazie a ON CONFLICT DO UPDATE:

INSERT INTO config.email_template (
    codice,
    unita_organizzativa_id,
    tipo_prestazione_id,
    lingua,
    oggetto,
    corpo_html,
    corpo_testo,
    variabili_disponibili,
    attivo,
    meta,
    user_insert,
    user_update
) VALUES (
    'INVITO_SHOP',
    NULL,
    NULL,
    'it',
    'Benvenuto in {{azienda}} - Attiva il tuo accesso allo shop',
    '<h2>Benvenuto {{nome}}!</h2>'
    '<p>Sei stato invitato ad accedere allo <strong>shop online</strong> '
    'di {{azienda}} come <em>{{entita}}</em>.</p>'
    '<p>Clicca sul link seguente per impostare la tua password e attivare '
    'l''accesso:</p>'
    '<p><a href="{{link}}">Attiva il tuo accesso allo shop</a></p>'
    '<p>Il link scade tra {{scadenza_ore}} ore.</p>'
    '<p>Una volta completata l''attivazione potrai consultare il catalogo, '
    'le tue ricevute e i tuoi ordini shop.</p>'
    '<p>Se non hai richiesto questo invito, ignora questa email.</p>'
    '<p>Cordiali saluti,<br/>{{invitato_da}}</p>',
    'Benvenuto {{nome}}! Sei stato invitato ad accedere allo shop di '
    '{{azienda}} come {{entita}}. Attiva il tuo accesso: {{link}} '
    '(scade tra {{scadenza_ore}} ore).',
    '["nome","entita","azienda","link","scadenza_ore","invitato_da","ruolo_applicativo","is_cross"]'::jsonb,
    true,
    '{}'::jsonb,
    'SEED',
    'SEED'
)
ON CONFLICT (codice, unita_organizzativa_id, tipo_prestazione_id, lingua)
DO UPDATE SET
    oggetto               = EXCLUDED.oggetto,
    corpo_html            = EXCLUDED.corpo_html,
    corpo_testo           = EXCLUDED.corpo_testo,
    variabili_disponibili = EXCLUDED.variabili_disponibili,
    attivo                = EXCLUDED.attivo,
    data_update           = now(),
    user_update           = EXCLUDED.user_update;
