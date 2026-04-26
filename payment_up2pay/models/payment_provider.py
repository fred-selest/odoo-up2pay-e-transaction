import hashlib
import hmac
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    pbx_site = fields.Char(string='Site ID (PBX_SITE)', help='The site identifier provided by Up2pay')
    pbx_rang = fields.Char(string='Rank (PBX_RANG)', help='The rank identifier provided by Up2pay')
    pbx_identifiant = fields.Char(string='Merchant ID (PBX_IDENTIFIANT)', help='The merchant identifier provided by Up2pay')
    pbx_hmac_key = fields.Char(string='HMAC Key', help='The HMAC key in hexadecimal format provided by Up2pay')

    def _get_up2pay_url(self):
        """Return the Up2pay payment URL based on the environment."""
        self.ensure_one()
        if self.state == 'test':
            return 'https://tpeweb.e-transactions.fr/php/'
        return 'https://tpeweb.e-transactions.fr/php/'

    def _calculate_hmac(self, params):
        """
        Calculate HMAC-SHA512 signature according to Up2pay specifications.
        
        Order of fields: PBX_SITE, PBX_RANG, PBX_IDENTIFIANT, PBX_TOTAL, PBX_DEVISE, 
                        PBX_CMD, PBX_PORTEUR, PBX_RETOUR
        Concatenation without separator.
        Key: binary from hex string stored in database.
        Result: uppercase hexadecimal.
        
        :param params: dict containing the parameters to sign
        :return: HMAC signature in uppercase hexadecimal
        """
        self.ensure_one()
        
        # Define the exact order of fields as per Up2pay documentation
        field_order = [
            'PBX_SITE',
            'PBX_RANG',
            'PBX_IDENTIFIANT',
            'PBX_TOTAL',
            'PBX_DEVISE',
            'PBX_CMD',
            'PBX_PORTEUR',
            'PBX_RETOUR',
        ]
        
        # Build the data string in the correct order
        data_string = ''
        for field in field_order:
            value = params.get(field, '')
            if value is None:
                value = ''
            data_string += str(value)
        
        # Convert hex key to binary
        hmac_key_hex = self.pbx_hmac_key or ''
        try:
            hmac_key_binary = bytes.fromhex(hmac_key_hex)
        except ValueError:
            _logger.error("Invalid HMAC key format. Expected hexadecimal string.")
            raise ValidationError(_("Invalid HMAC key format. Please provide a valid hexadecimal key."))
        
        # Calculate HMAC-SHA512
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
        
        # Extract payment information
        tx_reference = processing_values.get('tx_reference', '')
        amount = processing_values.get('total_amount', 0.0)
        currency = processing_values.get('currency', {})
        currency_code = currency.get('name', 'EUR')
        partner_name = processing_values.get('partner_name', '')
        
        # Convert amount to centimes (smallest currency unit)
        # Odoo stores amounts in the currency's smallest unit already in processing_values
        # But we need to ensure it's an integer
        amount_in_cents = int(round(amount * 100))
        
        # Map currency code to Up2pay numeric code (ISO 4217)
        currency_map = {
            'EUR': '978',
            'USD': '840',
            'GBP': '826',
            'CHF': '756',
            'CAD': '124',
        }
        devise_code = currency_map.get(currency_code, '978')
        
        # Define return fields: montant:M;ref_cmd:R;autorisation:A;erreur:E
        pbx_retour = 'montant:M;ref_cmd:R;autorisation:A;erreur:E'
        
        # Build the parameters dictionary
        params = {
            'PBX_SITE': self.pbx_site,
            'PBX_RANG': self.pbx_rang,
            'PBX_IDENTIFIANT': self.pbx_identifiant,
            'PBX_TOTAL': str(amount_in_cents),
            'PBX_DEVISE': devise_code,
            'PBX_CMD': tx_reference,
            'PBX_PORTEUR': partner_name,
            'PBX_RETOUR': pbx_retour,
            'PBX_EFFECTUE': '',  # Optional: URL for successful payment
            'PBX_REFUSE': '',    # Optional: URL for refused payment
            'PBX_ANNULE': '',    # Optional: URL for cancelled payment
        }
        
        # Calculate HMAC signature
        params['PBX_HMAC'] = self._calculate_hmac(params)
        
        # Add action_url for the form submission
        res['action_url'] = self._get_up2pay_url()
        res['data'] = params
        
        return res

    def _handle_notification(self, kwargs):
        """
        Handle the notification from Up2pay (IPN or return from customer).
        
        :param kwargs: dict with notification parameters (GET or POST)
        :return: tuple (transaction, status) where status is 'pending', 'done', or 'cancel'
        """
        self.ensure_one()
        
        if self.code != 'up2pay':
            return super()._handle_notification(kwargs)
        
        # Extract parameters from the request
        # Up2pay returns data in the format specified in PBX_RETOUR
        # We need to parse the response parameters
        
        # Get the transaction reference
        tx_reference = kwargs.get('ref_cmd', kwargs.get('PBX_CMD', ''))
        
        if not tx_reference:
            _logger.warning("Up2pay notification received without transaction reference")
            raise ValidationError(_("Transaction reference not found in notification"))
        
        # Find the transaction
        tx_sudo = self.env['payment.transaction'].sudo()._search([('reference', '=', tx_reference)], limit=1)
        if not tx_sudo:
            _logger.warning("Up2pay notification received for unknown transaction: %s", tx_reference)
            raise ValidationError(_("Transaction not found: %s", tx_reference))
        
        tx_sudo = tx_sudo.sudo()
        
        # Verify HMAC signature
        # Reconstruct the parameters for verification
        params_for_verification = {
            'PBX_SITE': kwargs.get('PBX_SITE', ''),
            'PBX_RANG': kwargs.get('PBX_RANG', ''),
            'PBX_IDENTIFIANT': kwargs.get('PBX_IDENTIFIANT', ''),
            'PBX_TOTAL': kwargs.get('montant', ''),  # Amount returned in cents
            'PBX_DEVISE': kwargs.get('PBX_DEVISE', ''),
            'PBX_CMD': tx_reference,
            'PBX_PORTEUR': kwargs.get('PBX_PORTEUR', ''),
            'PBX_RETOUR': 'montant:M;ref_cmd:R;autorisation:A;erreur:E',
        }
        
        received_hmac = kwargs.get('PBX_HMAC', kwargs.get('signature', ''))
        
        if received_hmac:
            expected_hmac = self._calculate_hmac(params_for_verification)
            if received_hmac.upper() != expected_hmac:
                _logger.warning("Up2pay notification HMAC verification failed for transaction %s", tx_reference)
                raise ValidationError(_("Security check failed: invalid HMAC signature"))
        
        # Process the payment result
        error_code = kwargs.get('erreur', kwargs.get('PBX_ERROR', '00000'))
        authorization = kwargs.get('autorisation', '')
        
        # Map Up2pay error codes to Odoo states
        # 00000 = success, other codes = failure
        if error_code == '00000':
            # Payment successful
            state = 'done'
            _logger.info("Up2pay payment successful for transaction %s", tx_reference)
        else:
            # Payment failed or cancelled
            state = 'cancel'
            _logger.info("Up2pay payment failed for transaction %s with error code %s", tx_reference, error_code)
        
        # Prepare notification data
        notification_data = {
            'status': state,
            'authorization': authorization,
            'error_code': error_code,
            'provider_response': kwargs,
        }
        
        # Call the standard notification handler
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
        
        # Store additional information
        if notification_data.get('authorization'):
            tx_sudo.write({
                'provider_reference': notification_data.get('authorization'),
            })
