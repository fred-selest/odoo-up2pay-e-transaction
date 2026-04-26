# -*- coding: utf-8 -*-
import hashlib
import hmac
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # Champs de configuration Up2pay
    pbx_site = fields.Char(string='Site ID (PBX_SITE)', help='The site identifier provided by Up2pay')
    pbx_rang = fields.Char(string='Rank (PBX_RANG)', help='The rank identifier provided by Up2pay')
    pbx_identifiant = fields.Char(string='Merchant ID (PBX_IDENTIFIANT)', help='The merchant identifier provided by Up2pay')
    pbx_hmac_key = fields.Char(string='HMAC Key', help='The HMAC key in hexadecimal format provided by Up2pay')
    
    # Champ pour le mode test/production
    test_mode = fields.Boolean(string='Test Mode', default=True, help='Enable test mode for Up2pay payments')
    
    # Champs pour les pages de retour configurables
    pbx_effectue = fields.Char(
        string='URL Page Effectué (PBX_EFFECTUE)',
        default='/payment/process',
        help='URL de redirection après un paiement réussi'
    )
    pbx_refuse = fields.Char(
        string='URL Page Refusé (PBX_REFUSE)',
        default='/payment/process',
        help='URL de redirection après un paiement refusé'
    )
    pbx_annule = fields.Char(
        string='URL Page Annulé (PBX_ANNULE)',
        default='/payment/process',
        help='URL de redirection après une annulation de paiement'
    )
    
    # URL de production personnalisable
    production_url = fields.Char(
        string='Production URL',
        default='https://tpeweb.e-transactions.fr/php/',
        help='URL de production pour Up2pay E-Transactions'
    )

    def _get_up2pay_url(self):
        """Return the Up2pay payment URL based on the environment (test or production)."""
        self.ensure_one()
        # Utilise le champ test_mode pour déterminer l'URL
        if self.test_mode:
            # URL de test
            return 'https://tpeweb.e-transactions.fr/php/'
        else:
            # URL de production (configurable)
            return self.production_url or 'https://tpeweb.e-transactions.fr/php/'

    def _calculate_hmac(self, params):
        """
        Calculate HMAC-SHA512 signature according to Up2pay specifications.
        
        Order of fields: PBX_SITE, PBX_RANG, PBX_IDENTIFIANT, PBX_TOTAL, PBX_DEVISE, 
                        PBX_CMD, PBX_PORTEUR, PBX_RETOUR, PBX_EFFECTUE, PBX_REFUSE, PBX_ANNULE
        Concatenation without separator.
        Key: binary from hex string stored in database.
        Result: uppercase hexadecimal.
        
        :param params: dict containing the parameters to sign
        :return: HMAC signature in uppercase hexadecimal
        """
        self.ensure_one()
        
        # Définir l'ordre exact des champs selon la documentation Up2pay
        field_order = [
            'PBX_SITE',
            'PBX_RANG',
            'PBX_IDENTIFIANT',
            'PBX_TOTAL',
            'PBX_DEVISE',
            'PBX_CMD',
            'PBX_PORTEUR',
            'PBX_RETOUR',
            'PBX_EFFECTUE',
            'PBX_REFUSE',
            'PBX_ANNULE',
        ]
        
        # Construire la chaîne de données dans l'ordre correct
        data_string = ''
        for field in field_order:
            value = params.get(field, '')
            if value is None:
                value = ''
            data_string += str(value)
        
        # Convertir la clé hexadécimale en binaire
        hmac_key_hex = self.pbx_hmac_key or ''
        try:
            hmac_key_binary = bytes.fromhex(hmac_key_hex)
        except ValueError:
            _logger.error("Invalid HMAC key format. Expected hexadecimal string.")
            raise ValidationError(_("Invalid HMAC key format. Please provide a valid hexadecimal key."))
        
        # Calculer HMAC-SHA512
        hmac_signature = hmac.new(
            hmac_key_binary,
            data_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest().upper()
        
        return hmac_signature

    def _get_specific_rendering_values(self, processing_values):
        """
        Prepare the specific rendering values for Up2pay redirection.
        
        :param processing_values: dict with payment processing values
        :return: dict with Up2pay specific parameters
        """
        res = super()._get_specific_rendering_values(processing_values)
        self.ensure_one()
        
        if self.code != 'up2pay':
            return res
        
        # Extraire les informations de paiement
        tx_reference = processing_values.get('tx_reference', '')
        amount = processing_values.get('total_amount', 0.0)
        currency = processing_values.get('currency', {})
        currency_code = currency.get('name', 'EUR')
        partner_name = processing_values.get('partner_name', '')
        
        # Convertir le montant en centimes (plus petite unité de devise)
        # Odoo stocke déjà les montants dans la plus petite unité de devise dans processing_values
        # Mais nous devons nous assurer que c'est un entier
        amount_in_cents = int(round(amount * 100))
        
        # Mapper le code devise vers le code numérique Up2pay (ISO 4217)
        # Support étendu des devises : EUR, USD, GBP, CHF, CAD
        currency_map = {
            'EUR': '978',
            'USD': '840',
            'GBP': '826',
            'CHF': '756',
            'CAD': '124',
        }
        devise_code = currency_map.get(currency_code, '978')  # EUR par défaut
        
        # Définir les champs de retour : montant:M;ref_cmd:R;autorisation:A;erreur:E
        pbx_retour = 'montant:M;ref_cmd:R;autorisation:A;erreur:E'
        
        # Récupérer les URLs de retour configurables
        pbx_effectue = self.pbx_effectue or '/payment/process'
        pbx_refuse = self.pbx_refuse or '/payment/process'
        pbx_annule = self.pbx_annule or '/payment/process'
        
        # Construire le dictionnaire de paramètres
        params = {
            'PBX_SITE': self.pbx_site,
            'PBX_RANG': self.pbx_rang,
            'PBX_IDENTIFIANT': self.pbx_identifiant,
            'PBX_TOTAL': str(amount_in_cents),
            'PBX_DEVISE': devise_code,
            'PBX_CMD': tx_reference,
            'PBX_PORTEUR': partner_name,
            'PBX_RETOUR': pbx_retour,
            'PBX_EFFECTUE': pbx_effectue,
            'PBX_REFUSE': pbx_refuse,
            'PBX_ANNULE': pbx_annule,
        }
        
        # Journalisation détaillée en mode debug (masquer la clé HMAC)
        if self.env.context.get('debug') or self.env['ir.config_parameter'].sudo().get_param('base.debug'):
            debug_params = params.copy()
            # Masquer la clé HMAC si elle était présente (elle ne l'est pas encore ici)
            _logger.debug("Up2pay - Paramètres envoyés avant signature: %s", debug_params)
        
        # Calculer la signature HMAC
        params['PBX_HMAC'] = self._calculate_hmac(params)
        
        # Journalisation de la signature (sans la clé)
        if self.env.context.get('debug') or self.env['ir.config_parameter'].sudo().get_param('base.debug'):
            _logger.debug("Up2pay - Signature HMAC générée: %s", params['PBX_HMAC'])
        
        # Ajouter action_url pour la soumission du formulaire
        res['action_url'] = self._get_up2pay_url()
        res['data'] = params
        
        return res

    def _handle_notification(self, kwargs):
        """
        Handle the notification from Up2pay (IPN or return from customer).
        
        Gestion fine des codes retour :
        - E = 00000 : paiement réussi -> état 'done'
        - E != 00000 : erreur ou refus -> état 'cancel' ou 'error' selon le code
        - Annulation détectée -> état 'cancel'
        
        Vérification de la signature HMAC dans tous les cas (retour client ET IPN).
        
        :param kwargs: dict with notification parameters (GET or POST)
        :return: tuple (transaction, status) where status is 'pending', 'done', or 'cancel'
        """
        self.ensure_one()
        
        if self.code != 'up2pay':
            return super()._handle_notification(kwargs)
        
        # Extraire les paramètres de la requête
        # Up2pay retourne les données dans le format spécifié dans PBX_RETOUR
        # Nous devons analyser les paramètres de réponse
        
        # Obtenir la référence de transaction
        tx_reference = kwargs.get('ref_cmd', kwargs.get('PBX_CMD', ''))
        
        if not tx_reference:
            _logger.warning("Up2pay notification received without transaction reference")
            raise ValidationError(_("Transaction reference not found in notification"))
        
        # Trouver la transaction
        tx_sudo = self.env['payment.transaction'].sudo()._search([('reference', '=', tx_reference)], limit=1)
        if not tx_sudo:
            _logger.warning("Up2pay notification received for unknown transaction: %s", tx_reference)
            raise ValidationError(_("Transaction not found: %s", tx_reference))
        
        tx_sudo = tx_sudo.sudo()
        
        # Vérifier la signature HMAC
        # Reconstruire les paramètres pour la vérification
        # Les champs retournés par Up2pay dans le retour client/IPN
        montant_retour = kwargs.get('montant', '')  # Montant retourné en centimes
        autorisation = kwargs.get('autorisation', '')
        erreur = kwargs.get('erreur', kwargs.get('PBX_ERROR', '00000'))
        
        params_for_verification = {
            'PBX_SITE': kwargs.get('PBX_SITE', ''),
            'PBX_RANG': kwargs.get('PBX_RANG', ''),
            'PBX_IDENTIFIANT': kwargs.get('PBX_IDENTIFIANT', ''),
            'PBX_TOTAL': str(montant_retour),
            'PBX_DEVISE': kwargs.get('PBX_DEVISE', ''),
            'PBX_CMD': tx_reference,
            'PBX_PORTEUR': kwargs.get('PBX_PORTEUR', ''),
            'PBX_RETOUR': 'montant:M;ref_cmd:R;autorisation:A;erreur:E',
            'PBX_EFFECTUE': '',  # Ces champs ne sont pas retournés dans la notification
            'PBX_REFUSE': '',
            'PBX_ANNULE': '',
        }
        
        received_hmac = kwargs.get('PBX_HMAC', kwargs.get('signature', ''))
        
        if received_hmac:
            expected_hmac = self._calculate_hmac(params_for_verification)
            if received_hmac.upper() != expected_hmac:
                _logger.warning(
                    "Up2pay notification HMAC verification failed for transaction %s. "
                    "Received: %s, Expected: %s",
                    tx_reference, received_hmac, expected_hmac
                )
                raise ValidationError(_("Security check failed: invalid HMAC signature"))
            else:
                _logger.info("Up2pay notification HMAC verification successful for transaction %s", tx_reference)
        else:
            _logger.warning("Up2pay notification received without HMAC signature for transaction %s", tx_reference)
            raise ValidationError(_("Security check failed: missing HMAC signature"))
        
        # Journalisation en mode debug
        if self.env.context.get('debug') or self.env['ir.config_parameter'].sudo().get_param('base.debug'):
            _logger.debug("Up2pay - Réception notification: %s", kwargs)
        
        # Traiter le résultat du paiement avec gestion fine des codes retour
        error_code = erreur or '00000'
        
        # Mapper les codes d'erreur Up2pay aux états Odoo
        # Selon la documentation Up2pay :
        # - 00000 : paiement accepté
        # - Autres codes : erreurs, refus, annulations
        if error_code == '00000':
            # Paiement réussi
            state = 'done'
            _logger.info("Up2pay payment successful for transaction %s (authorization: %s)", tx_reference, autorisation)
        elif error_code in ('000A0', '000A1', '000A2'):
            # Codes spécifiques pour annulation utilisateur
            state = 'cancel'
            _logger.info("Up2pay payment cancelled by user for transaction %s with error code %s", tx_reference, error_code)
        else:
            # Paiement refusé ou erreur
            state = 'error' if error_code.startswith('0') else 'cancel'
            _logger.info("Up2pay payment failed for transaction %s with error code %s", tx_reference, error_code)
        
        # Préparer les données de notification
        notification_data = {
            'status': state,
            'authorization': autorisation,
            'error_code': error_code,
            'provider_response': kwargs,
        }
        
        # Appeler le gestionnaire de notification standard
        self._handle_notification_data(tx_sudo, notification_data)
        
        return tx_sudo, state

    def _handle_notification_data(self, tx_sudo, notification_data):
        """
        Process the notification data and update the transaction.
        
        :param tx_sudo: payment.transaction record
        :param notification_data: dict with notification information
        """
        status = notification_data.get('status', 'pending')
        
        if status == 'done':
            tx_sudo._set_done()
        elif status == 'cancel':
            tx_sudo._set_cancel()
        elif status == 'pending':
            tx_sudo._set_pending()
        elif status == 'error':
            # Pour l'état error, on utilise _set_error si disponible, sinon _set_cancel
            if hasattr(tx_sudo, '_set_error'):
                tx_sudo._set_error()
            else:
                tx_sudo._set_cancel()
        
        # Stocker les informations supplémentaires
        if notification_data.get('authorization'):
            tx_sudo.write({
                'provider_reference': notification_data.get('authorization'),
            })
        
        # Journalisation en mode debug
        if self.env.context.get('debug') or self.env['ir.config_parameter'].sudo().get_param('base.debug'):
            _logger.debug("Up2pay - Transaction %s mise à jour avec le statut: %s", tx_sudo.reference, status)
