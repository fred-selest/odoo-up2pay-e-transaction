# -*- coding: utf-8 -*-
{
    'name': 'Up2pay E-Transactions Payment',
    'version': '19.0.1.1.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Intégration du paiement par redirection Up2pay E-Transactions (Crédit Agricole)',
    'description': """
Module de paiement pour Odoo 19 Community intégrant Up2pay E-Transactions
=========================================================================

Fonctionnalités :
-----------------
* Paiement par redirection vers la plateforme Up2pay E-Transactions
* Support des modes Test et Production avec bascule automatique
* Journalisation détaillée en mode debug
* Gestion multi-devises (EUR, USD, GBP, CHF, CAD)
* Pages de retour configurables (effectué, refusé, annulé)
* Gestion fine des codes retour et états de transaction
* Vérification de la signature HMAC pour sécuriser les échanges

Configuration requise :
-----------------------
* Un compte marchand Up2pay E-Transactions
* Une clé HMAC fournie par Up2pay
* Les identifiants : Site, Rang, Identifiant

""",
    'author': 'Odoo Community',
    'website': 'https://github.com/odoo/odoo',
    'license': 'LGPL-3',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
